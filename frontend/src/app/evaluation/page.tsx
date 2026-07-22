"use client";

import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

type EvalRun = {
  eval_id?: string;
  name?: string;
  dataset_id?: string;
  metrics?: Record<string, number | string | boolean>;
  samples?: Array<Record<string, unknown>>;
  created_at?: string;
};

type Dataset = { dataset_id: string; name: string; n_items: number; version?: string };

export default function EvaluationPage() {
  const [latest, setLatest] = useState<EvalRun | null>(null);
  const [history, setHistory] = useState<EvalRun[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState("golden_default");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadHistory() {
    try {
      const r = await api.evals();
      setHistory((r.items || []) as EvalRun[]);
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    void loadHistory();
    api
      .datasets()
      .then((r) => setDatasets(r.items))
      .catch(() => undefined);
  }, []);

  async function run() {
    setBusy(true);
    setError("");
    try {
      const r = (await api.evalRun({
        dataset_id: datasetId,
        name: `ui-${datasetId}`,
        fail_under: 0.2,
      })) as EvalRun;
      setLatest(r);
      await loadHistory();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const m = latest?.metrics || history[0]?.metrics;

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Model Evaluation</h1>
        <p>
          外部化ゴールデンセットで RAG 品質を計測。CI でも同 CLI を品質ゲートに使えます。
        </p>
      </section>
      <section className="panel wide">
        <div className="controls">
          <select value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
            {datasets.length === 0 ? (
              <option value="golden_default">golden_default</option>
            ) : (
              datasets.map((d) => (
                <option key={d.dataset_id} value={d.dataset_id}>
                  {d.name} (v{d.version || "?"} · {d.n_items})
                </option>
              ))
            )}
          </select>
          <button type="button" disabled={busy} onClick={run}>
            評価実行
          </button>
        </div>
        {error ? <p className="error-banner">{error}</p> : null}
        {m ? (
          <div className="metric-row">
            <div className="metric">
              <span>Combined</span>
              <strong>{String(m.avg_combined_score ?? "—")}</strong>
            </div>
            <div className="metric">
              <span>Keyword</span>
              <strong>{String(m.avg_keyword_score ?? "—")}</strong>
            </div>
            <div className="metric">
              <span>Retrieval</span>
              <strong>{String(m.avg_retrieval_score ?? "—")}</strong>
            </div>
            <div className="metric">
              <span>Gate</span>
              <strong>
                {m.passed === undefined ? "—" : m.passed ? "PASS" : "FAIL"}
              </strong>
            </div>
          </div>
        ) : null}
        {latest?.samples ? (
          <div className="eval-samples">
            {latest.samples.map((s) => (
              <article key={String(s.id)} className="cite-card">
                <div className="cite-head">
                  <strong>{String(s.id)}</strong>
                  <span className="cite-score">
                    {String(s.combined_score ?? s.keyword_score)}
                  </span>
                </div>
                <p className="muted">{String(s.prompt)}</p>
                <p>{String(s.answer || "").slice(0, 280)}</p>
              </article>
            ))}
          </div>
        ) : null}
        {history.length > 0 ? (
          <>
            <h2 style={{ marginTop: "1.25rem" }}>履歴</h2>
            <ul className="doc-list">
              {history.slice(0, 8).map((h) => (
                <li key={String(h.eval_id)}>
                  <div>
                    <strong>{h.name}</strong>
                    <span className="muted">
                      {" "}
                      · {h.dataset_id || "—"} · combined{" "}
                      {String(h.metrics?.avg_combined_score ?? "—")} · {h.created_at}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </>
        ) : null}
      </section>
    </main>
  );
}
