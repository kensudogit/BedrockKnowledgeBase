"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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

  async function snap() {
    setBusy(true);
    try {
      await api.monitorSnapshot();
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function promote(id: string, stage: string) {
    setBusy(true);
    try {
      await api.promoteModel(id, stage);
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
  const models = (ops?.models || []) as Array<Record<string, unknown>>;
  const monitor = (ops?.monitor || {}) as Record<string, unknown>;
  const alerts = (monitor.alerts || []) as Array<Record<string, unknown>>;
  const delivery = (ops?.delivery || {}) as Record<string, unknown>;
  const bedrock = (delivery.bedrock || {}) as Record<string, unknown>;

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Ops / Delivery / Monitoring</h1>
        <p>
          プロダクション化・継続デリバリー・精度モニタリング。分析は{" "}
          <Link href="/lab">AI Lab</Link>、評価は <Link href="/evaluation">Evaluation</Link>。
        </p>
      </section>

      {error ? <p className="error-banner">{error}</p> : null}

      <section className="grid">
        <article className="panel">
          <h2>Delivery status</h2>
          <p className="muted">APP_ENV: {String(ops?.app_env ?? delivery.app_env ?? "—")}</p>
          <p className="muted">mock: {String(ops?.mock_mode ?? delivery.mock_mode ?? "—")}</p>
          <div className="chips">
            <span>KB: {bedrock.knowledge_base ? "ON" : "OFF"}</span>
            <span>Guardrail: {bedrock.guardrail ? "ON" : "OFF"}</span>
            <span>Agent: {bedrock.agent ? "ON" : "OFF"}</span>
            <span>S3: {bedrock.s3 ? "ON" : "OFF"}</span>
          </div>
          <div className="controls">
            <button type="button" className="btn-ghost" onClick={reload}>
              更新
            </button>
            <button type="button" className="btn-ghost" disabled={busy} onClick={() => void snap()}>
              監視スナップショット
            </button>
          </div>
        </article>

        <article className="panel">
          <h2>Accuracy monitoring</h2>
          <p className="muted">
            healthy: {String(monitor.healthy ?? "—")} · series: {String(monitor.series_n ?? 0)}
          </p>
          {alerts.length === 0 ? (
            <p className="muted">アラートなし</p>
          ) : (
            <ul className="doc-list">
              {alerts.map((a, i) => (
                <li key={i}>
                  <div>
                    <strong>{String(a.code)}</strong>
                    <span className="muted">
                      {" "}
                      · {String(a.severity)} · {String(a.message)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
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

        <article className="panel wide">
          <h2>Model registry（プロダクション化）</h2>
          {models.length === 0 ? (
            <p className="muted">
              未登録です。<Link href="/lab">AI Lab</Link> でテーブル学習後に「レジストリ登録」、または
              Evaluation 後に API で登録してください。
            </p>
          ) : (
            <ul className="doc-list">
              {models.map((m) => (
                <li key={String(m.model_id)}>
                  <div>
                    <strong>
                      {String(m.name)} v{String(m.version)}
                    </strong>
                    <span className="muted">
                      {" "}
                      · {String(m.modality)} · {String(m.stage)} · {String(m.model_uri)}
                    </span>
                  </div>
                  <div className="controls">
                    {m.stage === "development" ? (
                      <button
                        type="button"
                        className="btn-ghost"
                        disabled={busy}
                        onClick={() => void promote(String(m.model_id), "staging")}
                      >
                        → staging
                      </button>
                    ) : null}
                    {m.stage === "staging" ? (
                      <button
                        type="button"
                        className="btn-ghost"
                        disabled={busy}
                        onClick={() => void promote(String(m.model_id), "production")}
                      >
                        → production
                      </button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
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
          {createdKey ? <p className="pre">API Key（一度だけ表示）: {createdKey}</p> : null}
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

        <article className="panel">
          <h2>Datasets / Evals</h2>
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
                    {String(
                      (e.metrics as Record<string, unknown> | undefined)?.avg_combined_score ?? "—",
                    )}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
