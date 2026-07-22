"use client";

import { useCallback, useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

type Doc = {
  document_id: string;
  filename: string;
  bytes?: number;
  status?: string;
};

export default function DocumentsPage() {
  const [items, setItems] = useState<Doc[]>([]);
  const [filename, setFilename] = useState("memo.md");
  const [content, setContent] = useState(
    "# メモ\n\nここに社内 FAQ や手順を貼り付けてインデックスできます。\n",
  );
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const reload = useCallback(() => {
    api
      .documents()
      .then((r) => setItems(r.items as Doc[]))
      .catch((e) => setMsg(String(e)));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function ingest() {
    setBusy(true);
    setMsg("");
    try {
      await api.ingestDocument(filename, content);
      setMsg("インデックスに追加しました。/chat の RAG から検索できます。");
      reload();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function ingestKb() {
    setBusy(true);
    setMsg("");
    try {
      const r = await api.kbIngest(filename, content);
      setMsg(`KB ingest: ${String(r.status)} ${String(r.message || r.s3_key || "")}`);
      reload();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onFile(file: File | null) {
    if (!file) return;
    setBusy(true);
    setMsg("");
    try {
      await api.uploadDocument(file);
      setMsg(`${file.name} を取り込みました。`);
      reload();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    setBusy(true);
    try {
      await api.deleteDocument(id);
      reload();
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Documents</h1>
        <p>
          Markdown / テキストをローカル索引に追加。本番では S3 → Knowledge Base 同期に置き換えます。
        </p>
      </section>

      <section className="grid">
        <article className="panel">
          <h2>テキスト取込</h2>
          <div className="controls">
            <input value={filename} onChange={(e) => setFilename(e.target.value)} />
            <button type="button" disabled={busy} onClick={ingest}>
              索引に追加
            </button>
            <button type="button" className="btn-ghost" disabled={busy} onClick={ingestKb}>
              S3 / KB 取込
            </button>
          </div>
          <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={12} />
        </article>

        <article className="panel">
          <h2>ファイルアップロード</h2>
          <p className="muted">.md / .txt（UTF-8）</p>
          <input
            type="file"
            accept=".md,.txt,text/plain,text/markdown"
            disabled={busy}
            onChange={(e) => void onFile(e.target.files?.[0] || null)}
          />
          {msg ? <p className="pre" style={{ marginTop: "1rem" }}>{msg}</p> : null}
        </article>

        <article className="panel wide">
          <h2>索引済み文書</h2>
          {items.length === 0 ? (
            <p className="muted">まだありません。samples/ のデモ文書は常に検索対象です。</p>
          ) : (
            <ul className="doc-list">
              {items.map((d) => (
                <li key={d.document_id}>
                  <div>
                    <strong>{d.filename}</strong>
                    <span className="muted">
                      {" "}
                      · {d.bytes ?? 0} bytes · {d.status || "indexed"}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn-ghost"
                    disabled={busy}
                    onClick={() => void remove(d.document_id)}
                  >
                    削除
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>
    </main>
  );
}
