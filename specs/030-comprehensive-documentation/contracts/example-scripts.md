# Contract: Example Scripts Interface

**Feature**: 030-comprehensive-documentation  
**Date**: 2026-01-14  
**Phase**: 1 - Design

## Overview

Example scripts demonstrate gepa-adk usage patterns. This contract defines the required structure and interface for all example scripts.

## Required Structure

### File Organization

All example scripts must be located in `examples/` directory at repository root:

```
examples/
├── basic_evolution.py
├── critic_agent.py
├── multi_agent.py
└── workflow.py
```

### Module-Level Requirements

Each example script MUST include:

1. **Module Docstring**:
   ```python
   """Example: [Brief description of what this example demonstrates].
   
   This example shows how to [specific use case].
   
   Prerequisites:
       - Python 3.12+
       - gepa-adk installed
       - [Any other requirements]
   
   Usage:
       python examples/[filename].py
   """
   ```

2. **Imports Section**:
   - All imports at top of file
   - Grouped: stdlib, third-party, local
   - Include type hints

3. **Configuration Section**:
   - Environment variables for API keys
   - Configuration constants
   - Clear comments explaining configuration

4. **Main Example Code**:
   - Complete, runnable workflow
   - Comprehensive inline comments
   - Demonstrates best practices

5. **Execution Block**:
   ```python
   if __name__ == "__main__":
       # Execution code here
   ```

## Interface Requirements

### Environment Variables

Example scripts MUST use environment variables for sensitive configuration:

```python
import os

# API keys from environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable required")
```

### Error Handling

Example scripts MUST include appropriate error handling:

```python
try:
    # Example code
except Exception as e:
    print(f"Error: {e}")
    raise
```

### Logging

Example scripts SHOULD demonstrate structured logging:

```python
import structlog

logger = structlog.get_logger()
logger.info("Starting evolution", agent_name="example-agent")
```

### Type Hints

Example scripts MUST include type hints for all functions:

```python
from typing import Any

def create_agent(name: str) -> LlmAgent:
    """Create an agent with the given name."""
    ...
```

## Example Script Contracts

### basic_evolution.py

**Purpose**: Demonstrate minimal single-agent evolution workflow.

**Required Elements**:
- Create a basic `LlmAgent`
- Define a simple training dataset
- Call `evolve_sync()` or `evolve()`
- Display results

**Expected Runtime**: < 30 seconds (with mock/fast LLM)

---

### critic_agent.py

**Purpose**: Demonstrate structured critic usage.

**Required Elements**:
- Create an `LlmAgent` (main agent)
- Create a critic `LlmAgent`
- Define training dataset
- Call `evolve()` with `critic` parameter
- Display results showing critic feedback

**Expected Runtime**: < 60 seconds (with mock/fast LLM)

---

### multi_agent.py

**Purpose**: Demonstrate multi-agent co-evolution.

**Required Elements**:
- Create multiple `LlmAgent` instances
- Define training dataset
- Call `evolve_group()` or equivalent
- Display results for all agents

**Expected Runtime**: < 90 seconds (with mock/fast LLM)

---

### workflow.py

**Purpose**: Demonstrate SequentialAgent/workflow evolution.

**Required Elements**:
- Create a `SequentialAgent` or workflow
- Define training dataset
- Call `evolve_workflow()` or equivalent
- Display results

**Expected Runtime**: < 90 seconds (with mock/fast LLM)

## Validation Rules

1. **Syntax Validation**: All scripts must pass `python -m py_compile [script]`
2. **Type Checking**: All scripts should pass `ty check [script]` (if type checker available)
3. **Execution Test**: All scripts must execute without errors (with proper environment)
4. **Documentation**: All scripts must have complete docstrings and comments

## Dependencies

Example scripts may depend on:
- `gepa-adk` (required)
- `google-adk>=1.22.0` (required)
- `structlog>=25.5.0` (recommended for logging examples)
- Standard library only (preferred for basic examples)

## Notes

- Example scripts are for demonstration, not production use
- Scripts should be self-contained (no external data files unless necessary)
- Scripts should include clear output showing what's happening
- Scripts may use mock/fast LLMs for CI/testing purposes
