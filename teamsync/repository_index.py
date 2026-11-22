"""Bounded static Git-object index. Never imports or executes target code."""
import ast
import re
import subprocess

from .phase2_config import Policy


def git(root, *args):
    return subprocess.run(['git', '-c', 'core.quotePath=false', *args], cwd=root, check=True,
                          capture_output=True, timeout=30).stdout


def check_sha(sha):
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Full commit SHA required')


def module(path):
    return path.removesuffix('.py').replace('/', '.').removesuffix('.__init__')


def index(root, sha, policy: Policy):
    check_sha(sha)
    files, symbols, calls, unresolved, warnings = [], [], [], [], []
    used = 0
    entries = git(root, 'ls-tree', '-rz', sha).split(b'\0')
    for entry in entries:
        if not entry:
            continue
        meta, rawpath = entry.split(b'\t', 1)
        mode, _kind, oid = meta.split()
        path = rawpath.decode('utf-8', errors='replace')
        if not path.endswith('.py') or mode not in (b'100644', b'100755'):
            continue
        if any(p in path.split('/') for p in ('.venv', 'node_modules', 'dist', 'build')):
            continue
        size = int(git(root, 'cat-file', '-s', oid.decode()))
        if len(files) >= policy.maxFiles or size > policy.maxFileBytes or used + size > policy.maxTotalBytes:
            warnings.append(f'index_limit:{path}')
            continue
        code = git(root, 'cat-file', 'blob', oid.decode()).decode('utf-8', errors='replace')
        used += size
        files.append(path)
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            warnings.append(f'syntax_error:{path}:{exc.lineno}')
            continue
        aliases = {}
        mod = module(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    aliases[alias.asname or alias.name.split('.')[0]] = alias.name
            elif isinstance(node, ast.ImportFrom):
                prefix = node.module or ''
                if node.level:
                    prefix = '.'.join(mod.split('.')[:-node.level] + ([prefix] if prefix else []))
                for alias in node.names:
                    aliases[alias.asname or alias.name] = prefix + '.' + alias.name
        class Visitor(ast.NodeVisitor):
            def __init__(self, mod=mod, path=path, aliases=aliases):
                self.stack = []
                self.mod, self.path, self.aliases = mod, path, aliases

            def visit_FunctionDef(self, node):
                self.symbol(node)

            def visit_AsyncFunctionDef(self, node):
                self.symbol(node)

            def visit_ClassDef(self, node):
                self.symbol(node)

            def symbol(self, node):
                self.stack.append(node.name)
                symbols.append({'name': self.mod + '.' + '.'.join(self.stack), 'file': self.path,
                                'line': node.lineno, 'kind': type(node).__name__})
                self.generic_visit(node)
                self.stack.pop()

            def visit_Call(self, node):
                expr = ast.unparse(node.func)
                parts = expr.split('.')
                target = None
                if isinstance(node.func, ast.Name):
                    target = self.aliases.get(expr, self.mod + '.' + expr)
                elif isinstance(node.func, ast.Attribute) and len(parts) == 2 and parts[0] in self.aliases:
                    target = self.aliases[parts[0]] + '.' + parts[1]
                call = {'caller': self.mod + ('.' + '.'.join(self.stack) if self.stack else ''),
                        'target': target, 'expression': expr, 'file': self.path, 'line': node.lineno}
                calls.append(call)
                self.generic_visit(node)
        Visitor().visit(tree)
    known = {s['name'] for s in symbols}
    resolved = []
    for call in calls:
        if call['target'] in known:
            resolved.append(call)
        else:
            unresolved.append(call)
    return {'revision': sha, 'files': files, 'symbols': symbols, 'calls': resolved,
            'unresolved': unresolved, 'warnings': warnings, 'bytes': used}


def impact(root, base, head, policy: Policy):
    before, after = index(root, base, policy), index(root, head, policy)
    raw = git(root, 'diff', '--name-status', '-z', '-M', base, head).split(b'\0')
    changes = []
    i = 0
    while i < len(raw) and raw[i]:
        status = raw[i].decode(); i += 1
        old = raw[i].decode(); i += 1
        new = old
        if status.startswith(('R', 'C')):
            new = raw[i].decode(); i += 1
        changes.append({'status': status, 'old': old, 'new': new})
    paths = {c['old'] for c in changes} | {c['new'] for c in changes}
    affected = {s['name'] for graph in (before, after) for s in graph['symbols'] if s['file'] in paths}
    edges = before['calls'] + after['calls']
    initial = set(affected)
    for _ in range(len(edges) + 1):
        added = {e['caller'] for e in edges if e['target'] in affected} - affected
        if not added:
            break
        affected.update(added)
    return {'changes': changes, 'changedSymbols': sorted(initial), 'affectedSymbols': sorted(affected),
            'base': before, 'head': after, 'warnings': before['warnings'] + after['warnings'],
            'note': 'Static approximation; dynamic calls and truncated files remain unresolved.'}
