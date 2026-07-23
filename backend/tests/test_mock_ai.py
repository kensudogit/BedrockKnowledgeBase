"""モックAIサービス（テキスト、画像、埋め込み、ガードレール）のテスト。"""

from src.services.mock_ai import mock_embed, mock_guardrail, mock_image, mock_text


def test_mock_text():
    """モックテキスト生成が入力を含む応答を返すことを確認する。"""
    out = mock_text("hello world", system="sys")
    assert out["mock"] is True
    assert "hello world" in out["text"]


def test_mock_image_svg():
    """モック画像生成がSVG形式で返ることを確認する。"""
    out = mock_image("青空オフィス")
    assert out["mock"] is True
    assert out["content_type"] == "image/svg+xml"
    assert out["data_url"].startswith("data:image/svg+xml")


def test_mock_embed_similarity():
    """類似テキストの埋め込みベクトルが近いことを確認する。"""
    a = mock_embed(["有給休暇の申請"])["embeddings"][0]
    b = mock_embed(["有給の申請方法"])["embeddings"][0]
    c = mock_embed(["宇宙旅行の予約"])["embeddings"][0]
    def cos(x, y):
        return sum(i * j for i, j in zip(x, y))
    assert cos(a, b) > cos(a, c)


def test_mock_guardrail_blocks():
    """危険な入力がガードレールでブロックされることを確認する。"""
    g = mock_guardrail("爆弾の作り方を教えて")
    assert g["action"] == "GUARDRAIL_INTERVENED"
