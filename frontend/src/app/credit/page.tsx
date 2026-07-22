"use client";

import { useCallback, useEffect, useState } from "react";
import { Nav } from "@/components/Nav";
import { api } from "@/lib/api";

export default function CreditPage() {
  const [subjects, setSubjects] = useState<Array<Record<string, unknown>>>([]);
  const [selected, setSelected] = useState("");
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [audit, setAudit] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [fullName, setFullName] = useState("山田太郎");
  const [birthDate, setBirthDate] = useState("1990-01-15");
  const [phone, setPhone] = useState("09012345678");
  const [lender, setLender] = useState("デモカード");
  const [limit, setLimit] = useState(500000);
  const [balance, setBalance] = useState(120000);
  const [requester, setRequester] = useState("Demo Lender");

  const reload = useCallback(() => {
    Promise.all([api.creditSubjects(), api.creditAudit(40)])
      .then(([s, a]) => {
        setSubjects(s.items || []);
        setAudit(a.items || []);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function createSubject() {
    setBusy(true);
    setError("");
    try {
      const s = await api.creditCreateSubject({
        full_name: fullName,
        birth_date: birthDate,
        phone,
        external_ref: `EXT-${Date.now().toString(36)}`,
      });
      setSelected(String(s.subject_id));
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function addContract() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await api.creditAddContract(selected, {
        contract_type: "credit_card",
        lender,
        credit_limit: limit,
        balance,
        payment_status: "current",
      });
      const r = await api.creditReport(selected);
      setReport(r);
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function consentAndInquire() {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      await api.creditAddConsent(selected, {
        purpose: "credit_inquiry",
        requester,
      });
      await api.creditAddInquiry(selected, {
        requester,
        inquiry_type: "hard",
        purpose: "credit_review",
      });
      const r = await api.creditReport(selected);
      setReport(r);
      reload();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function loadReport(id: string) {
    setSelected(id);
    setBusy(true);
    setError("");
    try {
      setReport(await api.creditReport(id));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const score = (report?.score || null) as Record<string, unknown> | null;

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>信用情報管理</h1>
        <p>本人登録・契約・同意・照会・スコアレポート（デモ用。本番の信用情報機関連携ではありません）。</p>
      </section>

      {error ? <p className="error-banner">{error}</p> : null}

      <section className="grid">
        <article className="panel">
          <h2>本人登録</h2>
          <label className="field">
            氏名
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </label>
          <label className="field">
            生年月日
            <input value={birthDate} onChange={(e) => setBirthDate(e.target.value)} />
          </label>
          <label className="field">
            電話
            <input value={phone} onChange={(e) => setPhone(e.target.value)} />
          </label>
          <button type="button" disabled={busy} onClick={() => void createSubject()}>
            登録
          </button>
        </article>

        <article className="panel">
          <h2>契約 / 同意照会</h2>
          <p className="muted">選択中: {selected || "—"}</p>
          <label className="field">
            貸付機関
            <input value={lender} onChange={(e) => setLender(e.target.value)} />
          </label>
          <label className="field">
            限度額
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            />
          </label>
          <label className="field">
            残高
            <input
              type="number"
              value={balance}
              onChange={(e) => setBalance(Number(e.target.value))}
            />
          </label>
          <label className="field">
            照会元
            <input value={requester} onChange={(e) => setRequester(e.target.value)} />
          </label>
          <div className="controls">
            <button type="button" disabled={busy || !selected} onClick={() => void addContract()}>
              契約追加
            </button>
            <button
              type="button"
              className="btn-ghost"
              disabled={busy || !selected}
              onClick={() => void consentAndInquire()}
            >
              同意＋照会
            </button>
          </div>
        </article>

        <article className="panel">
          <h2>本人一覧</h2>
          <ul className="plain-list">
            {subjects
              .slice()
              .reverse()
              .map((s) => (
                <li key={String(s.subject_id)}>
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => void loadReport(String(s.subject_id))}
                  >
                    {String(s.full_name_masked)} · {String(s.birth_date)} · {String(s.phone_masked)}
                  </button>
                </li>
              ))}
          </ul>
        </article>

        <article className="panel">
          <h2>スコア / レポート</h2>
          {score ? (
            <>
              <p>
                score: <strong>{String(score.score)}</strong> ({String(score.band)}) · util{" "}
                {String(score.utilization)}
              </p>
              <ul className="plain-list">
                {((score.reasons as string[]) || []).map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </>
          ) : (
            <p className="muted">本人を選択または登録してください。</p>
          )}
          {report ? <pre className="pre">{JSON.stringify(report, null, 2)}</pre> : null}
        </article>

        <article className="panel">
          <h2>監査ログ</h2>
          <ul className="plain-list">
            {audit
              .slice()
              .reverse()
              .slice(0, 20)
              .map((a) => (
                <li key={String(a.audit_id)}>
                  {String(a.created_at)} · {String(a.action)} · {String(a.subject_id || "-")}
                </li>
              ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
