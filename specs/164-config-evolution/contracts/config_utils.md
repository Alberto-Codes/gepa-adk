# Contract: Config Utilities

**Module**: `utils/config_utils.py`

## Functions

### serialize_generate_config

```python
def serialize_generate_config(config: GenerateContentConfig) -> str
```

**Purpose**: Convert GenerateContentConfig to YAML string with parameter descriptions.

**Preconditions**:
- `config` is a valid GenerateContentConfig instance

**Postconditions**:
- Returns YAML string
- Output includes only evolvable parameters (temperature, top_p, etc.)
- Output includes comment descriptions for each parameter
- Output is parseable by `yaml.safe_load()`

**Contract Tests**:
```python
def test_serialize_returns_yaml_string():
    config = GenerateContentConfig(temperature=0.7)
    result = serialize_generate_config(config)
    assert isinstance(result, str)
    assert "temperature" in result

def test_serialize_includes_descriptions():
    config = GenerateContentConfig(temperature=0.7)
    result = serialize_generate_config(config)
    assert "# temperature:" in result  # Comment present

def test_serialize_excludes_non_evolvable():
    config = GenerateContentConfig(
        temperature=0.7,
        system_instruction="ignored"  # Not evolvable
    )
    result = serialize_generate_config(config)
    assert "system_instruction" not in result

def test_serialize_roundtrip():
    config = GenerateContentConfig(temperature=0.7, top_p=0.9)
    yaml_str = serialize_generate_config(config)
    parsed = yaml.safe_load(yaml_str)
    assert parsed["temperature"] == 0.7
    assert parsed["top_p"] == 0.9
```

---

### deserialize_generate_config

```python
def deserialize_generate_config(
    yaml_text: str,
    existing: GenerateContentConfig | None = None,
) -> GenerateContentConfig
```

**Purpose**: Parse YAML text into GenerateContentConfig, optionally merging with existing.

**Preconditions**:
- `yaml_text` is a string (may be empty or invalid)
- `existing` is either None or a valid GenerateContentConfig

**Postconditions**:
- Returns GenerateContentConfig instance
- If `existing` provided, unspecified parameters retain existing values
- Raises `ConfigValidationError` on invalid YAML syntax
- Does NOT validate parameter constraints (that's `validate_generate_config`)

**Contract Tests**:
```python
def test_deserialize_parses_yaml():
    result = deserialize_generate_config("temperature: 0.5")
    assert result.temperature == 0.5

def test_deserialize_merges_with_existing():
    existing = GenerateContentConfig(temperature=0.7, top_p=0.9)
    result = deserialize_generate_config("temperature: 0.5", existing)
    assert result.temperature == 0.5
    assert result.top_p == 0.9  # Preserved from existing

def test_deserialize_empty_returns_default():
    result = deserialize_generate_config("")
    assert result is not None

def test_deserialize_invalid_yaml_raises():
    with pytest.raises(ConfigValidationError):
        deserialize_generate_config("{{{{invalid")
```

---

### validate_generate_config

```python
def validate_generate_config(config_dict: dict[str, Any]) -> list[str]
```

**Purpose**: Validate config dict against known parameter constraints.

**Preconditions**:
- `config_dict` is a dictionary

**Postconditions**:
- Returns list of validation error messages
- Empty list means valid
- Unknown parameters trigger warning log but not error

**Validation Rules**:

| Parameter | Constraint |
|-----------|------------|
| `temperature` | 0.0 ≤ x ≤ 2.0 |
| `top_p` | 0.0 ≤ x ≤ 1.0 |
| `top_k` | x > 0 |
| `max_output_tokens` | x > 0 |
| `presence_penalty` | -2.0 ≤ x ≤ 2.0 |
| `frequency_penalty` | -2.0 ≤ x ≤ 2.0 |

**Contract Tests**:
```python
def test_validate_empty_dict():
    errors = validate_generate_config({})
    assert errors == []

def test_validate_valid_config():
    errors = validate_generate_config({
        "temperature": 0.7,
        "top_p": 0.9,
    })
    assert errors == []

def test_validate_temperature_out_of_range():
    errors = validate_generate_config({"temperature": 3.0})
    assert len(errors) == 1
    assert "temperature" in errors[0]

def test_validate_negative_top_k():
    errors = validate_generate_config({"top_k": -1})
    assert len(errors) == 1
    assert "top_k" in errors[0]

def test_validate_multiple_errors():
    errors = validate_generate_config({
        "temperature": 999,
        "top_p": -1,
    })
    assert len(errors) == 2

def test_validate_unknown_param_no_error():
    errors = validate_generate_config({"unknown_param": 42})
    assert errors == []  # Warning logged, no error
```

---

## Exception Contract

### ConfigValidationError

```python
class ConfigValidationError(EvolutionError):
    def __init__(self, message: str, errors: list[str] | None = None):
        ...
```

**Attributes**:
- `message`: Human-readable summary
- `errors`: List of individual validation errors (optional)

**Contract Tests**:
```python
def test_config_validation_error_is_evolution_error():
    from gepa_adk.domain.exceptions import EvolutionError
    error = ConfigValidationError("test")
    assert isinstance(error, EvolutionError)

def test_config_validation_error_stores_errors():
    error = ConfigValidationError("failed", errors=["error1", "error2"])
    assert error.errors == ["error1", "error2"]
```
