export type Citation = {
  id?: string;
  source?: string;
  text?: string;
  score?: number | null;
  rank?: number;
};

export type ChatMessage = {
  role: string;
  content: string;
  citations?: Citation[];
  meta?: Record<string, unknown>;
  created_at?: string;
};

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () =>
    json<{ status: string; mock_mode: boolean; features: string[] }>("/health"),
  useCases: () => json<{ items: { id: string; label: string }[] }>("/api/use-cases"),
  text: (prompt: string, system?: string) =>
    json<{ text: string; mock?: boolean }>("/api/text/generate", {
      method: "POST",
      body: JSON.stringify({ prompt, system, apply_guardrail: true }),
    }),
  rag: (query: string, use_case = "document_search", session_id?: string) =>
    json<{
      answer: string;
      citations: Citation[];
      mock?: boolean;
      blocked?: boolean;
      session_id?: string;
    }>("/api/rag/query", {
      method: "POST",
      body: JSON.stringify({ query, use_case, session_id }),
    }),
  chat: (payload: {
    message: string;
    use_case?: string;
    mode?: "rag" | "text";
    session_id?: string | null;
  }) =>
    json<{
      session_id: string;
      answer: string;
      citations: Citation[];
      messages: ChatMessage[];
      mock?: boolean;
      blocked?: boolean;
      source?: string;
    }>("/api/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  sessions: () =>
    json<{
      items: Array<{
        session_id: string;
        title: string;
        use_case: string;
        message_count: number;
      }>;
    }>("/api/sessions"),
  session: (id: string) =>
    json<{ session_id: string; messages: ChatMessage[]; use_case: string }>(
      `/api/sessions/${id}`,
    ),
  createSession: (use_case: string) =>
    json<{ session_id: string }>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ use_case }),
    }),
  documents: () =>
    json<{
      items: Array<{
        document_id: string;
        filename: string;
        bytes?: number;
        status?: string;
      }>;
    }>("/api/documents"),
  ingestDocument: (filename: string, content: string) =>
    json<Record<string, unknown>>("/api/documents", {
      method: "POST",
      body: JSON.stringify({ filename, content }),
    }),
  uploadDocument: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/documents/upload", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json() as Promise<Record<string, unknown>>;
  },
  deleteDocument: (id: string) =>
    json<{ ok: boolean }>(`/api/documents/${id}`, { method: "DELETE" }),
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
  upsertPrompt: (body: {
    name: string;
    template: string;
    use_case: string;
    variables?: string[];
    prompt_id?: string;
  }) =>
    json<Record<string, unknown>>("/api/prompts", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  evalRun: (payload?: { dataset_id?: string; name?: string; fail_under?: number }) =>
    json<Record<string, unknown>>("/api/evaluation/run", {
      method: "POST",
      body: JSON.stringify(payload || { dataset_id: "golden_default" }),
    }),
  evals: () => json<{ items: Array<Record<string, unknown>> }>("/api/evaluation"),
  datasets: () =>
    json<{ items: Array<{ dataset_id: string; name: string; n_items: number; version?: string }> }>(
      "/api/datasets",
    ),
  feedback: (payload: {
    rating: number;
    session_id?: string | null;
    message_index?: number;
    comment?: string;
    use_case?: string;
    answer_preview?: string;
  }) =>
    json<Record<string, unknown>>("/api/feedback", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  feedbackList: () =>
    json<{ items: unknown[]; summary: { n: number; up: number; down: number; approval_rate: number | null } }>(
      "/api/feedback",
    ),
  projects: () => json<{ items: Array<Record<string, unknown>> }>("/api/projects"),
  createProject: (body: { name: string; client_name?: string; env?: string; notes?: string }) =>
    json<Record<string, unknown>>("/api/projects", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  opsSummary: () => json<Record<string, unknown>>("/api/ops/summary"),
  metricsSummary: () => json<Record<string, unknown>>("/api/metrics/summary"),
  kbIngest: (filename: string, content: string) =>
    json<Record<string, unknown>>("/api/documents/kb-ingest", {
      method: "POST",
      body: JSON.stringify({ filename, content }),
    }),
  agent: (message: string, session_id?: string | null) =>
    json<{ answer: string; plan?: string; mock?: boolean; session_id?: string }>(
      "/api/agents/invoke",
      {
        method: "POST",
        body: JSON.stringify({ message, session_id }),
      },
    ),
};
