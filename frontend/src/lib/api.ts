async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => json<{ status: string; mock_mode: boolean; features: string[] }>("/health"),
  useCases: () => json<{ items: { id: string; label: string }[] }>("/api/use-cases"),
  text: (prompt: string, system?: string) =>
    json<{ text: string; mock?: boolean }>("/api/text/generate", {
      method: "POST",
      body: JSON.stringify({ prompt, system, apply_guardrail: true }),
    }),
  rag: (query: string, use_case = "document_search") =>
    json<{ answer: string; citations: unknown[]; mock?: boolean }>("/api/rag/query", {
      method: "POST",
      body: JSON.stringify({ query, use_case }),
    }),
  image: (prompt: string) =>
    json<{ data_url: string; mock?: boolean }>("/api/image/generate", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
  embed: (texts: string[]) =>
    json<{ embeddings: number[][]; dimensions: number; mock?: boolean }>("/api/embedding", {
      method: "POST",
      body: JSON.stringify({ texts }),
    }),
  guard: (text: string) =>
    json<{ action: string; outputs: { text: string }[] }>("/api/guardrails/apply", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  prompts: () => json<{ items: Array<Record<string, unknown>> }>("/api/prompts"),
  evalRun: () => json<Record<string, unknown>>("/api/evaluation/run", { method: "POST" }),
  evals: () => json<{ items: Array<Record<string, unknown>> }>("/api/evaluation"),
  agent: (message: string) =>
    json<{ answer: string; plan?: string; mock?: boolean }>("/api/agents/invoke", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
