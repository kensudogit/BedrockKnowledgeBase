"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function GuardrailsPage() {
  const [text, setText] = useState("会議室の予約方法を教えてください");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const r = await api.guard(text);
      setOut(JSON.stringify(r, null, 2));
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
        <h1>Guardrails</h1>
        <p>有害・機密漏えいリスクのある入出力を検知・遮断します。</p>
      </section>
      <section className="panel wide">
        <textarea value={text} onChange={(e) => setText(e.target.value)} />
        <div className="controls">
          <button type="button" disabled={busy} onClick={run}>
            検査
          </button>
        </div>
        {out && <pre className="pre">{out}</pre>}
      </section>
    </main>
  );
}
