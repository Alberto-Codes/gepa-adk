---
description: "Google Python Style Guide conventions with TACOS docstring watermark for all Python code"
globs:
  - "**/*.py"
alwaysApply: false
---

# Python Code Style Rules

Follow the Google Python Style Guide (https://google.github.io/styleguide/pyguide.html) for all Python code.

## Docstring Watermark (TACOS Acrostic)

**CRITICAL**: Include Google-style `Note:` sections in docstrings where the first letter of each Note line follows **TACOS** pattern:
- **T**: Module level
- **A**: Class level  
- **C**: `__init__` method level
- **O**: Regular method level
- **S**: Helper function level

Only the first letter matters for the acrostic. The Note content must be relevant and accurate - write natural documentation that happens to start with the required letter.

## Docstring Format

Use Google-style docstrings with triple double-quotes. Structure: one-line summary (max 80 chars, ending with period), blank line, then detailed description. Include sections: Args, Returns, Raises, Yields, Examples.

For `@property` decorators, use attribute style ("The table path.") not "Returns the...". Use "Yields:" for generator functions.

Reference: `docs/contributing/docstring-templates.md`

## Naming Conventions

- **Functions/variables**: `lower_with_under` (snake_case)
- **Classes**: `CapWords` (PascalCase)
- **Constants**: `CAPS_WITH_UNDER`
- **Module names**: `lower_with_under.py` (never dashes)
- **Protected members**: `_lower_with_under`
- **Exceptions**: end with "Error" suffix

Avoid single-character names except: counters/iterators (i, j, k, v), exception identifiers (e), file handles (f), type variables (_T, _P).

## Import Rules

Order imports:
1. `from __future__ import annotations` (if used)
2. Standard library
3. Third-party
4. Local application

Use full package paths, avoid relative imports. Import modules, not individual classes/functions (exception: typing and collections.abc). Place imports on separate lines unless from typing/collections.abc.

Never use wildcard imports.

## Formatting Standards

- **Line length**: 88 chars (formatter target), 100 chars (linter threshold)
- **Indentation**: 4 spaces per level (never tabs)
- **Line continuation**: Use implicit continuation with parentheses/brackets/braces. Never use backslash.
- **Blank lines**: Two blank lines around top-level functions/classes. One blank line between methods.

## Whitespace Rules

- No whitespace inside parentheses/brackets/braces: `spam(ham[1], {'eggs': 2})`
- No whitespace before comma/semicolon/colon
- Whitespace after comma/semicolon/colon (except end of line)
- No whitespace before open paren/bracket: `spam(1)`, `dict['key']`
- Single space around binary operators: `x == 1`
- No spaces around `=` for keyword args: `def func(a, b=None)`
- Spaces around `=` with type annotations: `def func(a: int = 0)`
- No trailing whitespace
- Never use semicolons to join statements

## Type Hints

Include type hints for all function parameters and return values. Use modern syntax (`list[str]` not `List[str]` for Python 3.9+).

Use `X | None` for optional types (Python 3.10+) or `Optional[X]` for older code. Always be explicit about None.

Use `from __future__ import annotations` at top of files. Do not annotate `self` or `cls`.

## String Formatting

Use f-strings, %-formatting, or `.format()`. Never use `+` operator for formatted strings.

For logging, use %-formatting with lazy evaluation (not f-strings):
```python
logger.info('Processing file: %s', filename)
```

Be consistent with quote choice (`'` or `"`) within a file.

## Comments and Documentation

Write comments that explain WHY, not WHAT. Use complete sentences with proper punctuation.

TODO format: `# TODO: <link> - <explanation>`

Include module-level docstring after license boilerplate.

## Boolean and None Checks

Use implicit boolean evaluation:
```python
if my_list:
    process(my_list)
if not my_dict:
    return
```

Always use explicit `is` or `is not` for None:
```python
if value is None:
    return
```

Never compare booleans using `==` or `!=`.

## Functions and Methods

Keep functions focused and reasonably short (~40 lines max). Never use mutable objects as default arguments.

Use `@property` for simple attribute-like access. Use `get_foo()`/`set_foo()` for complex/costly operations.

## File and Resource Management

Always use `with` statements. For objects without context manager support, use `contextlib.closing()`.

## Exception Handling

Use specific exception types. Never use bare `except:` or catch-all `except Exception:` without re-raising.

Include informative error messages with context:
```python
if not 0 <= probability <= 1:
    raise ValueError(f'Not a probability: {probability=}')
```

## Comprehensions and Generators

Use comprehensions for simple transformations. Keep simple (max one or two conditions). Break complex comprehensions into multiple lines.

Avoid multiple `for` clauses in single comprehension. Use generator expressions `()` for memory efficiency.

Document generators with "Yields:" section in docstring.

## Main Guard

Include main guard for executable scripts:
```python
def main():
    """Main function logic."""
    ...

if __name__ == '__main__':
    main()
```

## General Principles

- Prioritize readability and clarity over cleverness
- Use descriptive variable names
- Avoid abbreviations unless standard and widely understood
- Be consistent with existing code style when editing
- Use `from __future__ import annotations` for better type hint syntax
- Avoid power features (metaclasses, bytecode access, custom import hooks) unless necessary
