"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";
import { buildPlaceholderDataUrl, isTinyOrEmptyDataUrl } from "@/lib/imagePlaceholder";

export default function ImagePage() {
  const [prompt, setPrompt] = useState("青空の下のモダンなオフィス、イラスト風");
  const [url, setUrl] = useState("");
  const [mock, setMock] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    const text = prompt.trim();
    if (!text || busy) return;
    setBusy(true);
    setError("");
    setStatus("生成中…");
    try {
      const r = await api.image(text);
      const isMock = Boolean(r.mock);
      const displayUrl =
        isMock || isTinyOrEmptyDataUrl(r.data_url)
          ? buildPlaceholderDataUrl(text)
          : r.data_url;
      setUrl(displayUrl);
      setMock(isMock || isTinyOrEmptyDataUrl(r.data_url));
      setStatus(isMock || isTinyOrEmptyDataUrl(r.data_url) ? "生成完了（モック）" : "生成完了");
    } catch (e) {
      setUrl("");
      setMock(false);
      setStatus("");
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Image Generation</h1>
        <p>
          Amazon Titan Image 等による画像生成。モック時は見えるプレースホルダを表示します（本番は{" "}
          <code>USE_BEDROCK_MOCK=false</code>）。
        </p>
      </section>
      <section className="panel wide">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={busy}
        />
        <div className="controls">
          <button type="button" disabled={busy || !prompt.trim()} onClick={run}>
            {busy ? "生成中…" : "生成"}
          </button>
          {status && !error && (
            <span style={{ marginLeft: 12, color: "#93c5fd", fontSize: 14 }}>{status}</span>
          )}
        </div>
        {error && (
          <p style={{ color: "#fca5a5", marginTop: 12 }}>エラー: {error}</p>
        )}
        {url && (
          <div style={{ marginTop: 16 }}>
            {mock && (
              <p style={{ color: "#93c5fd", marginBottom: 8, fontSize: 14 }}>
                MOCK MODE — プレースホルダ画像です。実画像にするには AWS 認証と{" "}
                <code>USE_BEDROCK_MOCK=false</code> を設定してください。
              </p>
            )}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={url}
              alt="generated"
              style={{
                width: "min(100%, 512px)",
                aspectRatio: "1 / 1",
                objectFit: "contain",
                borderRadius: 12,
                border: "1px solid var(--line)",
                background: "#0b1220",
                display: "block",
              }}
            />
          </div>
        )}
      </section>
    </main>
  );
}
