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
  title: "Next.js BFF + FastAPI + Amazon Bedrock",
  body:
    "Web は同一オリジンで FastAPI にプロキシ。ローカルはモック、本番は Bedrock Runtime / Knowledge Bases / Agents / Guardrails に切替。API キーはサーバー側のみ。",
  variant: "architecture",
  items: [
    "Next.js — Text/RAG · Image · Embedding · Guardrails · Prompts · Evaluation · Agents",
    "FastAPI :8290 — Bedrock 呼び出し · RAG · DynamoDB プロンプト管理",
    "PostgreSQL — セッション・監査ログ用（任意）",
    "DynamoDB — Prompt / Eval / Session（未接続時はメモリフォールバック）",
    "S3 → Knowledge Base → Bedrock — 文書 RAG",
    "/health — 生存確認 · /docs — Swagger",
  ],
};

const ragFeatured: FeaturedBlock = {
  badge: "Text / RAG",
  title: "テキスト生成と社内文書検索（/chat）",
  body:
    "Claude 系テキスト生成と Knowledge Bases による RAG を同一画面で試せます。モック時は samples/ 文書をローカル検索します。",
  variant: "rag",
  items: [
    "Text Generation — POST /api/text/generate（system / guardrail 任意）",
    "RAG — POST /api/rag/query（use_case で FAQ / 契約書 / 医療 等を切替）",
    "利用例 — 社内チャット · FAQ · 文書検索 · 契約書レビュー · コード生成",
    "本番 — BEDROCK_KNOWLEDGE_BASE_ID + S3 文書同期",
  ],
};

const imageFeatured: FeaturedBlock = {
  badge: "Image",
  title: "画像生成（/image）",
  body: "Titan Image 等でプロンプトから画像を生成。モック時はプレースホルダ SVG を返します。",
  variant: "image",
  items: [
    "POST /api/image/generate — prompt → data_url",
    "用途 — 資料・UI モック・マニュアル挿絵の試作",
    "本番 — BEDROCK_IMAGE_MODEL_ID（Titan Image Generator）",
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
    "本番 — Titan Embed Text v2",
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
  title: "Railway · Terraform · ローカル",
  body:
    "単一コンテナ（Next + uvicorn）で Railway 公開。AWS 基盤は Terraform で S3 / Lambda / API GW / DynamoDB を定義。",
  variant: "deploy",
  items: [
    "Railway — Dockerfile + railway.toml + start.sh",
    "Variables — USE_BEDROCK_MOCK · CORS_ORIGINS · DATABASE_URL",
    "IaC — terraform/ で AI 基盤をコード化",
    "Java — java-spring/ で Runtime API 組込みスタブ",
  ],
};

const techStack = [
  "Python · FastAPI",
  "Next.js 15 · React",
  "PostgreSQL · DynamoDB",
  "Amazon Bedrock",
  "Knowledge Bases",
  "Guardrails · Agents",
  "S3 · Lambda · API GW",
  "Terraform IaC",
  "Railway · Docker",
] as const;

const archDiagram = `Browser (Enterprise User)
    │ HTTPS
    ▼
Next.js :PORT (Railway / :3010 local)
    ├─ /chat          Text · RAG
    ├─ /image         Image Generation
    ├─ /embedding     Embedding
    ├─ /guardrails    Guardrails
    ├─ /prompts       Prompt Management
    ├─ /evaluation    Model Evaluation
    ├─ /agents        Bedrock Agents
    └─ /api/* ──proxy──► FastAPI :8290
              ├─ Bedrock Runtime (Text / Image / Embed)
              ├─ Knowledge Bases (RAG ← S3)
              ├─ Guardrails · Agents
              ├─ DynamoDB (prompts · evals)
              └─ PostgreSQL (optional)`;

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
          "ナビ — Text/RAG · Image · Embedding · Guardrails · Prompts · Evaluation · Agents",
          "推奨フロー — ホーム → Text/RAG → Guardrails → Prompts → Agents",
          "プレゼン時 — パネルを画面端に寄せ、メイン画面を広く使う",
        ],
      },
      {
        title: "接続確認（最初に）",
        body: "本番・ローカル共通。障害切り分けとデモ前チェックの起点です。",
        items: [
          "ローカル UI — http://localhost:3010",
          "ローカル API — http://localhost:8290/docs",
          "/health — app: bedrock-knowledge-base · mock_mode を確認",
          "MOCK MODE — AWS 無しで 6 機能を体験可能",
        ],
      },
      {
        title: "初回セットアップ（5 分）",
        body: "ローカル開発の最短手順です。",
        items: [
          "① setup.bat — Postgres · DynamoDB Local · 依存関係",
          "② backend — python run.py（:8290）",
          "③ frontend — npm run dev（:3010）",
          "④ /chat で「有給休暇の申請手順」など RAG を試す",
          "⑤ /guardrails · /prompts · /agents を順に確認",
        ],
      },
    ],
  },
  {
    label: "6コア機能 詳細",
    steps: [
      {
        title: "① Text Generation / RAG",
        body: "/chat でプロンプト送信または文書質問を実行します。",
        items: [
          "通常生成 — システムプロンプト付きテキスト生成",
          "RAG — samples/ または Knowledge Base から根拠付き回答",
          "ユースケース — 社内 FAQ · 契約書 · 医療文書 · 金融アドバイス",
        ],
      },
      {
        title: "②〜⑥ Image / Embed / Guard / Prompt / Eval",
        body: "各専用画面から API を直接操作できます。",
        items: [
          "/image — プロンプトから画像 data URL",
          "/embedding — 複数テキストのベクトル次元を確認",
          "/guardrails — 入力テキストのブロック/マスク結果",
          "/prompts — テンプレート一覧 · 変数描画",
          "/evaluation — 評価実行とスコア履歴",
        ],
      },
    ],
  },
  {
    label: "AWS · Railway 運用",
    steps: [
      {
        title: "モック → 本番 Bedrock",
        body: ".env / Railway Variables で切替します。",
        items: [
          "USE_BEDROCK_MOCK=false",
          "AWS_ACCESS_KEY_ID · AWS_SECRET_ACCESS_KEY · AWS_REGION",
          "BEDROCK_KNOWLEDGE_BASE_ID · BEDROCK_GUARDRAIL_ID",
          "BEDROCK_AGENT_ID · BEDROCK_AGENT_ALIAS_ID · S3_DOCUMENTS_BUCKET",
        ],
      },
      {
        title: "Railway デプロイ",
        body: "ルート Dockerfile で Next + FastAPI を一体公開します。",
        items: [
          "railway.toml — builder = DOCKERFILE",
          "scripts/set-railway-vars.ps1 — モック用変数を一括設定",
          "CORS_ORIGINS=* · DYNAMODB_ENDPOINT=（空）",
          "公開 URL の /health で稼働確認",
        ],
      },
      {
        title: "よくあるエラーと対処",
        body: "画面や API が期待どおり動かないときの確認手順です。",
        items: [
          "空白ページ :3000 — 他アプリ占有。本プロジェクトは :3010",
          "API 404 — 古いプロセスがポートを掴む場合あり。:8290 を確認",
          "RAG が薄い — samples/*.md の有無 · KB ID 設定を確認",
          "DynamoDB エラー — ローカルは DYNAMODB_ENDPOINT · 本番は空でメモリ可",
          "Railway Railpack 失敗 — Dockerfile / start.sh がルートにあるか確認",
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
    "Amazon Bedrock を中核に Text / Image / Embedding / Guardrails / Prompt / Evaluation と RAG・Agents を一体提供。社内チャットから文書検索・業務自動化まで。",
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
