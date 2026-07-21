"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function AgentsPage() {
  const [msg, setMsg] = useState("契約書の秘密保持条項を確認し、リスクを要約して");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [out, setOut] = useState("");
  const [plan, setPlan] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const r = await api.agent(msg, sessionId);
      if (r.session_id) setSessionId(r.session_id);
      setOut(r.answer);
      setPlan(r.plan ?? "");
    } catch (e) {
      setOut(String(e));
      setPlan("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>AI Agents</h1>
        <p>Bedrock Agents による業務自動化（未設定時は RAG + 計画モック）。セッションを保持して連続依頼できます。</p>
      </section>
      <section className="panel wide">
        <div className="controls">
          {sessionId ? <span className="badge">session: {sessionId.slice(0, 8)}…</span> : null}
          <button
            type="button"
            className="btn-ghost"
            onClick={() => {
              setSessionId(null);
              setOut("");
              setPlan("");
            }}
          >
            セッションリセット
          </button>
        </div>
        <textarea value={msg} onChange={(e) => setMsg(e.target.value)} />
        <div className="controls">
          <button type="button" disabled={busy} onClick={run}>
            Invoke
          </button>
        </div>
        {out ? <pre className="pre">{out}</pre> : null}
        {plan ? (
          <>
            <h2 style={{ marginTop: "1rem" }}>Plan</h2>
            <pre className="pre">{plan}</pre>
          </>
        ) : null}
      </section>
    </main>
  );
}
