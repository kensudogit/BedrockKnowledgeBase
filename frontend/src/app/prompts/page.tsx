"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function PromptsPage() {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [name, setName] = useState("カスタム FAQ");
  const [useCase, setUseCase] = useState("faq");
  const [template, setTemplate] = useState(
    "あなたは FAQ 担当です。\n質問: {{question}}\n根拠に沿って番号付きで答えてください。",
  );
  const [busy, setBusy] = useState(false);

  async function reload() {
    try {
      const r = await api.prompts();
      setItems(r.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function save() {
    setBusy(true);
    setError("");
    try {
      await api.upsertPrompt({
        name,
        template,
        use_case: useCase,
        variables: ["question"],
      });
      await reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Prompt Management</h1>
        <p>
          テンプレートを保存し、RAG のユースケースと対応付けます。会話は{" "}
          <Link href="/chat">Text / RAG</Link> で実行。
        </p>
      </section>
      {error ? <p className="error-banner">{error}</p> : null}

      <section className="panel wide" style={{ marginBottom: "1rem" }}>
        <h2>新規 / 更新</h2>
        <div className="controls">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="名前" />
          <input
            value={useCase}
            onChange={(e) => setUseCase(e.target.value)}
            placeholder="use_case"
          />
          <button type="button" disabled={busy} onClick={save}>
            保存
          </button>
        </div>
        <textarea value={template} onChange={(e) => setTemplate(e.target.value)} rows={6} />
      </section>

      <section className="grid">
        {items.map((p) => (
          <article className="panel" key={String(p.prompt_id)}>
            <h2>{String(p.name)}</h2>
            <p className="muted">
              use_case: {String(p.use_case)} / v{String(p.version)}
            </p>
            <pre className="pre">{String(p.template)}</pre>
            <div className="controls">
              <Link className="btn-ghost" href={`/chat?use_case=${encodeURIComponent(String(p.use_case))}`}>
                このユースケースでチャット
              </Link>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
