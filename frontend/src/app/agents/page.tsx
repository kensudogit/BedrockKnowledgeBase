"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function AgentsPage() {
  const [msg, setMsg] = useState("契約書の秘密保持条項を確認し、リスクを要約して");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const r = await api.agent(msg);
      setOut(`${r.answer}\n\n--- plan ---\n${r.plan ?? ""}`);
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
        <h1>AI Agents</h1>
        <p>Bedrock Agents による業務自動化（未設定時は RAG + 計画モック）。</p>
      </section>
      <section className="panel wide">
        <textarea value={msg} onChange={(e) => setMsg(e.target.value)} />
        <div className="controls">
          <button type="button" disabled={busy} onClick={run}>
            Invoke
          </button>
        </div>
        {out && <pre className="pre">{out}</pre>}
      </section>
    </main>
  );
}
