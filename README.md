# AI Governance Platform

> **Status:** 🚧 Work in Progress  
> This project is under active development. Core policy engine is implemented, but gateway, model router, audit, and HITL modules are still being built.

## What This Platform Is

An **AI governance control plane** for enterprise LLM deployments. It sits between users and LLMs, enforcing policies, routing requests, and maintaining complete audit trails.

**Core capabilities (planned):**
- Policy enforcement at dual checkpoints (input and output)
- Pluggable compliance modules (MNPI, HIPAA, PDPL, custom rules)
- Human-in-the-loop workflows for high-risk decisions
- Complete audit trail for regulatory examination
- Multi-model routing with governance controls

**Current implementation status:**
- [x] Core policy models and interfaces (PolicyOutcome, PolicyContext, PolicyModule)
- [x] Policy registry and configuration loader
- [x] Policy engine with precedence resolution
- [ ] Gateway (API routes and orchestration) - In progress
- [ ] Model router (LLM abstraction) - Planned
- [ ] Audit module (logging service) - Planned
- [ ] HITL module (human review queue) - Planned

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

See [CORE_MODULE_STEPS.md](CORE_MODULE_STEPS.md) for implementation progress and remaining work.

### Getting Started

```bash
# Install dependencies
make install-dev

# Run tests
make test

# Run a single test
make test-one TEST=tests/test_policy_engine.py
```

### Architecture Decisions

See [architectural-decision-records/](architectural-decision-records/) for detailed design decisions and trade-offs.