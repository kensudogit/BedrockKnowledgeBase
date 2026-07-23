"""Python (pytest) と Frontend (vitest) を実行し、Web UI 用 JSON を永続化。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.services.persist import append, load, rewrite

_STORE = "test_runs"
_MAX_HISTORY = 40
_RUN_LOCK = threading.Lock()
_ACTIVE: set[str] = set()


def _resolve_layout() -> tuple[Path, Path]:
    """
    ローカルと Docker の両レイアウトに対応:
      - ローカル: <repo>/backend/... + <repo>/frontend
      - Docker:   /app/src/services/... + /app/frontend
    """
    here = Path(__file__).resolve()
    app_or_backend = here.parents[2]  # .../backend or /app
    sibling_frontend = app_or_backend.parent / "frontend"
    nested_frontend = app_or_backend / "frontend"

    if nested_frontend.is_dir() and (nested_frontend / "package.json").exists():
        return app_or_backend, nested_frontend
    if sibling_frontend.is_dir() and (sibling_frontend / "package.json").exists():
        return app_or_backend, sibling_frontend
    # 部分イメージ向けフォールバック
    if (app_or_backend / "tests").is_dir():
        return app_or_backend, nested_frontend
    return app_or_backend, sibling_frontend


_BACKEND, _FRONTEND = _resolve_layout()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_suite(suite: str, runner: str, error: str, duration_ms: int = 0) -> dict[str, Any]:
    return {
        "suite": suite,
        "runner": runner,
        "exit_code": -1,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0,
        "duration_ms": duration_ms,
        "tests": [],
        "error": error,
    }


def _collect_pytest() -> dict[str, Any]:
    """pytest を同一プロセスで実行し、テスト単位の結果を収集する。"""
    tests_dir = _BACKEND / "tests"
    if not tests_dir.is_dir():
        return _empty_suite(
            "python",
            "pytest",
            f"tests directory not found: {tests_dir} (backend={_BACKEND})",
        )

    try:
        import pytest
    except ImportError:
        return _empty_suite(
            "python",
            "pytest",
            "pytest is not installed in this image — add pytest to requirements-railway.txt",
        )

    results: list[dict[str, Any]] = []

    class _Plugin:
        def pytest_runtest_logreport(self, report):  # type: ignore[no-untyped-def]
            if report.when != "call" and not (report.when == "setup" and report.failed):
                return
            if report.when == "setup" and report.passed:
                return
            node = str(report.nodeid)
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

    start = time.perf_counter()
    try:
        code = pytest.main(
            [
                str(tests_dir),
                "-q",
                "--tb=line",
                "-p",
                "no:cacheprovider",
            ],
            plugins=[_Plugin()],
        )
    except Exception as exc:
        return _empty_suite(
            "python",
            "pytest",
            f"pytest crashed: {exc}\n{traceback.format_exc()[-1500:]}",
            duration_ms=int((time.perf_counter() - start) * 1000),
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
        "backend_root": str(_BACKEND),
        "tests_dir": str(tests_dir),
    }


def _collect_vitest() -> dict[str, Any]:
    """npm 経由で vitest を実行する（未インストール時は graceful skip）。"""
    pkg = _FRONTEND / "package.json"
    if not pkg.exists():
        return _empty_suite(
            "frontend",
            "vitest",
            f"frontend package.json not found at {_FRONTEND} (resolved backend={_BACKEND})",
        )

    out_file = _FRONTEND / ".test-results.json"
    if out_file.exists():
        try:
            out_file.unlink()
        except OSError:
            pass

    start = time.perf_counter()
    # 本番 React ビルドには React.act() が無いため NODE_ENV=test 必須
    env = {**os.environ, "CI": "1", "FORCE_COLOR": "0", "NODE_ENV": "test"}
    npm_cmd = ["npm", "run", "test:json"]
    try:
        proc = subprocess.run(
            npm_cmd,
            cwd=str(_FRONTEND),
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
            shell=os.name == "nt",
        )
    except FileNotFoundError:
        return _empty_suite("frontend", "vitest", "npm not available in this container")
    except subprocess.TimeoutExpired:
        return _empty_suite("frontend", "vitest", "vitest timed out", duration_ms=180000)

    elapsed = int((time.perf_counter() - start) * 1000)
    tests: list[dict[str, Any]] = []
    if out_file.exists():
        try:
            payload = json.loads(out_file.read_text(encoding="utf-8"))
            for tfile in payload.get("testResults") or []:
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
                **_empty_suite(
                    "frontend",
                    "vitest",
                    f"failed to parse vitest json: {exc}",
                    duration_ms=elapsed,
                ),
                "stderr": (proc.stderr or "")[-1500:],
                "exit_code": proc.returncode,
            }
    else:
        err = (proc.stderr or proc.stdout or "")[-1500:]
        return {
            **_empty_suite(
                "frontend",
                "vitest",
                err or "vitest json output missing — ensure vitest is installed (npm ci)",
                duration_ms=elapsed,
            ),
            "exit_code": proc.returncode,
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
        "frontend_root": str(_FRONTEND),
    }


def _upsert_run(run: dict[str, Any]) -> None:
    items = [r for r in load(_STORE) if r.get("run_id") != run.get("run_id")]
    items.append(run)
    items = sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)[:_MAX_HISTORY]
    rewrite(_STORE, items)


def _parse_ts(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def reap_stale_runs(max_age_sec: int = 120) -> int:
    """status=running のまま放置された実行をタイムアウトとしてマークする。"""
    now = time.time()
    items = load(_STORE)
    changed = 0
    out: list[dict[str, Any]] = []
    for r in items:
        if r.get("status") == "running" and now - _parse_ts(r.get("created_at")) > max_age_sec:
            r = {
                **r,
                "status": "error",
                "finished_at": _now(),
                "error": f"stale running run timed out after {max_age_sec}s",
                "message": "実行が中断されたかタイムアウトしました。再度「全スイート実行」を押してください。",
            }
            changed += 1
            with _RUN_LOCK:
                _ACTIVE.discard(str(r.get("run_id") or ""))
        out.append(r)
    if changed:
        rewrite(_STORE, out)
    return changed


def _progress(run_id: str | None, message: str, suites: list[dict[str, Any]] | None = None) -> None:
    if not run_id:
        return
    prev = get_run(run_id) or {"run_id": run_id, "created_at": _now()}
    _upsert_run(
        {
            **prev,
            "status": "running",
            "message": message,
            "suites": suites if suites is not None else prev.get("suites") or [],
            "updated_at": _now(),
        }
    )


def run_tests(
    suites: list[str] | None = None,
    *,
    run_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """指定スイートを同期実行し、集計結果を返す（必要なら永続化）。"""
    wanted = {s.lower() for s in (suites or ["python", "frontend"])}
    global _BACKEND, _FRONTEND
    _BACKEND, _FRONTEND = _resolve_layout()
    created_at = (get_run(run_id) or {}).get("created_at") if run_id else None
    created_at = created_at or _now()

    suite_results: list[dict[str, Any]] = []
    if "python" in wanted:
        if persist:
            _progress(run_id, "Python (pytest) 実行中…", suite_results)
        os.environ.setdefault("USE_BEDROCK_MOCK", "true")
        cwd = os.getcwd()
        try:
            os.chdir(_BACKEND)
            if str(_BACKEND) not in sys.path:
                sys.path.insert(0, str(_BACKEND))
            suite_results.append(_collect_pytest())
        except Exception as exc:
            suite_results.append(
                _empty_suite("python", "pytest", f"{exc}\n{traceback.format_exc()[-1200:]}")
            )
        finally:
            os.chdir(cwd)
        if persist:
            _progress(run_id, "Python 完了。Frontend 準備中…", suite_results)

    if "frontend" in wanted:
        if persist:
            _progress(run_id, "Frontend (Vitest) 実行中…", suite_results)
        try:
            suite_results.append(_collect_vitest())
        except Exception as exc:
            suite_results.append(
                _empty_suite("frontend", "vitest", f"{exc}\n{traceback.format_exc()[-1200:]}")
            )

    passed = sum(int(s.get("passed") or 0) for s in suite_results)
    failed = sum(int(s.get("failed") or 0) for s in suite_results)
    skipped = sum(int(s.get("skipped") or 0) for s in suite_results)
    total = sum(int(s.get("total") or 0) for s in suite_results)
    has_errors = any(s.get("error") for s in suite_results)
    if failed > 0:
        status = "failed"
    elif total > 0:
        status = "passed"
    elif has_errors:
        status = "error"
    else:
        status = "empty"

    run = {
        "run_id": run_id or str(uuid4()),
        "created_at": created_at,
        "finished_at": _now(),
        "status": status,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "duration_ms": sum(int(s.get("duration_ms") or 0) for s in suite_results),
        "suites": suite_results,
        "layout": {"backend": str(_BACKEND), "frontend": str(_FRONTEND)},
        "requested_suites": sorted(wanted),
        "message": f"完了: {passed} passed / {failed} failed / {total} total",
    }
    if persist:
        try:
            _upsert_run(run)
        except Exception:
            try:
                append(_STORE, run)
            except Exception:
                run["persist_error"] = "failed to persist test_runs"
    return run


def start_tests_async(suites: list[str] | None = None) -> dict[str, Any]:
    """即座に status=running を返し、バックグラウンドスレッドで完了させる。"""
    reap_stale_runs()
    wanted = [s.lower() for s in (suites or ["python", "frontend"])]

    with _RUN_LOCK:
        if _ACTIVE:
            active_id = next(iter(_ACTIVE))
            existing = get_run(active_id)
            if existing and existing.get("status") == "running":
                existing = {
                    **existing,
                    "message": existing.get("message")
                    or "別のテスト実行が進行中です。この結果を監視しています。",
                }
                return existing

    run_id = str(uuid4())
    stub: dict[str, Any] = {
        "run_id": run_id,
        "created_at": _now(),
        "status": "running",
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0,
        "duration_ms": 0,
        "suites": [
            {"suite": s, "runner": "pytest" if s == "python" else "vitest", "status": "queued"}
            for s in wanted
        ],
        "requested_suites": wanted,
        "message": "テスト実行を開始しました…",
    }
    with _RUN_LOCK:
        _ACTIVE.add(run_id)

    try:
        _upsert_run(stub)
    except Exception:
        append(_STORE, stub)

    def _worker() -> None:
        try:
            run_tests(wanted, run_id=run_id, persist=True)
        except Exception as exc:
            suites = []
            if "python" in wanted:
                suites.append(_empty_suite("python", "pytest", str(exc)))
            if "frontend" in wanted:
                suites.append(_empty_suite("frontend", "vitest", str(exc)))
            failed = {
                **stub,
                "status": "error",
                "finished_at": _now(),
                "error": str(exc),
                "message": f"runner crashed: {exc}",
                "suites": suites,
            }
            try:
                _upsert_run(failed)
            except Exception:
                pass
        finally:
            with _RUN_LOCK:
                _ACTIVE.discard(run_id)

    threading.Thread(target=_worker, name=f"tests-{run_id[:8]}", daemon=True).start()
    return stub


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    """テスト実行履歴の概要一覧を返す。"""
    reap_stale_runs()
    items = load(_STORE)
    items = sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)
    if len(items) > _MAX_HISTORY:
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
            "message": r.get("message"),
            "suite_names": [s.get("suite") for s in r.get("suites") or []],
        }
        for r in items[:limit]
    ]


def get_run(run_id: str) -> dict[str, Any] | None:
    """run_id に一致する実行レコードを返す。"""
    reap_stale_runs()
    for r in load(_STORE):
        if r.get("run_id") == run_id:
            return r
    return None


def latest_run() -> dict[str, Any] | None:
    """直近のテスト実行レコードを返す。"""
    reap_stale_runs()
    items = load(_STORE)
    if not items:
        return None
    items = sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)
    return items[0]
