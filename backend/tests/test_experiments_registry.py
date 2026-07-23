"""実験ログとモデルレジストリの登録・昇格テスト。"""

from src.services.experiments import get_experiment, list_experiments, log_experiment
from src.services.model_registry import list_models, promote_model, register_model


def test_experiment_log_and_get():
    """実験の記録・取得・一覧が動作することを確認する。"""
    exp = log_experiment(
        name="unit-exp",
        modality="text",
        params={"k": 1},
        metrics={"score": 0.9},
    )
    assert exp.get("experiment_id")
    got = get_experiment(exp["experiment_id"])
    assert got and got["name"] == "unit-exp"
    assert any(e["experiment_id"] == exp["experiment_id"] for e in list_experiments())


def test_model_register_and_promote():
    """モデル登録とステージ昇格が正しく行われることを確認する。"""
    m = register_model(
        name="unit-model",
        modality="text",
        version="0.0.1",
        metrics={"score": 0.8},
        stage="development",
    )
    mid = m["model_id"]
    promote_model(mid, "staging")
    items = list_models()
    found = next(x for x in items if x["model_id"] == mid)
    assert found["stage"] == "staging"
