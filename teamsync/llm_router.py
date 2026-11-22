"""Deterministic eligibility, not a claim that skipped analysis is correct."""
import json

from .phase2_config import Policy


def route(diff, checks, requirements, policy: Policy):
    if policy.llmMode == 'off' or policy.maxLLMCalls == 0:
        return {'call': False, 'reason': 'disabled', 'semanticCoverage': 'not_assessed'}
    if not diff['lines']:
        return {'call': False, 'reason': 'no_analyzable_diff', 'semanticCoverage': 'not_assessed'}
    if any(c.get('reason') in ('tool_missing', 'timeout', 'collection_error') for c in checks):
        return {'call': False, 'reason': 'repair_check_environment_first', 'semanticCoverage': 'not_assessed'}
    if policy.llmMode == 'always':
        return {'call': True, 'reason': 'always_policy', 'semanticCoverage': 'model_review'}
    # Unspecified semantics are unknown; never infer completeness from green checks.
    if not requirements or any(r.status == 'unverifiable' for r in requirements):
        return {'call': True, 'reason': 'semantic_evidence_missing', 'semanticCoverage': 'model_review'}
    if any(r.status == 'violated' for r in requirements):
        return {'call': False, 'reason': 'explicit_failure_already_reported', 'semanticCoverage': 'not_assessed'}
    return {'call': False, 'reason': 'mapped_contracts_passed_only', 'semanticCoverage': 'not_assessed'}


def bounded_input(diff, policy: Policy):
    lines = []
    for line in diff['lines']:
        if len(json.dumps(lines + [line], ensure_ascii=False)) > policy.maxInputChars:
            break
        lines.append(line)
    return {**diff, 'lines': lines, 'truncated': diff.get('truncated', False) or len(lines) < len(diff['lines'])}
