# AI Governance Platform

> **Status:** 🚧 Work in Progress  
> Core modules are implemented and functional. Audit and HITL modules are stubbed for future implementation.

## What This Platform Is

An **AI governance control plane** for enterprise LLM deployments. It sits between users and LLMs, enforcing policies, routing requests, and maintaining complete audit trails.

**Core capabilities:**
- [x] Policy enforcement at dual checkpoints (input and output)
- [x] Pluggable compliance modules (MNPI, PII detection, custom rules)
- [x] Multi-model routing with governance controls
- [x] Local model support (Ollama)
- [ ] Human-in-the-loop workflows (stub)
- [ ] Complete audit trail (stub)

**Current implementation status:**
- [x] **Policy Engine** - Complete with precedence resolution
- [x] **Model Router** - Complete with Ollama, OpenAI, Anthropic support
- [x] **Gateway** - Complete with dual checkpoint flow
- [x] **Example Policies** - PII detection, MNPI compliance
- [ ] **Audit Module** - Stub (logging placeholder)
- [ ] **HITL Module** - Stub (review queue placeholder)

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

## Target Users

**Primary:** Enterprises in regulated industries (finance, healthcare, defense, government)  
**Use cases:** Trading desks, clinical workflows, classified environments, any high-stakes AI deployment  
**Requirements:** Auditability, compliance, controlled execution, data sovereignty

## Architecture Philosophy

**Governed by design, not bolted on.**

The platform doesn't monitor or analyze LLM usage after the fact. It **controls access** at the request level. Users don't get LLM access unless it passes through governance.

This is enforcement, not surveillance.

## Development

### Quick Start

```bash
# Install dependencies
make install-dev

# Start Gateway (requires Ollama running)
make gateway

# Or run directly
uv run python main.py
```

### Prerequisites

- **Ollama** installed and running (`ollama serve`)
- **Mistral model** installed (`ollama pull mistral`)
- Python 3.10+

### Testing

```bash
# Run all tests
make test

# Run a single test
make test-one TEST=tests/test_policy_engine.py
```

### Example API Calls

#### ALLOW - Clean Request (Passes All Policies)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is the weather today?"}]
  }'
```

**Response:** `200 OK` with LLM response. No policy violations detected.

#### BLOCK - MNPI Violation (Restricted Security)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is the current stock price of AAPL?"}]
  }'
```

**Response:** `403 Forbidden` - Request blocked. AAPL is on the restricted securities list.

#### BLOCK - MNPI Keywords

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "I have insider information about an upcoming merger"}]
  }'
```

**Response:** `403 Forbidden` - Request blocked. Contains MNPI keywords.

#### REDACT - PII Detection (Email & Phone)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Please send the report to john.doe@example.com or call me at 555-123-4567"}]
  }'
```

**Response:** `200 OK` with redacted content. PII is replaced with tokens like `[REDACTED:EMAIL:ref_0001]`.

#### REDACT - SSN Detection

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "My social security number is 123-45-6789"}]
  }'
```

**Response:** `200 OK` with redacted SSN. Request proceeds but sensitive data is masked.

#### ESCALATE - Human Review Required

```bash
# TODO: ESCALATE outcome not yet fully implemented
# This would trigger human-in-the-loop review workflow
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Request that triggers escalation policy"}]
  }'
```

**Response:** `202 Accepted` - Request queued for human review. Review ID returned.

---

API docs available at: http://localhost:8000/docs

## Roadmap

### Agent Workflow Support

The platform will support agentic workflows by governing each action—both LLM calls and tool executions.

**Planned features:**
- [ ] Tool execution endpoint (`POST /api/tools`)
- [ ] Tool registry (register and manage available tools)
- [ ] Tool-specific policies (govern database queries, API calls, file operations)
- [ ] Agent workflow tracking (link multi-step workflows)
- [ ] Tool allowlists (user/role-based tool access)

**How it works:**
- Agents route LLM calls through `/api/chat` (already supported)
- Agents route tool calls through `/api/tools` (planned)
- Each action gets policy evaluation independently
- Complete audit trail of multi-step workflows

See [ADR-006](architectural-decision-records/adr-006-agent-workflow-support.md) for detailed design.

### Other Planned Features

- [ ] **Audit Module** - Real logging and audit trail storage
- [ ] **HITL Module** - Human review queue and workflows
- [ ] **Additional Policies** - HIPAA, prompt injection, custom compliance rules
- [ ] **Production Hardening** - Monitoring, scaling, security enhancements

### Architecture Decisions

See [architectural-decision-records/](architectural-decision-records/) for detailed design decisions and trade-offs.