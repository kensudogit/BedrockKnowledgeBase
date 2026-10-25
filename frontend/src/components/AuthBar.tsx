"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  fetchAuthConfig,
  fetchMe,
  getAccessToken,
  logout,
  type AuthConfig,
  type MeResponse,
} from "@/lib/auth";

export function AuthBar() {
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);

  useEffect(() => {
    fetchAuthConfig()
      .then(setConfig)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!getAccessToken()) {
      setMe(null);
      return;
    }
    fetchMe().then(setMe).catch(() => setMe(null));
  }, [config]);

  const signedIn = Boolean(getAccessToken() && me?.ok);

  return (
    <div className="auth-bar">
      {signedIn ? (
        <>
          <span className="badge" title={me?.provider}>
            {me?.tenant_id || "tenant"} · {me?.subject?.slice(0, 12) || "user"}
          </span>
          <button
            type="button"
            className="btn-ghost"
            style={{ padding: ".35rem .65rem", fontSize: ".8rem" }}
            onClick={() => logout(config)}
          >
            ログアウト
          </button>
        </>
      ) : (
        <Link href="/login" className="badge" style={{ color: "var(--accent)" }}>
          ログイン
        </Link>
      )}
    </div>
  );
}
