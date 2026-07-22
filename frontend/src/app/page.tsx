"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function HomePage() {
  const [health, setHealth] = useState<{ mock_mode: boolean; features: string[] } | null>(null);
  const [cases, setCases] = useState<{ id: string; label: string }[]>([]);

  useEffect(() => {
    Promise.all([api.health(), api.useCases()])
      .then(([h, u]) => {
        setHealth(h);
        setCases(u.items);
      })
      .catch(() => undefined);
  }, []);

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>エンタープライズ生成AI基盤</h1>
        <p>
          Amazon Bedrock + Knowledge Bases を中核に、Text / Image / Embedding / Guardrails /
          Prompt / Evaluation と RAG・Agents を一体提供します。ローカルはモック、AWS 接続で本番モデルへ切替。
        </p>
        <div className="chips">
          <span>S3 → KB → Bedrock → Lambda → API GW → Web</span>
          <span>{health ? (health.mock_mode ? "MOCK MODE" : "BEDROCK LIVE") : "…"}</span>
        </div>
      </section>

      <section className="grid" style={{ marginTop: "1.25rem" }}>
        <article className="panel">
          <h2>6コア機能</h2>
          <ul className="muted">
            <li><Link href="/chat">① Text Generation / RAG</Link></li>
            <li><Link href="/image">② Image Generation</Link></li>
            <li><Link href="/embedding">③ Embedding</Link></li>
            <li><Link href="/guardrails">④ Guardrails</Link></li>
            <li><Link href="/prompts">⑤ Prompt Management</Link></li>
            <li><Link href="/evaluation">⑥ Model Evaluation</Link></li>
            <li><Link href="/ops">Ops / MLOps（Projects · Telemetry · Feedback）</Link></li>
            <li><Link href="/documents">Documents / KB Ingest</Link></li>
          </ul>
        </article>
        <article className="panel">
          <h2>利用例</h2>
          <div className="chips">
            {cases.map((c) => (
              <span key={c.id}>{c.label}</span>
            ))}
          </div>
        </article>
        <article className="panel wide">
          <h2>実現構成</h2>
          <p className="muted">
            Bedrock Knowledge Bases（文書RAG）· Agents（業務自動化）· Lambda + API Gateway（サーバーレスAPI）·
            S3 文書取込 · Terraform IaC · Spring Boot Runtime 連携（java-spring/）
          </p>
          <pre className="pre">{`S3  →  Knowledge Base  →  Bedrock  →  Lambda  →  API Gateway  →  Web`}</pre>
        </article>
      </section>
    </main>
  );
}
