# API Examples

Complete examples for all policy outcomes and common operations.

## Policy Outcome Examples

### ALLOW - Clean Request (Passes All Policies)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is the weather today?"}]
  }'
```

**Response:** `200 OK` with LLM response. No policy violations detected.

### BLOCK - MNPI Violation (Restricted Security)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is the current stock price of AAPL?"}]
  }'
```

**Response:** `403 Forbidden` - Request blocked. AAPL is on the restricted securities list.

### BLOCK - MNPI Keywords

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "I have insider information about an upcoming merger"}]
  }'
```

**Response:** `403 Forbidden` - Request blocked. Contains MNPI keywords.

### REDACT - PII Detection (Email & Phone)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Please send the report to john.doe@example.com or call me at 555-123-4567"}]
  }'
```

**Response:** `200 OK` with redacted content. PII is replaced with tokens like `[REDACTED:EMAIL:ref_0001]`.

### REDACT - SSN Detection

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "My social security number is 123-45-6789"}]
  }'
```

**Response:** `200 OK` with redacted SSN. Request proceeds but sensitive data is masked.

### ESCALATE - Human Review Required

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "This request needs human review and approval before proceeding"}],
    "user_id": "test_user_123"
  }'
```

**Response:** `202 Accepted` with `EscalateResponse`:
```json
{
  "detail": {
    "review_id": "1",
    "status": "pending_review",
    "message": "Request has been escalated for human review (Review ID: 1)",
    "reason": "Request contains keywords requiring human review",
    "trace_id": "abc-123-def-456",
    "checkpoint": "input"
  }
}
```

## HITL Review Management Examples

### List Pending Reviews

```bash
curl -X GET "http://localhost:8000/api/hitl/reviews?status=pending&limit=10"
```

### Get Specific Review

```bash
curl -X GET "http://localhost:8000/api/hitl/reviews/1"
```

### Approve Review

```bash
curl -X POST "http://localhost:8000/api/hitl/reviews/1/approve?reviewed_by=admin&review_notes=Looks%20good"
```

### Reject Review

```bash
curl -X POST "http://localhost:8000/api/hitl/reviews/1/reject?reviewed_by=admin&review_notes=Not%20approved"
```

### Dequeue Reviews (for workers)

```bash
curl -X POST "http://localhost:8000/api/hitl/reviews/dequeue?assigned_to=reviewer_user&limit=5"
```

## Complete Escalation Flow Example

### Step 1: Send Request That Escalates

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "This request needs human review and approval before proceeding"}],
    "user_id": "test_user_123"
  }'
```

Save the `review_id` from the response (e.g., `"1"`).

### Step 2: Check Review in Database

```sql
SELECT * FROM hitl_reviews WHERE id = 1;
```

### Step 3: Approve Review

```bash
curl -X POST "http://localhost:8000/api/hitl/reviews/1/approve?reviewed_by=admin"
```

### Step 4: Re-submit Same Request (Bypass Test)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "This request needs human review and approval before proceeding"}],
    "user_id": "test_user_123"
  }'
```

**Expected:** `200 OK` with LLM response. Escalation is bypassed due to approved review.

## Querying Audit Trail

### By Trace ID

```sql
SELECT * FROM audit_events 
WHERE trace_id = '550e8400-e29b-41d4-a716-446655440000'
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

See [AUDIT.md](AUDIT.md) for more query examples.

