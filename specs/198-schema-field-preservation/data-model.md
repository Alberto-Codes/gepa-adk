# Data Model: Required Field Preservation for Output Schema Evolution

**Date**: 2026-01-22
**Feature**: 198-schema-field-preservation

## Entities

### SchemaConstraints

**Location**: `src/gepa_adk/domain/types.py`

Configuration object specifying constraints for output schema evolution. Immutable after construction.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `required_fields` | `tuple[str, ...]` | `()` | Field names that must exist in evolved schema |
| `preserve_types` | `dict[str, type \| tuple[type, ...]]` | `{}` | Field name → allowed type(s) |

**Constraints**:
- `required_fields` entries must be valid Python identifiers
- `preserve_types` keys must be valid Python identifiers
- `preserve_types` values must be type objects or tuples of type objects

**Validation Rules**:
- At configuration time: Verify fields in constraints exist in original schema
- At mutation time: Reject mutations missing required fields or with wrong types

**Example**:
```python
from gepa_adk.domain.types import SchemaConstraints

# Basic required fields only
constraints = SchemaConstraints(
    required_fields=("score", "feedback"),
)

# With type preservation
constraints = SchemaConstraints(
    required_fields=("score",),
    preserve_types={
        "score": (float, int),  # Allow numeric types
        "order_id": str,        # Must stay string
    },
)
```

---

### SchemaValidationResult (existing)

**Location**: `src/gepa_adk/utils/schema_utils.py`

Already exists. Used to inspect proposed schema before constraint validation.

| Field | Type | Description |
|-------|------|-------------|
| `schema_class` | `type[BaseModel]` | Deserialized Pydantic model class |
| `class_name` | `str` | Name of the class |
| `field_count` | `int` | Number of fields |
| `field_names` | `tuple[str, ...]` | Field names in order |

---

### ConstraintViolation (internal)

**Location**: `src/gepa_adk/utils/schema_utils.py` (not exported)

Internal structure for tracking constraint violations during validation.

| Field | Type | Description |
|-------|------|-------------|
| `field` | `str` | Field name with violation |
| `violation_type` | `str` | "missing_field" or "type_mismatch" |
| `message` | `str` | Human-readable description |

**Example violations**:
```python
ConstraintViolation(
    field="score",
    violation_type="missing_field",
    message="Required field 'score' not found in evolved schema"
)

ConstraintViolation(
    field="score",
    violation_type="type_mismatch",
    message="Field 'score' has type 'str', expected 'float' or 'int'"
)
```

---

## State Transitions

### Handler Constraint State

```
                                ┌─────────────────────┐
                                │ No Constraints      │
                                │ (_constraints=None) │
                                └──────────┬──────────┘
                                           │
                          set_constraints(constraints)
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │ Constraints Active  │
                                │ (_constraints set)  │
                                └──────────┬──────────┘
                                           │
                          set_constraints(None)
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │ No Constraints      │
                                │ (_constraints=None) │
                                └─────────────────────┘
```

### Mutation Validation Flow

```
                    ┌──────────────────────┐
                    │ Proposed Schema Text │
                    └──────────┬───────────┘
                               │
                    deserialize_schema(text)
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Proposed Schema Class│
                    └──────────┬───────────┘
                               │
              constraints set? │
                    ┌──────────┴──────────┐
                    │                     │
                   No                    Yes
                    │                     │
                    │     validate_against_constraints()
                    │                     │
                    │          ┌──────────┴──────────┐
                    │          │                     │
                    │        Valid              Invalid
                    │          │                     │
                    │          │              log warning
                    │          │              return original
                    │          │                     │
                    ▼          ▼                     ▼
             ┌────────────────────┐        ┌─────────────────┐
             │ Apply New Schema   │        │ Keep Original   │
             │ agent.output_schema│        │ (no change)     │
             └────────────────────┘        └─────────────────┘
```

---

## Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                           evolve()                              │
│                              │                                  │
│                   schema_constraints parameter                  │
│                              │                                  │
│                              ▼                                  │
│              ┌───────────────────────────────┐                  │
│              │      OutputSchemaHandler      │                  │
│              │  _constraints: SchemaConstraints?                │
│              │                               │                  │
│              │  set_constraints() ───────────┼──┐               │
│              │  apply() ─────────────────────┼──┼───────────┐   │
│              │  serialize()                  │  │           │   │
│              │  restore()                    │  │           │   │
│              └───────────────────────────────┘  │           │   │
│                                                 │           │   │
│                              ┌──────────────────┘           │   │
│                              │                              │   │
│                              ▼                              ▼   │
│              ┌──────────────────────┐     ┌─────────────────────┤
│              │   SchemaConstraints  │     │ validate_schema_    │
│              │   (domain/types.py)  │     │ against_constraints │
│              │                      │     │ (utils/schema_utils)│
│              │  required_fields     │◄────┤                     │
│              │  preserve_types      │     └─────────────────────┤
│              └──────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Field Type Mappings

For Pydantic schemas, field types are extracted via `model_fields[field_name].annotation`:

| Pydantic Type | Python Type | Notes |
|---------------|-------------|-------|
| `str` | `str` | Direct match |
| `int` | `int` | Direct match |
| `float` | `float` | Direct match |
| `bool` | `bool` | Direct match |
| `list[T]` | `list` | Generic origin |
| `dict[K, V]` | `dict` | Generic origin |
| `Optional[T]` | `T \| None` | Union with None |

**Type Extraction**:
```python
from typing import get_origin, get_args

field_info = schema_class.model_fields[field_name]
annotation = field_info.annotation

# Handle Optional[T] → extract T
origin = get_origin(annotation)
if origin is Union:
    args = get_args(annotation)
    # Filter out NoneType for Optional
    non_none_args = [a for a in args if a is not type(None)]
    actual_type = non_none_args[0] if len(non_none_args) == 1 else annotation
else:
    actual_type = origin or annotation
```
