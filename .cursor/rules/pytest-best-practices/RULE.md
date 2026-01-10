---
description: "Pytest best practices based on pytest-with-eric.com. Follow these conventions for test file naming, structure, fixtures, parametrization, assertions, markers, mocking, and organization."
globs:
  - "**/*test*.py"
  - "**/test_*.py"
  - "**/tests/**/*.py"
  - "**/conftest.py"
alwaysApply: false
---

# Pytest Best Practices

## Test File and Function Naming

### File Naming Conventions
- **MUST** use `test_*.py` or `*_test.py` pattern for pytest to discover tests
- Place test files in dedicated `tests/` directory at project root
- Mirror application structure in test directory
- Example: Testing `src/models/user.py` → `tests/models/test_user.py`

### Test Function Naming
- **MUST** prefix test functions with `test_`
- Use descriptive names following pattern: `test_<what>_<condition>_<expected_result>`
- Examples:
  - `test_user_creation_with_valid_email()`
  - `test_empty_list_has_zero_length()`
  - `test_division_raises_error_when_divisor_is_zero()`
- Avoid generic names like `test1()` or `test_function()`

### Test Class Naming
- **MUST** prefix test classes with `Test` (capital T)
- Class methods **MUST** start with `test_`
- No `__init__` method in test classes
- Use classes to group related tests for a specific feature or module

```python
class TestUser:
    def test_username_validation(self):
        pass
    
    def test_password_strength(self):
        pass
```

## Test Organization and Structure

### Project Structure (Recommended)
```
project/
├── src/
│   ├── models/
│   │   ├── user.py
│   │   └── order.py
│   └── services/
│       └── payment_service.py
├── tests/
│   ├── unit/
│   │   ├── models/
│   │   │   ├── test_user.py
│   │   │   └── test_order.py
│   │   └── services/
│   │       └── test_payment_service.py
│   ├── integration/
│   │   └── test_api_endpoints.py
│   ├── e2e/
│   │   └── test_user_journey.py
│   ├── conftest.py
│   └── pytest.ini
```

### Testing Pyramid
- **MOST tests**: Unit tests (fast, isolated, test discrete units)
- **FEWER tests**: Integration tests (test component interactions)
- **LEAST tests**: End-to-end tests (slow, test full workflows)

### Organization Principles
- Mirror application code structure in test directories
- Separate tests by type (unit/integration/e2e) using subdirectories
- Each test should verify ONE specific aspect of code
- Keep tests independent - no execution order dependencies
- Tests should be fast, deterministic, and readable

## Fixtures Best Practices

### Fixture Definition
```python
import pytest

# Basic fixture
@pytest.fixture
def user():
    return User(name="John", email="john@example.com")

# Fixture with setup/teardown using yield
@pytest.fixture
def database_connection():
    # SETUP
    conn = create_connection()
    yield conn
    # TEARDOWN - guaranteed to run
    conn.close()
```

### Fixture Scopes
Choose appropriate scope to balance isolation and performance:

- **function** (default): Created/destroyed for each test - maximum isolation
- **class**: Shared across all methods in a test class
- **module**: Shared across all tests in a module - for expensive setup
- **session**: Shared across entire test session - for very expensive operations

```python
@pytest.fixture(scope="function")  # Default - fresh for each test
def temp_user():
    return User()

@pytest.fixture(scope="session")  # Once per test session
def database_schema():
    return create_schema()
```

### conftest.py Usage
- Place shared fixtures in `conftest.py` for automatic discovery (no imports needed)
- Root-level `conftest.py` for global fixtures
- Directory-specific `conftest.py` for localized fixtures
- Use hybrid approach for large projects: centralized `fixtures/` folder + local `conftest.py`

```python
# tests/conftest.py
@pytest.fixture
def api_client():
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test_token"}
```

### Fixture Patterns

**Factory Fixtures (for flexibility):**
```python
@pytest.fixture
def make_user():
    def _make_user(name="John", role="user"):
        return User(name=name, role=role)
    return _make_user

def test_admin_user(make_user):
    admin = make_user(role="admin")
    assert admin.is_admin()
```

**Fixture Composition:**
```python
@pytest.fixture
def user():
    return User("Alice")

@pytest.fixture
def logged_in_user(user):
    user.login()
    return user
```

### Fixture Anti-Patterns to Avoid
- ❌ Overloaded fixtures with too many responsibilities
- ❌ Hardcoded values (use factory pattern instead)
- ❌ Global state leakage without proper cleanup
- ❌ Wrong scope causing performance issues or test contamination
- ❌ Deep fixture dependency chains
- ❌ Duplicating fixtures across test files (use conftest.py)

## Parametrization

### Basic Parametrization
```python
@pytest.mark.parametrize("input, expected", [
    (1, 2),
    (2, 3),
    (10, 11),
])
def test_increment(input, expected):
    assert increment(input) == expected
```

### Multiple Parameters
```python
@pytest.mark.parametrize("a, b, expected", [
    (2, 3, 5),
    (10, 20, 30),
    (-1, 1, 0),
])
def test_addition(a, b, expected):
    assert add(a, b) == expected
```

### Parametrizing with IDs
```python
@pytest.mark.parametrize("email, expected", [
    ("valid@example.com", True),
    ("invalid", False),
    ("", False),
], ids=["valid_email", "missing_domain", "empty_string"])
def test_email_validation(email, expected):
    assert validate_email(email) == expected
```

### Parametrizing Fixtures (Indirect)
```python
@pytest.fixture
def user(request):
    return User(**request.param)

@pytest.mark.parametrize("user", [
    {"name": "Alice", "role": "admin"},
    {"name": "Bob", "role": "user"},
], indirect=True)
def test_user_access(user):
    assert user.name
```

### Combining Parametrization with Markers
```python
@pytest.mark.parametrize("value, expected", [
    (1, 2),
    pytest.param(2, 3, marks=pytest.mark.slow),
    pytest.param(None, 0, marks=pytest.mark.xfail(reason="None not handled")),
])
def test_processing(value, expected):
    assert process(value) == expected
```

## Assertions and Testing Patterns

### Assertion Principles
- **One assert per test** (recommended) - makes failures easier to diagnose
- Use plain `assert` statements - pytest provides detailed introspection
- Test public interfaces, not private methods or implementation details
- Write descriptive test names that explain what's being asserted

```python
# Good - Single, clear assertion
def test_user_email():
    user = User("test@example.com")
    assert user.email == "test@example.com"

# Avoid - Multiple unrelated assertions
def test_user_creation_and_email():  # NOT RECOMMENDED
    user = User("test@example.com")
    assert user.email == "test@example.com"
    assert user.is_active
    assert user.created_at
```

### Exception Testing
```python
# Basic exception assertion
def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(1, 0)

# With message validation using excinfo
def test_invalid_email_error():
    with pytest.raises(ValueError) as excinfo:
        validate_email("invalid")
    assert "Invalid email format" in str(excinfo.value)

# Multiple exception types
def test_multiple_exceptions():
    with pytest.raises((ValueError, TypeError)):
        process_data(None)
```

### Approximate Assertions (Floating Point)
```python
import pytest

def test_floating_point_comparison():
    assert 0.1 + 0.2 == pytest.approx(0.3)

# With tolerance
def test_with_tolerance():
    assert 5.5 == pytest.approx(5.0, abs=0.6)  # Absolute tolerance
    assert 120 == pytest.approx(100, rel=0.2)  # Relative tolerance (20%)

# For collections
def test_list_approx():
    assert [0.1 + 0.2, 0.2 + 0.4] == pytest.approx([0.3, 0.6])
```

### Assertion Anti-Patterns
- ❌ Testing private methods (test public interface instead)
- ❌ Testing implementation details (allows refactoring without breaking tests)
- ❌ Non-deterministic assertions (using random, time without mocking)
- ❌ Multiple unrelated assertions in single test
- ❌ Not validating exception messages (always check message content)

## Test Markers

### Built-in Markers
```python
# Skip test unconditionally
@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature():
    pass

# Conditional skip
@pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python 3.8+")
def test_modern_feature():
    pass

# Expected failure (test runs but failure doesn't count)
@pytest.mark.xfail(reason="Known bug - fix pending")
def test_known_issue():
    assert False

# Parametrize tests
@pytest.mark.parametrize("input,expected", [(1, 2), (2, 3)])
def test_increment(input, expected):
    assert input + 1 == expected
```

### Custom Markers
Define custom markers in `pytest.ini` to avoid warnings:

```ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (test component interactions)
    e2e: End-to-end tests (full workflow)
    slow: Slow-running tests
    smoke: Essential functionality checks
    api: API-related tests
    external: Tests calling external services
```

Use custom markers:
```python
@pytest.mark.unit
@pytest.mark.fast
def test_calculation():
    assert calculate(2, 3) == 5

@pytest.mark.integration
@pytest.mark.slow
def test_api_integration():
    response = api_client.get("/users")
    assert response.status_code == 200
```

### Running Tests by Marker
```bash
# Run specific marker
pytest -m unit

# Exclude marker
pytest -m "not slow"

# Combine markers
pytest -m "unit and not slow"
pytest -m "integration or e2e"
```

### Module-level Markers
Apply markers to all tests in a module:
```python
# At top of test file
pytestmark = [pytest.mark.unit, pytest.mark.fast]

# All tests in this file now have these markers
def test_something():
    pass
```

## Mocking and Patching

### When to Mock
- External API calls
- Database connections
- File system operations
- Expensive computations
- Non-deterministic code (time, random)
- To isolate unit tests from dependencies

### Mocking with pytest-mock (Recommended)
Use the `mocker` fixture from pytest-mock plugin:

```python
def test_api_call(mocker):
    # Mock return value
    mock_response = {"data": "test"}
    mock_get = mocker.patch("requests.get")
    mock_get.return_value.json.return_value = mock_response
    
    result = fetch_data("https://api.example.com")
    
    assert result == mock_response
    mock_get.assert_called_once_with("https://api.example.com")
```

### Patching Strategies
**Key Rule**: Patch where the object is USED, not where it's DEFINED

```python
# If module_a.py imports: from requests import get
# Patch in module_a, not requests
mocker.patch("module_a.get")  # Correct
mocker.patch("requests.get")  # Wrong - too broad
```

### Common Mocking Patterns

**Mock file operations:**
```python
def test_file_creation(mocker):
    mock_file = mocker.mock_open()
    mocker.patch("builtins.open", mock_file)
    
    create_file("test.txt", "content")
    
    mock_file.assert_called_once_with("test.txt", "w")
    mock_file().write.assert_called_once_with("content")
```

**Mock class methods:**
```python
def test_user_method(mocker):
    user = User("Alice")
    mocker.patch.object(user, "get_data", return_value={"name": "Alice"})
    
    result = user.get_data()
    assert result["name"] == "Alice"
```

**Mock with side effects (exceptions, multiple values):**
```python
def test_exception_handling(mocker):
    mocker.patch("os.remove", side_effect=FileNotFoundError)
    
    with pytest.raises(FileNotFoundError):
        delete_file("missing.txt")

def test_multiple_calls(mocker):
    mock = mocker.Mock()
    mock.get_value.side_effect = [1, 2, 3]
    
    assert mock.get_value() == 1
    assert mock.get_value() == 2
    assert mock.get_value() == 3
```

### Monkeypatching (Built-in Alternative)
Use pytest's built-in `monkeypatch` fixture for safer patching:

```python
def test_environment_variable(monkeypatch):
    monkeypatch.setenv("APP_MODE", "testing")
    assert os.getenv("APP_MODE") == "testing"

def test_function_patch(monkeypatch):
    def mock_return():
        return "/fake/path"
    
    monkeypatch.setattr(Path, "home", mock_return)
    assert get_home_dir() == Path("/fake/path")
```

### Mock Assertions
```python
# Verify mock was called
mock.assert_called()
mock.assert_called_once()
mock.assert_not_called()

# Verify call arguments
mock.assert_called_with(arg1, arg2, kwarg=value)
mock.assert_called_once_with(arg1, arg2)

# Check call count
assert mock.call_count == 3
```

### Mocking Best Practices
- Mock roles and interactions, not objects
- Use `autospec=True` to respect method signatures
- Prefer fakes over mocks when possible (simpler, more maintainable)
- Avoid over-mocking (can indicate poor design)
- Mock external dependencies, not internal logic
- Document why mocking is necessary
- Combine unit tests (with mocks) and integration tests (without mocks)

### Mocking Anti-Patterns
- ❌ Mocking low-level architecture (makes refactoring difficult)
- ❌ Deep/recursive mocks (mock returning mock)
- ❌ Not respecting method signatures (use autospec)
- ❌ Patching wrong location (patch where used, not defined)
- ❌ Over-mocking internal logic (test interfaces instead)

## Setup and Teardown

### Use Fixtures (Recommended Approach)
Fixtures are the pytest way for setup/teardown:

```python
@pytest.fixture
def database():
    # SETUP - runs before test
    db = create_database()
    print("Database created")
    
    yield db  # Provide to test
    
    # TEARDOWN - runs after test (even if test fails)
    db.cleanup()
    print("Database cleaned up")

def test_database_query(database):
    result = database.query("SELECT * FROM users")
    assert len(result) > 0
```

### Fixture Scopes for Performance
```python
# Fresh for each test (maximum isolation)
@pytest.fixture(scope="function")
def user():
    return User()

# Shared across test module (expensive setup)
@pytest.fixture(scope="module")
def database_connection():
    conn = create_connection()
    yield conn
    conn.close()

# Shared across entire session (very expensive setup)
@pytest.fixture(scope="session")
def application_config():
    return load_config()
```

### Advanced: Using addfinalizer
For complex cleanup scenarios:

```python
@pytest.fixture
def resource(request):
    print("Setup resource")
    r = Resource()
    
    def cleanup():
        print("Teardown resource")
        r.cleanup()
    
    request.addfinalizer(cleanup)
    return r
```

### Autouse Fixtures
Automatically apply setup to all tests in scope:

```python
@pytest.fixture(autouse=True)
def reset_database():
    """Automatically reset database before each test"""
    print("Resetting database...")
    clear_database()
```

**Use autouse sparingly** - explicit is better than implicit. Only for truly universal setup.

## Common Testing Patterns

### Testing with Temporary Files
Use pytest's `tmp_path` fixture:
```python
def test_file_operations(tmp_path):
    # tmp_path is a Path object to temporary directory
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    
    assert test_file.read_text() == "content"
    # Automatic cleanup after test
```

### Database Testing Pattern
```python
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("postgresql://localhost/testdb")
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()  # Rollback after each test
    connection.close()
```

### API Testing Pattern
```python
@pytest.fixture
def api_client():
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_token():
    return generate_test_token()

def test_api_endpoint(api_client, auth_token):
    response = api_client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### Fake Objects Pattern (Preferred over Mocks)
```python
class FakeDatabaseAdapter:
    def __init__(self):
        self.data_store = []
    
    def save(self, data):
        self.data_store.append(data)
    
    def get_all(self):
        return self.data_store

def test_data_storage():
    fake_db = FakeDatabaseAdapter()
    service = DataService(fake_db)
    
    service.store_data({"id": 1, "name": "Test"})
    
    assert len(fake_db.data_store) == 1
    assert fake_db.data_store[0]["name"] == "Test"
```

## pytest.ini Configuration

Create `pytest.ini` at project root:

```ini
[pytest]
# Test discovery patterns
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Test paths
testpaths = tests

# Minimum pytest version
minversion = 7.0

# Register custom markers (avoids warnings)
markers =
    unit: Unit tests - fast, isolated
    integration: Integration tests - component interactions
    e2e: End-to-end tests - full workflows
    slow: Slow-running tests (skip with -m "not slow")
    smoke: Essential functionality smoke tests
    regression: Comprehensive regression tests
    api: API functionality tests
    ui: UI component tests
    external: Tests requiring external services
    wip: Work in progress tests

# Output options
addopts = 
    -ra
    --strict-markers
    --strict-config
    --showlocals

# Coverage (if using pytest-cov)
# addopts = --cov=src --cov-report=html --cov-report=term
```

## Testing Checklist

### Before Writing Tests
- [ ] Test files follow `test_*.py` or `*_test.py` naming
- [ ] Test structure mirrors application structure
- [ ] Custom markers registered in pytest.ini
- [ ] Fixtures organized in appropriate conftest.py files

### While Writing Tests
- [ ] Test function names start with `test_` and are descriptive
- [ ] One assertion per test (or closely related assertions)
- [ ] Tests are independent and can run in any order
- [ ] Appropriate fixture scope chosen (function/class/module/session)
- [ ] External dependencies mocked appropriately
- [ ] Exception messages validated, not just exception types
- [ ] No hardcoded paths or environment-specific values

### Code Quality
- [ ] Tests are fast (mock expensive operations)
- [ ] Tests are deterministic (same input = same output)
- [ ] Test names clearly describe what's being tested
- [ ] No testing of private methods or implementation details
- [ ] Proper cleanup with fixtures using yield
- [ ] Mark slow tests with @pytest.mark.slow

### Organization
- [ ] Tests organized by type (unit/integration/e2e)
- [ ] Related tests grouped in classes or modules
- [ ] Shared fixtures in conftest.py
- [ ] Test data organized and reusable
- [ ] Appropriate markers applied for test selection

## Quick Reference

### Run Tests
```bash
pytest                          # Run all tests
pytest tests/unit/              # Run specific directory
pytest tests/test_user.py       # Run specific file
pytest -k "user"                # Run tests matching keyword
pytest -m unit                  # Run tests with marker
pytest -m "not slow"            # Exclude slow tests
pytest -v                       # Verbose output
pytest --lf                     # Run last failed tests
pytest --ff                     # Run failures first
pytest -x                       # Stop on first failure
pytest --maxfail=3              # Stop after 3 failures
```

### Common Fixture Scopes
- `scope="function"` - Default, fresh for each test
- `scope="class"` - Shared across test class
- `scope="module"` - Shared across test file
- `scope="session"` - Shared across all tests

### Common Markers
- `@pytest.mark.skip(reason="...")` - Skip test
- `@pytest.mark.skipif(condition, reason="...")` - Conditional skip
- `@pytest.mark.xfail(reason="...")` - Expected failure
- `@pytest.mark.parametrize("arg, expected", [...])` - Parametrize test
- `@pytest.mark.custom_marker` - Custom markers (register in pytest.ini)

## Resources

Based on comprehensive best practices from pytest-with-eric.com, covering:
- Test organization and structure
- Fixture usage and scopes
- Parametrization techniques
- Assertion patterns
- Mocking and patching strategies
- Setup and teardown patterns
- Custom markers and test selection

For more details, visit [pytest-with-eric.com](https://pytest-with-eric.com)
