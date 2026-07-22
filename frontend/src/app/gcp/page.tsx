"use client";

import { useCallback, useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function GcpPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [prompt, setPrompt] = useState("GCP Vertex 連携の動作確認をしてください。");
  const [textOut, setTextOut] = useState("");
  const [uploads, setUploads] = useState<Array<Record<string, unknown>>>([]);
  const [filename, setFilename] = useState("gcp-demo.md");
  const [content, setContent] = useState("# GCP demo\nUploaded via /api/gcp/storage/upload");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(() => {
    Promise.all([api.gcpStatus(), api.gcsUploads()])
      .then(([st, up]) => {
        setStatus(st);
        setUploads(up.items || []);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function runText() {
    setBusy(true);
    setError("");
    try {
      const r = await api.gcpText(prompt);
      setTextOut(`${r.text}\n\n— provider=${r.provider} mock=${String(r.mock)} model=${r.model}`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runUpload() {
    setBusy(true);
    setError("");
    try {
      await api.gcsUpload(filename, content);
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>GCP / Vertex AI</h1>
        <p>
          Vertex テキスト生成と GCS 文書アップロード。GCP_PROJECT_ID 未設定でも{" "}
          <code>USE_VERTEX_MOCK=true</code>（既定）ならモックで動作します。
        </p>
        {status?.hint ? <p className="muted">{String(status.hint)}</p> : null}
        {status?.mode ? (
          <p className="muted">
            mode: <strong>{String(status.mode)}</strong>
            {status.configured ? "" : " · project 未設定（モック可）"}
          </p>
        ) : null}
      </section>

      {error ? <p className="error-banner">{error}</p> : null}

      <section className="grid">
        <article className="panel">
          <h2>接続状態</h2>
          <pre className="pre">{JSON.stringify(status, null, 2)}</pre>
          <button type="button" className="btn-ghost" onClick={reload}>
            再読込
          </button>
        </article>

        <article className="panel">
          <h2>Vertex テキスト</h2>
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4} />
          <div className="controls">
            <button type="button" disabled={busy} onClick={() => void runText()}>
              生成
            </button>
          </div>
          {textOut ? <pre className="pre">{textOut}</pre> : null}
        </article>

        <article className="panel">
          <h2>GCS アップロード</h2>
          <label className="field">
            ファイル名
            <input value={filename} onChange={(e) => setFilename(e.target.value)} />
          </label>
          <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={5} />
          <div className="controls">
            <button type="button" disabled={busy} onClick={() => void runUpload()}>
              アップロード
            </button>
          </div>
          <ul className="plain-list">
            {uploads
              .slice()
              .reverse()
              .slice(0, 8)
              .map((u) => (
                <li key={String(u.object_id)}>
                  {String(u.filename)} · {String(u.gcs_uri)} · mock={String(u.mock)}
                </li>
              ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
