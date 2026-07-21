from src.services.bedrock_embed import embed_texts
from src.services.bedrock_text import generate_text
from src.services.evaluation import run_model_evaluation
from src.services.guardrails import apply_guardrails
from src.services.rag import rag_answer


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


def test_evaluation():
    run = run_model_evaluation(name="unit")
    assert "metrics" in run
    assert run["metrics"]["n_samples"] >= 1
