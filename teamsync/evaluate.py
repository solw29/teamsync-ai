"""Offline seed-pair measurements, separate from actual model/PR evaluation."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SEEDS = [
    ("S01", "def safe_divide(a,b): return a/b", "def safe_divide(a,b): return None if b == 0 else a/b", "assert safe_divide(1,0) is None"),
    ("S02", "def parse_age(v): return int(v)", "def parse_age(v): return int(v) if str(v).isdigit() else None", "assert parse_age(-1) is None"),
    ("S03", "def normalize_name(v): return v.strip()", "def normalize_name(v): return v.strip() or None", "assert normalize_name(' ') is None"),
    ("S04", "def discount(p,r): return p*(1-r)", "def discount(p,r): return p*(1-r) if p >= 0 and 0 <= r <= 1 else None", "assert discount(10,2) is None"),
    ("S05", "def get_page(items,p): return items[p-1]", "def get_page(items,p): return items[p-1] if 1 <= p <= len(items) else None", "assert get_page([1],0) is None"),
    ("S06", "def parse_score(v): return float(v) if v else None", "def parse_score(v): return None if v is None else float(v)", "assert parse_score(0) == 0"),
]


def classify(buggy, fixed):
    if (buggy, fixed) == ("failed", "passed"):
        return "detected"
    if (buggy, fixed) == ("passed", "passed"):
        return "missed"
    if (buggy, fixed) == ("failed", "failed"):
        return "manual_review"
    if (buggy, fixed) == ("passed", "failed"):
        return "unstable_or_environment"
    return "environment_error"


def evaluate():
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        for case, buggy, fixed, assertion in SEEDS:
            outcomes = []
            for code in (buggy, fixed):
                path = Path(directory) / "test_seed.py"
                path.write_text(code + "\n\ndef test_contract():\n    " + assertion + "\n")
                result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-c", "/dev/null", str(path)],
                                        check=False, capture_output=True, timeout=20)
                outcomes.append({0: "passed", 1: "failed"}.get(result.returncode, "environment_error"))
            rows.append({"case_id": case, "buggy": outcomes[0], "fixed": outcomes[1],
                         "classification": classify(*outcomes), "source": "handwritten_contract_not_llm"})
    return rows


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
