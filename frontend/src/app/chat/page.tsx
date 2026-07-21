"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function ChatPage() {
  const [q, setQ] = useState("有給休暇の申請手順は？");
  const [mode, setMode] = useState<"rag" | "text">("rag");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      if (mode === "rag") {
        const r = await api.rag(q);
        setOut(`${r.answer}\n\n---\ncitations: ${JSON.stringify(r.citations, null, 2)}`);
      } else {
        const r = await api.text(q);
        setOut(r.text);
      }
    } catch (e) {
      setOut(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Text Generation / RAG</h1>
        <p>社内チャット・FAQ・文書検索向け。Knowledge Base（または samples/）を根拠に回答します。</p>
      </section>
      <section className="panel wide">
        <div className="controls">
          <select value={mode} onChange={(e) => setMode(e.target.value as "rag" | "text")}>
            <option value="rag">RAG（文書検索）</option>
            <option value="text">Text Generation</option>
          </select>
          <button type="button" disabled={busy} onClick={run}>
            実行
          </button>
        </div>
        <textarea value={q} onChange={(e) => setQ(e.target.value)} />
        {out && <pre className="pre">{out}</pre>}
      </section>
    </main>
  );
}
