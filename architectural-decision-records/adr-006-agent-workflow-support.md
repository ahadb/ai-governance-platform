# ADR-008: Agentic Workflow Support

## Context

LLM usage is evolving from single request-response to multi-step agentic workflows. An agent reasons about what to do, calls tools (APIs, databases, filesystem), observes results, and iterates until the task is complete.

Current system handles single LLM calls well: user asks question, LLM responds, policies enforce, done. But agents make 5-10 LLM calls plus 3-5 tool calls per user query. Each action is a decision point where something could go wrong.

Examples of risk:
- Agent calls database tool with poorly formed query → data leak
- Agent decides to delete files based on hallucinated reasoning → data loss
- Agent makes API call to external service with sensitive data → compliance violation

The question: should the platform govern agentic workflows, or only support single LLM interactions?

If yes, how do we govern tool execution (not just LLM reasoning)? If no, we become irrelevant as AI moves toward agents.

## Decision

**The platform supports agentic workflows by treating each action—LLM call or tool execution—as a governed request.**

Agents route both LLM calls and tool executions through the gateway. Each gets policy evaluation. Each gets logged. Multi-step workflows become a series of governed actions.

### How It Works

**Agent needs to reason:**
- Calls gateway `POST /api/chat`
- Policies evaluate the reasoning step
- LLM responds
- Agent continues

**Agent needs to use tool:**
- Calls gateway `POST /api/tools`
- Tool policies evaluate
- Tool executes (or blocked)
- Result returns
- Agent continues

Each step independent. Each step governed. No special "agent mode"—just more requests.

### Tool Governance

Tools are registered with the platform. Each tool has:
- **Allowlist:** Which users/roles can call it
- **Policies:** What checks apply before execution
- **Constraints:** Rate limits, timeouts, retry policies

Unregistered tools cannot be called through the platform.

**Example tool endpoint:**
```json
POST /api/tools
{
  "tool": "database_query",
  "args": {"query": "SELECT * FROM trades WHERE..."},
  "user_id": "agent_run_123"
}
```

Policy engine evaluates tool calls the same way it evaluates LLM calls:
- Same outcome model (ALLOW/BLOCK/REDACT/ESCALATE)
- Same audit trail
- Same precedence rules

## Alternatives Considered

**LLM-only governance (ignore tools):**  
Rejected because tool execution is where real risk lives. Governing only LLM reasoning misses the actual actions that cause damage. Trade-off: Simpler scope for incomplete protection.

**Separate tool governance system:**  
Rejected because it fragments governance. Agent workflows span LLM calls and tool calls. Two systems means two policies, two audit trails, operational nightmare. Trade-off: Separation of concerns for complexity and gaps.

**Trust agents to self-govern:**  
Rejected because agents hallucinate, make mistakes, and can be manipulated via prompt injection. Assuming agent judgment is safe defeats the purpose of governance. Trade-off: Nothing gained for everything lost.

**Agent-specific policies (different rules for agents vs humans):**  
Rejected because risk is in the action, not the caller. A dangerous database query is dangerous regardless of who initiated it. Trade-off: Agent-specific optimizations for unnecessary complexity.

## Consequences

### Positive

- Platform stays relevant as AI moves toward agents
- Single governance system for LLM calls and tool execution
- Complete audit trail of multi-step workflows
- Tool policies prevent dangerous actions (data deletion, unauthorized access)
- Simple agent integration (just route calls through gateway)
- Works with any agent framework that can make HTTP calls
- No architectural changes to core platform (tools are just another request type)

### Negative

- Gateway must handle tool execution (more surface area)
- Tool registry adds operational overhead (registration, configuration, maintenance)
- Need to write tool-specific policies (different from LLM policies)
- Latency compounds in multi-step workflows (each action adds governance overhead)
- High request volume from agent loops (10+ calls per user query)
- Tool execution failures need different handling than LLM failures

### When to Revisit

- If tool execution volume greatly exceeds LLM volume (separate tool gateway makes sense)
- If agents require <10ms tool latency (governance overhead unacceptable)
- If tool governance diverges significantly from LLM governance (separate systems justified)
- If agent frameworks add native governance (less need for external platform)

---

**Status:** Accepted  
**Date:** 2026  
**Number:** ADR-008