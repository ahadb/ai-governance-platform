# Human-In-The-Loop (HITL) Module

## Overview

The platform includes a complete HITL workflow for managing escalated requests that require human review. Reviews are stored in a PostgreSQL-based queue with support for concurrent workers.

## How It Works

1. **Escalation**: When a policy returns `ESCALATE`, a review is created in the `hitl_reviews` table with status `pending`
2. **Review Queue**: Reviews are stored in PostgreSQL with queue support using `SELECT FOR UPDATE SKIP LOCKED` for safe concurrent access
3. **Review Management**: Reviewers can approve or reject reviews via API endpoints
4. **Bypass Logic**: Approved reviews automatically bypass escalation for subsequent identical requests

## Review Lifecycle

```
Request → ESCALATE → Review Created (pending) → Assigned → Processing → Approved/Rejected
                                                                    ↓
                                                              Bypass Future Requests
```

## Review Status

- `pending` - Waiting in queue for assignment
- `assigned` - Assigned to a reviewer
- `processing` - Currently being reviewed
- `approved` - Approved by reviewer (enables bypass)
- `rejected` - Rejected by reviewer
- `expired` - Review expired (timeout)

## Review API Endpoints

### List Reviews

```bash
GET /api/hitl/reviews?status=pending&limit=10
```

Query parameters:
- `status` - Filter by status (pending, approved, rejected, etc.)
- `request_id` - Filter by request ID
- `trace_id` - Filter by trace ID
- `checkpoint` - Filter by checkpoint (input/output)
- `assigned_to` - Filter by assigned reviewer
- `limit` - Maximum results (1-1000)
- `offset` - Pagination offset

### Get Review

```bash
GET /api/hitl/reviews/{review_id}
```

Returns complete review details including:
- Original prompt and response
- Policy context (full PolicyContext snapshot)
- Review decision and notes
- Timestamps

### Approve Review

```bash
POST /api/hitl/reviews/{review_id}/approve?reviewed_by=admin&review_notes=Looks%20good
```

Query parameters:
- `reviewed_by` - User ID of reviewer (required)
- `review_notes` - Optional notes explaining approval

### Reject Review

```bash
POST /api/hitl/reviews/{review_id}/reject?reviewed_by=admin&review_notes=Not%20approved
```

Query parameters:
- `reviewed_by` - User ID of reviewer (required)
- `review_notes` - Optional notes explaining rejection

### Dequeue Reviews (for workers)

```bash
POST /api/hitl/reviews/dequeue?assigned_to=reviewer_user&limit=5
```

Query parameters:
- `assigned_to` - User ID to assign reviews to (required)
- `limit` - Number of reviews to dequeue (1-10)

This endpoint uses `SELECT FOR UPDATE SKIP LOCKED` to safely dequeue reviews even with multiple concurrent workers.

## Bypass Logic

When a request is escalated and later approved:

1. The review is stored with:
   - Original prompt (exact match required)
   - User ID (must match)
   - Checkpoint (input or output)
   - Approval timestamp

2. When the same user submits the same prompt again:
   - System checks for approved reviews matching:
     - Exact prompt match
     - Same user_id
     - Same checkpoint
     - Status = approved
     - Approved within last 7 days (configurable)
   - If found, escalation is bypassed
   - Request proceeds normally with `ALLOW` outcome

3. Bypass is logged and audited for compliance

## Database Schema

See `migrations/002_create_hitl_reviews_table.sql` for complete schema.

Key fields:
- `id` - Review ID (primary key)
- `request_id` - Original request identifier
- `trace_id` - End-to-end correlation ID
- `checkpoint` - Where escalation occurred (input/output)
- `reason` - Policy reason for escalation
- `context_data` - Full PolicyContext snapshot (JSONB)
- `prompt` - User prompt (for quick access)
- `response` - LLM response (if output checkpoint)
- `status` - Review status (enum)
- `assigned_to` - Reviewer user ID
- `reviewed_by` - User who made decision
- `review_notes` - Reviewer's notes
- `created_at` - When review was created
- `decision_timestamp` - When decision was made

## Queue Operations

The queue uses PostgreSQL's `SELECT FOR UPDATE SKIP LOCKED` pattern:

- **Safe concurrent access**: Multiple workers can dequeue without conflicts
- **No race conditions**: Database-level locking prevents duplicate assignments
- **Priority support**: Higher priority reviews dequeued first
- **Lock expiration**: Prevents stuck reviews with `locked_until` timestamp

## Implementation

See `hitl/` directory:
- `models.py` - Pydantic models for reviews
- `repository.py` - Database operations and queue logic
- `service.py` - Business logic layer
- `gateway/hitl_api.py` - API endpoints

