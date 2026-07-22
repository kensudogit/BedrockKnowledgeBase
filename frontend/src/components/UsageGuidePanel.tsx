"use client";

/**
 * 画面右下のドラッグ可能な利用手順パネル（localStorage で位置・開閉を保存）。
 * Bedrock Knowledge Base — アーキテクチャ・6コア機能・運用手順を表示。
 */
import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./UsageGuidePanel.module.css";

const STORAGE_KEY = "bkb-usage-guide-v1";
const PANEL_WIDTH = 440;

type GuideStep = {
  title: string;
  body: string;
  items?: readonly string[];
};

type FeaturedBlock = {
  badge: string;
  title: string;
  body: string;
  items?: readonly string[];
  variant?:
    | "architecture"
    | "rag"
    | "image"
    | "embed"
    | "guard"
    | "prompt"
    | "eval"
    | "agent"
    | "deploy";
};

const architectureFeatured: FeaturedBlock = {
  badge: "Architecture",
  title: "Next.js BFF + FastAPI + Bedrock / OpenAI",
  body:
    "Web は同一オリジンで FastAPI にプロキシ。テキストは Bedrock → OpenAI → モックの順で選択。画像・埋め込み等は Bedrock（未設定時はモック）。秘密情報はサーバー側 Variables のみ。",
  variant: "architecture",
  items: [
    "Next.js — Chat · Lab · Documents · Image · Embedding · Guardrails · Prompts · Evaluation · Agents · Ops",
    "FastAPI :8180（Railway 内部・INTERNAL_API_URL）/ ローカル競合時は :8290",
    "PostgreSQL — Railway DATABASE_URL（スキーマ自動初期化）",
    "DynamoDB — Prompt / Eval（未接続時はメモリフォールバック）",
    "LLM — Bedrock Runtime または OPENAI_API_KEY（gpt-4o-mini 等）",
    "/health — llm_provider · database_ok · openai_configured · jwt_configured",
  ],
};

const ragFeatured: FeaturedBlock = {
  badge: "Text / RAG",
  title: "テキスト生成と社内文書検索（/chat）",
  body:
    "チャット・RAG を同一画面で試せます。回答生成は llm_provider（bedrock / openai / mock）に従います。モック RAG は samples/ をローカル検索します。",
  variant: "rag",
  items: [
    "POST /api/chat · /api/text/generate — マルチターン / 単発生成",
    "RAG — POST /api/rag/query（use_case で FAQ / 契約書 / 医療 等）",
    "OpenAI — USE_BEDROCK_MOCK=true でも OPENAI_API_KEY があれば実テキスト応答",
    "Bedrock — USE_BEDROCK_MOCK=false + AWS 認証 + 任意で Knowledge Base",
  ],
};

const imageFeatured: FeaturedBlock = {
  badge: "Image",
  title: "画像生成（/image）",
  body:
    "Titan Image 等でプロンプトから画像を生成。「生成」後に MOCK IMAGE プレースホルダまたは実画像が表示されます。",
  variant: "image",
  items: [
    "操作 — プロンプト →「生成」→「生成完了（モック）」と青い 512×512 プレースホルダ",
    "POST /api/image/generate — prompt → data_url（モックは SVG）",
    "注意 — 旧 1×1 PNG は「動かない」ように見える。最新デプロイを Ctrl+F5",
    "実画像 — USE_BEDROCK_MOCK=false + AWS 認証 + Titan Image",
  ],
};

const embedFeatured: FeaturedBlock = {
  badge: "Embedding",
  title: "埋め込みベクトル（/embedding）",
  body: "テキストをベクトル化し、類似検索やクラスタリングの前処理に使います。",
  variant: "embed",
  items: [
    "POST /api/embedding — texts[] → embeddings[][]",
    "用途 — セマンティック検索 · 重複検知 · RAG 前処理",
    "本番 — Titan Embed Text v2 / モック時はローカル n-gram ベクトル",
  ],
};

const guardFeatured: FeaturedBlock = {
  badge: "Guardrails",
  title: "ガードレール（/guardrails）",
  body: "有害・個人情報・ポリシー違反テキストをフィルタ。生成前チェックや出力検証に利用。",
  variant: "guard",
  items: [
    "POST /api/guardrails/apply — text → action / outputs",
    "Text 生成時 — apply_guardrail=true で自動適用",
    "本番 — BEDROCK_GUARDRAIL_ID · BEDROCK_GUARDRAIL_VERSION",
  ],
};

const promptFeatured: FeaturedBlock = {
  badge: "Prompts",
  title: "プロンプト管理（/prompts）",
  body: "ユースケース別テンプレートを DynamoDB（またはメモリ）に保存・描画します。",
  variant: "prompt",
  items: [
    "GET/POST /api/prompts — 一覧 · 作成 · 更新",
    "変数 — {{question}} 等を render で置換",
    "シード — 社内チャット · FAQ · 契約レビュー 等",
  ],
};

const evalFeatured: FeaturedBlock = {
  badge: "Evaluation",
  title: "モデル評価（/evaluation）",
  body: "サンプル設問セットで回答品質を簡易スコアリング。改善サイクルの起点に。",
  variant: "eval",
  items: [
    "POST /api/evaluation/run — 評価ジョブ実行",
    "GET /api/evaluation — 履歴一覧",
    "観点 — 正確性 · 根拠引用 · ガードレール通過",
    "関連 — /lab（実験）· /ops（モニタリング・モデル昇格）",
  ],
};

const agentFeatured: FeaturedBlock = {
  badge: "Agents",
  title: "AI エージェント（/agents）",
  body: "Bedrock Agents による業務自動化の骨格。モック時はプラン付き回答を返します。",
  variant: "agent",
  items: [
    "POST /api/agents/invoke — message → answer / plan",
    "用途 — コールセンター支援 · OCR 連携 · 複数ステップ業務",
    "本番 — BEDROCK_AGENT_ID · BEDROCK_AGENT_ALIAS_ID",
  ],
};

const deployFeatured: FeaturedBlock = {
  badge: "Deploy",
  title: "Railway · Variables · ローカル",
  body:
    "単一コンテナ（Next + uvicorn）で Railway 公開。必須 Variables を揃えて Deploy。AWS 基盤は Terraform で拡張可能。",
  variant: "deploy",
  items: [
    "必須 — DATABASE_URL · OPENAI_API_KEY · JWT_SECRET · INTERNAL_API_URL=http://127.0.0.1:8180",
    "推奨 — APP_ENV=production · CORS_ORIGINS=* · DYNAMODB_ENDPOINT=（空）· USE_BEDROCK_MOCK=true",
    "禁止 — Suggested の localhost:3010 / :8290 / DynamoDB Local を本番に足さない",
    "確認 — /health の database_ok · openai_configured · llm_provider · jwt_configured",
  ],
};

const techStack = [
  "Python · FastAPI",
  "Next.js 15 · React",
  "PostgreSQL · DynamoDB",
  "Amazon Bedrock",
  "OpenAI API",
  "Knowledge Bases",
  "Guardrails · Agents",
  "S3 · Lambda · API GW",
  "Terraform IaC",
  "Railway · Docker",
] as const;

const archDiagram = `Browser (Enterprise User)
    │ HTTPS
    ▼
Next.js :PORT (Railway) / :3010 (local)
    ├─ /chat /lab /documents /image /embedding
    ├─ /guardrails /prompts /evaluation /agents /ops
    └─ /api/* · /health ──proxy──► FastAPI :8180
              ├─ LLM: Bedrock  or  OpenAI (OPENAI_API_KEY)
              ├─ Image / Embed: Bedrock  or  mock SVG/vector
              ├─ RAG: Knowledge Bases ← S3  or  samples/
              ├─ Auth: JWT_SECRET · X-API-Key
              ├─ PostgreSQL ← DATABASE_URL
              └─ DynamoDB or memory (prompts · evals)`;

type GuideSection = {
  label: string;
  steps: readonly GuideStep[];
};

const guideSections: readonly GuideSection[] = [
  {
    label: "クイックスタート",
    steps: [
      {
        title: "パネル操作・画面遷移",
        body: "本パネルは全画面で表示されます。PC ではヘッダーをドラッグして位置を変更でき、▼▲ で折りたたみ可能です。",
        items: [
          "PC — ヘッダーをドラッグで移動 · ▼▲ で開閉 · 位置はブラウザに自動保存",
          "ナビ — Text/RAG · AI Lab · Documents · Image · Embedding · Guardrails · Prompts · Evaluation · Agents · Ops",
          "推奨フロー — ホーム → /chat → /image → /lab → /ops → Guardrails / Prompts",
          "プレゼン時 — パネルを画面端に寄せ、メイン画面を広く使う",
        ],
      },
      {
        title: "接続確認（最初に）",
        body: "本番・ローカル共通。障害切り分けとデモ前チェックの起点です。",
        items: [
          "本番 — https://<your-app>.up.railway.app/health",
          "ローカル UI — http://localhost:3010",
          "ローカル API — http://localhost:8180/docs（占有時は :8290 + INTERNAL_API_URL 合わせ）",
          "/health — version · llm_provider · database_ok · openai_configured · jwt_configured",
          "/image —「生成」→ MOCK IMAGE が出ればフロント〜API 連携 OK",
          "/chat — OPENAI_API_KEY 設定時は実 LLM、未設定時はモック応答",
        ],
      },
      {
        title: "初回セットアップ（ローカル 5 分）",
        body: "ローカル開発の最短手順です。",
        items: [
          "① setup.bat — Postgres · DynamoDB Local · 依存関係",
          "② backend — python run.py（既定 :8180 / 競合時 PORT=8290）",
          "③ frontend — INTERNAL_API_URL を API ポートに合わせて npm run dev（:3010）",
          "④ /chat で RAG、「有給休暇の申請手順」などを試す",
          "⑤ /image で「生成」→ MOCK IMAGE を確認",
          "⑥ /lab · /ops · /documents を確認",
        ],
      },
    ],
  },
  {
    label: "画面・機能 詳細",
    steps: [
      {
        title: "① Text / RAG（/chat）",
        body: "プロンプト送信・文書質問・セッション付きチャット。",
        items: [
          "llm_provider=openai — OPENAI_API_KEY で Chat Completions",
          "llm_provider=bedrock — USE_BEDROCK_MOCK=false + AWS 認証",
          "llm_provider=mock — ローカル定型応答 + samples/ RAG",
          "ユースケース — 社内 FAQ · 契約書 · 医療文書 · 金融アドバイス",
        ],
      },
      {
        title: "② Image（/image）",
        body: "プロンプトから画像を生成します。",
        items: [
          "モック成功 — 青い MOCK IMAGE（512×512）と「生成完了（モック）」",
          "実画像 — Bedrock Titan（モック解除 + AWS）",
          "旧バグ — 1×1 透明 PNG は不可視。最新ビルドへ更新",
        ],
      },
      {
        title: "③ AI Lab / Documents / Ops",
        body: "分析・文書・運用の追加画面です。",
        items: [
          "/lab — テキスト/画像/RAG/表形式分析 · 実験ログ",
          "/documents — 文書アップロード · ローカル索引 · KB ingest",
          "/ops — テレメトリ · フィードバック · モデルレジストリ昇格 · 品質アラート",
        ],
      },
      {
        title: "④ Embed / Guard / Prompt / Eval / Agents",
        body: "各専用画面から API を直接操作できます。",
        items: [
          "/embedding — ベクトル次元確認",
          "/guardrails — ブロック/マスク結果",
          "/prompts — テンプレート一覧 · 変数描画",
          "/evaluation — 評価実行とスコア履歴",
          "/agents — プラン付きエージェント応答",
        ],
      },
      {
        title: "⑤ Auth（JWT）",
        body: "Railway JWT_SECRET で Bearer トークンを発行できます。",
        items: [
          "POST /api/auth/token — { subject, expires_in_sec } → access_token",
          "GET /api/auth/me — Authorization: Bearer <token>",
          "任意 — REQUIRE_API_KEY=true で X-API-Key または JWT を要求",
        ],
      },
    ],
  },
  {
    label: "AWS · Railway 運用",
    steps: [
      {
        title: "Railway Variables（必須セット）",
        body: "ダッシュボードで設定し Apply → Deploy します。",
        items: [
          "DATABASE_URL — Postgres サービスを Reference（postgres:// は自動正規化）",
          "OPENAI_API_KEY — テキスト/チャット実応答（Bedrock モック時の本番向け）",
          "JWT_SECRET — /api/auth/token 署名鍵",
          "INTERNAL_API_URL=http://127.0.0.1:8180 — コンテナ内 API（:8290 禁止）",
          "APP_ENV=production · CORS_ORIGINS=* · DYNAMODB_ENDPOINT=（空）",
          "USE_BEDROCK_MOCK=true — OpenAI テキスト + 画像モックの推奨構成",
        ],
      },
      {
        title: "LLM 切替（OpenAI ↔ Bedrock）",
        body: "/health の llm_provider で現在の経路を確認します。",
        items: [
          "openai — USE_BEDROCK_MOCK=true + OPENAI_API_KEY（推奨の Railway 構成）",
          "bedrock — USE_BEDROCK_MOCK=false + AWS_ACCESS_KEY_ID / SECRET + REGION",
          "mock — どちらも未設定（ローカル体験用）",
          "画像・埋め込みの実呼び出しは Bedrock 側の設定が必要",
        ],
      },
      {
        title: "モック → 本番 Bedrock（画像・KB・Agents）",
        body: "OpenAI だけでは足りない機能を Bedrock に切り替えます。",
        items: [
          "USE_BEDROCK_MOCK=false",
          "AWS_ACCESS_KEY_ID · AWS_SECRET_ACCESS_KEY · AWS_REGION",
          "BEDROCK_IMAGE_MODEL_ID · BEDROCK_KNOWLEDGE_BASE_ID · BEDROCK_GUARDRAIL_ID",
          "BEDROCK_AGENT_ID · BEDROCK_AGENT_ALIAS_ID · S3_DOCUMENTS_BUCKET",
        ],
      },
      {
        title: "デプロイ手順",
        body: "ルート Dockerfile で Next + FastAPI を一体公開します。",
        items: [
          "railway.toml — builder = DOCKERFILE · start.sh で API 起動待ち後に Next",
          "scripts/set-railway-vars.ps1 — 共通変数の一括設定",
          "Git push → Railway 自動ビルド → Variables Apply → Deploy",
          "公開 URL /health と /image「生成」でスモークテスト → 必要なら Ctrl+F5",
        ],
      },
      {
        title: "よくあるエラーと対処",
        body: "画面や API が期待どおり動かないときの確認手順です。",
        items: [
          "Railway ECONNREFUSED :8290 — INTERNAL_API_URL を :8180 にして再デプロイ",
          "Suggested Variables の localhost を本番に追加しない",
          "database_ok=false — Postgres の DATABASE_URL Reference と Deploy を確認",
          "llm_provider=mock のまま — OPENAI_API_KEY または Bedrock 認証を設定",
          "Image 無反応に見える — 旧 1×1 モック。最新デプロイ + Ctrl+F5",
          "ローカル API 404 — 古い run.py が :8180 を占有していないか確認",
          "DynamoDB エラー — 本番は DYNAMODB_ENDPOINT 空（メモリ可）",
        ],
      },
    ],
  },
];

const L = {
  title: "利用手順",
  subtitle: "Architecture & Ops",
  dragHint: "ドラッグで移動",
  expand: "開く",
  collapse: "閉じる",
  heroTitle: "Bedrock Knowledge Base 基盤",
  heroLead:
    "Bedrock / OpenAI を中核に Text·RAG·Image·Lab·Ops を一体提供。Railway Variables（DATABASE_URL · OPENAI_API_KEY · JWT_SECRET）で本番稼働し、必要に応じて Knowledge Bases / Agents へ拡張。",
  stackLabel: "Tech stack",
  diagramLabel: "Service topology",
  workflowLabel: "詳細利用手順",
  scrollHint: "↓ 画面別の詳細手順・運用手順は下へ",
  footer:
    "▼▲ で開閉 · PC はヘッダーをドラッグして移動 · スマホは画面下部のボトムシート · 表示状態は自動保存されます。",
} as const;

type SavedState = {
  x: number;
  y: number;
  expanded: boolean;
};

function defaultPosition(mobile = false) {
  if (typeof window === "undefined") return { x: 24, y: 24 };
  if (mobile || window.innerWidth < 768) {
    return { x: 8, y: Math.max(72, window.innerHeight - 72) };
  }
  const x = Math.max(16, window.innerWidth - PANEL_WIDTH - 24);
  const y = Math.max(72, window.innerHeight - 520);
  return { x, y };
}

function clampPosition(x: number, y: number, width: number, height: number) {
  const maxX = Math.max(8, window.innerWidth - width - 8);
  const maxY = Math.max(8, window.innerHeight - height - 8);
  return {
    x: Math.min(Math.max(8, x), maxX),
    y: Math.min(Math.max(8, y), maxY),
  };
}

const variantClass: Record<NonNullable<FeaturedBlock["variant"]>, string> = {
  architecture: styles.featuredArchitecture,
  rag: styles.featuredRag,
  image: styles.featuredImage,
  embed: styles.featuredEmbed,
  guard: styles.featuredGuard,
  prompt: styles.featuredPrompt,
  eval: styles.featuredEval,
  agent: styles.featuredAgent,
  deploy: styles.featuredDeploy,
};

function FeaturedSection({ block }: { block: FeaturedBlock }) {
  const variant = block.variant ?? "architecture";
  return (
    <section
      className={`${styles.featured} ${variantClass[variant]}`}
      aria-label={block.title}
    >
      <div className={styles.featuredHead}>
        <span className={styles.featuredBadge}>{block.badge}</span>
        <strong>{block.title}</strong>
      </div>
      <p>{block.body}</p>
      {block.items?.length ? (
        <ul className={styles.items}>
          {block.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export function UsageGuidePanel() {
  const panelRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
  } | null>(null);

  const [ready, setReady] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [pos, setPos] = useState({ x: 24, y: 24 });
  const [dragging, setDragging] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mobile = window.innerWidth < 768;
    setIsMobile(mobile);
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as SavedState;
        setPos(mobile ? defaultPosition(true) : { x: parsed.x, y: parsed.y });
        setExpanded(mobile ? false : parsed.expanded);
      } catch {
        setPos(defaultPosition(mobile));
        if (mobile) setExpanded(false);
      }
    } else {
      setPos(defaultPosition(mobile));
      if (mobile) setExpanded(false);
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    const payload: SavedState = { ...pos, expanded };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }, [pos, expanded, ready]);

  useEffect(() => {
    if (!ready) return;
    const onResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) return;
      const el = panelRef.current;
      if (!el) return;
      setPos((current) =>
        clampPosition(current.x, current.y, el.offsetWidth, el.offsetHeight),
      );
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [ready]);

  const onHeaderPointerDown = useCallback(
    (e: React.PointerEvent<HTMLElement>) => {
      if (isMobile) return;
      if ((e.target as HTMLElement).closest("button")) return;
      dragRef.current = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        originX: pos.x,
        originY: pos.y,
      };
      setDragging(true);
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [pos.x, pos.y, isMobile],
  );

  const onHeaderPointerMove = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    const el = panelRef.current;
    const width = el?.offsetWidth ?? PANEL_WIDTH;
    const height = el?.offsetHeight ?? 120;
    setPos(
      clampPosition(
        drag.originX + (e.clientX - drag.startX),
        drag.originY + (e.clientY - drag.startY),
        width,
        height,
      ),
    );
  }, []);

  const onHeaderPointerUp = useCallback((e: React.PointerEvent<HTMLElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    dragRef.current = null;
    setDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
  }, []);

  if (!ready) return null;

  return (
    <div
      ref={panelRef}
      className={[
        styles.panel,
        expanded ? styles.expanded : styles.collapsed,
        dragging ? styles.dragging : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={isMobile ? undefined : { left: pos.x, top: pos.y, width: PANEL_WIDTH }}
      role="dialog"
      aria-label={L.title}
      aria-modal="false"
    >
      <header
        className={styles.header}
        onPointerDown={onHeaderPointerDown}
        onPointerMove={onHeaderPointerMove}
        onPointerUp={onHeaderPointerUp}
        onPointerCancel={onHeaderPointerUp}
      >
        <div className={styles.headerText}>
          <span className={styles.dragIcon} aria-hidden>
            ☰
          </span>
          <div className={styles.headerTitles}>
            <strong>{L.title}</strong>
            <span className={styles.headerSub}>{L.subtitle}</span>
          </div>
          <span className={styles.dragHint}>{L.dragHint}</span>
        </div>
        <button
          type="button"
          className={styles.toggle}
          aria-label={expanded ? L.collapse : L.expand}
          aria-expanded={expanded}
          onClick={() => setExpanded((open) => !open)}
        >
          {expanded ? "▼" : "▲"}
        </button>
      </header>

      {expanded ? (
        <div className={styles.body}>
          <div className={styles.hero}>
            <p className={styles.heroKicker}>Bedrock Knowledge Base Platform</p>
            <h2 className={styles.heroTitle}>{L.heroTitle}</h2>
            <p className={styles.heroLead}>{L.heroLead}</p>
            <div className={styles.stack} aria-label={L.stackLabel}>
              {techStack.map((tag) => (
                <span key={tag} className={styles.stackPill}>
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <FeaturedSection block={architectureFeatured} />

          <figure className={styles.diagram} aria-label={L.diagramLabel}>
            <figcaption>{L.diagramLabel}</figcaption>
            <pre>{archDiagram}</pre>
          </figure>

          <FeaturedSection block={ragFeatured} />
          <FeaturedSection block={imageFeatured} />
          <FeaturedSection block={embedFeatured} />
          <FeaturedSection block={guardFeatured} />
          <FeaturedSection block={promptFeatured} />
          <FeaturedSection block={evalFeatured} />
          <FeaturedSection block={agentFeatured} />
          <FeaturedSection block={deployFeatured} />

          <p className={styles.scrollHint}>{L.scrollHint}</p>
          <h3 className={styles.workflowTitle}>{L.workflowLabel}</h3>
          {guideSections.map((section) => (
            <div key={section.label} className={styles.section}>
              <p className={styles.sectionLabel}>{section.label}</p>
              <ol className={styles.steps}>
                {section.steps.map((step) => (
                  <li key={step.title}>
                    <strong>{step.title}</strong>
                    <p>{step.body}</p>
                    {step.items?.length ? (
                      <ul className={styles.items}>
                        {step.items.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ol>
            </div>
          ))}
          <p className={styles.footer}>{L.footer}</p>
        </div>
      ) : null}
    </div>
  );
}
