# DataPulse AI — API Specification (v1)

Base URL: `https://api.datapulse.ai/v1`
Stack de referência: FastAPI + Pydantic v2 + SQLAlchemy 2.0 (async) + Alembic

## 1. Convenções gerais

- **Autenticação**: `Authorization: Bearer <jwt>` (login de usuário) ou `Authorization: Bearer <api_key>` (integrações machine-to-machine, prefixo `dp_live_...`).
- **Multi-tenant**: o `org_id` nunca vai na URL nem no body — é resolvido a partir do token (claim `org_id`) e injetado como `SET app.current_org_id` na sessão do banco (RLS cuida do isolamento).
- **Paginação**: cursor-based. `?limit=50&cursor=<opaque>`. Resposta inclui `next_cursor`.
- **Filtros**: query params diretos, ex: `?status=failed&environment=PRD&from=2026-07-01T00:00:00Z&to=2026-07-17T00:00:00Z`.
- **Ordenação**: `?sort=-started_at` (prefixo `-` = desc).
- **Versionamento**: via path (`/v1`, `/v2`). Sem breaking changes dentro da mesma major version.
- **Erros**: formato RFC 7807 (`application/problem+json`):
  ```json
  { "type": "validation_error", "title": "Invalid field", "status": 422,
    "detail": "sla_minutes must be > 0", "field": "sla_minutes" }
  ```
- **Rate limit**: por org e por plano, headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## 2. Auth

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/login` | email + senha → JWT (access + refresh) |
| POST | `/auth/refresh` | troca refresh token por novo access token |
| POST | `/auth/mfa/verify` | valida código MFA no login |
| POST | `/auth/sso/{provider}/callback` | callback OAuth2 (Azure AD, Google) |
| POST | `/auth/logout` | revoga refresh token |
| GET | `/auth/me` | perfil do usuário autenticado + roles/permissions |

## 3. Organizations & Users

| Método | Rota | Descrição |
|---|---|---|
| GET | `/organizations/me` | dados da org atual + plano/limites |
| PATCH | `/organizations/me` | atualizar settings |
| GET | `/users` | listar usuários da org |
| POST | `/users` | convidar usuário |
| GET | `/users/{id}` | detalhe |
| PATCH | `/users/{id}` | editar (roles, status) |
| DELETE | `/users/{id}` | desativar |
| GET | `/roles` | listar roles disponíveis |
| POST | `/roles` | criar role customizada |
| GET | `/api-keys` | listar chaves de API |
| POST | `/api-keys` | gerar nova chave (retorna valor em texto plano **uma única vez**) |
| DELETE | `/api-keys/{id}` | revogar |

## 4. Conexões / Integrações

| Método | Rota | Descrição |
|---|---|---|
| GET | `/integration-types` | catálogo de integrações suportadas |
| GET | `/connections` | listar conexões configuradas |
| POST | `/connections` | criar conexão (testa conectividade antes de salvar) |
| GET | `/connections/{id}` | detalhe |
| PATCH | `/connections/{id}` | editar config |
| DELETE | `/connections/{id}` | remover |
| POST | `/connections/{id}/test` | testar conectividade sob demanda |

## 5. Pipelines

| Método | Rota | Descrição |
|---|---|---|
| GET | `/pipelines` | listar (filtros: `environment`, `status`, `connection_id`, `tag`) |
| POST | `/pipelines` | registrar pipeline manualmente |
| GET | `/pipelines/{id}` | detalhe + últimos KPIs (SLA, tempo médio) |
| PATCH | `/pipelines/{id}` | editar (SLA, tags, owner) |
| DELETE | `/pipelines/{id}` | remover |
| GET | `/pipelines/{id}/runs` | histórico de execuções (paginado) |
| GET | `/pipelines/{id}/metrics` | série temporal (cpu, ram, duração) — `?metric=duration&granularity=1h` |
| GET | `/pipelines/{id}/logs` | logs (filtros: `level`, `from`, `to`) |

## 6. Ingestão (usada pelos coletores/agentes)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/ingest/runs` | reporta início/fim de execução (batch aceito) |
| POST | `/ingest/logs` | envia logs em lote |
| POST | `/ingest/metrics` | envia métricas em lote (formato similar ao Prometheus remote_write) |

> Rotas de ingestão usam API key com escopo `ingest:write` e são otimizadas para throughput alto (aceitam arrays, sem overhead de validação pesada).

## 7. Alertas

| Método | Rota | Descrição |
|---|---|---|
| GET | `/alert-rules` | listar regras |
| POST | `/alert-rules` | criar regra (`condition_type`, `condition_config`, `severity`) |
| PATCH | `/alert-rules/{id}` | editar |
| DELETE | `/alert-rules/{id}` | remover |
| GET | `/alerts` | listar alertas (filtros: `status`, `severity`, `pipeline_id`) |
| PATCH | `/alerts/{id}` | mudar status (`acknowledged`/`resolved`) |
| GET | `/notification-channels` | listar canais configurados |
| POST | `/notification-channels` | criar canal (Teams/Slack/Discord/Telegram/WhatsApp/Email/Push) |
| POST | `/notification-channels/{id}/test` | enviar notificação de teste |

## 8. Machine Learning / IA

| Método | Rota | Descrição |
|---|---|---|
| GET | `/pipelines/{id}/predictions` | previsões ativas (falha, duração, timeout) |
| GET | `/anomalies` | anomalias detectadas (filtros: `pipeline_id`, `severity`, `from/to`) |
| POST | `/ai/chat` | pergunta em linguagem natural → resposta com contexto dos dados |
| GET | `/ai/conversations` | histórico de conversas do usuário |
| GET | `/ai/conversations/{id}` | mensagens de uma conversa |

### Exemplo — `POST /ai/chat`

```json
// Request
{ "conversation_id": null, "message": "Por que o Pipeline Financeiro falhou?" }

// Response
{
  "conversation_id": "3f2b...",
  "answer": "O Pipeline Financeiro apresentou erro às 09:13. Motivo: timeout na conexão SQL Server. Probabilidade de recorrência: 92%. Sugestão: verificar disponibilidade do servidor SQL01.",
  "context_refs": {
    "pipeline_id": "a1b2...",
    "run_id": "c3d4...",
    "anomaly_id": null
  }
}
```
Internamente: o endpoint monta um contexto (últimas N runs, logs de erro, anomalias recentes do pipeline citado) e chama o LLM com esse contexto injetado — não é o modelo "adivinhando", é RAG sobre os dados operacionais do tenant.

## 9. Dashboards

| Método | Rota | Descrição |
|---|---|---|
| GET | `/dashboards` | listar dashboards do usuário/org |
| POST | `/dashboards` | criar |
| GET | `/dashboards/{id}` | detalhe com widgets |
| PATCH | `/dashboards/{id}` | atualizar layout/widgets |
| DELETE | `/dashboards/{id}` | remover |
| GET | `/dashboards/{id}/export` | exportar como PDF/Excel — `?format=pdf` |

## 10. Auditoria

| Método | Rota | Descrição |
|---|---|---|
| GET | `/audit-logs` | listar (somente roles admin) — filtros: `user_id`, `action`, `from/to` |

---

## 11. Exemplo de payload — `GET /pipelines/{id}`

```json
{
  "id": "a1b2c3d4-...",
  "name": "Pipeline Financeiro",
  "environment": "PRD",
  "pipeline_type": "etl",
  "connection": { "id": "...", "name": "Airflow Prod", "type": "airflow" },
  "sla_minutes": 15,
  "kpis": {
    "status": "healthy",
    "success_rate_24h": 0.97,
    "avg_duration_seconds": 182.4,
    "last_run_at": "2026-07-17T09:13:00Z",
    "last_run_status": "failed"
  },
  "tags": ["financeiro", "critico"]
}
```

## 12. Estrutura de erros HTTP padrão

| Código | Uso |
|---|---|
| 400 | payload malformado |
| 401 | token ausente/expirado |
| 403 | sem permissão (RBAC) |
| 404 | recurso não encontrado (ou fora do tenant — nunca vaza existência) |
| 409 | conflito (ex: nome duplicado) |
| 422 | validação de negócio |
| 429 | rate limit excedido |
| 5xx | erro interno (logado com correlation-id no header `X-Request-ID`) |

## 13. Próximos passos técnicos

1. Gerar OpenAPI 3.1 completo a partir dos modelos Pydantic (FastAPI faz isso automaticamente em `/openapi.json`).
2. Definir escopos de API key granulares por recurso (`pipelines:read`, `alerts:write`, `ingest:write`...).
3. Especificar contrato de webhooks de saída (para clientes que querem consumir eventos, não só polling).
