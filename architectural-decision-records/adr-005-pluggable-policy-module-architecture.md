# ADR-005: Pluggable Policy Module Architecture (Microkernel Pattern)

## Context

The platform needs to enforce different policies based on industry vertical, customer, and use case. Finance needs MNPI detection and data redaction. Healthcare needs HIPAA compliance and PHI protection. Government needs data sovereignty and classification enforcement.

We could hardcode all policies directly into the core engine, or design the engine to load policies as independent modules. 

Hardcoded approach means every new policy requires editing core engine code. Adding HIPAA support means modifying the same file that handles MNPI. Finance logic and healthcare logic all mixed together. Testing is all-or-nothing. Customers can't add custom policies.

Pluggable approach means policies are independent modules with a standard interface. Core engine just orchestrates—registers modules, runs them in sequence, aggregates outcomes. New verticals are new modules, not core changes. Customers could write their own policies.

The question: should the engine be a fixed product with specific policies, or infrastructure that executes pluggable modules?

## Decision

**Use microkernel architecture with pluggable policy modules.**

The core engine is stable infrastructure. Policies are plugins that implement a standard interface.

### The Interface Contract

Every policy module implements the same interface:
```python
class PolicyModule:
    def evaluate(self, context: PolicyContext) -> PolicyOutcome:
        """
        Receives: PolicyContext with all request data
        Returns: PolicyOutcome with decision and reason
        """
        pass
```

**PolicyContext** (universal contract passed to every policy):
- Prompt/request content
- User identity and role
- Data classification
- Metadata (customer, vertical, etc.)
- Prior policy decisions (if running multiple)

**PolicyOutcome** (standardized response):
- Decision (ALLOW/BLOCK/REDACT/ESCALATE)
- Reason (why this decision)
- Modified content (if REDACT)
- Confidence score

### Registration and Execution

**Modules register at startup:**
```python
engine.register("pii_detection", PIIDetectionPolicy())
engine.register("mnpi_check", MNPIPolicy())
engine.register("prompt_injection", PromptInjectionPolicy())
```

**Configuration controls which policies run:**
```yaml
policies:
  - name: pii_detection
    enabled: true
    config:
      redact_emails: true
      
  - name: mnpi_check
    enabled: true
    config:
      watch_list: /data/securities.txt
      
  - name: hipaa_compliance
    enabled: false  # Not needed in finance vertical
```

**Runtime evaluation runs enabled policies in sequence:**
```python
for policy in engine.get_active_policies():
    outcome = policy.evaluate(context)
    # Apply outcome precedence rules
```

### Module Structure

Each policy is isolated code:
```
/policies/
  pii_detection.py
  mnpi.py
  prompt_injection.py
  finance/
    client_comms.py
    data_redaction.py
  healthcare/
    hipaa.py
    phi_protection.py
```

Modules don't import from each other. They only depend on the interface contract (PolicyContext/PolicyOutcome).

### Critical Constraint

**PolicyContext must be comprehensive upfront.**

It's the only data policies receive. Must include everything any policy might need. Changes to PolicyContext break all existing policies, so it must be designed carefully at the start.

## Alternatives Considered

**Hardcoded policies in core engine:**  
Rejected because every new vertical requires core code changes. Finance and healthcare logic would be intertwined. Can't disable policies without code changes. Testing requires running all policies. Trade-off: Simplicity for inflexibility.

**Policy-as-service (each policy is a microservice):**  
Rejected because overhead is absurd. Network call for every policy on every request. Service discovery, deployment, monitoring for 100-line policy modules. Trade-off: Maximum isolation for operational nightmare and latency.

**Scripting layer (Lua/Python files loaded at runtime):**  
Rejected because runtime code loading is a security risk. Untrusted scripts could do anything. Hard to version, test, and debug. Trade-off: Ultimate flexibility for security holes.

**Rule engine (Drools-style declarative rules):**  
Rejected because some policies require ML models, API calls, complex logic that doesn't fit declarative rules. Good for simple "if X then Y" but limiting for real-world policies. Trade-off: Simplicity for capability ceiling.

## Consequences

### Positive

- Add new policies without touching core engine code
- Enable/disable policies via configuration (no deployments)
- Test policies in isolation (each is independent)
- Different customers get different policy sets (finance vs healthcare)
- Third parties could write custom policies (extensibility)
- Clear separation of concerns (core orchestration vs policy logic)
- Platform becomes infrastructure, not a product

### Negative

- Abstraction overhead (interface layer adds complexity)
- PolicyContext must be comprehensive upfront (hard to extend later)
- Can't optimize for specific policies (engine doesn't know their internals)
- Version compatibility burden (interface changes break all policies)
- Performance ceiling (can't tightly couple engine and policies)
- More files, more structure, steeper learning curve

### When to Revisit

- If PolicyContext becomes inadequate (policies need data we didn't anticipate)
- If interface overhead causes measurable performance degradation
- If 90%+ of policies fit a simpler pattern (rule engine might suffice)
- If version management becomes unmanageable (breaking changes proliferate)

---

**Status:** Accepted  
**Date:** 2024  
**Number:** ADR-005