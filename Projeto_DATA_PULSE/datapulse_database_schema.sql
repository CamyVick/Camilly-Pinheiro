-- ============================================================================
-- DataPulse AI - Database Schema
-- PostgreSQL 15+ / TimescaleDB 2.x
-- Arquitetura: Multi-tenant (single database, shared schema, org_id em toda
-- tabela + Row Level Security). Escolhido em vez de schema-per-tenant porque
-- escala melhor para "milhares de clientes" sem explosão de conexões/migrations.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- 1. TENANCY & PLANOS (SaaS billing)
-- ============================================================================

CREATE TABLE plans (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(50) UNIQUE NOT NULL,       -- 'free','pro','business','enterprise'
    name            VARCHAR(100) NOT NULL,
    price_cents     INTEGER NOT NULL DEFAULT 0,
    billing_cycle   VARCHAR(20) NOT NULL DEFAULT 'monthly', -- monthly | yearly
    limits          JSONB NOT NULL DEFAULT '{}',        -- {max_pipelines, max_users, retention_days, max_connections}
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active', -- active | suspended | cancelled
    settings        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE subscriptions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id                 UUID NOT NULL REFERENCES plans(id),
    status                  VARCHAR(20) NOT NULL DEFAULT 'trialing', -- trialing|active|past_due|cancelled
    current_period_start    TIMESTAMPTZ NOT NULL,
    current_period_end      TIMESTAMPTZ NOT NULL,
    stripe_customer_id      VARCHAR(100),
    stripe_subscription_id  VARCHAR(100),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_subscriptions_org ON subscriptions(org_id);

-- ============================================================================
-- 2. USUÁRIOS, RBAC E AUTENTICAÇÃO
-- ============================================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    password_hash   VARCHAR(255),                       -- null se login federado (SSO)
    full_name       VARCHAR(200) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active', -- active|invited|disabled
    mfa_enabled     BOOLEAN NOT NULL DEFAULT false,
    mfa_secret      VARCHAR(255),
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id, email)
);
CREATE INDEX idx_users_org ON users(org_id);

CREATE TABLE sso_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider        VARCHAR(30) NOT NULL, -- azure_ad | google | ldap
    config          JSONB NOT NULL,       -- client_id, tenant_id, endpoints (secrets no vault, não aqui)
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE, -- null = role de sistema (Admin, Viewer)
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    is_system       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE permissions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(100) UNIQUE NOT NULL, -- 'pipelines:read','alerts:write','users:admin'...
    description     TEXT
);

CREATE TABLE role_permissions (
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id   UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_roles (
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    name            VARCHAR(100) NOT NULL,
    key_hash        VARCHAR(255) NOT NULL,   -- hash da key, nunca texto puro
    key_prefix      VARCHAR(12) NOT NULL,    -- exibido na UI: dp_live_ab12...
    scopes          JSONB NOT NULL DEFAULT '[]',
    expires_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_api_keys_org ON api_keys(org_id);

CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,   -- 'pipeline.created','alert.resolved'...
    resource_type   VARCHAR(50) NOT NULL,
    resource_id     UUID,
    metadata        JSONB NOT NULL DEFAULT '{}',
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_org_created ON audit_logs(org_id, created_at DESC);

-- ============================================================================
-- 3. INTEGRAÇÕES / FONTES DE DADOS MONITORADAS
-- ============================================================================

CREATE TABLE integration_types (
    id              SMALLSERIAL PRIMARY KEY,
    code            VARCHAR(40) UNIQUE NOT NULL, -- airflow, adf, fabric, databricks,
                                                  -- sql_server_agent, python_script, rest_api,
                                                  -- power_bi, postgres, mysql, oracle, mongodb, redis
    display_name    VARCHAR(100) NOT NULL,
    category        VARCHAR(30) NOT NULL -- orchestrator | database | bi | script | api
);

CREATE TABLE data_source_connections (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    integration_type_id SMALLINT NOT NULL REFERENCES integration_types(id),
    name                VARCHAR(150) NOT NULL,
    environment         VARCHAR(10) NOT NULL DEFAULT 'PRD', -- DEV | HML | PRD
    connection_config   JSONB NOT NULL DEFAULT '{}',  -- host/porta/etc. Segredos ficam em secrets manager,
                                                        -- aqui guarda-se só uma referência (secret_ref)
    status              VARCHAR(20) NOT NULL DEFAULT 'active', -- active|error|paused
    last_sync_at        TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_connections_org ON data_source_connections(org_id);

-- ============================================================================
-- 4. PIPELINES MONITORADOS
-- ============================================================================

CREATE TABLE pipelines (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    connection_id   UUID NOT NULL REFERENCES data_source_connections(id) ON DELETE CASCADE,
    external_id     VARCHAR(255),          -- id do DAG/job na ferramenta de origem
    name            VARCHAR(200) NOT NULL,
    pipeline_type   VARCHAR(30) NOT NULL,  -- etl|api|report|script
    environment     VARCHAR(10) NOT NULL DEFAULT 'PRD',
    owner           VARCHAR(150),
    tags            JSONB NOT NULL DEFAULT '[]',
    sla_minutes     INTEGER,               -- limite de duração aceitável
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id, connection_id, external_id)
);
CREATE INDEX idx_pipelines_org ON pipelines(org_id);
CREATE INDEX idx_pipelines_connection ON pipelines(connection_id);

-- ----------------------------------------------------------------------------
-- 4.1 Execuções de pipeline (hypertable — alto volume, particionado por tempo)
-- ----------------------------------------------------------------------------
CREATE TABLE pipeline_runs (
    id              UUID NOT NULL DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL,
    pipeline_id     UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    started_at      TIMESTAMPTZ NOT NULL,
    finished_at     TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL, -- running|success|failed|timeout|cancelled
    duration_seconds  NUMERIC(12,2),
    cpu_usage_pct     NUMERIC(5,2),
    ram_usage_mb      NUMERIC(12,2),
    error_code        VARCHAR(50),
    error_message     TEXT,
    stack_trace       TEXT,
    triggered_by      VARCHAR(30) DEFAULT 'scheduler', -- scheduler|manual|api
    PRIMARY KEY (id, started_at)
);
SELECT create_hypertable('pipeline_runs', 'started_at', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_runs_org_pipeline_time ON pipeline_runs (org_id, pipeline_id, started_at DESC);
CREATE INDEX idx_runs_status ON pipeline_runs (org_id, status, started_at DESC);

-- ----------------------------------------------------------------------------
-- 4.2 Logs (hypertable)
-- ----------------------------------------------------------------------------
CREATE TABLE pipeline_logs (
    id              BIGSERIAL,
    org_id          UUID NOT NULL,
    pipeline_id     UUID NOT NULL,
    run_id          UUID,
    ts              TIMESTAMPTZ NOT NULL,
    level           VARCHAR(10) NOT NULL,  -- DEBUG|INFO|WARN|ERROR|CRITICAL
    server          VARCHAR(150),
    message         TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',
    PRIMARY KEY (id, ts)
);
SELECT create_hypertable('pipeline_logs', 'ts', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_logs_org_pipeline_time ON pipeline_logs (org_id, pipeline_id, ts DESC);
CREATE INDEX idx_logs_level ON pipeline_logs (org_id, level, ts DESC);

-- ----------------------------------------------------------------------------
-- 4.3 Métricas granulares (hypertable) — série temporal pura, usada por gráficos
-- ----------------------------------------------------------------------------
CREATE TABLE metrics (
    org_id          UUID NOT NULL,
    pipeline_id     UUID NOT NULL,
    metric_name     VARCHAR(50) NOT NULL,  -- cpu_pct, ram_mb, response_time_ms, rows_processed...
    value           DOUBLE PRECISION NOT NULL,
    unit            VARCHAR(20),
    ts              TIMESTAMPTZ NOT NULL
);
SELECT create_hypertable('metrics', 'ts', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_metrics_org_pipeline_name_time ON metrics (org_id, pipeline_id, metric_name, ts DESC);

-- Política de retenção padrão (ajustável por plano via job de manutenção)
SELECT add_retention_policy('pipeline_logs', INTERVAL '90 days');
SELECT add_retention_policy('metrics', INTERVAL '180 days');

-- ============================================================================
-- 5. ALERTAS E NOTIFICAÇÕES
-- ============================================================================

CREATE TABLE alert_rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    pipeline_id     UUID REFERENCES pipelines(id) ON DELETE CASCADE, -- null = regra global da org
    name            VARCHAR(150) NOT NULL,
    condition_type  VARCHAR(30) NOT NULL, -- status_failed|duration_threshold|sla_breach|anomaly_detected
    condition_config JSONB NOT NULL DEFAULT '{}', -- {"threshold_seconds": 300} etc.
    severity        VARCHAR(20) NOT NULL DEFAULT 'medium', -- low|medium|high|critical
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_alert_rules_org ON alert_rules(org_id);

CREATE TABLE notification_channels (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    channel_type    VARCHAR(20) NOT NULL, -- teams|slack|discord|telegram|whatsapp|email|push
    config          JSONB NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    alert_rule_id   UUID REFERENCES alert_rules(id) ON DELETE SET NULL,
    pipeline_id     UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    run_id          UUID,
    severity        VARCHAR(20) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'open', -- open|acknowledged|resolved
    message         TEXT NOT NULL,
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    resolved_by     UUID REFERENCES users(id)
);
CREATE INDEX idx_alerts_org_status ON alerts(org_id, status, triggered_at DESC);

CREATE TABLE alert_notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id        UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    channel_id      UUID NOT NULL REFERENCES notification_channels(id) ON DELETE CASCADE,
    sent_at         TIMESTAMPTZ,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending|sent|failed
    response        TEXT
);

-- ============================================================================
-- 6. MACHINE LEARNING / IA
-- ============================================================================

CREATE TABLE ml_models (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE, -- null = modelo global/base
    model_type      VARCHAR(40) NOT NULL, -- failure_prediction|duration_prediction|anomaly_detection
    version         VARCHAR(20) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'training', -- training|active|deprecated
    artifact_uri    VARCHAR(500), -- caminho no MinIO/S3
    metrics         JSONB DEFAULT '{}', -- {"auc":0.91,"precision":0.87}
    trained_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE predictions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    pipeline_id     UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    model_id        UUID NOT NULL REFERENCES ml_models(id),
    prediction_type VARCHAR(40) NOT NULL,
    predicted_value NUMERIC(12,4),
    probability     NUMERIC(5,4),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_predictions_org_pipeline ON predictions(org_id, pipeline_id, created_at DESC);

CREATE TABLE anomalies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    pipeline_id     UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    anomaly_type    VARCHAR(40) NOT NULL, -- duration_spike|cpu_spike|failure_rate...
    severity        VARCHAR(20) NOT NULL,
    description     TEXT,
    baseline_value  NUMERIC(12,4),
    observed_value  NUMERIC(12,4),
    deviation_pct   NUMERIC(6,2)
);
CREATE INDEX idx_anomalies_org_pipeline ON anomalies(org_id, pipeline_id, detected_at DESC);

CREATE TABLE ai_conversations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(200),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL, -- user|assistant
    content         TEXT NOT NULL,
    context_refs    JSONB DEFAULT '{}',   -- ids de pipelines/runs/alerts citados na resposta
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_messages_conversation ON ai_messages(conversation_id, created_at);

-- ============================================================================
-- 7. DASHBOARDS
-- ============================================================================

CREATE TABLE dashboards (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE, -- null = dashboard compartilhado da org
    name            VARCHAR(150) NOT NULL,
    is_default      BOOLEAN NOT NULL DEFAULT false,
    layout          JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE dashboard_widgets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dashboard_id    UUID NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
    widget_type     VARCHAR(40) NOT NULL, -- kpi|line_chart|heatmap|gauge|table|timeline
    config          JSONB NOT NULL DEFAULT '{}',
    position        JSONB NOT NULL DEFAULT '{}' -- {x,y,w,h}
);

-- ============================================================================
-- 8. ROW LEVEL SECURITY (isolamento multi-tenant a nível de banco)
-- ============================================================================
-- Aplicado nas tabelas que carregam org_id. A aplicação define
-- SET app.current_org_id = '<uuid>' por conexão/request.

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation_users ON users
    USING (org_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation_pipelines ON pipelines
    USING (org_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation_runs ON pipeline_runs
    USING (org_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation_logs ON pipeline_logs
    USING (org_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation_metrics ON metrics
    USING (org_id = current_setting('app.current_org_id')::UUID);
CREATE POLICY org_isolation_alerts ON alerts
    USING (org_id = current_setting('app.current_org_id')::UUID);

-- ============================================================================
-- 9. SEEDS MÍNIMOS
-- ============================================================================

INSERT INTO integration_types (code, display_name, category) VALUES
    ('airflow', 'Apache Airflow', 'orchestrator'),
    ('adf', 'Azure Data Factory', 'orchestrator'),
    ('fabric', 'Microsoft Fabric', 'orchestrator'),
    ('databricks', 'Databricks Jobs', 'orchestrator'),
    ('sql_server_agent', 'SQL Server Agent', 'orchestrator'),
    ('python_script', 'Python Script', 'script'),
    ('rest_api', 'API REST', 'api'),
    ('power_bi', 'Power BI Refresh', 'bi'),
    ('postgres', 'PostgreSQL', 'database'),
    ('mysql', 'MySQL', 'database'),
    ('oracle', 'Oracle', 'database'),
    ('mongodb', 'MongoDB', 'database'),
    ('redis', 'Redis', 'database');

INSERT INTO plans (code, name, price_cents, billing_cycle, limits) VALUES
    ('free', 'Free', 0, 'monthly', '{"max_pipelines":5,"max_users":2,"retention_days":7}'),
    ('pro', 'Pro', 29900, 'monthly', '{"max_pipelines":50,"max_users":10,"retention_days":30}'),
    ('business', 'Business', 99900, 'monthly', '{"max_pipelines":300,"max_users":50,"retention_days":90}'),
    ('enterprise', 'Enterprise', NULL, 'yearly', '{"max_pipelines":-1,"max_users":-1,"retention_days":365}');
