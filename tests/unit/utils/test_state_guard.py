"""Unit tests for StateGuard utility.

Tests verify token repair and escape logic for ADK state injection tokens.
Uses pytest conventions with TDD approach.
"""

import re

import pytest

from gepa_adk.utils.state_guard import StateGuard

pytestmark = pytest.mark.unit


class TestRepairSingleMissingToken:
    """Tests for repairing a single missing token (US1)."""

    def test_repair_single_missing_token(self) -> None:
        """Verify missing {current_step} is re-appended."""
        guard = StateGuard(required_tokens=["{current_step}"])
        original = "Use {current_step} to proceed"
        mutated = "Use this to proceed"

        result = guard.validate(original, mutated)

        assert "{current_step}" in result
        assert result.endswith("\n\n{current_step}")


class TestRepairMultipleMissingTokens:
    """Tests for repairing multiple missing tokens (US1)."""

    def test_repair_multiple_missing_tokens(self) -> None:
        """Verify only missing tokens from required_tokens are appended."""
        guard = StateGuard(required_tokens=["{user_id}", "{context}", "{current_step}"])
        original = "Hello {user_id}, context: {context}, step: {current_step}"
        mutated = "Hello {user_id}, welcome!"

        result = guard.validate(original, mutated)

        assert "{user_id}" in result
        assert "{context}" in result
        assert "{current_step}" in result
        # Verify tokens are appended at the end
        assert result.endswith("\n\n{context}\n\n{current_step}")


class TestNoRepairWhenTokensPresent:
    """Tests for no repair when tokens are present (US1)."""

    def test_no_repair_when_tokens_present(self) -> None:
        """Verify instruction unchanged when all tokens present."""
        guard = StateGuard(required_tokens=["{user_id}", "{context}"])
        original = "Hello {user_id}, context: {context}"
        mutated = "Hi {user_id}, your context: {context}"

        result = guard.validate(original, mutated)

        assert result == mutated
        assert result.count("{user_id}") == 1
        assert result.count("{context}") == 1


class TestRequiredTokensConfiguration:
    """Tests for required_tokens configuration (US3)."""

    def test_required_tokens_configuration(self) -> None:
        """Verify required_tokens list drives repair behavior."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Hello {user_id} and {other_token}"
        mutated = "Hello and {other_token}"

        result = guard.validate(original, mutated)

        # {user_id} should be repaired (in required_tokens)
        assert "{user_id}" in result
        # {other_token} should NOT be repaired (not in required_tokens)
        assert result.count("{other_token}") == 1
        assert "\n\n{other_token}" not in result


class TestEmptyRequiredTokens:
    """Tests for empty required_tokens configuration (US3)."""

    def test_empty_required_tokens(self) -> None:
        """Verify only original tokens considered when required_tokens is empty."""
        guard = StateGuard(required_tokens=[])
        original = "Hello {user_id} and {context}"
        mutated = "Hello and {context}"

        result = guard.validate(original, mutated)

        # No repair should happen since required_tokens is empty
        assert result == mutated
        assert "{user_id}" not in result


class TestEscapeUnauthorizedTokens:
    """Tests for escaping unauthorized tokens (US2)."""

    def test_escape_single_unauthorized_token(self) -> None:
        """Verify new {malicious} becomes {{malicious}}."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {malicious}"

        result = guard.validate(original, mutated)

        # Verify the token is escaped (double braces)
        assert "{{malicious}}" in result
        # Verify the result is different from mutated (escaping happened)
        assert result != mutated
        # Verify no standalone {malicious} token exists (use regex to find standalone patterns)
        # Find all {malicious} patterns that are not part of {{malicious}}
        standalone_matches = [
            m
            for m in re.finditer(r"\{malicious\}", result)
            if m.start() == 0
            or result[m.start() - 1] != "{"
            or m.end() >= len(result)
            or result[m.end()] != "}"
        ]
        assert len(standalone_matches) == 0, "Found standalone {malicious} token"
        assert "{user_id}" in result

    def test_escape_multiple_unauthorized_tokens(self) -> None:
        """Verify all new unauthorized tokens are escaped."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {malicious} and {secret}"

        result = guard.validate(original, mutated)

        assert "{{malicious}}" in result
        assert "{{secret}}" in result
        # Verify tokens are properly escaped (double braces)
        assert result.count("{{malicious}}") == 1
        assert result.count("{{secret}}") == 1

    def test_no_escape_authorized_new_token(self) -> None:
        """Verify token in required_tokens is NOT escaped even if new."""
        guard = StateGuard(required_tokens=["{user_id}", "{new_token}"])
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {new_token}"

        result = guard.validate(original, mutated)

        assert "{new_token}" in result
        assert "{{new_token}}" not in result

    def test_no_escape_existing_token(self) -> None:
        """Verify tokens in both original and mutated are not escaped."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Process for {user_id} and {existing}"
        mutated = "Process for {user_id} with {existing}"

        result = guard.validate(original, mutated)

        assert "{existing}" in result
        assert "{{existing}}" not in result


class TestConfigurableBehavior:
    """Tests for configurable behavior flags (US4)."""

    def test_repair_disabled(self) -> None:
        """Verify missing tokens NOT repaired when repair_missing=False."""
        guard = StateGuard(
            required_tokens=["{user_id}"],
            repair_missing=False,
            escape_unauthorized=True,
        )
        original = "Hello {user_id}"
        mutated = "Hello"

        result = guard.validate(original, mutated)

        # Token should NOT be repaired
        assert "{user_id}" not in result
        assert result == mutated

    def test_escape_disabled(self) -> None:
        """Verify new tokens NOT escaped when escape_unauthorized=False."""
        guard = StateGuard(
            required_tokens=["{user_id}"],
            repair_missing=True,
            escape_unauthorized=False,
        )
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {malicious}"

        result = guard.validate(original, mutated)

        # Token should NOT be escaped
        assert "{malicious}" in result
        assert "{{malicious}}" not in result

    def test_passthrough_mode(self) -> None:
        """Verify no changes when both behaviors disabled."""
        guard = StateGuard(
            required_tokens=["{user_id}"],
            repair_missing=False,
            escape_unauthorized=False,
        )
        original = "Hello {user_id}"
        mutated = "Hello with {malicious}"

        result = guard.validate(original, mutated)

        # Should be unchanged (passthrough)
        assert result == mutated
        assert "{user_id}" not in result
        assert "{malicious}" in result


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_original_instruction(self) -> None:
        """Verify new tokens escaped when original has no tokens."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "No tokens here"
        mutated = "No tokens here with {malicious}"

        result = guard.validate(original, mutated)

        # New token should be escaped (only double-braced version exists)
        assert "{{malicious}}" in result
        # Verify single-brace count equals double-brace count (no unescaped tokens)
        assert result.count("{malicious}") == result.count("{{malicious}}")

    def test_empty_mutated_instruction(self) -> None:
        """Verify missing tokens appended to empty result."""
        guard = StateGuard(required_tokens=["{user_id}", "{context}"])
        original = "Hello {user_id} and {context}"
        mutated = ""

        result = guard.validate(original, mutated)

        # Missing tokens should be appended (alphabetically sorted)
        assert "{user_id}" in result
        assert "{context}" in result
        # Tokens are sorted alphabetically, so user_id comes after context
        assert result.endswith("\n\n{user_id}")

    def test_already_escaped_tokens_ignored(self) -> None:
        """Verify {{escaped}} patterns are not matched."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {{already_escaped}}"

        result = guard.validate(original, mutated)

        # Already escaped token should remain EXACTLY unchanged (not triple-braced)
        assert result == mutated
        # Explicit check: no triple braces
        assert "{{{" not in result

    def test_malformed_tokens_ignored(self) -> None:
        """Verify {invalid-name} with hyphens passes through unchanged."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {invalid-name}"

        result = guard.validate(original, mutated)

        # Malformed token should pass through unchanged (not matched by \w+)
        assert "{invalid-name}" in result
        assert "{{invalid-name}}" not in result

    def test_duplicate_tokens_in_original(self) -> None:
        """Verify token counted once even if appears multiple times."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Hello {user_id}, welcome {user_id}, again {user_id}"
        mutated = "Hello, welcome, again"

        result = guard.validate(original, mutated)

        # Should append {user_id} only once
        assert result.count("{user_id}") == 1
        assert result.endswith("\n\n{user_id}")


class TestPrefixedTokenDetection:
    """Tests for detecting and repairing prefixed state tokens (US1)."""

    def test_repair_missing_app_prefixed_token(self) -> None:
        """Verify missing {app:settings} is re-appended."""
        guard = StateGuard(required_tokens=["{app:settings}"])
        original = "Use {app:settings} to configure"
        mutated = "Use something to configure"

        result = guard.validate(original, mutated)

        assert "{app:settings}" in result
        assert result.endswith("\n\n{app:settings}")

    def test_repair_missing_user_prefixed_token(self) -> None:
        """Verify missing {user:api_key} is re-appended."""
        guard = StateGuard(required_tokens=["{user:api_key}"])
        original = "Authenticate with {user:api_key}"
        mutated = "Authenticate with credentials"

        result = guard.validate(original, mutated)

        assert "{user:api_key}" in result
        assert result.endswith("\n\n{user:api_key}")

    def test_repair_missing_temp_prefixed_token(self) -> None:
        """Verify missing {temp:session} is re-appended."""
        guard = StateGuard(required_tokens=["{temp:session}"])
        original = "Session data: {temp:session}"
        mutated = "Session data: available"

        result = guard.validate(original, mutated)

        assert "{temp:session}" in result
        assert result.endswith("\n\n{temp:session}")

    def test_escape_unauthorized_prefixed_token(self) -> None:
        """Verify new {user:secret} becomes {{user:secret}}."""
        guard = StateGuard(required_tokens=["{user_id}"], escape_unauthorized=True)
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {user:secret}"

        result = guard.validate(original, mutated)

        # Verify the token is escaped (double braces)
        assert "{{user:secret}}" in result
        # Verify no standalone {user:secret} token exists
        standalone_matches = [
            m
            for m in re.finditer(r"\{user:secret\}", result)
            if m.start() == 0
            or result[m.start() - 1] != "{"
            or m.end() >= len(result)
            or result[m.end()] != "}"
        ]
        assert len(standalone_matches) == 0, "Found standalone {user:secret} token"
        assert "{user_id}" in result

    def test_no_escape_authorized_prefixed_token(self) -> None:
        """Verify token in required_tokens is NOT escaped even if new."""
        guard = StateGuard(
            required_tokens=["{user_id}", "{app:settings}"], escape_unauthorized=True
        )
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {app:settings}"

        result = guard.validate(original, mutated)

        assert "{app:settings}" in result
        assert "{{app:settings}}" not in result


class TestOptionalTokenDetection:
    """Tests for detecting and repairing optional state tokens (US3)."""

    def test_repair_missing_optional_token(self) -> None:
        """Verify missing {name?} is re-appended."""
        guard = StateGuard(required_tokens=["{name?}"])
        original = "Hello {name?}, welcome"
        mutated = "Hello, welcome"

        result = guard.validate(original, mutated)

        assert "{name?}" in result
        assert result.endswith("\n\n{name?}")

    def test_escape_unauthorized_optional_token(self) -> None:
        """Verify new {unknown?} becomes {{unknown?}}."""
        guard = StateGuard(required_tokens=["{user_id}"], escape_unauthorized=True)
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {unknown?}"

        result = guard.validate(original, mutated)

        # Verify the token is escaped (double braces)
        assert "{{unknown?}}" in result
        # Verify no standalone {unknown?} token exists
        standalone_matches = [
            m
            for m in re.finditer(r"\{unknown\?\}", result)
            if m.start() == 0
            or result[m.start() - 1] != "{"
            or m.end() >= len(result)
            or result[m.end()] != "}"
        ]
        assert len(standalone_matches) == 0, "Found standalone {unknown?} token"
        assert "{user_id}" in result


class TestCombinedTokenFormats:
    """Tests for combined token formats and edge cases."""

    def test_repair_combined_prefix_optional(self) -> None:
        """Verify missing {app:config?} is re-appended."""
        guard = StateGuard(required_tokens=["{app:config?}"])
        original = "Use {app:config?} if available"
        mutated = "Use default if available"

        result = guard.validate(original, mutated)

        assert "{app:config?}" in result
        assert result.endswith("\n\n{app:config?}")

    def test_mixed_token_formats(self) -> None:
        """Verify {simple}, {app:x}, {name?} work together."""
        guard = StateGuard(required_tokens=["{simple}", "{app:settings}", "{name?}"])
        original = "Hello {simple}, use {app:settings} and {name?}"
        mutated = "Hello, use default"

        result = guard.validate(original, mutated)

        # All tokens should be repaired
        assert "{simple}" in result
        assert "{app:settings}" in result
        assert "{name?}" in result
        # Verify tokens are appended (sorted alphabetically)
        assert result.endswith("\n\n{app:settings}\n\n{name?}\n\n{simple}")

    def test_artifact_token_not_matched(self) -> None:
        """Verify {artifact.name} passes through unchanged (contains dot)."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Process for {user_id}"
        mutated = "Process for {user_id} with {artifact.file_name}"

        result = guard.validate(original, mutated)

        # Artifact token should pass through unchanged (not matched by regex)
        assert "{artifact.file_name}" in result
        assert "{{artifact.file_name}}" not in result
        # Verify it's not treated as a state token
        assert "\n\n{artifact.file_name}" not in result


class TestValidationSummary:
    """Tests for validation summary reporting."""

    def test_summary_reports_repairs_and_escapes(self) -> None:
        """Verify summary returns missing required and unauthorized tokens."""
        guard = StateGuard(required_tokens=["{user_id}", "{context}"])
        original = "Hello {user_id} {context}"
        mutated = "Hello {user_id} with {malicious}"

        repaired, escaped = guard.get_validation_summary(original, mutated)

        assert repaired == ["{context}"]
        assert escaped == ["{malicious}"]

    def test_summary_respects_repair_disabled(self) -> None:
        """Verify summary omits repairs when repair_missing=False."""
        guard = StateGuard(required_tokens=["{user_id}"], repair_missing=False)
        original = "Hello {user_id}"
        mutated = "Hello"

        repaired, escaped = guard.get_validation_summary(original, mutated)

        assert repaired == []
        assert escaped == []

    def test_summary_respects_escape_disabled(self) -> None:
        """Verify summary omits escapes when escape_unauthorized=False."""
        guard = StateGuard(required_tokens=["{user_id}"], escape_unauthorized=False)
        original = "Hello {user_id}"
        mutated = "Hello {user_id} {malicious}"

        repaired, escaped = guard.get_validation_summary(original, mutated)

        assert repaired == []
        assert escaped == []

    def test_summary_no_changes(self) -> None:
        """Verify summary is empty when no repairs or escapes needed."""
        guard = StateGuard(required_tokens=["{user_id}"])
        original = "Hello {user_id}"
        mutated = "Hi {user_id}"

        repaired, escaped = guard.get_validation_summary(original, mutated)

        assert repaired == []
        assert escaped == []
