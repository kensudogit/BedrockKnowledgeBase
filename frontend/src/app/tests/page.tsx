"use client";

import { useCallback, useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

type TestCase = {
  id?: string;
  name?: string;
  file?: string;
  status?: string;
  duration_ms?: number;
  suite?: string;
  message?: string | null;
};

type SuiteResult = {
  suite?: string;
  runner?: string;
  passed?: number;
  failed?: number;
  skipped?: number;
  total?: number;
  duration_ms?: number;
  exit_code?: number;
  error?: string;
  tests?: TestCase[];
};

type Run = {
  run_id?: string;
  created_at?: string;
  status?: string;
  passed?: number;
  failed?: number;
  skipped?: number;
  total?: number;
  duration_ms?: number;
  suites?: SuiteResult[];
  layout?: { backend?: string; frontend?: string };
  message?: string;
  error?: string;
};

async function pollRun(id: string, onUpdate: (r: Run) => void, maxTicks = 120): Promise<Run> {
  let r = (await api.testsRun(id)) as Run;
  onUpdate(r);
  let guard = 0;
  while (r.status === "running" && guard < maxTicks) {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    r = (await api.testsRun(id)) as Run;
    onUpdate(r);
    guard += 1;
  }
  return r;
}

export default function TestsPage() {
  const [run, setRun] = useState<Run | null>(null);
  const [history, setHistory] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<"all" | "failed" | "passed">("all");

  const reloadHistory = useCallback(async () => {
    const hist = await api.testsHistory(15);
    setHistory(hist.items || []);
  }, []);

  const reload = useCallback(async () => {
    try {
      const [latest, hist] = await Promise.all([api.testsLatest(), api.testsHistory(15)]);
      const current = (latest.run as Run) || null;
      setRun(current);
      setHistory(hist.items || []);
      setError("");
      return current;
    } catch (e) {
      setError(String(e));
      return null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const current = await reload();
      if (cancelled || !current?.run_id || current.status !== "running") return;
      setBusy(true);
      try {
        await pollRun(current.run_id, (r) => {
          if (!cancelled) setRun(r);
        });
        if (!cancelled) await reloadHistory();
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reload, reloadHistory]);

  async function runSuites(suites: string[]) {
    setBusy(true);
    setError("");
    try {
      const started = (await api.runTests(suites)) as Run;
      setRun(started);
      const id = started.run_id;
      if (!id) throw new Error("run_id missing");
      const finished = await pollRun(id, setRun);
      await reloadHistory();
      if (finished.status === "running") {
        setError("タイムアウト: 「最新を再読込」で状態を確認してください。");
      }
    } catch (e) {
      setError(String(e));
      try {
        await reload();
      } catch {
        /* ignore */
      }
    } finally {
      setBusy(false);
    }
  }

  async function openRun(id: string) {
    setBusy(true);
    setError("");
    try {
      let r = (await api.testsRun(id)) as Run;
      setRun(r);
      if (r.status === "running") {
        r = await pollRun(id, setRun);
      }
      await reloadHistory();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const suites = run?.suites || [];
  const allTests = suites.flatMap((s) => s.tests || []);
  const visible = allTests.filter((t) => {
    if (filter === "all") return true;
    return t.status === filter;
  });

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>Test Results</h1>
        <p>
          Python（pytest）と Frontend（Vitest / React / TypeScript）のテストを実行し、結果を Web
          で確認します。
        </p>
      </section>

      <section className="panel wide">
        <div className="controls" style={{ gap: 8, flexWrap: "wrap" }}>
          <button type="button" disabled={busy} onClick={() => runSuites(["python", "frontend"])}>
            {busy ? "実行中…" : "全スイート実行"}
          </button>
          <button type="button" disabled={busy} onClick={() => runSuites(["python"])}>
            Python のみ
          </button>
          <button type="button" disabled={busy} onClick={() => runSuites(["frontend"])}>
            Frontend のみ
          </button>
          <button type="button" disabled={busy} onClick={() => reload()}>
            最新を再読込
          </button>
        </div>
        {error && (
          <p style={{ color: "#fca5a5", marginTop: 12, whiteSpace: "pre-wrap" }}>
            エラー: {error}
          </p>
        )}
        {run?.status === "error" && (
          <p style={{ color: "#fcd34d", marginTop: 8, fontSize: 14 }}>
            スイート実行は完了しましたが、環境不足などでテスト件数 0 です。各スイートの error
            を確認してください（Docker では pytest 同梱・frontend は /app/frontend）。
          </p>
        )}
      </section>

      <section className="grid">
        <article className="panel">
          <h2>サマリー</h2>
          {run ? (
            <ul>
              <li>
                状態:{" "}
                <strong style={{ color: run.status === "running" ? "#93c5fd" : undefined }}>
                  {run.status}
                </strong>
                {run.status === "running" ? " （実行中・1.5秒ごとに自動更新）" : ""}
              </li>
              {run.message && (
                <li style={{ color: "#93c5fd" }}>{run.message}</li>
              )}
              {run.error && <li style={{ color: "#fca5a5" }}>{run.error}</li>}
              <li>
                合計 {run.total ?? 0} / 成功 {run.passed ?? 0} / 失敗 {run.failed ?? 0} / スキップ{" "}
                {run.skipped ?? 0}
              </li>
              <li>所要: {run.duration_ms ?? 0} ms</li>
              <li>実行時刻: {run.created_at}</li>
              <li style={{ fontSize: 12, opacity: 0.8 }}>run_id: {run.run_id}</li>
            </ul>
          ) : (
            <p>まだ実行結果がありません。「全スイート実行」を押してください。</p>
          )}
        </article>

        <article className="panel">
          <h2>スイート</h2>
          {suites.length === 0 && <p>—</p>}
          {suites.map((s) => (
            <div key={String(s.suite)} style={{ marginBottom: 12 }}>
              <strong>
                {s.suite} ({s.runner})
              </strong>
              <div>
                {s.passed}/{s.total} passed · {s.failed} failed · {s.duration_ms} ms
              </div>
              {s.error ? (
                <pre style={{ whiteSpace: "pre-wrap", color: "#fca5a5", fontSize: 12 }}>
                  {s.error}
                </pre>
              ) : null}
            </div>
          ))}
          {run?.layout && (
            <p style={{ fontSize: 12, opacity: 0.75, marginTop: 8 }}>
              layout: backend={String((run.layout as Record<string, string>).backend)} · frontend=
              {String((run.layout as Record<string, string>).frontend)}
            </p>
          )}
        </article>

        <article className="panel">
          <h2>履歴</h2>
          <ul>
            {history.map((h) => (
              <li key={String(h.run_id)}>
                <button
                  type="button"
                  style={{ background: "transparent", border: "none", color: "#7dd3fc", cursor: "pointer" }}
                  onClick={() => openRun(String(h.run_id))}
                >
                  {String(h.created_at || "").slice(0, 19)} — {String(h.status)} ({String(h.passed)}/
                  {String(h.total)})
                </button>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="panel wide" style={{ marginTop: 16 }}>
        <div className="controls" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0, flex: 1 }}>テスト一覧</h2>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as "all" | "failed" | "passed")}
          >
            <option value="all">すべて</option>
            <option value="failed">失敗のみ</option>
            <option value="passed">成功のみ</option>
          </select>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid var(--line)" }}>
                <th style={{ padding: 8 }}>Suite</th>
                <th style={{ padding: 8 }}>Status</th>
                <th style={{ padding: 8 }}>Name</th>
                <th style={{ padding: 8 }}>File</th>
                <th style={{ padding: 8 }}>ms</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((t) => (
                <tr key={t.id || `${t.file}-${t.name}`} style={{ borderBottom: "1px solid var(--line)" }}>
                  <td style={{ padding: 8 }}>{t.suite}</td>
                  <td
                    style={{
                      padding: 8,
                      color: t.status === "passed" ? "#86efac" : t.status === "failed" ? "#fca5a5" : "#93c5fd",
                    }}
                  >
                    {t.status}
                  </td>
                  <td style={{ padding: 8 }}>{t.name}</td>
                  <td style={{ padding: 8, fontSize: 12, opacity: 0.85 }}>{t.file}</td>
                  <td style={{ padding: 8 }}>{t.duration_ms}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {visible.length === 0 && <p style={{ marginTop: 12 }}>表示するテストがありません。</p>}
        </div>
        {visible.some((t) => t.message) && (
          <div style={{ marginTop: 16 }}>
            <h3>失敗詳細</h3>
            {visible
              .filter((t) => t.message)
              .map((t) => (
                <pre
                  key={`err-${t.id}`}
                  style={{ whiteSpace: "pre-wrap", fontSize: 12, color: "#fecaca" }}
                >
                  {t.name}
                  {"\n"}
                  {t.message}
                </pre>
              ))}
          </div>
        )}
      </section>
    </main>
  );
}
