import {
  buildAuthorizeUrl,
  buildLogoutUrl,
  exchangeAuthorizationCode,
} from "./cognito";

const TOKEN_KEY = "bkb_access_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (!token) sessionStorage.removeItem(TOKEN_KEY);
  else sessionStorage.setItem(TOKEN_KEY, token);
}

export type AuthConfig = {
  auth_enforce: boolean;
  cognito_configured: boolean;
  dev_jwt_allowed: boolean;
  jwt_configured: boolean;
  aws_region: string;
  cognito_user_pool_id: string;
  cognito_app_client_id: string;
  cognito_hosted_ui_base_url: string;
  oauth_redirect_path: string;
};

export async function fetchAuthConfig(): Promise<AuthConfig> {
  const res = await fetch("/api/auth/config", { cache: "no-store" });
  if (!res.ok) throw new Error("auth config unavailable");
  return res.json() as Promise<AuthConfig>;
}

/** Cognito Hosted UI へリダイレクト（PKCE） */
export async function loginWithCognito(config: AuthConfig): Promise<void> {
  if (!config.cognito_hosted_ui_base_url || !config.cognito_app_client_id) {
    throw new Error("Cognito is not configured on the API");
  }
  const url = await buildAuthorizeUrl({
    hostedUiBase: config.cognito_hosted_ui_base_url,
    clientId: config.cognito_app_client_id,
  });
  window.location.href = url;
}

/** /auth/callback で code を access_token に交換 */
export async function completeCognitoLogin(
  config: AuthConfig,
  code: string,
): Promise<void> {
  const tokens = await exchangeAuthorizationCode({
    hostedUiBase: config.cognito_hosted_ui_base_url,
    clientId: config.cognito_app_client_id,
    code,
  });
  if (!tokens.access_token) throw new Error("No access_token in response");
  setAccessToken(tokens.access_token);
}

export async function logout(config?: AuthConfig | null): Promise<void> {
  setAccessToken(null);
  if (
    config?.cognito_configured &&
    config.cognito_hosted_ui_base_url &&
    config.cognito_app_client_id
  ) {
    window.location.href = buildLogoutUrl({
      hostedUiBase: config.cognito_hosted_ui_base_url,
      clientId: config.cognito_app_client_id,
    });
    return;
  }
  window.location.href = "/login";
}

/** 開発用: POST /api/auth/token で HS256 JWT を取得して保存 */
export async function loginDevToken(payload: {
  subject?: string;
  tenant_id?: string;
  roles?: string;
}): Promise<void> {
  const res = await fetch("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      subject: payload.subject ?? "dev-user",
      tenant_id: payload.tenant_id ?? "default",
      roles: payload.roles ?? "viewer,admin",
      expires_in_sec: 3600,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  const data = (await res.json()) as { access_token: string };
  setAccessToken(data.access_token);
}

export type MeResponse = {
  ok: boolean;
  provider: string;
  subject?: string;
  tenant_id?: string;
  roles?: string[];
  claims?: Record<string, unknown>;
};

export async function fetchMe(): Promise<MeResponse | null> {
  const token = getAccessToken();
  if (!token) return null;
  const res = await fetch("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json() as Promise<MeResponse>;
}

export function authHeaders(): Record<string, string> {
  const t = getAccessToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}
