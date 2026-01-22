# Contract: Schema Constraints Validation

**Date**: 2026-01-22
**Feature**: 198-schema-field-preservation

## Overview

This contract defines the behavior of schema constraint validation during output_schema evolution.

---

## Contract: SchemaConstraints Immutability

**Parties**: Domain consumer, SchemaConstraints

**Invariants**:
1. `SchemaConstraints` instances are immutable after construction
2. `required_fields` is a tuple (immutable sequence)
3. `preserve_types` values cannot be modified

**Test Cases**:
```python
def test_schema_constraints_is_frozen():
    constraints = SchemaConstraints(required_fields=("score",))
    with pytest.raises(dataclasses.FrozenInstanceError):
        constraints.required_fields = ("other",)

def test_schema_constraints_has_slots():
    constraints = SchemaConstraints()
    assert hasattr(constraints, "__slots__")
```

---

## Contract: Required Field Validation

**Parties**: OutputSchemaHandler, validate_schema_against_constraints

**Preconditions**:
- Original schema has the fields listed in `required_fields`
- Proposed schema is a valid Pydantic BaseModel

**Postconditions**:
- If ALL required fields exist in proposed schema → validation passes
- If ANY required field is missing → validation fails with specific message

**Test Cases**:
```python
def test_required_field_present_passes():
    """Proposed schema with required field passes validation."""
    original = create_schema({"score": float, "feedback": str})
    proposed = create_schema({"score": float, "result": str})  # feedback removed
    constraints = SchemaConstraints(required_fields=("score",))

    is_valid, violations = validate_schema_against_constraints(
        proposed, original, constraints
    )

    assert is_valid
    assert violations == []

def test_required_field_missing_fails():
    """Proposed schema missing required field fails validation."""
    original = create_schema({"score": float, "feedback": str})
    proposed = create_schema({"feedback": str})  # score removed!
    constraints = SchemaConstraints(required_fields=("score",))

    is_valid, violations = validate_schema_against_constraints(
        proposed, original, constraints
    )

    assert not is_valid
    assert len(violations) == 1
    assert "score" in violations[0]
    assert "missing" in violations[0].lower()
```

---

## Contract: Type Preservation Validation

**Parties**: OutputSchemaHandler, validate_schema_against_constraints

**Preconditions**:
- Original schema has the fields listed in `preserve_types`
- Proposed schema is a valid Pydantic BaseModel

**Postconditions**:
- If field type matches allowed type(s) → validation passes
- If field type doesn't match → validation fails with specific message
- If field is missing entirely → separate "missing field" violation (if also in required_fields)

**Test Cases**:
```python
def test_type_preserved_exact_match():
    """Field with exact type match passes."""
    original = create_schema({"score": float})
    proposed = create_schema({"score": float})
    constraints = SchemaConstraints(preserve_types={"score": float})

    is_valid, _ = validate_schema_against_constraints(
        proposed, original, constraints
    )

    assert is_valid

def test_type_preserved_tuple_match():
    """Field with type in allowed tuple passes."""
    original = create_schema({"score": float})
    proposed = create_schema({"score": int})  # int is in (float, int)
    constraints = SchemaConstraints(preserve_types={"score": (float, int)})

    is_valid, _ = validate_schema_against_constraints(
        proposed, original, constraints
    )

    assert is_valid

def test_type_mismatch_fails():
    """Field with wrong type fails validation."""
    original = create_schema({"score": float})
    proposed = create_schema({"score": str})  # Changed to str!
    constraints = SchemaConstraints(preserve_types={"score": float})

    is_valid, violations = validate_schema_against_constraints(
        proposed, original, constraints
    )

    assert not is_valid
    assert len(violations) == 1
    assert "score" in violations[0]
    assert "type" in violations[0].lower()
```

---

## Contract: Handler Integration

**Parties**: OutputSchemaHandler, evolve() API

**Preconditions**:
- Handler has constraints set via `set_constraints()`
- `apply()` is called with proposed schema text

**Postconditions**:
- Valid mutation → agent.output_schema is updated
- Invalid mutation → agent.output_schema is unchanged, warning logged
- Handler returns original schema in both cases (for restore)

**Test Cases**:
```python
def test_handler_accepts_valid_mutation():
    """Handler applies mutation when constraints satisfied."""
    handler = OutputSchemaHandler()
    handler.set_constraints(SchemaConstraints(required_fields=("score",)))

    agent = create_agent_with_schema({"score": float, "old_field": str})
    new_schema_text = '''
    class NewSchema(BaseModel):
        score: float
        new_field: str
    '''

    original = handler.apply(agent, new_schema_text)

    assert "new_field" in agent.output_schema.model_fields
    assert "old_field" not in agent.output_schema.model_fields

def test_handler_rejects_invalid_mutation():
    """Handler keeps original when constraints violated."""
    handler = OutputSchemaHandler()
    handler.set_constraints(SchemaConstraints(required_fields=("score",)))

    agent = create_agent_with_schema({"score": float, "feedback": str})
    original_schema = agent.output_schema
    invalid_schema_text = '''
    class NewSchema(BaseModel):
        feedback: str  # score removed!
    '''

    handler.apply(agent, invalid_schema_text)

    # Schema should be unchanged
    assert agent.output_schema is original_schema
    assert "score" in agent.output_schema.model_fields
```

---

## Contract: Configuration Validation

**Parties**: evolve() API, SchemaConstraints

**Preconditions**:
- User provides `schema_constraints` parameter
- Agent has `output_schema` set

**Postconditions**:
- If constraints reference non-existent fields → ConfigurationError raised before evolution
- If constraints are valid → evolution proceeds normally

**Test Cases**:
```python
def test_invalid_constraints_fail_fast():
    """Constraints referencing non-existent fields raise early error."""
    agent = create_agent_with_schema({"score": float})
    constraints = SchemaConstraints(required_fields=("nonexistent_field",))

    with pytest.raises(ConfigurationError) as exc:
        await evolve(agent, trainset, schema_constraints=constraints)

    assert "nonexistent_field" in str(exc.value)

def test_valid_constraints_proceed():
    """Valid constraints allow evolution to start."""
    agent = create_agent_with_schema({"score": float, "result": str})
    constraints = SchemaConstraints(required_fields=("score",))

    # Should not raise
    result = await evolve(agent, trainset, schema_constraints=constraints)

    assert result is not None
```

---

## Contract: Backward Compatibility

**Parties**: evolve() API, existing users

**Invariants**:
1. `evolve()` without `schema_constraints` behaves identically to current behavior
2. `OutputSchemaHandler` without constraints behaves identically to current behavior
3. No breaking changes to public API signatures

**Test Cases**:
```python
def test_evolve_without_constraints_unchanged():
    """Evolution without constraints works as before."""
    agent = create_agent_with_schema({"score": float})

    # No schema_constraints parameter
    result = await evolve(agent, trainset)

    # Should complete normally
    assert result.evolved_components is not None

def test_handler_without_constraints_unchanged():
    """Handler without constraints applies all mutations."""
    handler = OutputSchemaHandler()
    # No set_constraints() call

    agent = create_agent_with_schema({"score": float})
    new_schema_text = '''
    class NewSchema(BaseModel):
        totally_different: str
    '''

    handler.apply(agent, new_schema_text)

    # Should apply the mutation (no constraints to check)
    assert "totally_different" in agent.output_schema.model_fields
```
