"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/Nav";
import {
  fetchAuthConfig,
  getAccessToken,
  loginDevToken,
  loginWithCognito,
  type AuthConfig,
} from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tenantId, setTenantId] = useState("default");
  const [subject, setSubject] = useState("dev-user");

  useEffect(() => {
    if (getAccessToken()) {
      router.replace("/");
      return;
    }
    fetchAuthConfig()
      .then(setConfig)
      .catch((e) => setError(e instanceof Error ? e.message : "設定を読めません"));
  }, [router]);

  async function onCognito() {
    if (!config) return;
    setBusy(true);
    setError(null);
    try {
      await loginWithCognito(config);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cognito ログインに失敗しました");
      setBusy(false);
    }
  }

  async function onDevSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await loginDevToken({ subject, tenant_id: tenantId, roles: "viewer,admin" });
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "開発 JWT の取得に失敗しました");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <Nav />
      <section className="hero">
        <h1>ログイン</h1>
        <p className="muted">
          本番は Amazon Cognito（アクセストークン + PKCE）。ローカルは JWT_SECRET がある場合のみ開発 JWT を利用できます。
        </p>
      </section>

      {error && <div className="error-banner">{error}</div>}

      <div className="grid">
        {config?.cognito_configured && config.cognito_hosted_ui_base_url ? (
          <article className="panel">
            <h2>Amazon Cognito</h2>
            <p className="muted" style={{ fontSize: ".9rem", lineHeight: 1.5 }}>
              Hosted UI でサインインします。API には <strong>access token</strong> のみ送信します。
            </p>
            <div className="controls">
              <button type="button" disabled={busy} onClick={onCognito}>
                Cognito でログイン
              </button>
            </div>
          </article>
        ) : (
          <article className="panel">
            <h2>Cognito 未設定</h2>
            <p className="muted" style={{ fontSize: ".9rem" }}>
              API に COGNITO_USER_POOL_ID / COGNITO_APP_CLIENT_ID / COGNITO_DOMAIN_PREFIX を設定するか、
              Terraform <code>enable_cognito=true</code> を適用してください。
            </p>
          </article>
        )}

        {config?.dev_jwt_allowed ? (
          <article className="panel">
            <h2>開発 JWT（HS256）</h2>
            <form onSubmit={onDevSubmit}>
              <label className="muted" style={{ display: "block", marginBottom: 4 }}>
                subject
              </label>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                style={{ width: "100%", marginBottom: 8 }}
              />
              <label className="muted" style={{ display: "block", marginBottom: 4 }}>
                tenant_id（RAG ACL）
              </label>
              <input
                value={tenantId}
                onChange={(e) => setTenantId(e.target.value)}
                style={{ width: "100%", marginBottom: 12 }}
              />
              <button type="submit" disabled={busy}>
                開発トークンで続行
              </button>
            </form>
          </article>
        ) : (
          <article className="panel">
            <h2>開発 JWT</h2>
            <p className="muted" style={{ fontSize: ".9rem" }}>
              本番 Cognito 有効時は HS256 トークンは使えません。JWT_SECRET はローカルのみ。
            </p>
          </article>
        )}
      </div>
    </main>
  );
}
