"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function EmbeddingPage() {
  const [text, setText] = useState("情報セキュリティ\n有給休暇申請");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const texts = text.split("\n").map((s) => s.trim()).filter(Boolean);
      const r = await api.embed(texts);
      setOut(`dimensions=${r.dimensions}\ncount=${r.embeddings.length}\nfirst[:8]=${JSON.stringify(r.embeddings[0]?.slice(0, 8))}`);
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
        <h1>Embedding</h1>
        <p>文書検索・類似度計算用のベクトル化（Titan Embed / モック）。</p>
      </section>
      <section className="panel wide">
        <textarea value={text} onChange={(e) => setText(e.target.value)} />
        <div className="controls">
          <button type="button" disabled={busy} onClick={run}>
            Embed
          </button>
        </div>
        {out && <pre className="pre">{out}</pre>}
      </section>
    </main>
  );
}
