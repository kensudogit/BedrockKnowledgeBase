from src.services.datasets import get_dataset, list_datasets
from src.services.evaluation import run_model_evaluation
from src.services.feedback import add_feedback, feedback_summary
from src.services.kb_ingest import ingest_to_knowledge_base
from src.services.projects import create_project, list_projects, seed_default_project
from src.services.telemetry import record_event, summarize


def test_projects_and_feedback():
    seed_default_project()
    p = create_project(name="unit-client", client_name="UnitCo", env="staging")
    assert p["api_key"]
    assert any(x["name"] == "unit-client" for x in list_projects())
    add_feedback(rating=1, session_id="s1", answer_preview="ok", project_id=p["project_id"])
    s = feedback_summary()
    assert s["up"] >= 1


def test_datasets_and_eval():
    assert get_dataset("golden_default")
    assert list_datasets()
    run = run_model_evaluation(name="ops-unit", dataset_id="golden_default", fail_under=0.1)
    assert run["metrics"]["dataset_id"] == "golden_default"
    assert "passed" in run["metrics"]


def test_telemetry_and_ingest():
    record_event(path="/api/chat", method="POST", status_code=200, latency_ms=12, mock=True)
    m = summarize(50)
    assert m["n_events"] >= 1
    job = ingest_to_knowledge_base(filename="ops.md", content="# ops\ntelemetry test doc")
    assert job["status"] in ("local_indexed", "s3_uploaded", "s3_uploaded_pending_sync", "kb_ingestion_started", "error")
