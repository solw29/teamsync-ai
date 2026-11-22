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
