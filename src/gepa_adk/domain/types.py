"""Type aliases and configuration types for the domain layer.

This module defines semantic type aliases and configuration dataclasses
used throughout the gepa-adk domain models. These types provide documentation
and clarity without runtime overhead.

Attributes:
    Score (type): Type alias for normalized scores (typically [0.0, 1.0]).
    ComponentName (type): Type alias for component identifiers.
    ModelName (type): Type alias for model identifiers.
    TrajectoryConfig (class): Configuration for trajectory extraction behavior.
    ProposalResult (class): Result of a successful proposal operation.

Examples:
    Using type aliases for clarity:

    ```python
    from gepa_adk.domain.types import Score, ComponentName

    score: Score = 0.85
    component: ComponentName = "instruction"
    ```

    Configuring trajectory extraction:

    ```python
    from gepa_adk.domain.types import TrajectoryConfig

    config = TrajectoryConfig(
        include_tool_calls=True,
        redact_sensitive=True,
        max_string_length=5000,
    )
    ```

Note:
    Type aliases are lightweight hints that improve code readability
    and IDE support. They do not enforce validation at runtime.
    Configuration types use frozen dataclasses for immutability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, NewType, TypeAlias

if TYPE_CHECKING:
    from gepa_adk.domain.models import Candidate

Score: TypeAlias = float
"""Normalized score, typically in [0.0, 1.0]."""

ComponentName: TypeAlias = str
"""Name of a candidate component (e.g., 'instruction', 'output_schema')."""

DEFAULT_COMPONENT_NAME: ComponentName = "instruction"
"""Default component name for single-component evolution.

This constant provides a single source of truth for the default component
name used when evolving a single component (typically an agent's instruction).
Use this constant instead of hardcoding 'instruction' throughout the codebase.
"""

COMPONENT_INSTRUCTION: ComponentName = "instruction"
"""Component name for agent instructions (same as DEFAULT_COMPONENT_NAME)."""

COMPONENT_OUTPUT_SCHEMA: ComponentName = "output_schema"
"""Component name for Pydantic output schema definitions."""

COMPONENT_GENERATE_CONFIG: ComponentName = "generate_content_config"
"""Component name for LLM generation configuration (temperature, top_p, etc.)."""

QualifiedComponentName = NewType("QualifiedComponentName", str)
"""Qualified component name for multi-agent addressing.

A distinct type (via NewType) that represents a dot-separated qualified name
in the format `{agent_name}.{component_name}`. Using NewType enables type
checkers (ty, mypy, pyright) to catch accidental mixing of plain strings
with qualified component names.

See ADR-012 for the design rationale.

Examples:
    ```python
    from gepa_adk.domain.types import QualifiedComponentName

    # Explicit construction (required by type checkers)
    name: QualifiedComponentName = QualifiedComponentName("generator.instruction")

    # Using with ComponentSpec (preferred)
    spec = ComponentSpec(agent="generator", component="instruction")
    name = spec.qualified  # Returns QualifiedComponentName
    ```

Note:
    At runtime, QualifiedComponentName is just a str. The NewType wrapper
    only affects static type checking, not runtime behavior.
"""

ModelName: TypeAlias = str
"""Model identifier (e.g., 'gemini-2.5-flash', 'gpt-4o')."""

ComponentsMapping: TypeAlias = dict[str, list[str]]
"""Mapping of agent names to component names for multi-agent evolution.

Maps each agent name to a list of component names that should be evolved
for that agent. This enables per-agent component configuration in multi-agent
evolution runs.

See ADR-012 for the addressing scheme rationale.

Examples:
    Configure different components per agent:

    ```python
    from gepa_adk.domain.types import ComponentsMapping

    components: ComponentsMapping = {
        "generator": ["instruction", "output_schema"],
        "refiner": ["instruction"],
        "critic": ["generate_content_config"],
    }
    ```

    Exclude an agent from evolution:

    ```python
    components: ComponentsMapping = {
        "generator": ["instruction"],
        "validator": [],  # Empty list = no evolution
    }
    ```

Note:
    All agent names must exist in the agents dict.
    All component names must have registered handlers.
    Empty list excludes the agent from evolution.
"""


@dataclass(frozen=True, slots=True)
class TrajectoryConfig:
    """Configuration for trajectory extraction behavior.

    Controls which components are extracted from ADK event streams,
    whether sensitive data should be redacted, and whether large
    values should be truncated.

    Note:
        All configuration fields are immutable after instantiation,
        ensuring consistent extraction behavior throughout evolution.

    Attributes:
        include_tool_calls (bool): Extract tool/function call records.
            Defaults to True.
        include_state_deltas (bool): Extract session state changes.
            Defaults to True.
        include_token_usage (bool): Extract LLM token consumption metrics.
            Defaults to True.
        redact_sensitive (bool): Apply sensitive data redaction. When True,
            fields matching sensitive_keys will be replaced with "[REDACTED]".
            Defaults to True for secure-by-default behavior.
        sensitive_keys (tuple[str, ...]): Field names to redact via exact
            match. Case-sensitive. Defaults to ("password", "api_key", "token").
        max_string_length (int | None): Truncate strings longer than this
            with a marker indicating truncation. None disables truncation.
            Defaults to 10000 characters.

    Examples:
        Default configuration (secure, with truncation):

        ```python
        config = TrajectoryConfig()  # All features enabled, redaction ON
        ```

        Minimal configuration (tool calls only):

        ```python
        config = TrajectoryConfig(
            include_tool_calls=True,
            include_state_deltas=False,
            include_token_usage=False,
            redact_sensitive=False,
        )
        ```

        Custom sensitive keys and truncation:

        ```python
        config = TrajectoryConfig(
            sensitive_keys=("password", "api_key", "token", "ssn"),
            max_string_length=5000,  # Truncate DOM/screenshots earlier
        )
        ```

        Disable truncation (keep full values):

        ```python
        config = TrajectoryConfig(max_string_length=None)
        ```

    Note:
        Redaction takes precedence over truncation. Sensitive values are
        replaced with "[REDACTED]" first, then truncation applies to the
        remaining (non-sensitive) strings.
    """

    include_tool_calls: bool = True
    include_state_deltas: bool = True
    include_token_usage: bool = True
    redact_sensitive: bool = True
    sensitive_keys: tuple[str, ...] = ("password", "api_key", "token")
    max_string_length: int | None = 10000


@dataclass(frozen=True, slots=True)
class ComponentSpec:
    """Structured representation of an agent.component pair for multi-agent addressing.

    Provides type-safe construction and parsing of qualified component names
    in the format `{agent_name}.{component_name}`. Using a dataclass enables
    IDE autocomplete and type checker validation of field access.

    See ADR-012 for the design rationale.

    Attributes:
        agent (str): The agent name (must be a valid Python identifier).
        component (str): The component name (e.g., 'instruction', 'output_schema').

    Examples:
        Construction and qualified name access:

        ```python
        from gepa_adk.domain.types import ComponentSpec

        spec = ComponentSpec(agent="generator", component="instruction")
        print(spec.qualified)  # "generator.instruction"
        ```

        Parsing from qualified string:

        ```python
        spec = ComponentSpec.parse("critic.output_schema")
        print(spec.agent)  # "critic"
        print(spec.component)  # "output_schema"
        ```

        Using with candidates:

        ```python
        spec = ComponentSpec(agent="generator", component="instruction")
        candidate.components[spec.qualified] = "evolved instruction..."
        ```

    Note:
        An immutable (frozen) dataclass that provides type-safe qualified name
        construction. The qualified property returns a QualifiedComponentName
        (NewType) for type safety with handlers.
    """

    agent: str
    component: str

    @property
    def qualified(self) -> QualifiedComponentName:
        """Return dot-separated qualified name.

        Returns:
            QualifiedComponentName: The qualified name in format 'agent.component'.

        Examples:
            ```python
            spec = ComponentSpec(agent="gen", component="instruction")
            name = spec.qualified  # QualifiedComponentName("gen.instruction")
            ```

        Note:
            Output format follows ADR-012 dot-separated convention.
        """
        return QualifiedComponentName(f"{self.agent}.{self.component}")

    @classmethod
    def parse(cls, qualified: QualifiedComponentName | str) -> ComponentSpec:
        """Parse a qualified name into a ComponentSpec.

        Args:
            qualified: A dot-separated qualified name (e.g., 'generator.instruction').

        Returns:
            ComponentSpec: Parsed specification with agent and component fields.

        Raises:
            ValueError: If the qualified name does not contain a dot separator,
                or if agent or component is empty after parsing.

        Examples:
            ```python
            spec = ComponentSpec.parse("critic.output_schema")
            assert spec.agent == "critic"
            assert spec.component == "output_schema"
            ```

        Note:
            Only the first dot is used as separator, allowing component names
            with dots (though this is not recommended).
        """
        name = str(qualified)
        if "." not in name:
            raise ValueError(
                f"Invalid qualified component name '{name}': "
                "expected format 'agent.component'"
            )
        agent, component = name.split(".", 1)
        if not agent or not component:
            raise ValueError(
                f"Invalid qualified component name '{name}': "
                "both agent and component must be non-empty"
            )
        return cls(agent=agent, component=component)

    def __str__(self) -> str:
        """Return the qualified name as a string."""
        return f"{self.agent}.{self.component}"


class FrontierType(str, Enum):
    """Supported frontier tracking strategies for Pareto selection.

    Note:
        All four frontier types enable different Pareto dominance tracking
        strategies for multi-objective optimization.

    Examples:
        ```python
        frontier_type = FrontierType.INSTANCE
        ```
    """

    INSTANCE = "instance"
    OBJECTIVE = "objective"
    HYBRID = "hybrid"
    CARTESIAN = "cartesian"


# Multi-agent candidate: maps "{agent_name}.{component_name}" -> component value
MultiAgentCandidate: TypeAlias = dict[str, str]
"""Type alias for multi-agent candidate structure.

Maps qualified component names to their values using dot-separated format:
`{agent_name}.{component_name}` as the key.

See ADR-012 for the addressing scheme rationale.

Examples:
    Basic multi-agent candidate:

    ```python
    from gepa_adk.domain.types import MultiAgentCandidate, ComponentSpec

    # Using ComponentSpec for type-safe construction
    gen_inst = ComponentSpec(agent="generator", component="instruction")
    critic_schema = ComponentSpec(agent="critic", component="output_schema")

    candidate: MultiAgentCandidate = {
        gen_inst.qualified: "Generate Python code...",
        critic_schema.qualified: "Review code output schema...",
    }

    # Equivalent direct construction
    candidate: MultiAgentCandidate = {
        "generator.instruction": "Generate Python code...",
        "critic.output_schema": "Review code output schema...",
    }
    ```

Note:
    This type alias is compatible with GEPA's `Candidate` type
    (dict[str, str]), enabling seamless integration with existing
    mutation proposers and evolution engine components.
"""

FrontierKey: TypeAlias = (
    int | str | tuple[str, int] | tuple[str, str] | tuple[str, int, str]
)
"""Key type for frontier mappings across all frontier types.

Key structure varies by frontier type:
- int: example_idx for INSTANCE
- str: objective_name for OBJECTIVE
- tuple[str, int]: ("val_id", example_idx) for HYBRID instance-level
- tuple[str, str]: ("objective", objective_name) for HYBRID objective-level
- tuple[str, int, str]: ("cartesian", example_idx, objective_name) for CARTESIAN

Examples:
    ```python
    from gepa_adk.domain.types import FrontierKey

    # INSTANCE frontier key
    instance_key: FrontierKey = 0  # example_idx

    # OBJECTIVE frontier key
    objective_key: FrontierKey = "accuracy"  # objective_name

    # HYBRID frontier key
    hybrid_key: FrontierKey = ("val_id", 0)  # (type_tag, example_idx)

    # CARTESIAN frontier key
    cartesian_key: FrontierKey = (
        "cartesian", 0, "accuracy"
    )  # (type_tag, example_idx, objective_name)
    ```
"""

MergeAttempt: TypeAlias = tuple["Candidate", int, int, int] | None
"""Type alias for merge attempt results.

Represents a successful merge attempt with the merged candidate and parent/ancestor indices,
or None if merge was not possible.

    Type:
        tuple[Candidate, int, int, int] | None: (merged_candidate, parent1_idx,
            parent2_idx, ancestor_idx) or None

Examples:
    ```python
    from gepa_adk.domain.types import MergeAttempt
    from gepa_adk.domain.models import Candidate

    # Successful merge
    attempt: MergeAttempt = (
        Candidate(components={"instruction": "..."}),
        5,  # parent1_idx
        8,  # parent2_idx
        2,  # ancestor_idx
    )

    # Failed merge
    failed: MergeAttempt = None
    ```

Note:
    Type alias reserved for future merge reporting; currently unused but kept for
    parity with the merge-proposer design docs.
"""

AncestorLog: TypeAlias = tuple[int, int, int]
"""Type alias for tracking attempted merges.

Represents a merge attempt triplet that has been tried, preventing duplicate merges.

Type:
    tuple[int, int, int]: (parent1_idx, parent2_idx, ancestor_idx)

Examples:
    ```python
    from gepa_adk.domain.types import AncestorLog

    # Log of attempted merge
    log: AncestorLog = (5, 8, 2)  # (parent1_idx, parent2_idx, ancestor_idx)
    ```

Note:
    Type alias used by MergeProposer to track which merge combinations have already been attempted,
    preventing redundant merge operations.
"""


@dataclass(frozen=True, slots=True)
class SchemaConstraints:
    """Constraints for output schema evolution.

    Controls which fields must be preserved during schema evolution,
    including field existence and type constraints. Used by the
    OutputSchemaHandler to validate proposed schema mutations.

    Attributes:
        required_fields (tuple[str, ...]): Field names that must exist
            in evolved schemas. Mutations removing these fields are rejected.
        preserve_types (dict[str, type | tuple[type, ...]]): Mapping of
            field names to allowed type(s). Mutations changing a field's
            type to an incompatible type are rejected.

    Examples:
        Preserve required fields only:

        ```python
        from gepa_adk.domain.types import SchemaConstraints

        constraints = SchemaConstraints(
            required_fields=("score", "feedback"),
        )
        ```

        Preserve required fields with type constraints:

        ```python
        constraints = SchemaConstraints(
            required_fields=("score",),
            preserve_types={
                "score": (float, int),  # Allow numeric types
                "order_id": str,  # Must stay string
            },
        )
        ```

    Note:
        A frozen dataclass ensures immutability during evolution runs.
        Configuration is validated at evolution start.
    """

    required_fields: tuple[str, ...] = ()
    preserve_types: dict[str, type | tuple[type, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProposalResult:
    """Result of a successful proposal operation.

    Attributes:
        candidate (Candidate): The proposed candidate with components.
        parent_indices (list[int]): Indices of parent candidate(s) in ParetoState.
        tag (str): Type of proposal ("mutation" or "merge").
        metadata (dict[str, Any]): Additional proposal-specific metadata.

    Examples:
        Creating a mutation proposal result:

        ```python
        from gepa_adk.domain.types import ProposalResult
        from gepa_adk.domain.models import Candidate

        result = ProposalResult(
            candidate=Candidate(components={"instruction": "Be helpful"}),
            parent_indices=[5],
            tag="mutation",
        )
        ```

        Creating a merge proposal result:

        ```python
        result = ProposalResult(
            candidate=Candidate(components={"instruction": "..."}),
            parent_indices=[5, 8],
            tag="merge",
            metadata={"ancestor_idx": 2},
        )
        ```

    Note:
        A frozen dataclass ensures immutability of proposal results.
        Parent indices must be valid indices into the ParetoState.candidates list.
    """

    candidate: "Candidate"  # Forward reference to avoid circular import
    parent_indices: list[int]
    tag: str
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    # Type aliases
    "Score",
    "ComponentName",
    "QualifiedComponentName",
    "ComponentsMapping",
    "ModelName",
    "MultiAgentCandidate",
    "FrontierType",
    "FrontierKey",
    "MergeAttempt",
    "AncestorLog",
    # Dataclasses
    "TrajectoryConfig",
    "ComponentSpec",
    "ProposalResult",
    "SchemaConstraints",
    # Constants
    "DEFAULT_COMPONENT_NAME",
    "COMPONENT_INSTRUCTION",
    "COMPONENT_OUTPUT_SCHEMA",
    "COMPONENT_GENERATE_CONFIG",
]
