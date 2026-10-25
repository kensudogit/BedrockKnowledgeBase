/** Cognito Hosted UI + PKCE（公開クライアント・シークレット不要） */

const PKCE_VERIFIER_KEY = "bkb_pkce_verifier";

function randomString(bytes = 32): string {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return b64url(arr);
}

function b64url(data: Uint8Array | ArrayBuffer): string {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
  let bin = "";
  bytes.forEach((b) => {
    bin += String.fromCharCode(b);
  });
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sha256(input: string): Promise<ArrayBuffer> {
  const enc = new TextEncoder();
  return crypto.subtle.digest("SHA-256", enc.encode(input));
}

export async function createPkcePair(): Promise<{ verifier: string; challenge: string }> {
  const verifier = randomString(48);
  const digest = await sha256(verifier);
  return { verifier, challenge: b64url(digest) };
}

export function appOrigin(): string {
  if (typeof window !== "undefined") return window.location.origin;
  return (process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3010").replace(/\/$/, "");
}

export function redirectUri(): string {
  return `${appOrigin()}/auth/callback`;
}

export async function buildAuthorizeUrl(params: {
  hostedUiBase: string;
  clientId: string;
}): Promise<string> {
  const { verifier, challenge } = await createPkcePair();
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  const q = new URLSearchParams({
    client_id: params.clientId,
    response_type: "code",
    scope: "openid email profile",
    redirect_uri: redirectUri(),
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  return `${params.hostedUiBase.replace(/\/$/, "")}/oauth2/authorize?${q.toString()}`;
}

export async function exchangeAuthorizationCode(params: {
  hostedUiBase: string;
  clientId: string;
  code: string;
}): Promise<{ access_token: string; id_token?: string; refresh_token?: string }> {
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  if (!verifier) throw new Error("PKCE verifier missing; login again");

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: params.clientId,
    code: params.code,
    redirect_uri: redirectUri(),
    code_verifier: verifier,
  });

  const res = await fetch(`${params.hostedUiBase.replace(/\/$/, "")}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Token exchange failed: ${res.status} ${text}`);
  }
  return res.json() as Promise<{
    access_token: string;
    id_token?: string;
    refresh_token?: string;
  }>;
}

export function buildLogoutUrl(params: {
  hostedUiBase: string;
  clientId: string;
  logoutUri?: string;
}): string {
  const q = new URLSearchParams({
    client_id: params.clientId,
    logout_uri: params.logoutUri || `${appOrigin()}/login`,
  });
  return `${params.hostedUiBase.replace(/\/$/, "")}/logout?${q.toString()}`;
}
