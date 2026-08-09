import subprocess
import re
from db import database as db


def run_tests() -> dict:
    cmd = db.get_setting("test_run_command", "")
    if not cmd:
        return {"error": "No test run command configured.", "passed": 0, "failed": 0, "coverage_pct": None}
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        output = result.stdout + result.stderr
        return {
            "output": output,
            "returncode": result.returncode,
            "passed": _extract_int(output, r"(\d+) passed"),
            "failed": _extract_int(output, r"(\d+) failed"),
            "coverage_pct": _extract_coverage(output),
        }
    except subprocess.TimeoutExpired:
        return {"error": "Test run timed out (300s).", "passed": 0, "failed": 0, "coverage_pct": None}
    except Exception as e:
        return {"error": str(e), "passed": 0, "failed": 0, "coverage_pct": None}


def _extract_int(text: str, pattern: str) -> int:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else 0


def _extract_coverage(text: str) -> float | None:
    # pytest-cov: "TOTAL   123   45   63%"
    m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", text)
    if m:
        return float(m.group(1))
    # coverage.py report: "TOTAL ... 78%"
    m = re.search(r"(\d+)%\s*$", text, re.MULTILINE)
    if m:
        return float(m.group(1))
    return None
