"""Opt-in notebook source inspection. Never executes cells or retains outputs."""
import ast
import json
from pathlib import Path


def inspect(path: Path, enabled=False, max_bytes=200000):
    if not enabled:
        return {'status': 'skipped', 'reason': 'notebook_static_disabled', 'cells': []}
    if path.is_symlink() or path.stat().st_size > max_bytes:
        return {'status': 'environment_error', 'reason': 'notebook_size_or_path', 'cells': []}
    return inspect_source(path.read_bytes())


def inspect_source(payload: bytes):
    if len(payload) > 200000:
        return {'status': 'environment_error', 'reason': 'size_limit', 'cells': []}
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeError):
        return {'status': 'environment_error', 'reason': 'invalid_notebook_json', 'cells': []}
    if not isinstance(data, dict) or not isinstance(data.get('cells'), list):
        return {'status': 'environment_error', 'reason': 'invalid_notebook_schema', 'cells': []}
    cells = []
    for i, cell in enumerate(data.get('cells', [])[:100]):
        if not isinstance(cell, dict) or cell.get('cell_type') != 'code':
            continue
        source = cell.get('source', [])
        if not isinstance(source, (str, list)) or (isinstance(source, list) and not all(isinstance(x, str) for x in source)):
            cells.append({'index': i, 'status': 'unresolved', 'reason': 'invalid_source'})
            continue
        source = ''.join(source) if isinstance(source, list) else source
        try:
            tree = ast.parse(source)
            cells.append({'index': i, 'status': 'parsed',
                          'symbols': [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]})
        except SyntaxError:
            cells.append({'index': i, 'status': 'unresolved', 'reason': 'magic_or_syntax'})
    return {'status': 'passed', 'cells': cells, 'execution': 'not_run', 'truncated': len(data['cells']) > 100,
            'reason': 'Notebook automatic execution is optional and not enabled in phase 2'}
