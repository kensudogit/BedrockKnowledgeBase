"use client";

import { useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function ImagePage() {
  const [prompt, setPrompt] = useState("青空の下のモダンなオフィス、イラスト風");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    try {
      const r = await api.image(prompt);
      setUrl(r.data_url);
    } catch (e) {
      setUrl("");
      alert(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Image Generation</h1>
        <p>Amazon Titan Image 等による画像生成（ローカルはモック PNG）。</p>
      </section>
      <section className="panel wide">
        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <div className="controls">
          <button type="button" disabled={busy} onClick={run}>
            生成
          </button>
        </div>
        {url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt="generated" style={{ maxWidth: 320, borderRadius: 12, border: "1px solid var(--line)" }} />
        )}
      </section>
    </main>
  );
}
