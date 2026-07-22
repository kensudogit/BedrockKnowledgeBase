-- Bedrock Knowledge Base Platform — PostgreSQL

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    client_name VARCHAR(128),
    env VARCHAR(32) NOT NULL DEFAULT 'development',
    api_key_hash VARCHAR(128),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    s3_key VARCHAR(512),
    filename VARCHAR(256) NOT NULL,
    content_type VARCHAR(128),
    bytes BIGINT DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'uploaded',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    title VARCHAR(256) NOT NULL DEFAULT '新規セッション',
    use_case VARCHAR(64) NOT NULL DEFAULT 'internal_chatbot',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id BIGSERIAL PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    name VARCHAR(128) NOT NULL,
    dataset_id VARCHAR(128),
    model_id VARCHAR(128) NOT NULL,
    metrics JSONB NOT NULL,
    samples JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    session_id VARCHAR(64),
    message_index INTEGER,
    rating SMALLINT NOT NULL,
    comment TEXT,
    use_case VARCHAR(64),
    model_id VARCHAR(128),
    answer_preview TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telemetry_events (
    id BIGSERIAL PRIMARY KEY,
    project_id UUID,
    request_id VARCHAR(64),
    path VARCHAR(256),
    method VARCHAR(16),
    status_code INTEGER,
    latency_ms INTEGER,
    use_case VARCHAR(64),
    model_id VARCHAR(128),
    mock BOOLEAN,
    meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_doc ON rag_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_created ON telemetry_events(created_at DESC);
