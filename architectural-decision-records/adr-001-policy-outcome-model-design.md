# ADR-001: Policy Outcome Model Design

## Context

Policy evaluation needs to return something the gateway can act on. Binary allow/deny works for firewalls, but enterprise AI needs more nuance.

Real scenarios:
* Trader asks about a restricted security → BLOCK immediately
* Analyst pastes a document with PII → STRIP the PII, then allow
* Junior employee drafts client communication → PAUSE for senior review
* Normal query → ALLOW through

Binary forces us to either block everything risky or allow everything and handle edge cases downstream.

## Decision

**Four outcomes: ALLOW, BLOCK, REDACT, ESCALATE**

Each outcome applies to both input and output policies:
* Input policies evaluate the request before it hits the LLM
* Output policies evaluate the LLM response before returning to user
* Same outcome model, different checkpoint

### Outcome Definitions

* **ALLOW:** Request/response proceeds unchanged
* **BLOCK:** Stops flow immediately. Returns error to user. Logged with reason.
* **REDACT:** Returns new content (does not mutate original). Sensitive data replaced with tokens (e.g., `[REDACTED:PII:ref_4821]`). Original stored in secure lookup table. Flow continues with redacted version.
* **ESCALATE:** Synchronously blocks and creates review queue entry. Request suspended until human approves/rejects. If approved, flow resumes from where it paused. If rejected, treated as BLOCK.

### Outcome Precedence

When multiple policies fire, precedence (most to least restrictive):

1. **BLOCK** (most restrictive, stops everything)
2. **ESCALATE** (requires human decision)
3. **REDACT** (modifies but allows)
4. **ALLOW** (least restrictive)

*Example:* If input policy says REDACT and output policy says BLOCK → BLOCK wins.

### Flow Diagram
```
LLM Response → Policy Eval → Outcome Decision → [ALLOW/BLOCK/REDACT/ESCALATE] → User
```

## Alternatives Considered

**Binary model (ALLOW/BLOCK only):**  
Rejected because redaction and human review would need separate middleware. Trade-off: 2x complexity for 4x expressiveness.

**Six outcomes (adding WARN and DEFER):**  
Rejected because WARN can be logged without being a distinct outcome, and DEFER (rate limiting) belongs at the gateway layer. Trade-off: Less granularity for simpler mental model.

**Outcome combinations (REDACT + ESCALATE):**  
Rejected because it creates combinatorial explosion and unclear semantics. Trade-off: Single outcome per evaluation. Chain policies if you need both.

**Async ESCALATE:**  
Rejected for v1 because it requires distributed workflow engine and complex timeout handling. Trade-off: Synchronous blocking for simplicity. Will revisit at scale.

## Consequences

### Positive

* Human review is first-class (ESCALATE)
* Data sanitization happens at policy layer (REDACT)
* Clear precedence rules prevent conflicts
* Immutable redaction (returns new content, doesn't mutate)
* Same model works at both checkpoints

### Negative

* 4 code paths instead of 2
* ESCALATE blocks synchronously (can't scale to millions of concurrent escalations)
* Gateway must handle precedence logic
* Testing matrix: 4 outcomes × 2 checkpoints = 8 paths minimum

### When to Revisit

* If ESCALATE becomes async (would change entire queue architecture)
* If 90%+ of policies only use ALLOW/BLOCK
* If we need outcome combinations (REDACT + ESCALATE simultaneously)

---

**Status:** Accepted  
**Date:** 2026  
**Number:** ADR-001