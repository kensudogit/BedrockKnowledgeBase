"""生成AI・RAG・評価・運用向け REST API ルーター（/api プレフィックス）。"""
from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.services.agents import invoke_agent
from src.services.analysis import analyze_image, analyze_rag, analyze_tabular, analyze_text
from src.services.bedrock_embed import embed_texts
from src.services.bedrock_image import decode_preview_data_url, generate_image
from src.services.bedrock_text import generate_text
from src.services.datasets import get_dataset, list_datasets, save_dataset
from src.services.documents import delete_document, ingest_text, list_documents
from src.services.evaluation import compare_evaluations, list_evaluations, run_model_evaluation
from src.services.experiments import get_experiment, list_experiments, log_experiment
from src.services.feedback import add_feedback, feedback_summary, list_feedback
from src.services.guardrails import apply_guardrails
from src.services.kb_ingest import get_ingestion_status, ingest_to_knowledge_base, list_ingest_jobs
from src.services.model_registry import (
    active_models,
    get_model,
    list_models,
    promote_model,
    register_model,
)
from src.services.monitoring import (
    delivery_status,
    monitor_series,
    quality_alerts,
    record_monitor_snapshot,
)
from src.services.projects import create_project, list_projects
from src.services.prompts import get_prompt, list_prompts, render_prompt, seed_default_prompts, upsert_prompt
from src.services.rag import rag_answer, retrieve_knowledge_base
from src.services.sessions import (
    append_message,
    create_session,
    get_session,
    history_for_rag,
    list_sessions,
)
from src.services.tabular import synthesize_demo_csv
from src.services.telemetry import summarize as telemetry_summary

router = APIRouter(prefix="/api", tags=["ai"])


# --- リクエスト/レスポンスモデル ---


class TextRequest(BaseModel):
    """テキスト生成リクエスト。"""
    prompt: str
    system: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.3
    apply_guardrail: bool = True


class ImageRequest(BaseModel):
    """画像生成リクエスト。"""
    prompt: str
    width: int = 512
    height: int = 512


class EmbedRequest(BaseModel):
    """テキスト埋め込みリクエスト。"""
    texts: list[str] = Field(min_length=1)


class GuardRequest(BaseModel):
    """ガードレール適用リクエスト。"""
    text: str
    source: str = "OUTPUT"


class PromptUpsert(BaseModel):
    """プロンプト登録・更新リクエスト。"""
    prompt_id: Optional[str] = None
    name: str
    template: str
    use_case: str = "general"
    variables: list[str] = []


class PromptRender(BaseModel):
    """プロンプトテンプレート変数の置換値。"""
    values: dict[str, str]


class RagRequest(BaseModel):
    """RAG 検索・回答リクエスト。"""
    query: str
    use_case: str = "document_search"
    top_k: int = 5
    session_id: Optional[str] = None
    apply_guardrail: bool = True


class ChatRequest(BaseModel):
    """マルチターン チャット（RAG またはテキスト）リクエスト。"""
    message: str
    use_case: str = "document_search"
    mode: str = "rag"  # rag | text
    session_id: Optional[str] = None
    system: Optional[str] = None
    apply_guardrail: bool = True


class SessionCreate(BaseModel):
    """会話セッション作成リクエスト。"""
    use_case: str = "document_search"
    title: Optional[str] = None


class DocIngest(BaseModel):
    """テキストドキュメント取り込みリクエスト。"""
    filename: str = "note.md"
    content: str
    content_type: str = "text/markdown"


class AgentRequest(BaseModel):
    """Bedrock エージェント呼び出しリクエスト。"""
    message: str
    session_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    """回答へのフィードバック（評価・コメント）。"""
    rating: int  # 1 or -1
    session_id: Optional[str] = None
    message_index: Optional[int] = None
    comment: str = ""
    use_case: Optional[str] = None
    model_id: Optional[str] = None
    answer_preview: str = ""
    project_id: Optional[str] = None


class ProjectCreate(BaseModel):
    """プロジェクト（テナント）作成リクエスト。"""
    name: str
    client_name: str = ""
    env: str = "development"
    api_key: Optional[str] = None
    notes: str = ""


class DatasetCreate(BaseModel):
    """評価用データセット作成リクエスト。"""
    name: str
    items: list[dict[str, Any]]
    dataset_id: Optional[str] = None
    description: str = ""
    version: str = "1.0.0"


class EvalRunRequest(BaseModel):
    """モデル評価実行リクエスト。"""
    name: Optional[str] = None
    dataset_id: str = "golden_default"
    project_id: Optional[str] = None
    fail_under: Optional[float] = None


class IngestKbRequest(BaseModel):
    """ナレッジベースへのドキュメント取り込みリクエスト。"""
    filename: str
    content: str
    content_type: str = "text/markdown"
    project_id: Optional[str] = None


class TokenRequest(BaseModel):
    """JWT アクセストークン発行リクエスト。"""
    subject: str = "bkb-user"
    expires_in_sec: int = 3600


# --- 認証エンドポイント ---


@router.post("/auth/token")
def auth_token(body: TokenRequest):
    """JWT_SECRET で署名した Bearer JWT を発行する。"""
    from src.config import get_settings
    from src.services.jwt_tokens import issue_access_token

    if not get_settings().jwt_configured:
        raise HTTPException(503, "JWT_SECRET is not configured")
    try:
        return issue_access_token(subject=body.subject, expires_in_sec=body.expires_in_sec)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/auth/me")
def auth_me(authorization: Optional[str] = Header(default=None)):
    """Authorization: Bearer JWT を検証し、クレームを返す。"""
    from src.config import get_settings
    from src.services.jwt_tokens import verify_access_token

    if not get_settings().jwt_configured:
        raise HTTPException(503, "JWT_SECRET is not configured")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authorization: Bearer <token> required")
    claims = verify_access_token(authorization.split(" ", 1)[1].strip())
    if not claims:
        raise HTTPException(401, "invalid or expired JWT")
    return {"ok": True, "claims": claims}


# --- Bedrock 生成（テキスト/画像/埋め込み/ガードレール） ---


@router.post("/text/generate")
def text_generate(body: TextRequest):
    """LLM によるテキスト生成。"""
    return generate_text(
        body.prompt,
        system=body.system,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
        apply_guardrail=body.apply_guardrail,
    )


@router.post("/image/generate")
def image_generate(body: ImageRequest):
    """画像生成モデルでプロンプトから画像を生成する。"""
    out = generate_image(body.prompt, width=body.width, height=body.height)
    if not out.get("data_url"):
        out["data_url"] = decode_preview_data_url(
            out["image_base64"],
            out.get("content_type") or "image/png",
        )
    return out


@router.post("/embedding")
def embedding(body: EmbedRequest):
    """複数テキストのベクトル埋め込みを返す。"""
    return embed_texts(body.texts)


@router.post("/guardrails/apply")
def guardrails(body: GuardRequest):
    """入力/出力テキストにガードレールを適用する。"""
    return apply_guardrails(body.text, source=body.source)


# --- プロンプト管理 ---


@router.get("/prompts")
def prompts_list():
    """登録済みプロンプト一覧（空ならデフォルトをシード）。"""
    items = list_prompts()
    if not items:
        items = seed_default_prompts()
    return {"items": items}


@router.post("/prompts")
def prompts_upsert(body: PromptUpsert):
    """プロンプトを新規登録または更新する。"""
    return upsert_prompt(
        prompt_id=body.prompt_id,
        name=body.name,
        template=body.template,
        use_case=body.use_case,
        variables=body.variables,
    )


@router.post("/prompts/{prompt_id}/render")
def prompts_render(prompt_id: str, body: PromptRender):
    """テンプレート変数を置換してプロンプトをレンダリングする。"""
    try:
        return render_prompt(prompt_id, body.values)
    except KeyError:
        raise HTTPException(404, "prompt not found")


@router.get("/prompts/{prompt_id}")
def prompts_get(prompt_id: str):
    """指定 ID のプロンプトを取得する。"""
    p = get_prompt(prompt_id)
    if not p:
        raise HTTPException(404, "prompt not found")
    return p


# --- モデル評価 ---


@router.post("/evaluation/run")
def evaluation_run(body: Optional[EvalRunRequest] = None, name: Optional[str] = None):
    """データセットに対する RAG/モデル評価を実行する。"""
    req = body or EvalRunRequest(name=name)
    try:
        return run_model_evaluation(
            name=req.name,
            dataset_id=req.dataset_id,
            project_id=req.project_id,
            fail_under=req.fail_under,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/evaluation")
def evaluation_list():
    """過去の評価実行結果一覧。"""
    return {"items": list_evaluations()}


@router.get("/evaluation/compare")
def evaluation_compare(a: str, b: str):
    """2 件の評価結果を比較する。"""
    try:
        return compare_evaluations(a, b)
    except KeyError:
        raise HTTPException(404, "eval not found")


# --- RAG / チャット / セッション ---


@router.post("/rag/query")
def rag_query(body: RagRequest):
    """RAG で質問に回答し、任意でセッション履歴に追記する。"""
    hist = history_for_rag(body.session_id)
    out = rag_answer(
        body.query,
        use_case=body.use_case,
        top_k=body.top_k,
        history=hist,
        apply_guardrail=body.apply_guardrail,
    )
    if body.session_id:
        append_message(body.session_id, role="user", content=body.query, use_case=body.use_case)
        append_message(
            body.session_id,
            role="assistant",
            content=out.get("answer") or "",
            citations=out.get("citations") or [],
            meta={"blocked": out.get("blocked"), "mock": out.get("mock")},
            use_case=body.use_case,
        )
        out["session_id"] = body.session_id
    return out


@router.post("/rag/retrieve")
def rag_retrieve(body: RagRequest):
    """ナレッジベースから関連チャンクのみ取得する（生成なし）。"""
    return retrieve_knowledge_base(body.query, top_k=body.top_k)


@router.post("/chat")
def chat(body: ChatRequest):
    """マルチターン チャット。必要ならセッション作成し RAG/テキストで回答。"""
    sid = body.session_id or create_session(use_case=body.use_case)["session_id"]
    append_message(sid, role="user", content=body.message, use_case=body.use_case)

    if body.mode == "text":
        hist = history_for_rag(sid)
        ctx = "\n".join(f"{h['role']}: {h['content']}" for h in hist[:-1][-6:])
        prompt = f"{ctx}\nuser: {body.message}" if ctx else body.message
        gen = generate_text(
            prompt,
            system=body.system or "丁寧な日本語で回答してください。",
            apply_guardrail=body.apply_guardrail,
        )
        answer = gen.get("text") or ""
        cites: list[Any] = []
        meta = {"mode": "text", "mock": gen.get("mock")}
    else:
        hist = history_for_rag(sid)
        # 直前に追加したユーザーメッセージの重複を避ける
        hist_prior = hist[:-1] if hist and hist[-1].get("role") == "user" else hist
        out = rag_answer(
            body.message,
            use_case=body.use_case,
            history=hist_prior,
            apply_guardrail=body.apply_guardrail,
        )
        answer = out.get("answer") or ""
        cites = out.get("citations") or []
        meta = {
            "mode": "rag",
            "mock": out.get("mock"),
            "blocked": out.get("blocked"),
            "source": out.get("source"),
        }

    append_message(
        sid,
        role="assistant",
        content=answer,
        citations=cites,
        meta=meta,
        use_case=body.use_case,
    )
    sess = get_session(sid)
    return {
        "session_id": sid,
        "answer": answer,
        "citations": cites,
        "messages": (sess or {}).get("messages") or [],
        **meta,
        "use_case": body.use_case,
    }


@router.post("/sessions")
def sessions_create(body: SessionCreate):
    """新規会話セッションを作成する。"""
    return create_session(use_case=body.use_case, title=body.title)


@router.get("/sessions")
def sessions_list():
    """セッション一覧。"""
    return {"items": list_sessions()}


@router.get("/sessions/{session_id}")
def sessions_get(session_id: str):
    """指定セッションのメッセージ履歴を取得する。"""
    sess = get_session(session_id)
    if not sess:
        raise HTTPException(404, "session not found")
    return sess


# --- ドキュメント / KB 取り込み ---


@router.get("/documents")
def documents_list():
    """取り込み済みドキュメント一覧。"""
    return {"items": list_documents()}


@router.post("/documents")
def documents_create(body: DocIngest):
    """テキスト内容をドキュメントストアに取り込む。"""
    if not body.content.strip():
        raise HTTPException(400, "content is empty")
    return ingest_text(
        filename=body.filename,
        content=body.content,
        content_type=body.content_type,
    )


@router.post("/documents/kb-ingest")
def documents_kb_ingest(body: IngestKbRequest):
    """Bedrock ナレッジベースへの非同期取り込みジョブを開始する。"""
    if not body.content.strip():
        raise HTTPException(400, "content is empty")
    return ingest_to_knowledge_base(
        filename=body.filename,
        content=body.content,
        content_type=body.content_type,
        project_id=body.project_id,
    )


@router.get("/documents/ingest-jobs")
def documents_ingest_jobs():
    """KB 取り込みジョブ一覧。"""
    return {"items": list_ingest_jobs()}


@router.get("/documents/ingest-jobs/{ingestion_job_id}")
def documents_ingest_status(ingestion_job_id: str):
    """指定取り込みジョブの状態を返す。"""
    return get_ingestion_status(ingestion_job_id)


@router.post("/documents/upload")
async def documents_upload(file: UploadFile = File(...)):
    """アップロードファイルを UTF-8/CP932 でデコードして取り込む。"""
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp932", errors="ignore")
    if not text.strip():
        raise HTTPException(400, "empty or unsupported file")
    name = file.filename or f"upload-{uuid4().hex[:8]}.txt"
    return ingest_text(
        filename=name,
        content=text,
        content_type=file.content_type or "text/plain",
    )


@router.delete("/documents/{document_id}")
def documents_delete(document_id: str):
    """ドキュメントを削除する。"""
    if not delete_document(document_id):
        raise HTTPException(404, "document not found")
    return {"ok": True, "document_id": document_id}


# --- エージェント / ユースケース / プロジェクト ---


@router.post("/agents/invoke")
def agents_invoke(body: AgentRequest):
    """Bedrock エージェントにメッセージを送り応答を得る。"""
    return invoke_agent(body.message, session_id=body.session_id)


@router.get("/use-cases")
def use_cases():
    """UI 向けユースケース定義一覧。"""
    return {
        "items": [
            {"id": "internal_chatbot", "label": "社内チャットボット"},
            {"id": "faq", "label": "FAQシステム"},
            {"id": "document_search", "label": "文書検索（RAG）"},
            {"id": "contract_review", "label": "契約書レビュー"},
            {"id": "codegen", "label": "ソースコード生成"},
            {"id": "callcenter", "label": "コールセンター支援"},
            {"id": "medical_search", "label": "医療文書検索"},
            {"id": "finance_advice", "label": "金融アドバイス"},
            {"id": "ocr", "label": "OCRとの連携"},
            {"id": "ai_agent", "label": "AIエージェント"},
        ]
    }


@router.get("/projects")
def projects_list():
    """プロジェクト（テナント）一覧。"""
    return {"items": list_projects()}


@router.post("/projects")
def projects_create(body: ProjectCreate):
    """新規プロジェクトを作成する。"""
    return create_project(
        name=body.name,
        client_name=body.client_name,
        env=body.env,
        api_key=body.api_key,
        notes=body.notes,
    )


# --- フィードバック ---


@router.post("/feedback")
def feedback_create(body: FeedbackRequest):
    """回答への thumbs up/down 等のフィードバックを記録する。"""
    try:
        return add_feedback(
            rating=body.rating,
            session_id=body.session_id,
            message_index=body.message_index,
            comment=body.comment,
            use_case=body.use_case,
            model_id=body.model_id,
            answer_preview=body.answer_preview,
            project_id=body.project_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/feedback")
def feedback_list():
    """フィードバック一覧と集計サマリ。"""
    return {"items": list_feedback(), "summary": feedback_summary()}


# --- データセット ---


@router.get("/datasets")
def datasets_list():
    """評価用データセット一覧。"""
    return {"items": list_datasets()}


@router.get("/datasets/{dataset_id}")
def datasets_get(dataset_id: str):
    """指定データセットの内容を取得する。"""
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, "dataset not found")
    return ds


@router.post("/datasets")
def datasets_create(body: DatasetCreate):
    """評価用データセットを保存する。"""
    return save_dataset(
        name=body.name,
        items=body.items,
        dataset_id=body.dataset_id,
        description=body.description,
        version=body.version,
    )


# --- テレメトリ / 運用サマリ ---


@router.get("/metrics/summary")
def metrics_summary():
    """API テレメトリの集計サマリ。"""
    return telemetry_summary()


@router.get("/ops/summary")
def ops_summary():
    """運用ダッシュボード向けの横断サマリ。"""
    from src.config import get_settings

    s = get_settings()
    return {
        "app_env": s.app_env,
        "mock_mode": s.mock_mode,
        "telemetry": telemetry_summary(),
        "feedback": feedback_summary(),
        "projects": list_projects(),
        "datasets": list_datasets(),
        "ingest_jobs": list_ingest_jobs(10),
        "recent_evals": list_evaluations(5),
        "delivery": delivery_status(),
        "models": list_models()[:20],
        "experiments": list_experiments(10),
        "monitor": quality_alerts(),
    }


class TestRunRequest(BaseModel):
    """バックグラウンドテスト実行リクエスト。"""
    suites: list[str] = Field(default_factory=lambda: ["python", "frontend"])


# --- テストランナー ---


@router.post("/tests/run")
def tests_run(body: TestRunRequest):
    """pytest + vitest をバックグラウンド起動。GET /api/tests/runs/{id} でポーリング。"""
    from src.services.test_runner import start_tests_async

    try:
        return start_tests_async(body.suites)
    except Exception as exc:
        raise HTTPException(500, f"test runner failed: {exc}") from exc


@router.get("/tests/latest")
def tests_latest():
    """直近のテスト実行結果。"""
    from src.services.test_runner import latest_run

    run = latest_run()
    if not run:
        return {"run": None}
    return {"run": run}


@router.get("/tests/history")
def tests_history(limit: int = 20):
    """テスト実行履歴（件数上限あり）。"""
    from src.services.test_runner import list_runs

    return {"items": list_runs(limit=min(max(limit, 1), 50))}


@router.get("/tests/runs/{run_id}")
def tests_get_run(run_id: str):
    """指定 run_id のテスト実行詳細。"""
    from src.services.test_runner import get_run

    run = get_run(run_id)
    if not run:
        raise HTTPException(404, "test run not found")
    return run


class AnalysisTextRequest(BaseModel):
    """分析ラボ: テキスト生成リクエスト。"""
    prompt: str
    project_id: Optional[str] = None


class AnalysisRagRequest(BaseModel):
    """分析ラボ: RAG クエリリクエスト。"""
    query: str
    use_case: str = "document_search"
    project_id: Optional[str] = None


class AnalysisTabularRequest(BaseModel):
    """分析ラボ: CSV 表形式データ分析リクエスト。"""
    csv_text: str
    target: Optional[str] = None
    task: str = "auto"
    project_id: Optional[str] = None


class ExperimentCreate(BaseModel):
    """実験ログ登録リクエスト。"""
    name: str
    modality: str
    params: dict[str, Any] = {}
    metrics: dict[str, Any] = {}
    artifacts: dict[str, Any] = {}
    project_id: Optional[str] = None
    notes: str = ""


class ModelRegister(BaseModel):
    """モデルレジストリ登録リクエスト。"""
    name: str
    modality: str
    version: str = "0.1.0"
    provider: str = "bedrock"
    model_uri: str = ""
    metrics: dict[str, Any] = {}
    experiment_id: Optional[str] = None
    project_id: Optional[str] = None
    stage: str = "development"
    meta: dict[str, Any] = {}


class ModelPromote(BaseModel):
    """モデルステージ昇格リクエスト。"""
    to_stage: str


# --- 分析ラボ ---


@router.post("/analysis/text")
def analysis_text(body: AnalysisTextRequest):
    """分析用途のテキスト生成パイプラインを実行する。"""
    return analyze_text(body.prompt, project_id=body.project_id)


@router.post("/analysis/image")
def analysis_image(body: AnalysisTextRequest):
    """分析用途の画像生成とプレビュー data URL 付与。"""
    out = analyze_image(body.prompt, project_id=body.project_id)
    if out.get("result"):
        out["result"]["data_url"] = decode_preview_data_url(out["result"].get("image_base64") or "")
    return out


@router.post("/analysis/rag")
def analysis_rag(body: AnalysisRagRequest):
    """分析用途の RAG パイプラインを実行する。"""
    return analyze_rag(body.query, use_case=body.use_case, project_id=body.project_id)


@router.post("/analysis/tabular")
def analysis_tabular(body: AnalysisTabularRequest):
    """CSV 表データの分類/回帰等の分析を実行する。"""
    try:
        return analyze_tabular(
            body.csv_text,
            target=body.target,
            task=body.task,
            project_id=body.project_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/analysis/tabular/demo-csv")
def analysis_tabular_demo():
    """表分析デモ用のサンプル CSV を返す。"""
    return {"csv_text": synthesize_demo_csv(), "target": "churn"}


# --- 実験管理 ---


@router.get("/experiments")
def experiments_list(modality: Optional[str] = None):
    """実験ログ一覧（モダリティでフィルタ可）。"""
    return {"items": list_experiments(50, modality=modality)}


@router.get("/experiments/{experiment_id}")
def experiments_get(experiment_id: str):
    """指定実験の詳細を取得する。"""
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(404, "experiment not found")
    return exp


@router.post("/experiments")
def experiments_create(body: ExperimentCreate):
    """新規実験ログを記録する。"""
    return log_experiment(
        name=body.name,
        modality=body.modality,
        params=body.params,
        metrics=body.metrics,
        artifacts=body.artifacts,
        project_id=body.project_id,
        notes=body.notes,
    )


# --- モデルレジストリ ---


@router.get("/models")
def models_list(stage: Optional[str] = None):
    """登録モデル一覧とアクティブモデル。"""
    return {"items": list_models(stage=stage), "active": active_models()}


@router.get("/models/{model_id}")
def models_get(model_id: str):
    """指定モデルのメタデータを取得する。"""
    m = get_model(model_id)
    if not m:
        raise HTTPException(404, "model not found")
    return m


@router.post("/models")
def models_register(body: ModelRegister):
    """モデルレジストリに新規モデルを登録する。"""
    try:
        return register_model(
            name=body.name,
            modality=body.modality,
            version=body.version,
            provider=body.provider,
            model_uri=body.model_uri,
            metrics=body.metrics,
            experiment_id=body.experiment_id,
            project_id=body.project_id,
            stage=body.stage,
            meta=body.meta,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/models/{model_id}/promote")
def models_promote(model_id: str, body: ModelPromote):
    """モデルを指定ステージ（例: production）へ昇格する。"""
    try:
        return promote_model(model_id, body.to_stage)
    except KeyError:
        raise HTTPException(404, "model not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# --- 品質モニタリング ---


@router.get("/monitoring/series")
def monitoring_series():
    """品質メトリクス時系列データ。"""
    return {"items": monitor_series()}


@router.post("/monitoring/snapshot")
def monitoring_snapshot():
    """現在の品質スナップショットを記録する。"""
    return record_monitor_snapshot(source="api")


@router.get("/monitoring/alerts")
def monitoring_alerts():
    """品質アラート一覧。"""
    return quality_alerts()


@router.get("/delivery/status")
def delivery_status_api():
    """デリバリー/リリース状態サマリ。"""
    return delivery_status()


# --- GCP / Vertex / GCS ---


class GcpTextRequest(BaseModel):
    """Vertex AI テキスト生成リクエスト。"""
    prompt: str
    system: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.3
    apply_guardrail: bool = True


class GcsUploadRequest(BaseModel):
    """GCS ドキュメントアップロードリクエスト。"""
    filename: str
    content: str
    content_type: str = "text/plain"
    project_id: Optional[str] = None


@router.get("/gcp/status")
def gcp_status_api():
    """GCP / Vertex / GCS の設定・利用可能状態。"""
    from src.gcp_clients import gcp_status

    return gcp_status()


@router.post("/gcp/text")
def gcp_text_generate(body: GcpTextRequest):
    """Vertex AI でテキスト生成（任意でガードレール適用）。"""
    from src.services.vertex_text import generate_text_vertex

    try:
        out = generate_text_vertex(
            body.prompt,
            system=body.system,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
        )
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    if body.apply_guardrail:
        from src.config import get_settings
        from src.services.guardrails import apply_guardrails

        if get_settings().enable_guardrails:
            gr = apply_guardrails(out["text"])
            out["guardrail"] = gr
            if gr.get("action") == "GUARDRAIL_INTERVENED":
                out["text"] = gr["outputs"][0]["text"]
    return out


@router.post("/gcp/storage/upload")
def gcp_storage_upload(body: GcsUploadRequest):
    """GCS（またはモックローカル）へドキュメントをアップロードする。"""
    from src.services.gcs_storage import upload_document

    return upload_document(
        filename=body.filename,
        content=body.content,
        content_type=body.content_type,
        project_id=body.project_id,
    )


@router.get("/gcp/storage/uploads")
def gcp_storage_list():
    """GCS アップロード済みファイル一覧。"""
    from src.services.gcs_storage import list_uploads

    return {"items": list_uploads()}


# --- 信用情報管理 ---


class CreditSubjectCreate(BaseModel):
    """信用情報: 本人（被調査者）登録リクエスト。"""
    full_name: str
    birth_date: str
    phone: str = ""
    email: str = ""
    external_ref: str = ""
    notes: str = ""


class CreditContractCreate(BaseModel):
    """信用情報: 契約（借入等）追加リクエスト。"""
    contract_type: str = "credit_card"
    lender: str
    credit_limit: int = 0
    balance: int = 0
    status: str = "open"
    opened_on: str = ""
    payment_status: str = "current"
    months_delinquent: int = 0


class CreditConsentCreate(BaseModel):
    """信用情報: 本人同意記録リクエスト。"""
    purpose: str = "credit_inquiry"
    requester: str
    channel: str = "web"
    expires_at: str = ""


class CreditInquiryCreate(BaseModel):
    """信用情報: 照会（インフォメーション）記録リクエスト。"""
    requester: str
    purpose: str = "credit_review"
    inquiry_type: str = "hard"
    require_consent: bool = True


@router.get("/credit/subjects")
def credit_subjects_list():
    """信用情報: 登録済み本人一覧。"""
    from src.services.credit_info import list_subjects

    return {"items": list_subjects()}


@router.post("/credit/subjects")
def credit_subjects_create(body: CreditSubjectCreate):
    """信用情報: 本人を新規登録する。"""
    from src.services.credit_info import register_subject

    return register_subject(
        full_name=body.full_name,
        birth_date=body.birth_date,
        phone=body.phone,
        email=body.email,
        external_ref=body.external_ref,
        notes=body.notes,
    )


@router.get("/credit/subjects/{subject_id}")
def credit_subjects_get(subject_id: str, reveal: bool = False):
    """信用情報: 本人詳細（reveal で機微情報表示）。"""
    from src.services.credit_info import get_subject

    item = get_subject(subject_id, reveal=reveal)
    if not item:
        raise HTTPException(404, "subject not found")
    return item


@router.post("/credit/subjects/{subject_id}/contracts")
def credit_contracts_add(subject_id: str, body: CreditContractCreate):
    """信用情報: 本人に契約情報を追加する。"""
    from src.services.credit_info import add_contract

    try:
        return add_contract(
            subject_id=subject_id,
            contract_type=body.contract_type,
            lender=body.lender,
            credit_limit=body.credit_limit,
            balance=body.balance,
            status=body.status,
            opened_on=body.opened_on,
            payment_status=body.payment_status,
            months_delinquent=body.months_delinquent,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/credit/subjects/{subject_id}/contracts")
def credit_contracts_list(subject_id: str):
    """信用情報: 本人の契約一覧。"""
    from src.services.credit_info import get_subject, list_contracts

    if not get_subject(subject_id):
        raise HTTPException(404, "subject not found")
    return {"items": list_contracts(subject_id)}


@router.post("/credit/subjects/{subject_id}/consents")
def credit_consents_add(subject_id: str, body: CreditConsentCreate):
    """信用情報: 本人同意を記録する。"""
    from src.services.credit_info import record_consent

    try:
        return record_consent(
            subject_id=subject_id,
            purpose=body.purpose,
            requester=body.requester,
            channel=body.channel,
            expires_at=body.expires_at,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/credit/subjects/{subject_id}/consents")
def credit_consents_list(subject_id: str):
    """信用情報: 本人の同意履歴一覧。"""
    from src.services.credit_info import get_subject, list_consents

    if not get_subject(subject_id):
        raise HTTPException(404, "subject not found")
    return {"items": list_consents(subject_id)}


@router.post("/credit/subjects/{subject_id}/inquiries")
def credit_inquiries_add(subject_id: str, body: CreditInquiryCreate):
    """信用情報: 照会を記録する（同意必須オプションあり）。"""
    from src.services.credit_info import record_inquiry

    try:
        return record_inquiry(
            subject_id=subject_id,
            requester=body.requester,
            purpose=body.purpose,
            inquiry_type=body.inquiry_type,
            require_consent=body.require_consent,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.get("/credit/subjects/{subject_id}/inquiries")
def credit_inquiries_list(subject_id: str):
    """信用情報: 本人への照会履歴一覧。"""
    from src.services.credit_info import get_subject, list_inquiries

    if not get_subject(subject_id):
        raise HTTPException(404, "subject not found")
    return {"items": list_inquiries(subject_id)}


@router.get("/credit/subjects/{subject_id}/score")
def credit_score_get(subject_id: str):
    """信用情報: スコアを算出して返す。"""
    from src.services.credit_info import compute_score, get_subject

    if not get_subject(subject_id):
        raise HTTPException(404, "subject not found")
    return compute_score(subject_id)


@router.get("/credit/subjects/{subject_id}/report")
def credit_report_get(subject_id: str, reveal: bool = False):
    """信用情報: 本人レポートを組み立てて返す。"""
    from src.services.credit_info import build_report

    try:
        return build_report(subject_id, reveal=reveal)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/credit/audit")
def credit_audit_list(limit: int = 100, subject_id: Optional[str] = None):
    """信用情報: 監査ログ一覧（件数・本人でフィルタ可）。"""
    from src.services.credit_info import list_audit

    return {"items": list_audit(limit=limit, subject_id=subject_id)}

