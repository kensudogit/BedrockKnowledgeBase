"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Nav } from "@/components/Nav";
import { completeCognitoLogin, fetchAuthConfig } from "@/lib/auth";

function AuthCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = params.get("code");
    const err = params.get("error_description") || params.get("error");
    if (err) {
      setError(String(err));
      return;
    }
    if (!code) {
      setError("認可コードがありません");
      return;
    }
    (async () => {
      try {
        const config = await fetchAuthConfig();
        await completeCognitoLogin(config, code);
        router.replace("/");
      } catch (e) {
        setError(e instanceof Error ? e.message : "ログイン完了に失敗しました");
      }
    })();
  }, [params, router]);

  return (
    <section className="hero">
      <h1>サインイン処理中…</h1>
      {error ? (
        <div className="error-banner">{error}</div>
      ) : (
        <p className="muted">Cognito からトークンを取得しています。</p>
      )}
    </section>
  );
}

export default function AuthCallbackPage() {
  return (
    <main>
      <Nav />
      <Suspense
        fallback={
          <section className="hero">
            <h1>サインイン処理中…</h1>
            <p className="muted">読み込んでいます…</p>
          </section>
        }
      >
        <AuthCallbackInner />
      </Suspense>
    </main>
  );
}
