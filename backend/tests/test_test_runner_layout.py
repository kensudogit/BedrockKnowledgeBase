from src.services import test_runner as tr


def test_resolve_layout_points_at_backend_tests_and_frontend():
    backend, frontend = tr._resolve_layout()
    assert (backend / "tests").is_dir()
    assert (frontend / "package.json").is_file()


def test_empty_suite_helper():
    suite = tr._empty_suite("python", "pytest", "demo-error")
    assert suite["total"] == 0
    assert suite["error"] == "demo-error"
    assert suite["tests"] == []
