# ADR-003: Modular Monolith to Microservices Strategy

## Context

We could build this as microservices from day one or start as a monolith. The architecture has clear components—Gateway, Policy Engine, Audit Logger, HITL Queue, Model Router—that could be separate services.

Microservices are the default for "scalable systems," but they come with real operational overhead: service discovery, distributed tracing, network calls instead of function calls, deployment orchestration, data consistency across services. For a 3-week MVP, that's a lot of infrastructure for unclear benefit.

But we also know this needs to scale eventually. Audit logging has different scaling characteristics than policy evaluation. At high traffic, these need to be independent services.

The question: do we pay the microservices tax upfront, or start simple and split later?

## Decision

**Start as a modular monolith. Design for microservices decomposition from day one.**

All components run in a single FastAPI application, but they're structured as independent modules with clear boundaries:

- `/gateway` - API routes and orchestration
- `/policy_engine` - Evaluation logic and module registry  
- `/audit` - Logging service
- `/hitl` - Review queue management
- `/model_router` - LLM abstraction layer

Each module:
- Has its own interface (not directly importing from other modules)
- Owns its data access (no cross-module database queries)
- Communicates through defined contracts
- Could be extracted to a service by wrapping in HTTP/gRPC

Single deployment, single database, single process. But architected so that extracting a service is moving a folder to a new repo and adding a network boundary, not rewriting code.

### Decomposition Strategy

When to split (based on actual bottlenecks, not premature optimization):

1. **Audit Service first** (10x traffic) - High write volume, read occasionally. Different scaling profile.
2. **Policy Engine second** (100x traffic) - CPU-intensive evaluation becomes bottleneck.
3. **HITL Service third** (if review volume grows) - Async workflows, different availability needs.
4. **Full microservices** (1000x traffic) - Gateway becomes thin orchestrator, everything else independent.

## Alternatives Considered

**Microservices from day one:**  
Rejected because it adds weeks to development for features we don't need yet (service mesh, distributed tracing, deployment orchestration). Trade-off: Premature complexity for theoretical future scale.

**Pure monolith (no module boundaries):**  
Rejected because splitting later would require major refactoring. Tight coupling makes extraction expensive. Trade-off: Faster initial development for painful future migration.

**Serverless (Lambda functions):**  
Rejected because the request flow is orchestration-heavy with state. Lambda works for independent functions, not multi-step workflows with shared context. Trade-off: Auto-scaling for poor fit to problem domain.

**Service-per-policy-module:**  
Rejected because policy modules are plugins, not services. Each module is ~100 lines of code. The overhead of making each one a service is absurd. Trade-off: Maximum isolation for operational nightmare.

## Consequences

### Positive

- Single deployment (docker-compose up, done)
- Fast development (no network calls, no service discovery)
- Easier debugging (single process, stack traces work)
- Lower infrastructure cost (one container vs five)
- Designed for split (clear boundaries, defined interfaces)
- Can defer microservices decisions until actual bottlenecks appear

### Negative

- Can't scale components independently yet (audit and policy engine share resources)
- Single point of failure (if the process crashes, everything crashes)
- Shared database initially (can't optimize storage per service)
- Deploy together (can't update audit service without redeploying everything)
- Risk of coupling creep (need discipline to maintain boundaries)

### When to Revisit

- When audit writes become bottleneck (>1000 writes/sec, PostgreSQL struggling)
- When policy engine CPU consumption separates from gateway (different scaling needs visible)
- When team grows beyond 3-4 people (separate ownership needed)
- When different components need different deployment schedules (audit changes daily, core is stable)

---

**Status:** Accepted  
**Date:** 2026   
**Number:** ADR-003