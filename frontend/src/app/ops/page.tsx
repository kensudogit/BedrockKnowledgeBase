"use client";

import { useCallback, useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function OpsPage() {
  const [ops, setOps] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [name, setName] = useState("client-poc");
  const [client, setClient] = useState("Customer A");
  const [createdKey, setCreatedKey] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(() => {
    api
      .opsSummary()
      .then(setOps)
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function createProj() {
    setBusy(true);
    setError("");
    try {
      const r = await api.createProject({
        name,
        client_name: client,
        env: "staging",
        notes: "受託 PoC プロジェクト",
      });
      setCreatedKey(String(r.api_key || ""));
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const telemetry = (ops?.telemetry || {}) as Record<string, unknown>;
  const feedback = (ops?.feedback || {}) as Record<string, unknown>;
  const projects = (ops?.projects || []) as Array<Record<string, unknown>>;
  const datasets = (ops?.datasets || []) as Array<Record<string, unknown>>;
  const evals = (ops?.recent_evals || []) as Array<Record<string, unknown>>;

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Ops / MLOps</h1>
        <p>
          受託・自社向けの運用ダッシュボード。テレメトリ、フィードバック、プロジェクト、評価データセットを集約します。
        </p>
      </section>

      {error ? <p className="error-banner">{error}</p> : null}

      <section className="grid">
        <article className="panel">
          <h2>Environment</h2>
          <p className="muted">APP_ENV: {String(ops?.app_env ?? "—")}</p>
          <p className="muted">mock: {String(ops?.mock_mode ?? "—")}</p>
          <button type="button" className="btn-ghost" onClick={reload}>
            更新
          </button>
        </article>

        <article className="panel">
          <h2>Telemetry</h2>
          <div className="metric-row" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div className="metric">
              <span>Events</span>
              <strong>{String(telemetry.n_events ?? 0)}</strong>
            </div>
            <div className="metric">
              <span>Avg ms</span>
              <strong>{String(telemetry.avg_latency_ms ?? 0)}</strong>
            </div>
            <div className="metric">
              <span>p95 ms</span>
              <strong>{String(telemetry.p95_latency_ms ?? 0)}</strong>
            </div>
            <div className="metric">
              <span>Error rate</span>
              <strong>{String(telemetry.error_rate ?? 0)}</strong>
            </div>
          </div>
        </article>

        <article className="panel">
          <h2>Human feedback</h2>
          <div className="metric-row" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div className="metric">
              <span>👍</span>
              <strong>{String(feedback.up ?? 0)}</strong>
            </div>
            <div className="metric">
              <span>👎</span>
              <strong>{String(feedback.down ?? 0)}</strong>
            </div>
            <div className="metric">
              <span>Approval</span>
              <strong>{String(feedback.approval_rate ?? "—")}</strong>
            </div>
            <div className="metric">
              <span>Total</span>
              <strong>{String(feedback.n ?? 0)}</strong>
            </div>
          </div>
        </article>

        <article className="panel">
          <h2>Projects（受託分離）</h2>
          <div className="controls">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="name" />
            <input value={client} onChange={(e) => setClient(e.target.value)} placeholder="client" />
            <button type="button" disabled={busy} onClick={createProj}>
              作成
            </button>
          </div>
          {createdKey ? (
            <p className="pre">API Key（一度だけ表示）: {createdKey}</p>
          ) : null}
          <ul className="doc-list">
            {projects.map((p) => (
              <li key={String(p.project_id)}>
                <div>
                  <strong>{String(p.name)}</strong>
                  <span className="muted">
                    {" "}
                    · {String(p.client_name)} · {String(p.env)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel wide">
          <h2>Datasets / Recent evals</h2>
          <div className="chips">
            {datasets.map((d) => (
              <span key={String(d.dataset_id)}>
                {String(d.name)} ({String(d.n_items)})
              </span>
            ))}
          </div>
          <ul className="doc-list" style={{ marginTop: "0.75rem" }}>
            {evals.map((e) => (
              <li key={String(e.eval_id)}>
                <div>
                  <strong>{String(e.name)}</strong>
                  <span className="muted">
                    {" "}
                    · combined{" "}
                    {String((e.metrics as Record<string, unknown> | undefined)?.avg_combined_score ?? "—")}
                  </span>
                </div>
              </li>
            ))}
          </ul>
          <p className="muted" style={{ marginTop: "0.75rem" }}>
            DS 手順: docs/DS_WORKFLOW.md · CLI: python -m src.scripts.run_eval · export: python -m
            src.scripts.export_ops
          </p>
        </article>
      </section>
    </main>
  );
}
