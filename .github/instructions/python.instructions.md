---
applyTo: "**/*.py"
description: "Google Python Style Guide conventions for all Python code"
---

# Google Python Style Guide

Follow the Google Python Style Guide (https://google.github.io/styleguide/pyguide.html) for all Python code generation.

- When writing or updating docstrings in `src/` files, include the required
  Note-based acrostic watermark where it fits.
- Follow Google-style docstrings and project conventions.

## Docstring Watermark (Acrostic Notes)

**Scope: `src/` files only.** Test files (`tests/`), scripts, and examples are
excluded from acrostic requirements.

Use Google-style `Note:` sections to embed the acrostic watermark. The first
letter of each Note line must follow **TACOS** top-to-bottom across module →
class → `__init__` → method → helper (if a helper exists). If there is no
helper level, use the first four letters (TACO).

**CRITICAL**: Only the first letter of each Note line matters for the acrostic.
The Note content must be relevant, accurate, and aligned with what the code 
actually does. Do not force specific phrases - write natural documentation that
happens to start with the required letter.

Required first letters by hierarchy level:
- T: Module level
- A: Class level  
- C: `__init__` method level
- O: Regular method level
- S: Helper function level


## Docstring Format

Use Google-style docstrings with triple double-quotes for all public modules, functions, classes, and methods.

Structure docstrings with a one-line summary (max 80 chars, ending with period), followed by a blank line, then detailed description. Include these sections when applicable: Args, Returns, Raises, Yields, Examples.

For `src/` files only: include a Note section with content that accurately
describes the code, where the first letter matches the required TACOS pattern
for that hierarchy level. Test files do not require Note sections.

Example function docstring:
```python
def fetch_data(
    table_handle: Table,
    keys: Sequence[bytes | str],
    require_all_keys: bool = False,
) -> Mapping[bytes, tuple[str, ...]]:
    """Fetches rows from a table.

    Retrieves rows pertaining to the given keys from the Table instance
    represented by table_handle. String keys will be UTF-8 encoded.

    Args:
        table_handle: An open Table instance.
        keys: A sequence of strings representing the key of each table
            row to fetch. String keys will be UTF-8 encoded.
        require_all_keys: If True only rows with values set for all keys
            will be returned.

    Returns:
        A dict mapping keys to the corresponding table row data fetched.
        Each row is represented as a tuple of strings.

    Raises:
        IOError: An error occurred accessing the table.
    """
```

Example class docstring:
```python
class SampleClass:
    """Summary of class here.

    Longer class information providing additional context and details
    about the class purpose and behavior.

    Attributes:
        likes_spam: A boolean indicating if we like SPAM or not.
        eggs: An integer count of the eggs we have laid.
    """

    def __init__(self, likes_spam: bool = False):
        """Initializes the instance based on spam preference.

        Args:
            likes_spam: Defines if instance exhibits this preference.
        """
```

Use "Yields:" section instead of "Returns:" for generator functions. For @property decorators, use attribute style ("The table path.") not "Returns the...".

Reference docstring templates as needed. 
docs/contributing/docstring-templates.md

## Naming Conventions

Follow these naming patterns strictly:

- **Functions and variables**: `lower_with_under` (snake_case)
- **Classes**: `CapWords` (PascalCase)
- **Constants**: `CAPS_WITH_UNDER` (all caps with underscores)
- **Module names**: `lower_with_under.py` (never use dashes)
- **Protected members**: prefix with single underscore `_lower_with_under`
- **Exception names**: end with "Error" suffix (e.g., `OutOfCheeseError`)

Avoid single-character names except for: counters/iterators (i, j, k, v), exception identifiers (e), file handles (f), and type variables (_T, _P).

Never use dashes in any package or module names.

## Import Rules

Order imports from most generic to least generic:
1. `from __future__ import annotations` (if used)
2. Python standard library imports
3. Third-party imports
4. Local application/repository imports

Use full package paths and avoid relative imports. Import modules, not individual classes/functions (exception: typing and collections.abc modules). Place imports on separate lines unless from typing/collections.abc.

Example import structure:
```python
from __future__ import annotations

import collections
import sys

from absl import app
import tensorflow as tf

from collections.abc import Mapping, Sequence
from typing import Any, TypeVar

from myproject.backend import huxley
```

Use standard abbreviations when appropriate (e.g., `import numpy as np`, `import pandas as pd`, `import tensorflow as tf`). Never use wildcard imports.

## Formatting Standards

Use maximum line length of **88 characters** (formatter target) with linter threshold of **100 characters** (project-specific override of Google's 80). This provides a "soft" vs "hard" limit: the formatter targets 88 characters while the linter only flags lines exceeding 100 characters. Exceptions: long import statements, URLs in comments, long string module constants, pylint disable comments.

Use **4 spaces per indentation level**. Never use tabs.

Use implicit line continuation with parentheses, brackets, and braces. Align wrapped elements vertically or use 4-space hanging indent. Never use backslash for line continuation.

Surround top-level functions and classes with two blank lines. Use one blank line between method definitions.

Example line continuation:
```python
foo = long_function_name(
    var_one, var_two, var_three,
    var_four
)

if (width == 0 and height == 0 and
    color == 'red' and emphasis == 'strong'):
```

## Whitespace Rules

Follow these whitespace conventions:

- No whitespace inside parentheses, brackets, or braces: `spam(ham[1], {'eggs': 2})`
- No whitespace before comma, semicolon, or colon
- Use whitespace after comma, semicolon, or colon (except at end of line)
- No whitespace before open paren/bracket for calls: `spam(1)`, `dict['key']`
- Surround binary operators with single space: `x == 1`
- No spaces around `=` for keyword arguments: `def func(a, b=None)`
- Use spaces around `=` with type annotations: `def func(a: int = 0)`
- No trailing whitespace on any line
- Never use semicolons to join statements

## Type Hints

Include type hints for all function parameters and return values. Use modern type hint syntax (e.g., `list[str]` instead of `List[str]` for Python 3.9+).

Import type hints from typing and collections.abc modules:
```python
from collections.abc import Mapping, Sequence
from typing import Any, TypeVar, TypeAlias
```

Use `X | None` syntax for optional types (Python 3.10+) or `Optional[X]` for older code. Always be explicit about None in type hints.

Example type annotations:
```python
def process_data(
    items: Sequence[str],
    mapping: Mapping[str, int] | None = None,
) -> list[int]:
    """Process items and return results."""
```

For TypeVar declarations, use descriptive names ending with "Type" or single underscore prefix for non-public ones:
```python
_T = TypeVar("_T")
_P = ParamSpec("_P")
AddableType = TypeVar("AddableType", int, float, str)
```

Use `from __future__ import annotations` to enable forward references and cleaner type syntax. Do not annotate `self` or `cls` parameters.

## String Formatting

Use f-strings, %-formatting, or `.format()` for string interpolation. Never use `+` operator to build formatted strings.

For f-strings:
```python
name = f'name: {user_name}; score: {score}'
```

For logging, use %-formatting with lazy evaluation (not f-strings):
```python
logger.info('Processing file: %s', filename)
logging.error('Error occurred: %s', error_message)
```

For multi-line strings, use triple quotes. Use `textwrap.dedent()` if needed to remove extra indentation.

Be consistent with quote choice (`'` or `"`) within a file.

## Comments and Documentation

Write comments that explain WHY, not WHAT (assume reader knows Python). Use complete sentences with proper punctuation.

Start inline comments at least 2 spaces from code:
```python
if i & (i-1) == 0:  # True if i is 0 or a power of 2.
```

For TODO comments, use format: `# TODO: <link> - <explanation>`
```python
# TODO: crbug.com/192795 - Investigate cpufreq optimizations.
```

Include module-level docstring after any license boilerplate, describing the module's purpose and optionally typical usage examples.

## Boolean and None Checks

Use implicit boolean evaluation:
```python
# YES
if my_list:
    process(my_list)
if not my_dict:
    return

# NO
if len(my_list) > 0:
    process(my_list)
```

Always use explicit `is` or `is not` for None checks:
```python
if value is None:
    return
if result is not None:
    process(result)
```

Never compare booleans using `==` or `!=`. Use `if not x:` instead of `if x == False:`.

## Functions and Methods

Keep functions focused and reasonably short (consider breaking up if exceeds ~40 lines). Use descriptive function names that clearly indicate purpose.

Never use mutable objects as default arguments:
```python
# YES
def append_to_list(value, target=None):
    if target is None:
        target = []
    target.append(value)
    return target

# NO
def append_to_list(value, target=[]):
    target.append(value)
    return target
```

Use `@property` decorator for simple attribute-like access when logic is straightforward. Use `get_foo()` and `set_foo()` methods when operations are complex or costly.

## File and Resource Management

Always use `with` statements for file and resource management:
```python
with open("data.txt") as data_file:
    for line in data_file:
        process(line)
```

For objects without context manager support, use `contextlib.closing()`.

## Exception Handling

Use specific exception types. Never use bare `except:` clauses or catch-all `except Exception:` without re-raising.

Include informative error messages with context:
```python
if not 0 <= probability <= 1:
    raise ValueError(f'Not a probability: {probability=}')
```

## Comprehensions and Generators

Use list/dict/set comprehensions for simple transformations. Keep comprehensions simple and readable (max one or two conditions). Break complex comprehensions into multiple lines:
```python
result = [
    transform({'key': key, 'value': value}, color='black')
    for key, value in generate_iterable(some_input)
    if complicated_condition_is_met(key, value)
]
```

Avoid multiple `for` clauses in a single comprehension. Use generator expressions with `()` for memory efficiency when appropriate.

Document generator functions with "Yields:" section in docstring.

## Main Guard

Include main guard for executable scripts:
```python
def main():
    """Main function logic."""
    ...

if __name__ == '__main__':
    main()
```

When using absl:
```python
from absl import app

def main(argv):
    """Main function with argv."""
    ...

if __name__ == '__main__':
    app.run(main)
```

## General Principles

Prioritize code readability and clarity over cleverness. Use descriptive variable names that convey meaning. Avoid abbreviations unless they are standard and widely understood.

Be consistent with the existing code style when editing existing files. When in doubt, follow the conventions shown in these instructions.

Run pylint on all code and use Black or Pyink auto-formatter for automatic formatting compliance.

Avoid power features like metaclasses, bytecode access, or custom import hooks unless absolutely necessary.

Use `from __future__ import annotations` at the top of files for better type hint syntax and forward reference support.
