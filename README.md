# AI Governance Platform

> **Status:** 🚧 Work in Progress  
> Core modules are implemented and functional. Audit and HITL modules are fully implemented with PostgreSQL-backed storage.

## Architecture Diagrams

- **[Architecture Diagram](https://lucid.app/lucidchart/3e60cae0-e210-4855-ad53-53f0a3bae7f3/edit?invitationId=inv_7d457cde-50f8-4740-b81f-c64bf82ccd12&page=0_0#)** - System architecture and component relationships
- **[Flow Diagram](https://lucid.app/lucidchart/a639c3b2-5f57-45b1-b883-9c21f1f4e904/edit?invitationId=inv_cb011cd4-2674-4612-9266-48db6bd927aa&page=0_0#)** - Request flow and dual checkpoint validation

## Architecture Decisions

See [architectural-decision-records/](architectural-decision-records/) for detailed design decisions and trade-offs.

## What This Platform Is

An **AI governance control plane** for enterprise LLM deployments. It sits between users and LLMs, enforcing policies, routing requests, and maintaining complete audit trails.

**Core capabilities:**
- Policy enforcement at dual checkpoints (input and output)
- Pluggable compliance modules (MNPI, PII detection, custom rules)
- Multi-model routing with governance controls
- Local model support (Ollama)
- Human-in-the-loop workflows (PostgreSQL queue with review management)
- Complete audit trail (PostgreSQL-backed with end-to-end traceability)

## What This Platform Governs

**Governed:**
- Internal applications calling LLM APIs
- Custom chatbots and conversational interfaces
- Automated workflows using AI
- Agentic systems (multi-step reasoning with tools)
- Any programmatic LLM access

**Not Governed:**
- Direct access to public LLM websites (chatgpt.com, claude.ai)
- Personal devices outside corporate network
- Shadow IT workarounds

## Target Users

**Primary:** Enterprises in regulated industries (finance, healthcare, defense, government)  
**Use cases:** Trading desks, clinical workflows, classified environments, any high-stakes AI deployment  
**Requirements:** Auditability, compliance, controlled execution, data sovereignty

## Architecture Philosophy

**Governed by design, not bolted on.**

The platform doesn't monitor or analyze LLM usage after the fact. It **controls access** at the request level. Users don't get LLM access unless it passes through governance.

This is enforcement, not surveillance.

## Deployment Model

The platform operates as an **API gateway** that applications call instead of calling OpenAI/Claude directly.

**Before (ungoverned):**
```python
response = openai.chat.completions.create(...)
```

**After (governed):**
```python
response = requests.post("https://governance-platform.company.com/api/chat", ...)
```

**Enforcement:**
- Network-level blocks on public LLM sites (chatgpt.com, etc.)
- Platform provides approved alternative with better capabilities
- Audit trail for compliance and violation detection

## Policy Outcomes

The platform uses four policy outcomes, ordered by precedence (most restrictive to least):

| Outcome | Description | Example |
|---------|-------------|---------|
| **BLOCK** | Stops request immediately | MNPI violation, restricted security |
| **ESCALATE** | Queues for human review | High-risk content requiring approval |
| **REDACT** | Modifies content, then allows | PII detected and redacted |
| **ALLOW** | Request proceeds unchanged | No policy violations |

When multiple policies evaluate the same request, the most restrictive outcome wins (BLOCK > ESCALATE > REDACT > ALLOW).

## Architecture Overview

The platform is organized into independent modules:

- **Gateway** (`gateway/`) - HTTP API, request orchestration, dual checkpoint coordination
- **Policy Engine** (`policy_engine/`) - Policy registration, evaluation, precedence resolution
- **Model Router** (`model_router/`) - LLM provider abstraction, routing, error handling
- **Policies** (`policies/`) - Pluggable compliance modules (MNPI, PII, custom)
- **Audit Module** (`audit/`) - PostgreSQL-backed audit trail with end-to-end traceability
- **HITL Module** (`hitl/`) - Review queue management with bypass logic

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed service boundaries and internal models.

## Development

### Quick Start

```bash
# Install dependencies
make install-dev

# Start Gateway (requires Ollama and PostgreSQL running)
make gateway

# Or run directly
uv run python main.py
```

### Prerequisites

- **PostgreSQL** installed and running
- **Ollama** installed and running (`ollama serve`)
- **Mistral model** installed (`ollama pull mistral`)
- Python 3.10+

### Database Setup

1. **Create database:**
   ```bash
   createdb audit_db
   # Or using psql:
   psql -U your_username -c "CREATE DATABASE audit_db;"
   ```

2. **Run migrations:**
   ```bash
   psql -U your_username -d audit_db -f migrations/001_create_audit_events_table.sql
   psql -U your_username -d audit_db -f migrations/002_create_hitl_reviews_table.sql
   ```

3. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```bash
   DATABASE_URL=postgresql://username:password@localhost:5432/audit_db
   DB_POOL_SIZE=10
   DB_POOL_MAX_OVERFLOW=5
   ```

See [migrations/README.md](migrations/README.md) for detailed migration instructions.

### Testing

```bash
# Run all tests
make test

# Run a single test
make test-one TEST=tests/test_policy_engine.py
```

## Example API Calls

### ALLOW - Clean Request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is the weather today?"}]
  }'
```

**Response:** `200 OK` with LLM response.

### ESCALATE - Human Review Required

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "This request needs human review and approval before proceeding"}],
    "user_id": "test_user_123"
  }'
```

**Response:** `202 Accepted` with `EscalateResponse` containing `review_id`.

**Next Steps:**
1. Approve: `POST /api/hitl/reviews/{review_id}/approve?reviewed_by=admin`
2. Re-submit same request - it will bypass escalation and proceed

### BLOCK - Policy Violation

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is the current stock price of AAPL?"}]
  }'
```

**Response:** `403 Forbidden` - Request blocked (AAPL is on restricted list).

See [EXAMPLES.md](EXAMPLES.md) for complete examples of all outcomes and HITL operations.

---

**API docs:** http://localhost:8000/docs

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Service boundaries, internal models, module details
- **[AUDIT.md](AUDIT.md)** - Audit trail features, querying examples, event types
- **[HITL.md](HITL.md)** - Human-in-the-loop workflow, review API, bypass logic
- **[EXAMPLES.md](EXAMPLES.md)** - Complete API examples for all outcomes
- **[LOGGING.md](LOGGING.md)** - Event-style structured logging format
- **[NEXT_STEPS.md](NEXT_STEPS.md)** - Roadmap and future enhancements
- **[USABILITY_FOR_TESTING.md](USABILITY_FOR_TESTING.md)** - Testing improvements needed

## Auditability

The platform maintains a **complete, immutable audit trail** for compliance and forensics:

- **End-to-end correlation** via `trace_id` (UUID) across all components
- **Component-level granularity** - each module audits its own domain
- **PostgreSQL-backed storage** with JSONB for flexible querying
- **Compliance-ready** for regulatory audits (SOC 2, HIPAA, FINRA, etc.)

See [AUDIT.md](AUDIT.md) for detailed querying examples and event types.

## Human-In-The-Loop (HITL)

The platform includes a complete HITL workflow:

- **Escalation** creates reviews in PostgreSQL queue
- **Review management** via API endpoints (approve/reject/list)
- **Bypass logic** - approved reviews skip escalation for identical requests
- **Queue support** using `SELECT FOR UPDATE SKIP LOCKED` for concurrent workers

See [HITL.md](HITL.md) for complete workflow documentation and API details.

## Logging

The platform uses **event-style structured logging** with JSON output for machine-readability and queryability.

See [LOGGING.md](LOGGING.md) for event format specification, common patterns, and best practices.

## Roadmap

### Agent Workflow Support

The platform will support agentic workflows by governing each action—both LLM calls and tool executions.

**Planned features:**
- [ ] Tool execution endpoint (`POST /api/tools`)
- [ ] Tool registry (register and manage available tools)
- [ ] Tool-specific policies (govern database queries, API calls, file operations)
- [ ] Agent workflow tracking (link multi-step workflows)
- [ ] Tool allowlists (user/role-based tool access)

See [ADR-006](architectural-decision-records/adr-006-agent-workflow-support.md) for detailed design.

### Other Planned Features

- [ ] **Additional Policies** - HIPAA, prompt injection, custom compliance rules
- [ ] **Production Hardening** - Monitoring, scaling, security enhancements

See [NEXT_STEPS.md](NEXT_STEPS.md) for complete roadmap.
