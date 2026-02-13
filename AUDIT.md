# Audit Trail Documentation

## Overview

The platform maintains a **complete, immutable audit trail** for compliance and forensics. Every request is tracked end-to-end with full traceability.

## Audit Trail Features

### End-to-End Correlation

- Every request receives a unique `trace_id` (UUID)
- `trace_id` flows through all components (Gateway → Policy Engine → Model Router)
- Complete request lifecycle captured in database
- Query all events for a single request

### Component-Level Granularity

- **Policy Engine** audits: policy evaluations, outcomes, violations, performance metrics
- **Model Router** audits: routing decisions, provider selection, fallbacks, retries
- **Gateway** audits: request lifecycle, high-level flow coordination
- **HITL** audits: review creation, approval/rejection decisions
- Each component owns its audit domain for clear separation of concerns

### Structured Event Storage

- All audit events stored in PostgreSQL with JSONB for flexible querying
- Immutable audit trail (write-only, tamper-proof)
- Indexed for fast queries by `trace_id`, `request_id`, `user_id`, `event_type`
- Long-term retention for regulatory compliance (configurable)

### Compliance-Ready

- Complete request/response lifecycle tracking
- Policy violation detection and reporting
- User activity audit trail
- Performance metrics and timing data
- Ready for regulatory audits (SOC 2, HIPAA, FINRA, etc.)

## Querying the Audit Trail

### By Trace ID (End-to-End Request)

```sql
SELECT * FROM audit_events 
WHERE trace_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY timestamp;
```

### By Request ID

```sql
SELECT * FROM audit_events 
WHERE request_id = 'request-uuid-here'
ORDER BY timestamp;
```

### By User ID

```sql
SELECT * FROM audit_events 
WHERE event_data->>'user_id' = 'user123'
ORDER BY timestamp DESC;
```

### Policy Violations

```sql
SELECT * FROM audit_events 
WHERE event_type IN ('request_blocked', 'response_blocked', 'request_escalated', 'response_escalated')
ORDER BY timestamp DESC;
```

### By Event Type

```sql
SELECT * FROM audit_events 
WHERE event_type = 'policy_evaluation_complete'
AND timestamp > NOW() - INTERVAL '24 hours';
```

### Time Range Queries

```sql
SELECT * FROM audit_events 
WHERE timestamp BETWEEN '2024-01-01' AND '2024-01-31'
AND event_data->>'outcome' = 'BLOCK'
ORDER BY timestamp DESC;
```

## Audit vs Logging

**Logging (Operational):**
- High-volume, short retention (days/weeks)
- Real-time monitoring and debugging
- Structured JSON logs for operational visibility
- Used by: DevOps, SRE, developers

**Audit (Compliance):**
- Lower volume, long retention (years)
- Immutable, tamper-proof database records
- Queryable for compliance and forensics
- Used by: Compliance, Legal, Risk, Internal Audit

The platform provides both: operational logging for day-to-day operations, and a compliance-grade audit trail for regulatory requirements.

## Event Types

Common audit event types:

- `request_received` - Request arrived at gateway
- `request_blocked` - Request blocked by policy
- `request_escalated` - Request escalated for review
- `response_blocked` - Response blocked by policy
- `response_escalated` - Response escalated for review
- `request_completed` - Request successfully completed
- `policy_evaluation_start` - Policy evaluation began
- `policy_evaluated` - Individual policy evaluated
- `policy_evaluation_complete` - All policies evaluated
- `routing_start` - Model routing began
- `routing_success` - Model routing succeeded
- `routing_failed` - Model routing failed

See [LOGGING.md](LOGGING.md) for complete event format specification.

