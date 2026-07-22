"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

function buildPlaceholderDataUrl(prompt: string): string {
  const safe = prompt
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  const line1 = safe.slice(0, 42);
  const line2 = safe.slice(42, 84);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#0f2744"/><stop offset="100%" stop-color="#0284c7"/>
  </linearGradient></defs>
  <rect width="512" height="512" fill="url(#g)"/>
  <rect x="28" y="28" width="456" height="456" rx="24" fill="none" stroke="#7dd3fc" stroke-width="2" opacity="0.55"/>
  <text x="256" y="170" text-anchor="middle" fill="#e0f2fe" font-size="34" font-family="Segoe UI, sans-serif" font-weight="700">MOCK IMAGE</text>
  <text x="256" y="220" text-anchor="middle" fill="#bae6fd" font-size="16" font-family="Segoe UI, sans-serif">Bedrock 未接続 — プレースホルダ</text>
  <text x="256" y="290" text-anchor="middle" fill="#ffffff" font-size="18" font-family="Segoe UI, sans-serif">${line1}</text>
  <text x="256" y="322" text-anchor="middle" fill="#ffffff" font-size="18" font-family="Segoe UI, sans-serif">${line2}</text>
  <text x="256" y="400" text-anchor="middle" fill="#93c5fd" font-size="14" font-family="Segoe UI, sans-serif">USE_BEDROCK_MOCK=false で Titan Image へ</text>
</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function isTinyOrEmptyDataUrl(dataUrl: string | undefined): boolean {
  if (!dataUrl) return true;
  // classic 1x1 PNG used by the old mock
  if (dataUrl.includes("iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB")) return true;
  return false;
}

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
