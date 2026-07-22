"use client";

import { FormEvent, Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Nav } from "@/components/Nav";
import { api, type ChatMessage, type Citation } from "@/lib/api";

type UseCase = { id: string; label: string };

export default function ChatPage() {
  return (
    <Suspense fallback={<main><Nav /><p className="muted">読み込み中…</p></main>}>
      <ChatPageInner />
    </Suspense>
  );
}

function ChatPageInner() {
  const search = useSearchParams();
  const [q, setQ] = useState("");
  const [mode, setMode] = useState<"rag" | "text">("rag");
  const [useCase, setUseCase] = useState("document_search");
  const [cases, setCases] = useState<UseCase[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState<string>("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const uc = search.get("use_case");
    if (uc) setUseCase(uc);
  }, [search]);

  useEffect(() => {
    api.useCases().then((u) => setCases(u.items)).catch(() => undefined);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(e?: FormEvent) {
    e?.preventDefault();
    const text = q.trim();
    if (!text || busy) return;
    setBusy(true);
    setError("");
    setQ("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    try {
      const r = await api.chat({
        message: text,
        use_case: useCase,
        mode,
        session_id: sessionId,
      });
      setSessionId(r.session_id);
      setMessages(
        r.messages?.length
          ? r.messages
          : [
              { role: "user", content: text },
              { role: "assistant", content: r.answer, citations: r.citations },
            ],
      );
      const flags = [
        r.mock ? "MOCK" : "LIVE",
        r.blocked ? "BLOCKED" : null,
        r.source || null,
      ].filter(Boolean);
      setMeta(flags.join(" · "));
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  function resetChat() {
    setSessionId(null);
    setMessages([]);
    setMeta("");
    setError("");
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Text Generation / RAG</h1>
        <p>
          マルチターン会話・ユースケース切替・根拠引用付き。文書は「Documents」から追加できます。
        </p>
      </section>

      <section className="panel wide chat-shell">
        <div className="controls">
          <select value={mode} onChange={(e) => setMode(e.target.value as "rag" | "text")}>
            <option value="rag">RAG（文書検索）</option>
            <option value="text">Text Generation</option>
          </select>
          <select value={useCase} onChange={(e) => setUseCase(e.target.value)}>
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
          <button type="button" className="btn-ghost" onClick={resetChat}>
            新規セッション
          </button>
          {meta ? <span className="badge">{meta}</span> : null}
        </div>

        <div className="chat-thread" aria-live="polite">
          {messages.length === 0 ? (
            <p className="muted chat-empty">
              例: 「有給休暇の申請手順は？」「秘密保持条項の確認ポイントは？」
            </p>
          ) : null}
          {messages.map((m, i) => (
            <article
              key={`${m.role}-${i}-${m.created_at || ""}`}
              className={`chat-bubble ${m.role === "user" ? "is-user" : "is-assistant"}`}
            >
              <header>{m.role === "user" ? "あなた" : "アシスタント"}</header>
              <div className="chat-content">{m.content}</div>
              {m.role === "assistant" && m.citations?.length ? (
                <CitationList citations={m.citations} />
              ) : null}
              {m.role === "assistant" ? (
                <div className="feedback-row">
                  <button
                    type="button"
                    className="btn-ghost"
                    disabled={busy}
                    onClick={() =>
                      void api
                        .feedback({
                          rating: 1,
                          session_id: sessionId,
                          message_index: i,
                          use_case: useCase,
                          answer_preview: m.content,
                        })
                        .then(() => setMeta((prev) => `${prev} · 👍`.trim()))
                        .catch((e) => setError(String(e)))
                    }
                  >
                    👍 有用
                  </button>
                  <button
                    type="button"
                    className="btn-ghost"
                    disabled={busy}
                    onClick={() =>
                      void api
                        .feedback({
                          rating: -1,
                          session_id: sessionId,
                          message_index: i,
                          use_case: useCase,
                          answer_preview: m.content,
                        })
                        .then(() => setMeta((prev) => `${prev} · 👎`.trim()))
                        .catch((e) => setError(String(e)))
                    }
                  >
                    👎 要改善
                  </button>
                </div>
              ) : null}
            </article>
          ))}
          {busy ? <p className="muted">回答生成中…</p> : null}
          <div ref={bottomRef} />
        </div>

        {error ? <p className="error-banner">{error}</p> : null}

        <form className="chat-composer" onSubmit={send}>
          <textarea
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="質問を入力（Enter+Ctrl で送信）"
            rows={3}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                void send();
              }
            }}
          />
          <button type="submit" disabled={busy || !q.trim()}>
            送信
          </button>
        </form>
      </section>
    </main>
  );
}

function CitationList({ citations }: { citations: Citation[] }) {
  return (
    <div className="cite-list">
      <p className="cite-label">根拠</p>
      {citations.map((c, i) => (
        <div key={c.id || i} className="cite-card">
          <div className="cite-head">
            <strong>{c.source || `出典 ${i + 1}`}</strong>
            {typeof c.score === "number" ? (
              <span className="cite-score">{(c.score * 100).toFixed(0)}%</span>
            ) : null}
          </div>
          <p>{c.text}</p>
        </div>
      ))}
    </div>
  );
}
