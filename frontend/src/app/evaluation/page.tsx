"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function EvaluationPage() {
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const r = await api.evalRun();
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
        <h1>Model Evaluation</h1>
        <p>ゴールデン質問セットでキーワード一致率などを計測します。</p>
      </section>
      <section className="panel wide">
        <div className="controls">
          <button type="button" disabled={busy} onClick={run}>
            評価実行
          </button>
        </div>
        {out && <pre className="pre">{out}</pre>}
      </section>
    </main>
  );
}
