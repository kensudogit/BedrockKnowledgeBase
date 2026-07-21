"use client";

import { useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function PromptsPage() {
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .prompts()
      .then((r) => setItems(r.items))
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Prompt Management</h1>
        <p>DynamoDB にプロンプトテンプレートを保存・版管理します。</p>
      </section>
      {error && <p className="muted">エラー: {error}（DynamoDB Local 起動後に setup を再実行）</p>}
      <section className="grid">
        {items.map((p) => (
          <article className="panel" key={String(p.prompt_id)}>
            <h2>{String(p.name)}</h2>
            <p className="muted">use_case: {String(p.use_case)} / v{String(p.version)}</p>
            <pre className="pre">{String(p.template)}</pre>
          </article>
        ))}
      </section>
    </main>
  );
}
