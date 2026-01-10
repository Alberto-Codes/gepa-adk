# ADR-008: Structured Logging Pattern

> **Status**: Accepted
> **Date**: 2026-01-10
> **Deciders**: gepa-adk maintainers

## Context

Logging serves multiple purposes in gepa-adk:
- **Development**: Human-readable console output for debugging evolution runs
- **Production**: Machine-parseable events for analysis and alerting
- **Auditing**: Traceable records of evolution decisions, scores, and proposals

Following [12-Factor App principles](https://12factor.net/logs), logs are event streams—the application emits to stdout, and the execution environment routes to destinations.

## Decision

### Technology Stack

- **structlog**: Structured logging with context binding
- **ObservabilityPort**: Hexagonal interface for external backends (optional)

### Core Principle

**Emit structured events to stdout; let infrastructure handle routing.**

```
+---------------------------------------------------------------+
|                      Application Code                          |
|                                                                |
|   logger = get_logger(__name__)                               |
|   logger.info("Evolution started", agent="my_agent", iter=1)  |
|                                                                |
+---------------------------------------------------------------+
                              |
                              | structlog processors
                              v
+---------------------------------------------------------------+
|                    structlog Pipeline                          |
|                                                                |
|   1. merge_contextvars     (async-safe context)               |
|   2. add_log_level         (INFO, ERROR, etc.)                |
|   3. TimeStamper           (ISO8601 UTC)                      |
|   4. RedactionProcessor    (mask secrets)                     |
|   5. ConsoleRenderer       (human-readable stdout)            |
|                                                                |
+---------------------------------------------------------------+
                              |
                              v
+-------------------------+
|   stdout (always)       |
|   Human-readable        |
+-------------------------+
```

---

## Usage

### Getting a Logger

```python
from gepa_adk.utils import get_logger

logger = get_logger(__name__)
```

### Log Levels

| Level | Use Case |
|-------|----------|
| `DEBUG` | Detailed diagnostic info (evaluation details, scores) |
| `INFO` | Normal operations, milestones (iteration start/end) |
| `WARNING` | Unexpected but recoverable situations (retry, fallback) |
| `ERROR` | Failures requiring attention (evaluation failed) |

```python
logger.debug("Evaluating candidate", candidate_id="cand-001", batch_size=10)
logger.info("Evolution started", agent_name="my_agent", max_iterations=50)
logger.warning("Proposal rejected", score=0.45, threshold=0.5)
logger.error("Evaluation failed", error=str(e), agent_name="my_agent")
```

### Context Binding

Bind context once, include in all subsequent logs:

```python
# Bind evolution context
logger = logger.bind(evolution_id="evo-123", agent_name="analyzer")

# All logs now include evolution_id and agent_name
logger.info("Starting evolution")
logger.info("Iteration complete", iteration=1, best_score=0.85)
```

### Async Context Variables

For async code, use context variables (automatically merged):

```python
import structlog

# Set context for current async task
structlog.contextvars.bind_contextvars(evolution_id="evo-456")

# All logs in this async context include evolution_id
logger.info("Evaluating batch")
```

---

## Event Schema

### Required Fields (Auto-Added)

| Field | Type | Source |
|-------|------|--------|
| `timestamp` | ISO8601 string | `TimeStamper` processor |
| `level` | string | `add_log_level` processor |
| `logger` | string | `add_logger_name` processor |
| `event` | string | Log message |

### Common Context Fields

| Field | Type | When to Include |
|-------|------|-----------------|
| `evolution_id` | string | All evolution-scoped operations |
| `agent_name` | string | Agent execution logs |
| `iteration` | int | Iteration-scoped logs |
| `candidate_id` | string | Candidate evaluation logs |
| `score` | float | Scoring-related logs |
| `duration_ms` | float | Performance-sensitive operations |
| `error` | string | Error logs (exception message) |

### Example Event

```json
{
  "timestamp": "2026-01-10T15:30:45.123456Z",
  "level": "info",
  "logger": "gepa_adk.engine.async_engine",
  "event": "Iteration complete",
  "evolution_id": "evo-abc123",
  "agent_name": "my_agent",
  "iteration": 5,
  "best_score": 0.92,
  "duration_ms": 1523.4
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Minimum log level |
| `LOG_FORMAT` | `console` | Output format (`console` or `json`) |

### Initialization

```python
# At application startup
from gepa_adk.utils.logging import configure_logging

configure_logging()  # Loads config from environment
```

---

## Secret Redaction

Sensitive fields are automatically redacted before emission:

```python
# Redacted keys (case-insensitive)
REDACTION_KEYS = [
    "api_key", "token", "password", "secret",
    "private_key", "authorization", "bearer"
]

# Input
logger.info("API call", api_key="sk-abc123", endpoint="/v1/evolve")

# Output
{"event": "API call", "api_key": "[REDACTED]", "endpoint": "/v1/evolve"}
```

---

## Testing

### Capture Logs in Tests

```python
import structlog

def test_logs_evolution_start(caplog):
    """Verify evolution logs expected events."""
    structlog.configure(
        processors=[structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    engine.run()

    assert "Evolution started" in caplog.text
    assert "my_agent" in caplog.text
```

### Suppress Logs in Tests

```python
# conftest.py
@pytest.fixture(autouse=True)
def quiet_logs():
    """Suppress logs during tests."""
    import logging
    logging.getLogger("gepa_adk").setLevel(logging.CRITICAL)
```

---

## What NOT to Log

| Don't Log | Why | Alternative |
|-----------|-----|-------------|
| Full prompts/instructions | Size, potential PII | Log summary + length |
| Full LLM responses | Size, cost | Log truncated + token count |
| High-frequency loop iterations | Noise, performance | Log batch summary |
| Stack traces (INFO level) | Noise | Only at ERROR level |

---

## Consequences

### Positive

- Consistent structured format across all components
- Context propagation in async code
- Automatic secret redaction
- 12-factor compliant (stdout + routing)
- Easy to add observability backends later

### Negative

- structlog learning curve
- Must remember to bind context
- Additional dependency

### Neutral

- JSON format available for production
- Console format available for development

---

## References

- [12-Factor App: Logs](https://12factor.net/logs)
- [structlog Documentation](https://www.structlog.org/)
- [structlog Best Practices](https://www.structlog.org/en/stable/logging-best-practices.html)
- **ADR-000**: Hexagonal Architecture
- **ADR-006**: External Library Integration
