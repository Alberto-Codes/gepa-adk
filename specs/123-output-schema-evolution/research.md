# Research: Output Schema Evolution

**Feature**: 123-output-schema-evolution
**Date**: 2026-01-18
**Status**: Complete

## Executive Summary

This research validates the feasibility of evolving Pydantic output schemas as components within the existing gepa-adk architecture. The existing component system is fully generic and requires **no modifications**. Three new utilities are needed: serialization, validation, and deserialization.

---

## 1. Component Architecture Analysis

### Current Implementation

**gepa-adk** implements its own evolution engine. The component system uses a `dict[str, str]` pattern:

**gepa-adk Candidate** (`domain/models.py:385`):
```python
@dataclass(slots=True, kw_only=True)
class Candidate:
    components: dict[str, str] = field(default_factory=dict)  # Same pattern
```

### Component Flow

1. **Initialization**: `Candidate(components={"instruction": "...", "output_schema": "..."})`
2. **Selection**: `ComponentSelector.select_components()` returns `["output_schema"]`
3. **Reflection**: `make_reflective_dataset()` builds dataset for selected components
4. **Mutation**: `propose()` generates new text via LLM reflection
5. **Acceptance**: Engine validates score improvement and accepts/rejects
6. **Result**: `EvolutionResult.evolved_component_text` contains final text

### Decision: No Engine Modifications Needed

The component system is already generic. Adding `"output_schema"` as a component works out-of-the-box. The only additions are:
- Pre-evolution: Serialize Pydantic model to text
- During acceptance: Validate proposed schema text
- Post-evolution: Deserialize text back to Pydantic model

---

## 2. Serialization Approach

### Decision: Python Source Code (not JSON Schema)

**Rationale**:
1. **Preserves Field Constraints**: JSON Schema loses `Field()` validators, defaults, descriptions
2. **Human Readable**: Developers recognize Python class syntax
3. **Pydantic Native**: Uses `inspect.getsource()` for original source

### Implementation

```python
import inspect
from pydantic import BaseModel

def serialize_pydantic_schema(schema_class: type[BaseModel]) -> str:
    """Serialize a Pydantic model class to Python source code."""
    return inspect.getsource(schema_class)
```

**Example**:
```python
class CriticOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    feedback: str = Field(default="")

source = serialize_pydantic_schema(CriticOutput)
# Returns:
# class CriticOutput(BaseModel):
#     score: float = Field(ge=0.0, le=1.0)
#     feedback: str = Field(default="")
```

### Alternatives Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Python Source (`inspect.getsource`) | Preserves all metadata, human-readable | Requires self-contained code | **CHOSEN** |
| JSON Schema (`.model_json_schema()`) | Standard format, portable | Loses Field validators, descriptions | Rejected |
| Pydantic Export | Native to Pydantic | No round-trip capability | Rejected |
| AST Reconstruction | Full control | Complex, error-prone | Rejected |

---

## 3. Validation Approach

### Decision: AST Parse + Controlled Exec

**Rationale**:
- `ast.parse()` validates Python syntax without execution
- AST inspection verifies BaseModel subclass presence
- Controlled `exec()` creates the class in isolated namespace

### Implementation Pattern

```python
import ast
from pydantic import BaseModel

def validate_schema_text(schema_text: str) -> type[BaseModel]:
    """Validate schema text and return the Pydantic model class."""

    # Step 1: Syntax validation
    try:
        tree = ast.parse(schema_text)
    except SyntaxError as e:
        raise SchemaValidationError(
            f"Invalid Python syntax at line {e.lineno}",
            raw_output=schema_text,
            validation_error=str(e),
        )

    # Step 2: Structure validation (BaseModel subclass)
    class_name = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "BaseModel":
                    class_name = node.name
                    break

    if not class_name:
        raise SchemaValidationError(
            "No BaseModel subclass found",
            raw_output=schema_text,
            validation_error="Schema must define a class inheriting from BaseModel",
        )

    # Step 3: Execute in controlled namespace
    namespace = {
        "BaseModel": BaseModel,
        "Field": Field,
        # Add allowed types: str, int, float, bool, list, dict, Optional, etc.
    }
    try:
        exec(schema_text, namespace)
    except Exception as e:
        raise SchemaValidationError(
            f"Schema execution failed: {e}",
            raw_output=schema_text,
            validation_error=str(e),
        )

    # Step 4: Return the class
    schema_class = namespace.get(class_name)
    if not issubclass(schema_class, BaseModel):
        raise SchemaValidationError(
            f"{class_name} is not a valid BaseModel",
            raw_output=schema_text,
            validation_error="Class does not inherit from BaseModel",
        )

    return schema_class
```

### Security Considerations

| Risk | Mitigation |
|------|------------|
| Arbitrary code execution | Controlled namespace with only Pydantic imports |
| Import statements | AST check rejects `import` and `from...import` statements |
| Malicious class methods | Only allow `Field()` definitions, reject method definitions |
| Infinite loops | No function definitions allowed |

### Allowed Namespace

```python
ALLOWED_NAMESPACE = {
    # Pydantic
    "BaseModel": BaseModel,
    "Field": Field,
    # Standard types
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    # Typing
    "Optional": Optional,
    "List": List,
    "Dict": Dict,
    "Any": Any,
}
```

---

## 4. Deserialization Approach

### Decision: Reuse Validation Function

The `validate_schema_text()` function both validates AND returns the class, so deserialization is simply calling validation:

```python
def deserialize_schema(schema_text: str) -> type[BaseModel]:
    """Deserialize validated schema text to a Pydantic model class."""
    return validate_schema_text(schema_text)  # Validation includes deserialization
```

### Usage After Evolution

```python
# After evolution completes
result = await evolve(agent, ...)
evolved_schema_text = result.evolved_component_text

# Deserialize to usable class
EvolvedSchema = deserialize_schema(evolved_schema_text)

# Apply to agent
agent.output_schema = EvolvedSchema
```

---

## 5. Integration Points

### Where to Add Validation

**Location**: `async_engine.py` in the acceptance flow

```python
# In _accept_proposal() or equivalent
if "output_schema" in proposal.components:
    try:
        validate_schema_text(proposal.components["output_schema"])
    except SchemaValidationError as e:
        logger.warning("schema_validation.rejected", error=str(e))
        return False  # Reject the proposal
```

### Existing Exception to Extend

`SchemaValidationError` already exists in `domain/exceptions.py:509`:

```python
class SchemaValidationError(ScoringError):
    def __init__(self, message, *, raw_output, validation_error, cause=None):
        self.raw_output = raw_output
        self.validation_error = validation_error
```

This fits perfectly for our schema validation needs.

---

## 6. File Organization

Following hexagonal architecture (ADR-000):

| File | Layer | Purpose |
|------|-------|---------|
| `utils/schema_utils.py` | utils | Serialization, validation, deserialization |
| `domain/exceptions.py` | domain | Extend SchemaValidationError if needed |
| `engine/async_engine.py` | engine | Integration hook for validation |

No changes needed to:
- `ports/` - No new protocols required
- `adapters/` - Validation is internal, not an adapter concern
- `domain/models.py` - Candidate already supports arbitrary components

---

## 7. Edge Cases and Mitigations

| Edge Case | Mitigation |
|-----------|------------|
| Schema has external imports | AST check rejects import statements |
| Class name conflicts | Use unique namespace per validation |
| Circular type references | AST check for forward references |
| LLM proposes JSON Schema instead | Validation rejects non-Python syntax |
| Field with custom validator | Reject `@validator` decorators in AST |
| Missing Field import | Include in controlled namespace |
| Complex type annotations | Support common typing module exports |

---

## 8. Open Questions Resolved

### Q1: What serialization format?
**Answer**: Python source code via `inspect.getsource()`

### Q2: How to handle security for code execution?
**Answer**: Controlled namespace with whitelist of allowed names; AST validation rejects imports and method definitions

### Q3: Should validator be pluggable/configurable?
**Answer**: No, for MVP. Single validator in `utils/schema_utils.py`. Can be made pluggable in future if needed.

---

## 9. Dependencies

**No new dependencies required**. All functionality uses:
- `ast` (stdlib)
- `inspect` (stdlib)
- `pydantic` (existing dependency)
- `structlog` (existing dependency)

---

## 10. Test Strategy

Following ADR-005 (Three-Layer Testing):

| Layer | Tests |
|-------|-------|
| Contract | `test_schema_serializer_protocol.py` - Verify serialization round-trip |
| Unit | `test_schema_utils.py` - Test serialize, validate, deserialize functions |
| Integration | `test_output_schema_evolution.py` - End-to-end evolution with output_schema |

---

## References

- Candidate Model: `src/gepa_adk/domain/models.py:345-389`
- Component Selector: `src/gepa_adk/adapters/component_selector.py`
- Async Engine: `src/gepa_adk/engine/async_engine.py`
- SchemaValidationError: `src/gepa_adk/domain/exceptions.py:509-577`
- CriticOutput Example: `src/gepa_adk/adapters/critic_scorer.py:66-100`
