# Architecture Details

## Service Boundaries

The platform is organized into clear, independent modules:

**Gateway** (`gateway/`)
- HTTP API entry point
- Request orchestration
- Dual checkpoint flow coordination
- **Boundary:** Handles HTTP, delegates to Policy Engine and Model Router

**Policy Engine** (`policy_engine/`)
- Policy registration and management
- Policy evaluation orchestration
- Precedence resolution
- **Boundary:** Policy logic only, no HTTP, no LLM calls

**Model Router** (`model_router/`)
- LLM provider abstraction
- Request routing to providers
- Error handling and retries
- **Boundary:** LLM communication only, no policy logic

**Policies** (`policies/`)
- Pluggable policy implementations
- Domain-specific compliance rules
- **Boundary:** Pure policy logic, implements PolicyModule interface

**Audit Module** (`audit/`)
- Audit event storage and retrieval
- PostgreSQL-backed persistence
- Query interface for compliance

**HITL Module** (`hitl/`)
- Review queue management
- PostgreSQL-based queue with `SELECT FOR UPDATE SKIP LOCKED`
- Review approval/rejection workflow
- Bypass logic for approved reviews

Each module communicates through well-defined interfaces, enabling independent development and testing.

## Internal Models

Key data models that define the platform's contracts:

**PolicyContext** - Universal context for policy evaluation
```python
{
  "prompt": "User's input text",
  "response": "LLM response (for output checkpoint)",
  "user_id": "user123",
  "user_role": "trader",
  "checkpoint": "input" | "output",
  "metadata": {...}
}
```

**LLMRequest** - Standardized LLM request format
```python
{
  "messages": [{"role": "user", "content": "Hello"}],
  "model": "mistral",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**LLMResponse** - Standardized LLM response format
```python
{
  "content": "Generated text",
  "model": "mistral",
  "provider": "ollama",
  "usage": {"prompt_tokens": 10, "completion_tokens": 20},
  "latency_ms": 150.5
}
```

**PolicyResult** - Policy evaluation result
```python
{
  "outcome": "REDACT",
  "reason": "PII detected: email address",
  "modified_content": "[REDACTED:EMAIL:ref_0001]",
  "policy_name": "pii_detection"
}
```

**EscalateResponse** - Response for escalated requests
```python
{
  "review_id": "1",
  "status": "pending_review",
  "message": "Request has been escalated for human review",
  "reason": "Policy reason for escalation",
  "trace_id": "abc-123-def-456",
  "checkpoint": "input" | "output"
}
```

See the codebase for complete model definitions:
- `policy_engine/models.py` - Policy models
- `model_router/models.py` - LLM models
- `gateway/models.py` - API models
- `hitl/models.py` - HITL models
- `audit/models.py` - Audit models

