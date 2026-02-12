# Logging Format Documentation

## Overview

The AI Governance Platform uses **event-style structured logging** with JSON output. All log entries follow a consistent format that makes them machine-readable, queryable, and suitable for log aggregation tools.

## Event Format

All logging uses the pattern:

```python
logger.info("event_name", key1=value1, key2=value2, ...)
```

### Structure

Every log entry is a JSON object with the following structure:

```json
{
  "event": "event_name",
  "level": "info|warning|error|debug",
  "timestamp": "2024-01-15T10:30:00.123456Z",
  "key1": "value1",
  "key2": "value2",
  ...
}
```

### Required Fields (Auto-Added)

- `event`: The event name (snake_case)
- `level`: Log level (auto-added by structlog)
- `timestamp`: ISO 8601 timestamp (auto-added by structlog)

### Event Naming Convention

- Use `snake_case` for event names
- Be descriptive and specific
- Use verb_past_tense for actions (e.g., `request_received`, `policy_evaluated`)
- Use noun_state for states (e.g., `initialization_complete`, `provider_ready`)

**Examples:**
- `request_received`
- `policy_evaluation_failed`
- `model_fallback_triggered`
- `RequestReceived` (wrong case)
- `request received` (spaces)
- `req` (too vague)

## Common Event Patterns

### Request Lifecycle Events

#### `request_received`
Triggered when a new request enters the Gateway.

```json
{
  "event": "request_received",
  "level": "info",
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "abc-123",
  "user_id": "user123",
  "prompt_length": 50,
  "checkpoint": "input"
}
```

#### `request_blocked`
Triggered when a request is blocked by policy.

```json
{
  "event": "request_blocked",
  "level": "warning",
  "timestamp": "2024-01-15T10:30:01Z",
  "request_id": "abc-123",
  "outcome": "BLOCK",
  "reason": "MNPI violation detected: Restricted security ticker found: AAPL",
  "checkpoint": "input"
}
```

#### `request_escalated`
Triggered when a request is escalated for human review.

```json
{
  "event": "request_escalated",
  "level": "info",
  "timestamp": "2024-01-15T10:30:02Z",
  "request_id": "abc-123",
  "review_id": "review_xyz-789",
  "outcome": "ESCALATE",
  "reason": "High-risk content requiring manual approval",
  "checkpoint": "input"
}
```

#### `request_completed`
Triggered when a request successfully completes.

```json
{
  "event": "request_completed",
  "level": "info",
  "timestamp": "2024-01-15T10:30:05Z",
  "request_id": "abc-123",
  "final_outcome": "ALLOW",
  "response_redacted": false,
  "model": "mistral",
  "provider": "ollama"
}
```

### Policy Engine Events

#### `config_policies_not_in_registry`
Triggered when configuration references policies not in the registry.

```json
{
  "event": "config_policies_not_in_registry",
  "level": "warning",
  "timestamp": "2024-01-15T10:00:00Z",
  "missing_policies": ["unknown_policy", "another_missing"],
  "config_path": "config/default.yaml"
}
```

#### `policy_evaluation_failed`
Triggered when a policy evaluation throws an exception.

```json
{
  "event": "policy_evaluation_failed",
  "level": "error",
  "timestamp": "2024-01-15T10:30:01Z",
  "policy_name": "pii_detection",
  "request_id": "abc-123",
  "checkpoint": "input",
  "error": "KeyError: 'redact_emails'",
  "error_type": "KeyError"
}
```

### Model Router Events

#### `provider_initialization_failed`
Triggered when a provider fails to initialize.

```json
{
  "event": "provider_initialization_failed",
  "level": "warning",
  "timestamp": "2024-01-15T10:00:00Z",
  "provider": "ollama",
  "error": "Connection refused",
  "error_type": "ConnectionError"
}
```

#### `model_fallback_triggered`
Triggered when the router falls back to a secondary model.

```json
{
  "event": "model_fallback_triggered",
  "level": "info",
  "timestamp": "2024-01-15T10:30:03Z",
  "primary_model": "mistral",
  "fallback_model": "llama2",
  "error": "Model not found",
  "error_type": "ModelNotFoundError"
}
```

#### `router_error`
Triggered when the router encounters an error.

```json
{
  "event": "router_error",
  "level": "error",
  "timestamp": "2024-01-15T10:30:04Z",
  "request_id": "abc-123",
  "error": "All providers failed",
  "error_type": "ModelRouterError"
}
```

### Initialization Events

#### `initializing_policy_engine`
Triggered when the Policy Engine starts initialization.

```json
{
  "event": "initializing_policy_engine",
  "level": "info",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

#### `policy_engine_initialized`
Triggered when the Policy Engine completes initialization.

```json
{
  "event": "policy_engine_initialized",
  "level": "info",
  "timestamp": "2024-01-15T10:00:01Z",
  "active_policies": 3,
  "config_path": "config/default.yaml"
}
```

## Best Practices

### 1. Always Include Context

Include relevant identifiers and context:

```python
# Good
logger.info("request_received", request_id=request_id, user_id=user_id, checkpoint="input")

# Bad
logger.info("request_received")  # Missing context
```

### 2. Use Appropriate Log Levels

- **DEBUG**: Detailed diagnostic information (not used in production)
- **INFO**: General informational messages (request flow, initialization)
- **WARNING**: Warning messages (fallbacks, missing config)
- **ERROR**: Error conditions (exceptions, failures)
- **CRITICAL**: Critical errors (system failures)

### 3. Include Error Details

When logging errors, include both the error message and type:

```python
logger.error(
    "policy_evaluation_failed",
    policy_name=policy_name,
    error=str(e),
    error_type=type(e).__name__,
)
```

### 4. Be Consistent

Use consistent field names across events:

- `request_id`: Always use this name for request identifiers
- `user_id`: Always use this name for user identifiers
- `checkpoint`: Always use "input" or "output"
- `error`: Always use this name for error messages
- `error_type`: Always use this name for error types

### 5. Don't Log Sensitive Data

Never log:
- Passwords or API keys
- Full PII (use redaction tokens)
- Complete request/response content (log lengths instead)

```python
# Good
logger.info("request_received", prompt_length=len(prompt), user_id=user_id)

# Bad
logger.info("request_received", prompt=prompt)  # May contain sensitive data
```

## Querying Logs

With structured JSON logs, you can easily query them:

### Using `jq` (command line)

```bash
# Find all blocked requests
cat logs.json | jq 'select(.event == "request_blocked")'

# Find errors for a specific request
cat logs.json | jq 'select(.request_id == "abc-123" and .level == "error")'

# Count events by type
cat logs.json | jq -r '.event' | sort | uniq -c
```

### Using Log Aggregation Tools

Structured JSON logs work seamlessly with:
- **Elasticsearch/Logstash/Kibana (ELK)**
- **Datadog**
- **Splunk**
- **CloudWatch Logs Insights**
- **Grafana Loki**

Example CloudWatch Logs Insights query:

```
fields @timestamp, event, request_id, level
| filter event == "request_blocked"
| stats count() by request_id
```

## Configuration

Logging is configured in `common/logging.py` and initialized at startup in `main.py`.

To change the log level, set the `LOG_LEVEL` environment variable:

```bash
LOG_LEVEL=DEBUG python main.py
```

Valid levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

