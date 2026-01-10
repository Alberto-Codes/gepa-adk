#!/usr/bin/env python3
"""Docstring enrichment audit script.

Identifies opportunities to enrich docstrings with sections that maximize
mkdocs-material documentation quality via griffe parsing.

Checks for enrichment opportunities in:
- Modules (__init__.py): Attributes (for exports) + Examples + See Also
- Classes: Attributes (for instance vars) + Examples
- Dataclasses: Attributes (for fields) + Examples
- NamedTuple/TypedDict: Attributes (for fields)
- Enums: Examples
- Functions/Methods:
  - Examples (if public with parameters)
  - Raises (if has raise statements)
  - Yields (if has yield statements)
  - Receives (if generator uses send() pattern: value = yield)
  - Warns (if calls warnings.warn())
  - Other Parameters (if has **kwargs)
- Protocols: Examples

Output: Markdown report grouped by enrichment opportunity type

See Also:
    - ADR-017: Docstring Quality Standards
    - docs/contributing/docstring-templates.md
    - https://mkdocstrings.github.io/griffe/reference/docstrings/
"""

from __future__ import annotations

import argparse
import ast
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Setup paths
root = Path(__file__).resolve().parents[1]
src = root / "src" / "gepa_adk"


def get_available_layers() -> list[str]:
    """Discover available layers from filesystem.

    Returns:
        List of subdirectory names under src/ (e.g., ["domain", "cli", "adapters"])
    """
    if not src.exists():
        return []
    return sorted(
        [
            d.name
            for d in src.iterdir()
            if d.is_dir() and not d.name.startswith("_") and d.name != "__pycache__"
        ]
    )


# Special base classes/decorators that require specific sections
DATACLASS_DECORATORS = {"dataclass", "dataclasses.dataclass"}
NAMEDTUPLE_BASES = {"NamedTuple", "typing.NamedTuple"}
TYPEDDICT_BASES = {"TypedDict", "typing.TypedDict", "typing_extensions.TypedDict"}
ENUM_BASES = {"Enum", "enum.Enum", "IntEnum", "enum.IntEnum", "StrEnum", "enum.StrEnum"}
PROTOCOL_BASES = {"Protocol", "typing.Protocol", "typing_extensions.Protocol"}
EXCEPTION_BASES = {"Exception", "BaseException", "Error"}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Fix Windows console encoding for Unicode output (emojis, etc.)
if sys.stdout.encoding != "utf-8" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]


@dataclass
class EnrichmentOpportunity:
    """Represents a docstring enrichment opportunity."""

    file: Path
    name: str
    kind: str  # "class", "function"
    line: int
    missing_section: str  # "Examples", "Attributes"
    reason: str  # "Public class with 8 methods", "Has 5 instance attributes"


def should_skip(path: Path) -> bool:
    """Check if a file should be skipped during parsing."""
    if "__pycache__" in path.parts:
        return True
    if path.name == "__main__.py":
        return True
    if path.name.startswith("_") and path.name not in {"__init__.py"}:
        return True
    return False


def has_section(docstring: str | None, section: str) -> bool:
    """Check if docstring has a specific section.

    Args:
        docstring: The docstring text to check
        section: Section name to look for (e.g., "Examples", "Attributes")

    Returns:
        True if section is found, False otherwise
    """
    if not docstring:
        return False

    # Match section headers like "Examples:", "Attributes:", etc.
    # Case-insensitive, at start of line, followed by colon
    pattern = rf"^\s*{re.escape(section)}\s*:"
    return bool(re.search(pattern, docstring, re.MULTILINE | re.IGNORECASE))


def has_typed_attributes(docstring: str | None) -> bool:
    """Check if Attributes section includes type annotations.

    Per docstring-templates.md, Attributes should include types in parentheses:
    - `name (str): Description`
    - `config (EvolutionConfig): Evolution parameters`

    This is required because types aren't visible from class/module-level
    attributes like they are in function Args.

    Args:
        docstring: The docstring text to check

    Returns:
        True if Attributes section has typed entries, False otherwise
    """
    if not docstring:
        return False

    # Find the Attributes section
    attrs_match = re.search(
        r"^\s*Attributes\s*:", docstring, re.MULTILINE | re.IGNORECASE
    )
    if not attrs_match:
        return False

    # Get text after Attributes:
    after_attrs = docstring[attrs_match.end() :]

    # Find where the next section starts (or end of docstring)
    next_section = re.search(r"^\s*[A-Z][a-z]+\s*:", after_attrs, re.MULTILINE)
    if next_section:
        attrs_content = after_attrs[: next_section.start()]
    else:
        attrs_content = after_attrs

    # Check if there are any attribute entries (indented lines with name:)
    # Pattern: name (type): description OR name: description
    # We want to find at least one that has the (type) format
    attr_lines = re.findall(r"^\s+(\w+).*?:", attrs_content, re.MULTILINE)

    if not attr_lines:
        return True  # No attributes found, nothing to check

    # Check if at least one attribute has a type annotation in parentheses
    # Pattern: name (SomeType): or name (type | None):
    typed_pattern = r"^\s+\w+\s+\([^)]+\)\s*:"
    return bool(re.search(typed_pattern, attrs_content, re.MULTILINE))


def has_cross_reference_syntax(docstring: str | None) -> bool:
    """Check if See Also section uses proper cross-reference syntax.

    Per docstring-templates.md, See Also links should use mkdocstrings
    cross-reference syntax: [`module.name`][module.name]

    Args:
        docstring: The docstring text to check

    Returns:
        True if See Also section uses cross-references, False otherwise
    """
    if not docstring:
        return False

    # Find the See Also section
    see_also_match = re.search(
        r"^\s*See Also\s*:", docstring, re.MULTILINE | re.IGNORECASE
    )
    if not see_also_match:
        return False

    # Get text after See Also:
    after_see_also = docstring[see_also_match.end() :]

    # Find where the next section starts (or end of docstring)
    next_section = re.search(r"^\s*[A-Z][a-z]+\s*:", after_see_also, re.MULTILINE)
    if next_section:
        see_also_content = after_see_also[: next_section.start()]
    else:
        see_also_content = after_see_also

    # Check if there are any links (lines with backticks or brackets)
    # We want to find cross-reference syntax: [`name`][ref] or [name][ref]
    # Pattern: [`something`][something] or [something][something]
    cross_ref_pattern = r"\[`?[^\]]+`?\]\[[^\]]+\]"
    return bool(re.search(cross_ref_pattern, see_also_content))


def has_doctest_format(docstring: str | None) -> bool:
    """Check if docstring Examples section uses doctest format (>>> prompts).

    Fenced code blocks (```python) are preferred over doctest format because
    they copy cleanly without prompt characters.

    Args:
        docstring: The docstring text to check

    Returns:
        True if Examples section uses doctest format, False otherwise
    """
    if not docstring:
        return False

    # Check if there's an Examples section with >>> prompts
    # First find the Examples section
    examples_match = re.search(
        r"^\s*Examples?\s*:", docstring, re.MULTILINE | re.IGNORECASE
    )
    if not examples_match:
        return False

    # Get text after Examples:
    after_examples = docstring[examples_match.end() :]

    # Check for >>> prompts before the next section or end
    # Next section would be a line starting with a word followed by colon
    next_section = re.search(r"^\s*[A-Z][a-z]+\s*:", after_examples, re.MULTILINE)
    if next_section:
        examples_content = after_examples[: next_section.start()]
    else:
        examples_content = after_examples

    # Check for doctest prompts
    return bool(re.search(r"^\s*>>>", examples_content, re.MULTILINE))


def is_public_api(name: str) -> bool:
    """Check if a name represents a public API (no underscore prefix).

    Args:
        name: The name to check

    Returns:
        True if public API, False otherwise
    """
    return not name.startswith("_")


def count_public_methods(node: ast.ClassDef) -> int:
    """Count public methods in a class.

    Args:
        node: ClassDef AST node

    Returns:
        Number of public methods
    """
    count = 0
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if is_public_api(item.name):
                count += 1
    return count


def get_class_attributes(node: ast.ClassDef) -> list[str]:
    """Extract instance attributes from class __init__ method.

    Args:
        node: ClassDef AST node

    Returns:
        List of attribute names (e.g., ["name", "model", "instruction"])
    """
    attributes: list[str] = []

    # Find __init__ method
    init_method = None
    for item in node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            init_method = item
            break

    if not init_method:
        return attributes

    # Walk __init__ body for self.x = ... assignments
    for stmt in ast.walk(init_method):
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Attribute):
                    # Check if it's self.something
                    if isinstance(target.value, ast.Name) and target.value.id == "self":
                        attributes.append(target.attr)

    return attributes


def get_dataclass_fields(node: ast.ClassDef) -> list[str]:
    """Extract field names from a dataclass (class-level annotations).

    Args:
        node: ClassDef AST node

    Returns:
        List of field names (e.g., ["status", "output", "warnings"])
    """
    fields: list[str] = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            fields.append(item.target.id)
    return fields


def get_decorator_names(node: ast.ClassDef) -> set[str]:
    """Get set of decorator names for a class.

    Args:
        node: ClassDef AST node

    Returns:
        Set of decorator names (e.g., {"dataclass", "frozen"})
    """
    names: set[str] = set()
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            names.add(decorator.id)
        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            names.add(decorator.func.id)
        elif isinstance(decorator, ast.Attribute):
            names.add(
                f"{decorator.value.id}.{decorator.attr}"
                if isinstance(decorator.value, ast.Name)
                else decorator.attr
            )
    return names


def get_base_names(node: ast.ClassDef) -> set[str]:
    """Get set of base class names for a class.

    Args:
        node: ClassDef AST node

    Returns:
        Set of base class names (e.g., {"Enum", "str"})
    """
    names: set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            if isinstance(base.value, ast.Name):
                names.add(f"{base.value.id}.{base.attr}")
            names.add(base.attr)
    return names


def is_dataclass(node: ast.ClassDef) -> bool:
    """Check if class is a dataclass."""
    return bool(get_decorator_names(node) & DATACLASS_DECORATORS)


def is_namedtuple(node: ast.ClassDef) -> bool:
    """Check if class is a NamedTuple."""
    return bool(get_base_names(node) & NAMEDTUPLE_BASES)


def is_typeddict(node: ast.ClassDef) -> bool:
    """Check if class is a TypedDict."""
    return bool(get_base_names(node) & TYPEDDICT_BASES)


def is_enum(node: ast.ClassDef) -> bool:
    """Check if class is an Enum."""
    return bool(get_base_names(node) & ENUM_BASES)


def is_protocol(node: ast.ClassDef) -> bool:
    """Check if class is a Protocol."""
    return bool(get_base_names(node) & PROTOCOL_BASES)


def is_exception(node: ast.ClassDef) -> bool:
    """Check if class is an Exception."""
    return bool(get_base_names(node) & EXCEPTION_BASES)


def get_raised_exceptions(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Extract exception names from raise statements in a function.

    Args:
        node: FunctionDef or AsyncFunctionDef AST node

    Returns:
        List of exception names (e.g., ["ValueError", "TypeError"])

    Examples:
        Extract exceptions from a function:

        ```python
        import ast

        code = "def f(): raise ValueError('error')"
        tree = ast.parse(code)
        func = tree.body[0]
        assert get_raised_exceptions(func) == ["ValueError"]
        ```
    """
    exceptions: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Raise) and child.exc is not None:
            # raise ExceptionType(...)
            if isinstance(child.exc, ast.Call):
                if isinstance(child.exc.func, ast.Name):
                    exceptions.append(child.exc.func.id)
                elif isinstance(child.exc.func, ast.Attribute):
                    exceptions.append(child.exc.func.attr)
            # raise ExceptionType
            elif isinstance(child.exc, ast.Name):
                exceptions.append(child.exc.id)
    return list(set(exceptions))  # Dedupe


def has_yield_statements(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if function contains yield or yield from statements.

    Args:
        node: FunctionDef or AsyncFunctionDef AST node

    Returns:
        True if function has yield statements
    """
    for child in ast.walk(node):
        if isinstance(child, (ast.Yield, ast.YieldFrom)):
            return True
    return False


def has_warnings_warn_calls(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if function calls warnings.warn().

    Args:
        node: FunctionDef or AsyncFunctionDef AST node

    Returns:
        True if function calls warnings.warn()
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            # warnings.warn(...)
            if isinstance(child.func, ast.Attribute):
                if child.func.attr == "warn":
                    if isinstance(child.func.value, ast.Name):
                        if child.func.value.id == "warnings":
                            return True
            # warn(...) - direct import
            elif isinstance(child.func, ast.Name) and child.func.id == "warn":
                return True
    return False


def has_kwargs_parameter(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if function has **kwargs parameter.

    Args:
        node: FunctionDef or AsyncFunctionDef AST node

    Returns:
        True if function has **kwargs
    """
    return node.args.kwarg is not None


def has_receive_pattern(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    r"""Check if generator uses receive pattern (value = yield or value = yield expr).

    This pattern indicates the generator accepts values via send(), which should
    be documented in a Receives section.

    Args:
        node: FunctionDef or AsyncFunctionDef AST node

    Returns:
        True if generator uses receive pattern

    Examples:
        Detect receive pattern in a generator:

        ```python
        import ast

        code = "def gen():\\n    received = yield 'value'"
        tree = ast.parse(code)
        func = tree.body[0]
        assert has_receive_pattern(func)
        ```
    """
    for child in ast.walk(node):
        # Pattern: x = yield or x = yield value
        if isinstance(child, ast.Assign):
            if isinstance(child.value, ast.Yield):
                return True
        # Pattern: x := yield (walrus operator)
        if isinstance(child, ast.NamedExpr):
            if isinstance(child.value, ast.Yield):
                return True
    return False


def get_module_exports(tree: ast.Module) -> list[str]:
    """Extract module exports from __all__ if present.

    Args:
        tree: Module AST node

    Returns:
        List of export names, or empty if no __all__
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        return [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant)
                            and isinstance(elt.value, str)
                        ]
    return []


def analyze_file(file: Path) -> list[EnrichmentOpportunity]:
    """Analyze a single Python file for enrichment opportunities.

    Checks for:
    - Module docstrings: Attributes (if __all__), Examples, See Also
    - Classes: Examples, Attributes (from __init__)
    - Dataclasses: Examples, Attributes (from fields)
    - NamedTuple/TypedDict: Attributes (from fields)
    - Enums: Examples
    - Functions: Examples (if public with params)

    Args:
        file: Path to Python file

    Returns:
        List of EnrichmentOpportunity objects
    """
    try:
        source = file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file))
    except (SyntaxError, UnicodeDecodeError) as exc:
        logger.debug("Failed to parse %s: %s", file, exc)
        return []

    opportunities: list[EnrichmentOpportunity] = []

    # Check module-level docstring (especially for __init__.py)
    module_docstring = ast.get_docstring(tree)
    exports = get_module_exports(tree)

    # Module needs Attributes if it has __all__ exports
    if exports and not has_section(module_docstring, "Attributes"):
        export_list = ", ".join(exports[:5])
        if len(exports) > 5:
            export_list += f", +{len(exports) - 5} more"
        opportunities.append(
            EnrichmentOpportunity(
                file=file,
                name=file.stem,
                kind="module",
                line=1,
                missing_section="Attributes",
                reason=f"Has {len(exports)} exports: {export_list}",
            )
        )
    # Module Attributes should include types
    elif exports and not has_typed_attributes(module_docstring):
        opportunities.append(
            EnrichmentOpportunity(
                file=file,
                name=file.stem,
                kind="module",
                line=1,
                missing_section="Attributes (add types)",
                reason="Attributes should include types: `name (type): desc`",
            )
        )

    # Module needs Examples (for __init__.py especially)
    if file.name == "__init__.py" and not has_section(module_docstring, "Examples"):
        opportunities.append(
            EnrichmentOpportunity(
                file=file,
                name=file.stem,
                kind="module",
                line=1,
                missing_section="Examples",
                reason="Package __init__.py should show usage",
            )
        )

    # Module needs See Also (for __init__.py to cross-reference related packages)
    if file.name == "__init__.py" and not has_section(module_docstring, "See Also"):
        opportunities.append(
            EnrichmentOpportunity(
                file=file,
                name=file.stem,
                kind="module",
                line=1,
                missing_section="See Also",
                reason="Package __init__.py should link related modules",
            )
        )
    # Module See Also should use cross-reference syntax
    elif file.name == "__init__.py" and not has_cross_reference_syntax(
        module_docstring
    ):
        opportunities.append(
            EnrichmentOpportunity(
                file=file,
                name=file.stem,
                kind="module",
                line=1,
                missing_section="See Also (use cross-refs)",
                reason="Use [`module`][module] syntax for links",
            )
        )

    # Walk AST for classes and functions
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if not is_public_api(node.name):
                continue

            docstring = ast.get_docstring(node)

            # Determine class type and check accordingly
            if is_dataclass(node):
                # Dataclass: needs Attributes (from fields) + Examples
                fields = get_dataclass_fields(node)
                if fields and not has_section(docstring, "Attributes"):
                    field_list = ", ".join(fields[:5])
                    if len(fields) > 5:
                        field_list += f", +{len(fields) - 5} more"
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="dataclass",
                            line=node.lineno,
                            missing_section="Attributes",
                            reason=f"Has {len(fields)} fields: {field_list}",
                        )
                    )
                # Dataclass Attributes should include types
                elif fields and not has_typed_attributes(docstring):
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="dataclass",
                            line=node.lineno,
                            missing_section="Attributes (add types)",
                            reason="Attributes should include types: `name (type): desc`",
                        )
                    )
                if not has_section(docstring, "Examples"):
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="dataclass",
                            line=node.lineno,
                            missing_section="Examples",
                            reason="Dataclass should show instantiation",
                        )
                    )

            elif is_namedtuple(node):
                # NamedTuple: needs Attributes (from fields)
                fields = get_dataclass_fields(node)  # Same structure
                if fields and not has_section(docstring, "Attributes"):
                    field_list = ", ".join(fields[:5])
                    if len(fields) > 5:
                        field_list += f", +{len(fields) - 5} more"
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="namedtuple",
                            line=node.lineno,
                            missing_section="Attributes",
                            reason=f"Has {len(fields)} fields: {field_list}",
                        )
                    )
                # NamedTuple Attributes should include types
                elif fields and not has_typed_attributes(docstring):
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="namedtuple",
                            line=node.lineno,
                            missing_section="Attributes (add types)",
                            reason="Attributes should include types: `name (type): desc`",
                        )
                    )

            elif is_typeddict(node):
                # TypedDict: needs Attributes (from fields)
                fields = get_dataclass_fields(node)  # Same structure
                if fields and not has_section(docstring, "Attributes"):
                    field_list = ", ".join(fields[:5])
                    if len(fields) > 5:
                        field_list += f", +{len(fields) - 5} more"
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="typeddict",
                            line=node.lineno,
                            missing_section="Attributes",
                            reason=f"Has {len(fields)} fields: {field_list}",
                        )
                    )
                # TypedDict Attributes should include types
                elif fields and not has_typed_attributes(docstring):
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="typeddict",
                            line=node.lineno,
                            missing_section="Attributes (add types)",
                            reason="Attributes should include types: `name (type): desc`",
                        )
                    )

            elif is_enum(node):
                # Enum: needs Examples
                if not has_section(docstring, "Examples"):
                    # Count enum members
                    member_count = sum(
                        1 for item in node.body if isinstance(item, ast.Assign)
                    )
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="enum",
                            line=node.lineno,
                            missing_section="Examples",
                            reason=f"Enum with {member_count} members",
                        )
                    )

            elif is_protocol(node):
                # Protocol: needs Examples
                if not has_section(docstring, "Examples"):
                    method_count = count_public_methods(node)
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="protocol",
                            line=node.lineno,
                            missing_section="Examples",
                            reason=f"Protocol with {method_count} methods",
                        )
                    )

            else:
                # Regular class: Examples + Attributes
                if not has_section(docstring, "Examples"):
                    method_count = count_public_methods(node)
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="class",
                            line=node.lineno,
                            missing_section="Examples",
                            reason=f"Public class with {method_count} public methods",
                        )
                    )

                # Check for missing Attributes section (classes with self.x)
                attributes = get_class_attributes(node)
                if attributes and not has_section(docstring, "Attributes"):
                    attr_list = ", ".join(attributes[:5])
                    if len(attributes) > 5:
                        attr_list += f", +{len(attributes) - 5} more"
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="class",
                            line=node.lineno,
                            missing_section="Attributes",
                            reason=f"Has {len(attributes)} attributes: {attr_list}",
                        )
                    )
                # Class Attributes should include types
                elif attributes and not has_typed_attributes(docstring):
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="class",
                            line=node.lineno,
                            missing_section="Attributes (add types)",
                            reason="Attributes should include types: `name (type): desc`",
                        )
                    )

            # Check for doctest format in Examples (prefer fenced code blocks)
            # This applies to all class types
            if has_doctest_format(docstring):
                opportunities.append(
                    EnrichmentOpportunity(
                        file=file,
                        name=node.name,
                        kind="class",
                        line=node.lineno,
                        missing_section="Examples (use fenced blocks)",
                        reason="Uses >>> doctest format instead of ```python",
                    )
                )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check for missing sections (public functions)
            if is_public_api(node.name):
                docstring = ast.get_docstring(node)

                # Check for missing Examples section
                if not has_section(docstring, "Examples"):
                    # Only flag if it has parameters (more likely to need examples)
                    has_params = len(node.args.args) > 0
                    # Exclude self/cls from param count
                    param_count = len(node.args.args)
                    if param_count > 0:
                        first_param = node.args.args[0].arg
                        if first_param in ("self", "cls"):
                            param_count -= 1

                    if has_params and param_count > 0:
                        opportunities.append(
                            EnrichmentOpportunity(
                                file=file,
                                name=node.name,
                                kind="function",
                                line=node.lineno,
                                missing_section="Examples",
                                reason=f"Public function with {param_count} parameters",
                            )
                        )

                # Check for missing Raises section
                raised_exceptions = get_raised_exceptions(node)
                if raised_exceptions and not has_section(docstring, "Raises"):
                    exc_list = ", ".join(raised_exceptions[:3])
                    if len(raised_exceptions) > 3:
                        exc_list += f", +{len(raised_exceptions) - 3} more"
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="function",
                            line=node.lineno,
                            missing_section="Raises",
                            reason=f"Raises {exc_list}",
                        )
                    )

                # Check for missing Yields section (generators)
                if has_yield_statements(node) and not has_section(docstring, "Yields"):
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="generator",
                            line=node.lineno,
                            missing_section="Yields",
                            reason="Generator function with yield statements",
                        )
                    )

                # Check for missing Warns section
                if has_warnings_warn_calls(node) and not has_section(
                    docstring, "Warns"
                ):
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="function",
                            line=node.lineno,
                            missing_section="Warns",
                            reason="Calls warnings.warn()",
                        )
                    )

                # Check for missing Receives section (generator with send() pattern)
                if has_receive_pattern(node) and not has_section(docstring, "Receives"):
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="generator",
                            line=node.lineno,
                            missing_section="Receives",
                            reason="Generator uses send() pattern (value = yield)",
                        )
                    )

                # Check for missing Other Parameters section (**kwargs)
                if has_kwargs_parameter(node) and not has_section(
                    docstring, "Other Parameters"
                ):
                    # Also check alternate names: "Keyword Args", "Other Args"
                    has_other_params = (
                        has_section(docstring, "Keyword Args")
                        or has_section(docstring, "Other Args")
                        or has_section(docstring, "Keyword Arguments")
                    )
                    if not has_other_params:
                        kwarg_name = (
                            node.args.kwarg.arg if node.args.kwarg else "kwargs"
                        )
                        opportunities.append(
                            EnrichmentOpportunity(
                                file=file,
                                name=node.name,
                                kind="function",
                                line=node.lineno,
                                missing_section="Other Parameters",
                                reason=f"Has **{kwarg_name} parameter",
                            )
                        )

                # Check for doctest format in Examples (prefer fenced code blocks)
                if has_doctest_format(docstring):
                    opportunities.append(
                        EnrichmentOpportunity(
                            file=file,
                            name=node.name,
                            kind="function",
                            line=node.lineno,
                            missing_section="Examples (use fenced blocks)",
                            reason="Uses >>> doctest format instead of ```python",
                        )
                    )

    return opportunities


def analyze_codebase(
    layer: str | None = None,
    files: list[Path] | None = None,
) -> list[EnrichmentOpportunity]:
    """Analyze entire codebase for enrichment opportunities.

    Args:
        layer: Optional layer to filter by (e.g., "adapters", "ports")
        files: Optional list of specific files to analyze (overrides layer)

    Returns:
        List of all EnrichmentOpportunity objects
    """
    all_opportunities: list[EnrichmentOpportunity] = []

    if files is not None:
        # Analyze only specified files (ignore layer)
        if layer:
            logger.warning("--layer filter ignored when --files specified")

        for py_file in sorted(files):
            if should_skip(py_file):
                continue
            logger.debug("Analyzing %s", py_file.relative_to(root))
            file_opportunities = analyze_file(py_file)
            all_opportunities.extend(file_opportunities)
    else:
        # Original: layer-based or full scan
        # Determine search path
        if layer:
            available_layers = get_available_layers()
            if layer not in available_layers:
                logger.error(
                    "Invalid layer: %s. Valid layers: %s",
                    layer,
                    ", ".join(available_layers) if available_layers else "none",
                )
                return all_opportunities
            search_path = src / layer
            if not search_path.exists():
                logger.warning("Layer directory not found: %s", search_path)
                return all_opportunities
        else:
            search_path = src

        # Analyze Python files
        for py_file in sorted(search_path.rglob("*.py")):
            if should_skip(py_file):
                continue

            logger.debug("Analyzing %s", py_file.relative_to(root))
            file_opportunities = analyze_file(py_file)
            all_opportunities.extend(file_opportunities)

    return all_opportunities


def generate_report(
    opportunities: list[EnrichmentOpportunity],
    layer: str | None,
    section_filter: str | None,
    limit: int,
) -> str:
    """Generate markdown report from enrichment opportunities.

    Args:
        opportunities: List of EnrichmentOpportunity objects
        layer: Layer filter applied (or None)
        section_filter: Section filter applied (or None)
        limit: Max results per section (0 for all)

    Returns:
        Markdown report as string
    """
    # Group by missing section
    by_section: dict[str, list[EnrichmentOpportunity]] = {}
    for opp in opportunities:
        if opp.missing_section not in by_section:
            by_section[opp.missing_section] = []
        by_section[opp.missing_section].append(opp)

    # Sort within each section by file path
    for section_list in by_section.values():
        section_list.sort(key=lambda o: (o.file, o.line))

    # Build report
    lines: list[str] = []
    lines.append("# Docstring Enrichment Audit")
    lines.append("")
    layer_info = f"Layer: {layer}" if layer else "Layer: all"
    lines.append(f"Generated: {layer_info}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    total = 0
    for section_name in sorted(by_section.keys()):
        count = len(by_section[section_name])
        total += count
        lines.append(f"- **Missing {section_name}**: {count} items")
    lines.append(f"- **Total enrichment opportunities**: {total}")
    lines.append("")

    # Filter by section if requested
    if section_filter:
        # Case-insensitive match
        by_section = {
            k: v for k, v in by_section.items() if k.lower() == section_filter.lower()
        }
        if not by_section:
            lines.append(f"No opportunities found for section: {section_filter}")
            lines.append("")
            return "\n".join(lines)

    # Detail sections
    for section_name in sorted(by_section.keys()):
        section_opportunities = by_section[section_name]
        display_opps = (
            section_opportunities if limit == 0 else section_opportunities[:limit]
        )

        lines.append(f"## Missing: {section_name} ({len(section_opportunities)} items)")
        lines.append("")

        if limit > 0 and len(section_opportunities) > limit:
            lines.append(f"*Showing top {limit} of {len(section_opportunities)} total*")
            lines.append("")

        # Table headers
        lines.append("| File | Name | Kind | Line | Reason |")
        lines.append("|------|------|------|------|--------|")

        # Table rows
        for opp in display_opps:
            rel_file = opp.file.relative_to(root)
            lines.append(
                f"| `{rel_file}` | `{opp.name}` | {opp.kind} | {opp.line} | {opp.reason} |"
            )

        lines.append("")

    # No results message
    if not by_section:
        lines.append("✨ No enrichment opportunities found!")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Generate docstring enrichment audit report."""
    parser = argparse.ArgumentParser(
        description="Audit docstrings for enrichment opportunities"
    )

    # Dynamically get available layers
    available_layers = get_available_layers()

    layers_str = ", ".join(available_layers) if available_layers else "none"
    layer_help = f"Filter by layer (available: {layers_str})"
    parser.add_argument(
        "--layer",
        choices=available_layers if available_layers else None,
        help=layer_help,
    )
    parser.add_argument(
        "--section",
        choices=[
            "examples",
            "examples (use fenced blocks)",
            "attributes",
            "see also",
            "raises",
            "yields",
            "warns",
            "receives",
            "other parameters",
        ],
        help="Filter by section type (case-insensitive)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max results per section (default: 5, use 0 for all)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--files",
        type=Path,
        nargs="+",
        help="Specific files to analyze (overrides --layer)",
    )

    args = parser.parse_args()

    logger.info("Starting docstring enrichment audit...")
    if args.layer:
        logger.info("Layer filter: %s", args.layer)
    if args.section:
        logger.info("Section filter: %s", args.section)

    try:
        # Parse file list (convert to absolute paths)
        file_list = None
        if args.files:
            file_list = [root / f if not f.is_absolute() else f for f in args.files]
            logger.info("Analyzing %d specific files", len(file_list))

        # Analyze codebase
        opportunities = analyze_codebase(args.layer, file_list)

        # Generate report
        report = generate_report(opportunities, args.layer, args.section, args.limit)

        # Output report
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report, encoding="utf-8")
            logger.info("Report written to: %s", args.output)
        else:
            print(report)

        logger.info("Analysis complete - found %d opportunities", len(opportunities))

    except Exception as exc:
        logger.error("Failed to generate enrichment report: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
