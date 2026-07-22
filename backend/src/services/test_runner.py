"""Run Python (pytest) and Frontend (vitest) suites; persist JSON for the Web UI."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.services.persist import append, load

_STORE = "test_runs"
_ROOT = Path(__file__).resolve().parents[3]  # BedrockKnowledgeBase/
_BACKEND = _ROOT / "backend"
_FRONTEND = _ROOT / "frontend"
_MAX_HISTORY = 40


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collect_pytest(suite_filter: str | None = None) -> dict[str, Any]:
    """Run pytest in-process and collect per-test results."""
    results: list[dict[str, Any]] = []

    class _Plugin:
        def pytest_runtest_logreport(self, report):  # type: ignore[no-untyped-def]
            if report.when != "call" and not (report.when == "setup" and report.failed):
                return
            if report.when == "setup" and report.passed:
                return
            node = str(report.nodeid)
            if suite_filter and suite_filter not in node:
                return
            entry: dict[str, Any] = {
                "id": node,
                "name": node.split("::")[-1] if "::" in node else node,
                "file": node.split("::")[0] if "::" in node else node,
                "status": "passed" if report.passed else ("skipped" if report.skipped else "failed"),
                "duration_ms": int((report.duration or 0) * 1000),
                "suite": "python",
            }
            if report.failed:
                entry["message"] = str(report.longrepr)[:2000]
            results.append(entry)

    import pytest

    start = time.perf_counter()
    code = pytest.main(
        [
            str(_BACKEND / "tests"),
            "-q",
            "--tb=line",
            "-p",
            "no:cacheprovider",
        ],
        plugins=[_Plugin()],
    )
    elapsed = int((time.perf_counter() - start) * 1000)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    return {
        "suite": "python",
        "runner": "pytest",
        "exit_code": int(code),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": len(results),
        "duration_ms": elapsed,
        "tests": results,
    }


def _collect_vitest() -> dict[str, Any]:
    """Run vitest via npm; graceful skip if unavailable (e.g. slim prod image)."""
    pkg = _FRONTEND / "package.json"
    if not pkg.exists():
        return {
            "suite": "frontend",
            "runner": "vitest",
            "exit_code": -1,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "duration_ms": 0,
            "tests": [],
            "error": "frontend package.json not found",
        }

    out_file = _FRONTEND / ".test-results.json"
    if out_file.exists():
        try:
            out_file.unlink()
        except OSError:
            pass

    start = time.perf_counter()
    env = {**os.environ, "CI": "1", "FORCE_COLOR": "0"}
    try:
        proc = subprocess.run(
            ["npm", "run", "test:json"],
            cwd=str(_FRONTEND),
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
            shell=os.name == "nt",
        )
    except FileNotFoundError:
        return {
            "suite": "frontend",
            "runner": "vitest",
            "exit_code": -1,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "duration_ms": 0,
            "tests": [],
            "error": "npm not available",
        }
    except subprocess.TimeoutExpired:
        return {
            "suite": "frontend",
            "runner": "vitest",
            "exit_code": -1,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "duration_ms": 180000,
            "tests": [],
            "error": "vitest timed out",
        }

    elapsed = int((time.perf_counter() - start) * 1000)
    tests: list[dict[str, Any]] = []
    if out_file.exists():
        try:
            payload = json.loads(out_file.read_text(encoding="utf-8"))
            for tfile in payload.get("testResults") or []:
                fpath = tfile.get("name") or tfile.get("assertionResults", [{}])
                file_name = str(tfile.get("name") or "unknown")
                for assertion in tfile.get("assertionResults") or []:
                    status = assertion.get("status") or "failed"
                    mapped = {
                        "passed": "passed",
                        "failed": "failed",
                        "skipped": "skipped",
                        "pending": "skipped",
                        "todo": "skipped",
                    }.get(status, "failed")
                    tests.append(
                        {
                            "id": f"{file_name}::{assertion.get('fullName') or assertion.get('title')}",
                            "name": assertion.get("title") or assertion.get("fullName") or "test",
                            "file": file_name.replace("\\", "/").split("/frontend/")[-1],
                            "status": mapped,
                            "duration_ms": int(assertion.get("duration") or 0),
                            "suite": "frontend",
                            "message": "\n".join(assertion.get("failureMessages") or [])[:2000] or None,
                        }
                    )
        except Exception as exc:
            return {
                "suite": "frontend",
                "runner": "vitest",
                "exit_code": proc.returncode,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "total": 0,
                "duration_ms": elapsed,
                "tests": [],
                "error": f"failed to parse vitest json: {exc}",
                "stderr": (proc.stderr or "")[-1500:],
            }
    else:
        # vitest not installed or script missing
        err = (proc.stderr or proc.stdout or "")[-1500:]
        return {
            "suite": "frontend",
            "runner": "vitest",
            "exit_code": proc.returncode,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
            "duration_ms": elapsed,
            "tests": [],
            "error": err or "vitest json output missing — run npm install in frontend",
        }

    passed = sum(1 for t in tests if t["status"] == "passed")
    failed = sum(1 for t in tests if t["status"] == "failed")
    skipped = sum(1 for t in tests if t["status"] == "skipped")
    return {
        "suite": "frontend",
        "runner": "vitest",
        "exit_code": int(proc.returncode),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": len(tests),
        "duration_ms": elapsed,
        "tests": tests,
    }


def run_tests(suites: list[str] | None = None) -> dict[str, Any]:
    wanted = {s.lower() for s in (suites or ["python", "frontend"])}
    suite_results: list[dict[str, Any]] = []
    if "python" in wanted:
        # Ensure mock mode for safety
        os.environ.setdefault("USE_BEDROCK_MOCK", "true")
        os.environ.setdefault("DYNAMODB_ENDPOINT", "")
        cwd = os.getcwd()
        try:
            os.chdir(_BACKEND)
            if str(_BACKEND) not in sys.path:
                sys.path.insert(0, str(_BACKEND))
            suite_results.append(_collect_pytest())
        finally:
            os.chdir(cwd)
    if "frontend" in wanted:
        suite_results.append(_collect_vitest())

    passed = sum(s.get("passed", 0) for s in suite_results)
    failed = sum(s.get("failed", 0) for s in suite_results)
    skipped = sum(s.get("skipped", 0) for s in suite_results)
    total = sum(s.get("total", 0) for s in suite_results)
    run = {
        "run_id": str(uuid4()),
        "created_at": _now(),
        "status": "passed" if failed == 0 and total > 0 else ("failed" if failed else "empty"),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "duration_ms": sum(s.get("duration_ms", 0) for s in suite_results),
        "suites": suite_results,
    }
    append(_STORE, run)
    return run


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    items = load(_STORE)
    items = sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)
    # trim store
    if len(items) > _MAX_HISTORY:
        from src.services.persist import rewrite

        rewrite(_STORE, items[:_MAX_HISTORY])
    return [
        {
            "run_id": r.get("run_id"),
            "created_at": r.get("created_at"),
            "status": r.get("status"),
            "passed": r.get("passed"),
            "failed": r.get("failed"),
            "skipped": r.get("skipped"),
            "total": r.get("total"),
            "duration_ms": r.get("duration_ms"),
            "suite_names": [s.get("suite") for s in r.get("suites") or []],
        }
        for r in items[:limit]
    ]


def get_run(run_id: str) -> dict[str, Any] | None:
    for r in load(_STORE):
        if r.get("run_id") == run_id:
            return r
    return None


def latest_run() -> dict[str, Any] | None:
    items = list_runs(limit=1)
    if not items:
        return None
    return get_run(str(items[0]["run_id"]))
