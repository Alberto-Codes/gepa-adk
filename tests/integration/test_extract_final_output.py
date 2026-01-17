"""Integration tests for extract_final_output with real ADK event objects.

Tests verify the function works correctly with actual ADK Event structures
rather than mocks. These tests require the google-adk package.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestExtractFinalOutputWithRealADKEvents:
    """Integration tests using real ADK event structures."""

    def test_with_genai_part_objects(self) -> None:
        """Test extraction with real google.genai.types.Part objects."""
        from google.genai import types

        from gepa_adk.utils.events import extract_final_output

        # Create a mock event structure using real Part objects
        class RealPartEvent:
            def __init__(self) -> None:
                self.actions = None
                self.content = types.Content(
                    role="model",
                    parts=[types.Part(text="Real ADK output")],
                )

            def is_final_response(self) -> bool:
                return True

        result = extract_final_output([RealPartEvent()])
        assert result == "Real ADK output"

    def test_with_thought_part_from_adk(self) -> None:
        """Test thought filtering with ADK Part that has thought attribute."""
        from google.genai import types

        from gepa_adk.utils.events import extract_final_output

        class ThoughtPartEvent:
            def __init__(self) -> None:
                self.actions = None
                # Create parts - note: google.genai.types.Part may not have
                # thought attribute directly, so we simulate it
                thought_part = types.Part(text="Reasoning content")
                # ADK sets thought attribute dynamically
                object.__setattr__(thought_part, "thought", True)

                output_part = types.Part(text="Final output")

                self.content = types.Content(
                    role="model",
                    parts=[thought_part, output_part],
                )

            def is_final_response(self) -> bool:
                return True

        result = extract_final_output([ThoughtPartEvent()])
        assert result == "Final output"
        assert "Reasoning" not in result

    def test_concatenated_mode_with_real_parts(self) -> None:
        """Test concatenation with real ADK Part objects."""
        from google.genai import types

        from gepa_adk.utils.events import extract_final_output

        class ChunkEvent:
            def __init__(self, text: str) -> None:
                self.actions = None
                self.content = types.Content(
                    role="model",
                    parts=[types.Part(text=text)],
                )

            def is_final_response(self) -> bool:
                return True

        events = [ChunkEvent("Hello, "), ChunkEvent("World!")]

        result = extract_final_output(events, prefer_concatenated=True)
        assert result == "Hello, World!"

    def test_with_response_content_structure(self) -> None:
        """Test extraction from actions.response_content structure."""
        from google.genai import types

        from gepa_adk.utils.events import extract_final_output

        class ResponseContentEvent:
            def __init__(self) -> None:
                # Simulate actions.response_content structure
                class Actions:
                    response_content = [types.Part(text="From response_content")]

                self.actions = Actions()
                self.content = types.Content(
                    role="model",
                    parts=[types.Part(text="From content.parts")],
                )

            def is_final_response(self) -> bool:
                return True

        result = extract_final_output([ResponseContentEvent()])
        assert result == "From response_content"

    def test_graceful_handling_of_adk_event_variations(self) -> None:
        """Test that various ADK event structures are handled gracefully."""
        from gepa_adk.utils.events import extract_final_output

        # Event with None content
        class NoneContentEvent:
            def __init__(self) -> None:
                self.actions = None
                self.content = None

            def is_final_response(self) -> bool:
                return True

        result = extract_final_output([NoneContentEvent()])
        assert result == ""

        # Event with empty parts list
        class EmptyPartsEvent:
            def __init__(self) -> None:
                self.actions = None

                class Content:
                    parts = []

                self.content = Content()

            def is_final_response(self) -> bool:
                return True

        result = extract_final_output([EmptyPartsEvent()])
        assert result == ""
