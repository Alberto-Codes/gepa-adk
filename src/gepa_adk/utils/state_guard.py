"""StateGuard utility for preserving ADK state injection tokens.

This module provides the StateGuard class which validates and repairs mutated
instructions to ensure required state injection tokens are preserved and
unauthorized tokens are escaped.
"""

import re


class StateGuard:
    """Validates and repairs mutated instructions to preserve ADK state tokens.

    StateGuard ensures that required state injection tokens (e.g., {user_id})
    are preserved during instruction evolution, and escapes unauthorized new
    tokens introduced by reflection.

    Attributes:
        required_tokens: List of tokens that must always be present,
            including braces (e.g., ["{user_id}", "{context}"]).
        repair_missing: Whether to re-append missing tokens. Defaults to True.
        escape_unauthorized: Whether to escape new unauthorized tokens.
            Defaults to True.
        _token_pattern: Compiled regex for token detection (private).
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
        """
        self.required_tokens = required_tokens or []
        self.repair_missing = repair_missing
        self.escape_unauthorized = escape_unauthorized
        self._token_pattern = re.compile(r"\{(\w+)\}")

    def _extract_tokens(self, text: str) -> set[str]:
        """Extract token names from text using regex.

        Args:
            text: Text to extract tokens from.

        Returns:
            Set of token names (without braces).
        """
        matches = self._token_pattern.findall(text)
        return set(matches)

    def validate(self, original: str, mutated: str) -> str:
        """Validate and repair mutated instruction.

        Args:
            original: The instruction before mutation (reference for tokens).
            mutated: The instruction after mutation (to be validated).

        Returns:
            The mutated instruction with repairs and escapes applied.
        """
        result = mutated

        # Extract tokens from both instructions
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
