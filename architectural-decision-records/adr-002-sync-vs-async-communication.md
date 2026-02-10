# ADR-002: Synchronous vs Async Communication Patterns

## Context

The system has multiple components that need to communicate: Gateway calls Policy Engine, policies write to Audit Logger, escalations go to HITL Queue, etc. Each interaction could be sync (caller waits for response) or async (fire-and-forget or eventual response).

When a user sends a request to the Gateway, their HTTP connection stays open waiting for a response. The Gateway must orchestrate a sequence of decisions—evaluate policies, route to model, evaluate output—before it can return anything to the user. Each step depends on the previous step's outcome.

The core question: when should we block waiting for a response vs. when should we publish an event and move on?

## Decision

**Use sync for the main request flow, async for everything else.**

### Synchronous (caller waits for response)

* Gateway → Policy Engine (input evaluation)
* Gateway → Model Router
* Model Router → LLM (OpenAI/Claude/etc)
* Gateway → Policy Engine (output evaluation)
* HITL Service → Gateway (when human approves/rejects and request resumes)

**Why sync:** The user's HTTP connection is open. The Gateway can't proceed to the next step without knowing the outcome of the current step. This is orchestration—each decision determines what happens next.

### Asynchronous (fire-and-forget via message queue)

* Any component → Audit Logger
* Policy Engine → HITL Queue (when escalation happens)
* All background jobs (metrics, cleanup, archiving)

**Why async:** Nobody is waiting for these operations. Logging shouldn't slow down responses. Human review takes minutes/hours. Background work happens independently.

### Communication Infrastructure

**Sync:** Direct HTTP/gRPC calls between services  
**Async:** Redis (development) or Kafka (production) message queues

## Alternatives Considered

**All sync:**  
Rejected because logging and escalations would block request threads. A slow audit write would delay the user's response. Trade-off: Simpler code for worse performance and coupling.

**All async:**  
Rejected because the main flow requires answers before proceeding. The Gateway can't route to a model without knowing which model the policy allows. Trade-off: Lower latency for broken orchestration semantics.

**Async HITL with webhooks:**  
Rejected for v1 because it requires callers to provide callback URLs and handle async responses. Enterprise clients aren't ready for this complexity. Trade-off: Simpler client integration for blocked request threads during human review.

**Async main flow with polling:**  
Rejected because it creates terrible UX. User submits request, gets "request ID", polls for status. They're waiting anyway—just with worse experience. Trade-off: Distributed system purity for poor user experience.

## Consequences

### Positive

* Main request flow is fast (only blocks on necessary decisions)
* Audit logging never slows down user responses
* Clear separation: sync = user waiting, async = background work
* Can scale audit and HITL systems independently from request handling
* Failure modes are explicit (sync fails immediately, async retries in background)

### Negative

* Dual communication patterns (both REST and message queues)
* More infrastructure required (Redis/Kafka for async)
* Different failure handling (sync = retry immediately, async = dead letter queue)
* HITL escalations block request threads (can't handle millions of concurrent reviews)
* Need to handle async failures separately (dead letter queues, monitoring)

### When to Revisit

* If HITL review volume grows to thousands/day (need async with webhooks or polling)
* If audit writes become a bottleneck even with async (need faster pipeline or batching)
* If policy evaluation becomes slow enough that sync calls are noticeable (>100ms)
* If we add features that don't fit request-response model (streaming, real-time updates)

---

**Status:** Accepted  
**Date:** 2026  
**Number:** ADR-002