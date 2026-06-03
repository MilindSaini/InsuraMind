CREATE SCHEMA IF NOT EXISTS insuramind;

SET search_path TO insuramind;

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(160) NOT NULL,
    role VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE documents (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(512) NOT NULL,
    file_type VARCHAR(120) NOT NULL,
    object_key VARCHAR(1024) NOT NULL,
    sha256 VARCHAR(128) NOT NULL,
    size_bytes BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    document_type VARCHAR(64),
    processing_message TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_documents_user_status ON documents(user_id, status);
CREATE INDEX idx_documents_created_at ON documents(created_at);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    section_type VARCHAR(80) NOT NULL,
    heading VARCHAR(512),
    text TEXT NOT NULL,
    page_number INTEGER,
    risk_level VARCHAR(32) NOT NULL,
    importance VARCHAR(32) NOT NULL,
    citation_label VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_chunks_document_section ON document_chunks(document_id, section_type);

CREATE TABLE extracted_entities (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type VARCHAR(120) NOT NULL,
    entity_value TEXT NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    page_number INTEGER,
    source_chunk_index INTEGER,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_entities_document_type ON extracted_entities(document_id, entity_type);

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    confidence DOUBLE PRECISION,
    citations_json TEXT,
    risk_alerts_json TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_chat_session_created ON chat_messages(session_id, created_at);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(120) NOT NULL,
    resource_id VARCHAR(160),
    ip_address VARCHAR(80),
    metadata TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_audit_user_created ON audit_logs(user_id, created_at);
