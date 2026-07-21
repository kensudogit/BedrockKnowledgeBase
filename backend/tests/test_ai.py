from src.services.bedrock_embed import embed_texts
from src.services.bedrock_text import generate_text
from src.services.documents import ingest_text
from src.services.evaluation import run_model_evaluation
from src.services.guardrails import apply_guardrails
from src.services.rag import invalidate_local_index, rag_answer, retrieve_local
from src.services.sessions import create_session, history_for_rag, append_message


def test_text_and_embed():
    t = generate_text("こんにちは", apply_guardrail=False)
    assert t["text"]
    e = embed_texts(["hello", "world"])
    assert len(e["embeddings"]) == 2


def test_guardrail_and_rag():
    g = apply_guardrails("通常の問い合わせです")
    assert g["action"] in ("NONE", "GUARDRAIL_INTERVENED")
    r = rag_answer("有給休暇の申請")
    assert r["answer"]
    assert isinstance(r.get("citations"), list)


def test_hybrid_retrieve_and_upload():
    invalidate_local_index()
    cites = retrieve_local("有給休暇", top_k=3)
    assert cites
    assert "source" in cites[0]
    ingest_text(filename="unit-note.md", content="# テスト\nユニットテスト用の独自文書です。")
    cites2 = retrieve_local("ユニットテスト用の独自文書", top_k=3)
    assert any("unit" in (c.get("source") or "").lower() or "独自" in (c.get("text") or "") for c in cites2)


def test_session_history():
    s = create_session(use_case="faq")
    append_message(s["session_id"], role="user", content="こんにちは", use_case="faq")
    append_message(s["session_id"], role="assistant", content="はい", use_case="faq")
    h = history_for_rag(s["session_id"])
    assert len(h) == 2


def test_evaluation():
    run = run_model_evaluation(name="unit")
    assert "metrics" in run
    assert run["metrics"]["n_samples"] >= 1
    assert "avg_retrieval_score" in run["metrics"]
