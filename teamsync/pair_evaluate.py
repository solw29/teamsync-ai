"""Same immutable LLM draft on both code versions, in disposable CI only."""
import hashlib
import json
import os
from pathlib import Path

from .evaluate import classify
from .run_generated_tests import execute
from .schema import Review


def main():
    payload = Path('artifacts/analysis.json').read_bytes()
    analysis = json.loads(payload)
    result = {"case_id": os.environ['CASE_ID'], "analysis_sha256": hashlib.sha256(payload).hexdigest(),
              "buggy_sha": os.environ['BUGGY_SHA'], "fixed_sha": os.environ['FIXED_SHA'],
              "source": "same_llm_drafts_disposable_ci", "tests": []}
    if analysis.get('review'):
        review = Review.model_validate(analysis['review'])
        buggy = execute(review, 'buggy')
        fixed = execute(review, 'fixed')
        for index, (b, f) in enumerate(zip(buggy, fixed, strict=True)):
            result['tests'].append({"index": index, "target": b.get('target'),
                                    "buggy": b['status'], "fixed": f['status'],
                                    "classification": classify(b['status'], f['status'])})
    Path('artifacts/pair-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
