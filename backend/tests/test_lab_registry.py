from src.services.analysis import analyze_tabular, analyze_text
from src.services.model_registry import active_models, list_models, promote_model, register_model
from src.services.monitoring import quality_alerts, record_monitor_snapshot
from src.services.tabular import synthesize_demo_csv, train_tabular_baseline


def test_tabular_train_and_register():
    csv_text = synthesize_demo_csv(60)
    trained = train_tabular_baseline(csv_text, target="churn", task="classification")
    assert trained["metrics"]["task"] == "classification"
    assert "accuracy" in trained["metrics"]
    analysis = analyze_tabular(csv_text, target="churn")
    assert analysis["experiment"]["modality"] == "tabular"
    model = register_model(
        name="churn-baseline",
        modality="tabular",
        metrics=trained["metrics"],
        experiment_id=analysis["experiment"]["experiment_id"],
        stage="development",
    )
    promoted = promote_model(model["model_id"], "staging")
    assert promoted["stage"] == "staging"
    assert any(m["model_id"] == model["model_id"] for m in list_models())
    assert "tabular" in active_models()["active"] or len(active_models()["active"]) >= 1


def test_text_analysis_and_monitoring():
    out = analyze_text("短い要約テスト")
    assert out["experiment"]["modality"] == "text"
    snap = record_monitor_snapshot(source="unit", combined_score=0.9, approval_rate=0.8)
    assert snap["combined_score"] == 0.9
    alerts = quality_alerts(min_combined=0.1, min_approval=0.1)
    assert "healthy" in alerts
