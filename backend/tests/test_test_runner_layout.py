from src.services import test_runner as tr


def test_resolve_layout_points_at_backend_tests_and_frontend():
    backend, frontend = tr._resolve_layout()
    assert (backend / "tests").is_dir()
    assert (frontend / "package.json").is_file()


def test_run_python_suite_smoke():
    run = tr.run_tests(["python"])
    assert run["total"] >= 1
    assert run["status"] in ("passed", "failed")
    assert run["layout"]["backend"]
    py = next(s for s in run["suites"] if s["suite"] == "python")
    assert py["total"] >= 1
