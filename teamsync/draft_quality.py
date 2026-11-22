"""Conservative lint for generated drafts; not an isolation boundary."""
import ast

BLOCKED = {'os', 'sys', 'socket', 'subprocess', 'shutil', 'ctypes', 'resource', 'multiprocessing', 'pathlib'}
CALLS = {'exec', 'eval', 'compile', 'open', '__import__', 'getattr', 'setattr', 'delattr', 'globals', 'locals', 'input'}


def check_draft(code: str, target: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ['syntax_error']
    reasons, imports = [], set()
    assertions = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [node.module or ''] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
            if any(m.split('.')[0] in BLOCKED for m in modules):
                reasons.append('disallowed_import')
            if isinstance(node, ast.ImportFrom):
                imports.update(a.name for a in node.names)
        if isinstance(node, ast.Assert):
            assertions += 1
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in CALLS:
            reasons.append('disallowed_call')
        if isinstance(node, ast.Attribute) and node.attr.startswith('__'):
            reasons.append('dunder_access')
    if target.split('.')[-1] not in imports:
        reasons.append('standalone_target_import_missing')
    if not assertions:
        reasons.append('assertion_missing')
    return sorted(set(reasons))


def expectation_conflicts(code: str, target: str, contracts: list[dict]):
    """Reject a contradictory literal expectation for the EXACT same declared input.

    Different inputs or nonliteral predicates remain unverified; never execute
    a contract string, and never claim general semantic equivalence.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    def signature(node):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
            return None
        if not isinstance(node.left, ast.Call):
            return None
        call = node.left
        name = call.func.id if isinstance(call.func, ast.Name) else call.func.attr if isinstance(call.func, ast.Attribute) else ''
        if name != target.split('.')[-1] or not isinstance(node.ops[0], (ast.Eq, ast.Is)):
            return None
        args = ast.dump(ast.Tuple(elts=call.args, ctx=ast.Load())) + repr([(k.arg, ast.dump(k.value)) for k in call.keywords])
        try:
            literal = ast.literal_eval(node.comparators[0])
            for arg in call.args:
                ast.literal_eval(arg)
            for keyword in call.keywords:
                ast.literal_eval(keyword.value)
        except (ValueError, TypeError):
            return None
        if not isinstance(literal, (str, int, float, bool, type(None))):
            return None
        return args, (type(literal).__name__, repr(literal))

    expected = {}
    for contract in contracts:
        if contract.get('symbol', '').split('.')[-1] != target.split('.')[-1]:
            continue
        for assertion in contract.get('assertions', []):
            try:
                statement = ast.parse(assertion).body
            except (ValueError, SyntaxError):
                continue
            if len(statement) == 1 and isinstance(statement[0], ast.Assert):
                pair = signature(statement[0].test)
                if pair:
                    expected[pair[0]] = pair[1]
    conflicts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            pair = signature(node.test)
            if pair and pair[0] in expected and expected[pair[0]] != pair[1]:
                conflicts.append('explicit_literal_expectation_conflict')
    return sorted(set(conflicts))
