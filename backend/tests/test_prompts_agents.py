"""プロンプト管理、エージェント呼び出し、画像生成のテスト。"""

from src.services.agents import invoke_agent
from src.services.bedrock_image import generate_image
from src.services.prompts import list_prompts, render_prompt, seed_default_prompts, upsert_prompt


def test_prompts_upsert_and_render():
    """プロンプトの登録・一覧・レンダリングを確認する。"""
    seed_default_prompts()
    items = list_prompts()
    assert items
    p = upsert_prompt(
        name="unit-prompt",
        template="Q: {{question}}",
        use_case="unit",
        variables=["question"],
    )
    rendered = render_prompt(p["prompt_id"], {"question": "こんにちは"})
    assert "こんにちは" in rendered["rendered"]


def test_agent_mock_invoke():
    """モックエージェント呼び出しが応答を返すことを確認する。"""
    out = invoke_agent("請求書の処理を手伝って")
    assert out.get("answer")
    assert out.get("mock") is True or "plan" in out or out.get("answer")


def test_image_mock_generate(monkeypatch):
    """モック画像生成がbase64データを返すことを確認する。"""
    monkeypatch.setenv("USE_BEDROCK_MOCK", "true")
    from src.config import get_settings

    get_settings.cache_clear()
    out = generate_image("テスト画像")
    assert out["mock"] is True
    assert out.get("image_base64")
