"""StateGuard utility for preserving ADK state injection tokens.

This module provides the StateGuard class which validates and repairs mutated
component_text to ensure required state injection tokens are preserved and
unauthorized tokens are escaped.

Terminology:
    - **component_text**: The text content being evolved (e.g., agent instruction)
    - **token**: ADK state injection placeholder (e.g., {user_id}, {context})

Note:
    This utility ensures ADK state injection tokens (e.g., {user_id}) remain
    functional after LLM reflection modifies component_text. Tokens must be
    present in both the original component_text and required_tokens list to be
    repaired.
"""

import re


class StateGuard:
    r"""Validates and repairs mutated component_text to preserve ADK state tokens.

    StateGuard ensures that required state injection tokens are preserved
    during component_text evolution, and escapes unauthorized new tokens introduced
    by reflection. Supports simple tokens ({name}), prefixed tokens ({app:settings}),
    optional tokens ({name?}), and combined formats ({app:config?}).

    Attributes:
        required_tokens (list[str]): List of tokens that must always be present,
            including braces (e.g., ["{user_id}", "{app:settings}", "{name?}"]).
        repair_missing (bool): Whether to re-append missing tokens. Defaults to True.
        escape_unauthorized (bool): Whether to escape new unauthorized tokens.
            Defaults to True.
        _token_pattern (re.Pattern[str]): Compiled regex for token detection (private).

    Examples:
        Basic usage with token repair:

        ```python
        guard = StateGuard(required_tokens=["{user_id}", "{context}"])
        original = "Hello {user_id}, context: {context}"
        mutated = "Hello {user_id}, welcome!"
        result = guard.validate(original, mutated)
        # result == "Hello {user_id}, welcome!\n\n{context}"
        ```

        Escaping unauthorized tokens:

        ```python
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {malicious}"
        result = guard.validate(original, mutated)
        # result == "Process for {user_id} with {{malicious}}"
        ```

    Note:
        All validation logic is stateless and operates on string inputs only.
        No external dependencies or I/O operations are performed.

        Supported token formats:
            - Simple tokens: {name}, {user_id}, {context}
            - Prefixed tokens: {app:settings}, {user:api_key}, {temp:session}
            - Optional tokens: {name?}, {user_id?}
            - Combined: {app:config?}, {user:pref?}
    """

    def __init__(
        self,
        required_tokens: list[str] | None = None,
        repair_missing: bool = True,
        escape_unauthorized: bool = True,
    ) -> None:
        """Initialize StateGuard with configuration.

        Args:
            required_tokens: List of tokens that must be preserved,
                including braces (e.g., ["{user_id}", "{context}"]).
                Defaults to empty list.
            repair_missing: If True, re-append missing required tokens.
                Defaults to True.
            escape_unauthorized: If True, escape new unauthorized tokens.
                Defaults to True.

        Note:
            Configuration determines which tokens are protected and which
            behaviors are enabled. Both repair and escape are enabled by default
            for maximum safety.
        """
        self.required_tokens = required_tokens or []
        self.repair_missing = repair_missing
        self.escape_unauthorized = escape_unauthorized
        self._token_pattern = re.compile(r"(?<!\{)\{(\w+(?::\w+)?(?:\?)?)\}(?!\})")

    def _extract_tokens(self, text: str) -> set[str]:
        r"""Extract token names from text using regex.

        Args:
            text: Text to extract tokens from.

        Returns:
            Set of token names (without braces), including full token content
            for prefixed and optional tokens (e.g., "app:settings", "name?").

        Note:
            Tokens are matched using the regex pattern
            `(?<!\{)\{(\w+(?::\w+)?(?:\?)?)\}(?!\})`.

            This pattern matches:
            - Simple tokens: {name} → "name"
            - Prefixed tokens: {app:settings} → "app:settings"
            - Optional tokens: {name?} → "name?"
            - Combined: {app:config?} → "app:config?"

            The negative lookbehind `(?<!\{)` and lookahead `(?!\})` ensure
            already-escaped tokens like `{{token}}` are NOT matched.

            Artifact references (e.g., {artifact.name}) are not matched as they
            contain dots and have different semantics.
        """
        matches = self._token_pattern.findall(text)
        return set(matches)

    def get_validation_summary(
        self, original: str, mutated: str
    ) -> tuple[list[str], list[str]]:
        """Summarize missing token repairs and unauthorized token escapes.

        Args:
            original: The component_text before mutation (reference for tokens).
            mutated: The component_text after mutation (pre-validation).

        Returns:
            Tuple of (repaired_tokens, escaped_tokens) as token strings with braces.

        Examples:
            Summarize repairs and escapes before validation:

            ```python
            guard = StateGuard(required_tokens=["{user_id}"])
            repaired, escaped = guard.get_validation_summary(
                "Hello {user_id}",
                "Hello {user_id} {malicious}",
            )
            # repaired == []
            # escaped == ["{malicious}"]
            ```

        Note:
            The summary reflects what validate() would repair or escape given the
            current configuration and inputs, using the same token detection
            logic as validate(), without modifying the component_text.
        """
        original_tokens = self._extract_tokens(original)
        mutated_tokens = self._extract_tokens(mutated)
        required_token_names = {token.strip("{}") for token in self.required_tokens}

        repaired_tokens: list[str] = []
        if self.repair_missing:
            missing_required = (original_tokens & required_token_names) - mutated_tokens
            repaired_tokens = [f"{{{token}}}" for token in sorted(missing_required)]

        escaped_tokens: list[str] = []
        if self.escape_unauthorized:
            new_tokens = mutated_tokens - original_tokens
            unauthorized_tokens = new_tokens - required_token_names
            escaped_tokens = [f"{{{token}}}" for token in sorted(unauthorized_tokens)]

        return repaired_tokens, escaped_tokens

    def validate(self, original: str, mutated: str) -> str:
        r"""Validate and repair mutated component_text.

        Compares the original and mutated component_text to:
        1. Re-append missing required tokens (if `repair_missing=True`)
        2. Escape unauthorized new tokens (if `escape_unauthorized=True`)

        Args:
            original: The component_text before mutation (reference for tokens).
                Used to determine which tokens were present initially.
            mutated: The component_text after mutation (to be validated).
                This is the component_text that may have missing or unauthorized tokens.

        Returns:
            The mutated component_text with repairs and escapes applied.
            Missing required tokens are appended at the end with `\n\n{token}`.
            Unauthorized new tokens are escaped by doubling braces: `{token}` → `{{token}}`.

        Examples:
            Repair missing token:

            ```python
            guard = StateGuard(required_tokens=["{user_id}"])
            result = guard.validate("Hello {user_id}", "Hello")
            # result == "Hello\n\n{user_id}"
            ```

            Escape unauthorized token:

            ```python
            guard = StateGuard(required_tokens=["{user_id}"])
            result = guard.validate(
                "Process {user_id}", "Process {user_id} {malicious}"
            )
            # result == "Process {user_id} {{malicious}}"
            ```

        Note:
            Only tokens present in both the original component_text and the
            required_tokens list are eligible for repair. New tokens not in
            required_tokens are escaped by default.
        """
        result = mutated

        # Extract tokens from both component_text values
        original_tokens = self._extract_tokens(original)
        mutated_tokens = self._extract_tokens(mutated)

        # Normalize required_tokens (strip braces for comparison)
        required_token_names = {token.strip("{}") for token in self.required_tokens}

        # Repair missing tokens
        if self.repair_missing:
            # Find tokens in original AND required_tokens AND missing from mutated
            missing_required = (original_tokens & required_token_names) - mutated_tokens

            # Append missing tokens
            for token_name in sorted(missing_required):
                full_token = f"{{{token_name}}}"
                result += f"\n\n{full_token}"

        # Escape unauthorized new tokens
        if self.escape_unauthorized:
            # Find tokens that are new (in mutated but not in original)
            new_tokens = mutated_tokens - original_tokens

            # Only escape tokens that are NOT in required_tokens
            unauthorized_tokens = new_tokens - required_token_names

            # Escape each unauthorized token
            for token_name in unauthorized_tokens:
                full_token = f"{{{token_name}}}"
                escaped_token = f"{{{{{token_name}}}}}"
                result = result.replace(full_token, escaped_token)

        return result
