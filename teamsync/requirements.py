"""Explicit contract + exact executed-test evidence, never symbol-only satisfaction."""
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .phase2_schema import Evidence, Requirement


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[A-Z][A-Z0-9_-]{1,63}$')
    description: str = Field(min_length=1, max_length=4000)
    symbol: str = Field(min_length=1)
    assertions: list[str] = Field(default_factory=list, max_length=20)
    testIds: list[str] = Field(default_factory=list, max_length=30)


def load_contracts(path: Path):
    if not path.exists():
        return []
    if path.is_symlink() or path.stat().st_size > 100000:
        raise ValueError('Contract input rejected')
    data = json.loads(path.read_text())
    if not isinstance(data, list) or len(data) > 100:
        raise ValueError('Contract count limit')
    contracts = [Contract.model_validate(d) for d in data]
    if len({c.id for c in contracts}) != len(contracts):
        raise ValueError('Duplicate contract ID')
    return contracts


def judge(contracts, graph, checks):
    evidence, results = [], []
    symbols = {s['name']: s for s in graph['symbols']}
    pytest = next((c for c in checks if c['name'] == 'pytest'), {})
    passed, failed = set(pytest.get('passedTests', [])), set(pytest.get('failedTests', []))
    for contract in contracts:
        ids = []
        cid = f'{contract.id}:contract'
        evidence.append(Evidence(id=cid, kind='contract', file='teamsync-requirements.json', line=0,
                                 detail=contract.description))
        ids.append(cid)
        symbol = symbols.get(contract.symbol)
        if symbol:
            sid = f'{contract.id}:symbol'
            evidence.append(Evidence(id=sid, kind='symbol', file=symbol['file'], line=symbol['line'], detail=contract.symbol))
            ids.append(sid)
        expected = set(contract.testIds)
        matched = expected & (passed | failed)
        for name in sorted(matched):
            eid = f'{contract.id}:test:{name}'
            evidence.append(Evidence(id=eid, kind='test', file=name.split('::')[0], line=0,
                                     detail=f'{name}: {"failed" if name in failed else "passed"}'))
            ids.append(eid)
        connected = set()
        for name in expected:
            klass, test = name.split('::', 1) if '::' in name else ('', '')
            start = klass + '.' + test.split('[')[0]
            reachable = {start}
            for _ in range(len(graph.get('calls', [])) + 1):
                more = {c['target'] for c in graph.get('calls', []) if c['caller'] in reachable} - reachable
                if not more:
                    break
                reachable.update(more)
            if contract.symbol in reachable:
                connected.add(name)
                evidence.append(Evidence(id=f'{contract.id}:call:{name}', kind='call', file=klass, line=0,
                                         detail=f'{start} -> {contract.symbol} (static call path)'))
                ids.append(f'{contract.id}:call:{name}')
        status, reason = 'unverifiable', 'Symbol or explicit executed contract tests unavailable'
        if symbol and expected and expected <= connected and not graph['warnings']:
            if expected & failed:
                status, reason = 'violated', 'Explicit mapped contract test failed'
            elif expected <= passed:
                status, reason = 'satisfied', 'Symbol, static call paths and all explicit mapped contract tests passed; limited to this contract'
        results.append(Requirement(id=contract.id, description=contract.description, status=status,
                                   evidenceIds=ids, reason=reason))
    return results, evidence
