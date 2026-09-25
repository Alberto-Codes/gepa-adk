"""Component handler for prompt strings held in a caller-owned mapping.

Some prompts live outside the agent, for example in a dict a tool reads
before it calls an external service. ``MappingComponentHandler`` evolves one
key of such a mapping, and ``register_mapping_components`` registers one
handler per key so each key becomes an ordinary component name.

Attributes:
    MappingComponentHandler (class): Handler for one key of a caller-owned
        mapping.
    register_mapping_components (function): Register a handler for every key
        of a mapping and return the component names.

Examples:
    Evolve the prompts a tool reads:

    ```python
    from gepa_adk import evolve, register_mapping_components

    prompts = {"summarize": "Summarize the text.", "classify": "Label it."}
    names = register_mapping_components(prompts)
    result = await evolve(
        agent,
        trainset,
        components=names,
        component_selector="round_robin",
    )
    prompts.update({name: result.evolved_components[name] for name in names})
    ```

See Also:
    - [`component_handler`][gepa_adk.ports.component_handler]:
      ComponentHandler protocol.
    - [`component_handlers`][gepa_adk.adapters.components.component_handlers]:
      Registry and built-in handlers.

Notes:
    The handlers write into the caller's mapping during evaluation and
    restore it afterwards, so the caller applies ``result.evolved_components``
    itself once evolution finishes.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import structlog

from gepa_adk.adapters.components.component_handlers import (
    ComponentHandlerRegistry,
    component_handlers,
)
from gepa_adk.domain.types import COMPONENT_INSTRUCTION, COMPONENT_OUTPUT_SCHEMA

__all__ = ["MappingComponentHandler", "register_mapping_components"]

logger = structlog.get_logger(__name__)

_RESERVED_NAMES = frozenset({COMPONENT_INSTRUCTION, COMPONENT_OUTPUT_SCHEMA})


class MappingComponentHandler:
    """Handler for one string value in a mapping the caller owns.

    Serializes, applies and restores ``mapping[key]``. The agent argument of
    each method is ignored, because the value does not live on the agent.

    Attributes:
        mapping (MutableMapping[str, str]): The caller's mapping, held by
            reference so writes are visible to its other readers.
        key (str): The mapping key this handler evolves.

    Examples:
        ```python
        prompts = {"greeting": "hello"}
        handler = MappingComponentHandler(prompts, key="greeting")
        original = handler.apply(None, "hi")  # prompts["greeting"] == "hi"
        handler.restore(None, original)  # prompts["greeting"] == "hello"
        ```

    Notes:
        The handler keeps a reference to the mapping, not a copy. Replacing
        the mapping object elsewhere detaches the handler from it.
    """

    def __init__(self, mapping: MutableMapping[str, str], key: str) -> None:
        """Bind the handler to one key of the caller's mapping.

        Args:
            mapping: The caller-owned mapping holding the prompt text.
            key: The key whose value this handler evolves.

        Raises:
            ValueError: If ``key`` is not in ``mapping``.
            TypeError: If ``mapping[key]`` is not a ``str``.

        Examples:
            ```python
            handler = MappingComponentHandler({"k": "v"}, key="k")
            ```
        """
        if key not in mapping:
            raise ValueError(f"Mapping has no key {key!r} to evolve")
        value: object = mapping[key]
        if not isinstance(value, str):
            raise TypeError(
                f"Mapping value for key {key!r} must be str, got {type(value).__name__}"
            )
        self.mapping = mapping
        self.key = key

    def serialize(self, agent: Any) -> str:
        """Return the current text of the mapping key.

        Args:
            agent: Ignored; may be ``None``.

        Returns:
            The value of ``mapping[key]``, or an empty string when the caller
            has removed the key or replaced its value with non-text since
            registration.

        Examples:
            ```python
            text = handler.serialize(None)
            ```

        Notes:
            Never raises, per the ``ComponentHandler`` contract. A missing or
            non-text value is logged as ``mapping_handler.key_missing``.
        """
        value = self.mapping.get(self.key)
        if not isinstance(value, str):
            logger.warning(
                "mapping_handler.key_missing",
                key=self.key,
                value_type=type(value).__name__,
            )
            return ""
        return value

    def apply(self, agent: Any, value: str) -> str:
        """Write new text to the mapping key and return the previous text.

        Args:
            agent: Ignored; may be ``None``.
            value: The new text for the key.

        Returns:
            The text the key held before this call.

        Examples:
            ```python
            original = handler.apply(None, "new text")
            ```
        """
        original = self.mapping[self.key]
        self.mapping[self.key] = value
        logger.debug(
            "mapping_handler.apply",
            key=self.key,
            original_preview=original[:50],
            new_preview=value[:50],
        )
        return original

    def restore(self, agent: Any, original: str) -> None:
        """Write the original text back to the mapping key.

        Args:
            agent: Ignored; may be ``None``.
            original: The text returned by ``apply()``.

        Examples:
            ```python
            handler.restore(None, original)
            ```
        """
        self.mapping[self.key] = original
        logger.debug("mapping_handler.restore", key=self.key, preview=original[:50])


def register_mapping_components(
    mapping: MutableMapping[str, str],
    *,
    registry: ComponentHandlerRegistry | None = None,
) -> list[str]:
    """Register a handler for every key of a mapping.

    Each key becomes a component name backed by a
    ``MappingComponentHandler``. Every key is validated before any handler
    is registered, so a rejected mapping leaves the registry unchanged.

    Args:
        mapping: The caller-owned mapping of prompt strings.
        registry: The registry to register into. Defaults to the default
            ``component_handlers`` registry that ``evolve()`` consults.

    Returns:
        The registered component names, in mapping order.

    Raises:
        ValueError: If the mapping is empty, a key is not a Python
            identifier, or a key equals ``instruction`` or ``output_schema``.
        TypeError: If a value is not a ``str``.

    Examples:
        ```python
        prompts = {"greeting": "hello", "farewell": "bye"}
        names = register_mapping_components(prompts)
        # names == ["greeting", "farewell"]
        ```

    See Also:
        - [`MappingComponentHandler`][gepa_adk.adapters.components.MappingComponentHandler]:
          The handler registered for each key.

    Notes:
        Registering a name that already has a handler replaces it.
    """
    if not mapping:
        raise ValueError("Cannot register components from an empty mapping")
    handlers: list[tuple[str, MappingComponentHandler]] = []
    for key in mapping:
        if not key.isidentifier():
            raise ValueError(
                f"Mapping key {key!r} must be a Python identifier to be a "
                "component name"
            )
        if key in _RESERVED_NAMES:
            raise ValueError(f"Mapping key {key!r} shadows a built-in component name")
        handlers.append((key, MappingComponentHandler(mapping, key)))

    target = registry if registry is not None else component_handlers
    for key, handler in handlers:
        target.register(key, handler)
    return [key for key, _ in handlers]
