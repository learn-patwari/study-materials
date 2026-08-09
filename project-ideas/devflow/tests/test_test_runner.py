import pytest
from unittest.mock import patch, MagicMock
from services import test_runner


def _run_with_output(stdout: str, returncode: int = 0):
    mock_result = MagicMock()
    mock_result.stdout = stdout
    mock_result.stderr = ""
    mock_result.returncode = returncode
    with patch("services.test_runner.db") as mock_db, \
         patch("subprocess.run", return_value=mock_result):
        mock_db.get_setting.return_value = "pytest"
        return test_runner.run_tests()


def test_no_command_configured():
    with patch("services.test_runner.db") as mock_db:
        mock_db.get_setting.return_value = ""
        result = test_runner.run_tests()
    assert "error" in result
    assert result["passed"] == 0


def test_parses_passed_count():
    result = _run_with_output("5 passed, 0 failed in 1.23s")
    assert result["passed"] == 5
    assert result["failed"] == 0


def test_parses_failed_count():
    result = _run_with_output("3 passed, 2 failed in 0.5s", returncode=1)
    assert result["passed"] == 3
    assert result["failed"] == 2


def test_parses_pytest_cov_coverage():
    output = (
        "5 passed in 1.0s\n"
        "----------- coverage -----------\n"
        "TOTAL      200    50    75%\n"
    )
    result = _run_with_output(output)
    assert result["coverage_pct"] == 75.0


def test_parses_coverage_py_format():
    output = "5 passed in 1.0s\nTotal coverage: 82%"
    result = _run_with_output(output)
    assert result["coverage_pct"] == 82.0


def test_no_coverage_returns_none():
    result = _run_with_output("5 passed in 1.0s")
    assert result["coverage_pct"] is None


def test_timeout_returns_error():
    import subprocess
    with patch("services.test_runner.db") as mock_db, \
         patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pytest", 300)):
        mock_db.get_setting.return_value = "pytest"
        result = test_runner.run_tests()
    assert "error" in result
    assert "timed out" in result["error"]


def test_extract_int_no_match():
    assert test_runner._extract_int("no numbers here", r"(\d+) passed") == 0


def test_extract_coverage_no_match():
    assert test_runner._extract_coverage("some output without coverage") is None
