"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

type Modality = "text" | "image" | "rag" | "tabular";

export default function LabPage() {
  const [modality, setModality] = useState<Modality>("text");
  const [prompt, setPrompt] = useState("社内FAQの改善ポイントを3つ挙げて");
  const [csv, setCsv] = useState("");
  const [target, setTarget] = useState("churn");
  const [out, setOut] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadDemo() {
    const d = await api.demoCsv();
    setCsv(d.csv_text);
    setTarget(d.target);
    setModality("tabular");
  }

  async function run() {
    setBusy(true);
    setError("");
    setOut(null);
    try {
      let r: Record<string, unknown>;
      if (modality === "text") r = await api.analyzeText(prompt);
      else if (modality === "image") r = await api.analyzeImage(prompt);
      else if (modality === "rag") r = await api.analyzeRag(prompt, "document_search");
      else r = await api.analyzeTabular(csv, target || undefined);
      setOut(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function registerFromTrain() {
    const train = out?.train as Record<string, unknown> | undefined;
    const exp = out?.experiment as Record<string, unknown> | undefined;
    if (!train) return;
    setBusy(true);
    try {
      const m = await api.registerModel({
        name: `tabular-${target}`,
        modality: "tabular",
        version: "0.1.0",
        provider: "local",
        metrics: train.metrics || {},
        experiment_id: exp?.experiment_id,
        stage: "development",
        meta: { model: train.model },
      });
      setOut({ ...out, registered: m });
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const imageUrl =
    modality === "image"
      ? ((out?.result as Record<string, unknown> | undefined)?.data_url as string | undefined)
      : undefined;

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>AI Lab</h1>
        <p>
          生成AI・自然言語・画像・テーブルデータの分析と実験記録。結果は Experiment に残り、Model
          Registry へ昇格できます。
        </p>
      </section>

      <section className="panel wide">
        <div className="controls">
          <select value={modality} onChange={(e) => setModality(e.target.value as Modality)}>
            <option value="text">Text / NLP</option>
            <option value="rag">RAG / 文書</option>
            <option value="image">Image</option>
            <option value="tabular">Tabular</option>
          </select>
          {modality === "tabular" ? (
            <button type="button" className="btn-ghost" onClick={() => void loadDemo()}>
              デモCSV読込
            </button>
          ) : null}
          <button type="button" disabled={busy} onClick={() => void run()}>
            分析実行
          </button>
          {out?.train ? (
            <button type="button" className="btn-ghost" disabled={busy} onClick={() => void registerFromTrain()}>
              レジストリ登録
            </button>
          ) : null}
        </div>

        {modality === "tabular" ? (
          <>
            <div className="controls">
              <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="target列" />
            </div>
            <textarea
              value={csv}
              onChange={(e) => setCsv(e.target.value)}
              rows={10}
              placeholder="CSV を貼り付け"
            />
          </>
        ) : (
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={5} />
        )}

        {error ? <p className="error-banner">{error}</p> : null}
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={imageUrl} alt="generated" style={{ marginTop: "1rem", maxWidth: 320, borderRadius: 12 }} />
        ) : null}
        {out ? <pre className="pre">{JSON.stringify(out, null, 2)}</pre> : null}
      </section>
    </main>
  );
}
