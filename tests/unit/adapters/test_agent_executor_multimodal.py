"""Unit tests for AgentExecutor multimodal input support.

Note:
    Tests the input_content parameter and Content building logic.
"""

from __future__ import annotations

import pytest
from google.genai.types import Content, Part

from gepa_adk.adapters.execution.agent_executor import AgentExecutor
from gepa_adk.ports.agent_executor import ExecutionStatus

pytestmark = pytest.mark.unit


class TestBuildContent:
    """Tests for _build_content method."""

    @pytest.fixture
    def executor(self):
        """Create executor instance."""
        return AgentExecutor()

    def test_wraps_text_in_content(self, executor) -> None:
        """Verify text is wrapped in Content when no input_content."""
        content = executor._build_content("Hello, world!")

        assert isinstance(content, Content)
        assert content.role == "user"
        assert len(content.parts) == 1
        assert content.parts[0].text == "Hello, world!"

    def test_uses_input_content_when_provided(self, executor) -> None:
        """Verify input_content is returned when provided."""
        input_content = Content(
            role="user",
            parts=[Part(text="from content"), Part(text="second part")],
        )

        result = executor._build_content("ignored text", input_content)

        assert result is input_content
        assert len(result.parts) == 2

    def test_input_content_takes_precedence(self, executor) -> None:
        """Verify input_content takes precedence over input_text."""
        input_content = Content(
            role="user",
            parts=[Part(text="from content")],
        )

        result = executor._build_content("from text param", input_content)

        assert result.parts[0].text == "from content"

    def test_empty_text_creates_empty_part(self, executor) -> None:
        """Verify empty text creates Content with empty text Part."""
        content = executor._build_content("")

        assert isinstance(content, Content)
        assert len(content.parts) == 1
        assert content.parts[0].text == ""


class TestExecuteAgentMultimodal:
    """Tests for execute_agent with multimodal support."""

    @pytest.fixture
    def mock_agent(self, mocker):
        """Create mock agent."""
        agent = mocker.MagicMock()
        agent.name = "test_agent"
        agent.model = "gemini-2.0-flash"
        agent.instruction = "Test instruction"
        agent.output_schema = None
        agent.output_key = None
        agent.tools = []
        agent.before_model_callback = None
        agent.after_model_callback = None
        return agent

    @pytest.fixture
    def executor(self):
        """Create executor with mocked session service."""
        return AgentExecutor()

    @pytest.mark.asyncio
    async def test_text_only_backward_compatible(
        self, executor, mock_agent, mocker
    ) -> None:
        """Verify text-only execution works unchanged."""
        mock_session = mocker.MagicMock(id="session_id")
        mocker.patch.object(executor, "_execute_with_timeout", return_value=([], False))
        mocker.patch.object(executor, "_extract_output", return_value="output")
        mocker.patch.object(executor, "_create_session", return_value=mock_session)

        result = await executor.execute_agent(
            agent=mock_agent,
            input_text="Hello, world!",
        )

        assert result.status == ExecutionStatus.SUCCESS
        # Verify input_content was None (not passed)
        executor._execute_with_timeout.assert_called_once()
        call_args = executor._execute_with_timeout.call_args
        assert call_args[0][3] == "Hello, world!"  # input_text
        assert call_args[0][5] is None  # input_content

    @pytest.mark.asyncio
    async def test_multimodal_content_passed_to_runner(
        self, executor, mock_agent, mocker
    ) -> None:
        """Verify multimodal Content is passed to runner."""
        input_content = Content(
            role="user",
            parts=[Part(text="describe this"), Part(text="video placeholder")],
        )
        mock_session = mocker.MagicMock(id="session_id")
        mocker.patch.object(executor, "_execute_with_timeout", return_value=([], False))
        mocker.patch.object(executor, "_extract_output", return_value="output")
        mocker.patch.object(executor, "_create_session", return_value=mock_session)

        result = await executor.execute_agent(
            agent=mock_agent,
            input_text="",
            input_content=input_content,
        )

        assert result.status == ExecutionStatus.SUCCESS
        # Verify input_content was passed
        executor._execute_with_timeout.assert_called_once()
        call_args = executor._execute_with_timeout.call_args
        assert call_args[0][5] is input_content  # input_content

    @pytest.mark.asyncio
    async def test_logging_indicates_multimodal(
        self, executor, mock_agent, mocker
    ) -> None:
        """Verify logging includes is_multimodal flag."""
        input_content = Content(
            role="user",
            parts=[Part(text="test")],
        )
        mock_session = mocker.MagicMock(id="session_id")
        mocker.patch.object(executor, "_execute_with_timeout", return_value=([], False))
        mocker.patch.object(executor, "_extract_output", return_value="output")
        mocker.patch.object(executor, "_create_session", return_value=mock_session)
        mock_logger = mocker.patch.object(executor, "_logger")

        await executor.execute_agent(
            agent=mock_agent,
            input_text="",
            input_content=input_content,
        )

        # Verify is_multimodal was logged
        call_args = mock_logger.info.call_args_list[0]
        assert call_args[1]["is_multimodal"] is True

    @pytest.mark.asyncio
    async def test_logging_indicates_text_only(
        self, executor, mock_agent, mocker
    ) -> None:
        """Verify logging shows is_multimodal=False for text-only."""
        mock_session = mocker.MagicMock(id="session_id")
        mocker.patch.object(executor, "_execute_with_timeout", return_value=([], False))
        mocker.patch.object(executor, "_extract_output", return_value="output")
        mocker.patch.object(executor, "_create_session", return_value=mock_session)
        mock_logger = mocker.patch.object(executor, "_logger")

        await executor.execute_agent(
            agent=mock_agent,
            input_text="Hello",
        )

        # Verify is_multimodal was False
        call_args = mock_logger.info.call_args_list[0]
        assert call_args[1]["is_multimodal"] is False

    @pytest.mark.asyncio
    async def test_overrides_work_with_multimodal(
        self, executor, mock_agent, mocker
    ) -> None:
        """Verify instruction override works with multimodal content."""
        input_content = Content(
            role="user",
            parts=[Part(text="test")],
        )
        mock_session = mocker.MagicMock(id="session_id")
        mocker.patch.object(executor, "_execute_with_timeout", return_value=([], False))
        mocker.patch.object(executor, "_extract_output", return_value="output")
        mocker.patch.object(executor, "_create_session", return_value=mock_session)
        mock_override = mocker.patch.object(
            executor, "_apply_overrides", return_value=mock_agent
        )

        await executor.execute_agent(
            agent=mock_agent,
            input_text="",
            input_content=input_content,
            instruction_override="Custom instruction",
        )

        mock_override.assert_called_once_with(mock_agent, "Custom instruction", None)


class TestExecuteRunnerMultimodal:
    """Tests for _execute_runner with multimodal support."""

    @pytest.fixture
    def executor(self):
        """Create executor instance."""
        return AgentExecutor()

    @pytest.mark.asyncio
    async def test_uses_build_content(self, executor, mocker) -> None:
        """Verify _execute_runner uses _build_content."""
        mock_runner = mocker.MagicMock()
        mock_session = mocker.MagicMock(id="session_id")

        async def empty_gen():
            return
            yield  # noqa: B901

        mock_runner.run_async.return_value = empty_gen()

        mock_build = mocker.patch.object(
            executor,
            "_build_content",
            return_value=Content(role="user", parts=[Part(text="built content")]),
        )

        await executor._execute_runner(
            runner=mock_runner,
            session=mock_session,
            user_id="user",
            input_text="text",
            input_content=None,
        )

        mock_build.assert_called_once_with("text", None)

    @pytest.mark.asyncio
    async def test_passes_content_to_runner(self, executor, mocker) -> None:
        """Verify built Content is passed to runner.run_async."""
        mock_runner = mocker.MagicMock()
        mock_session = mocker.MagicMock(id="session_id")
        expected_content = Content(
            role="user",
            parts=[Part(text="test content")],
        )

        async def empty_gen():
            return
            yield  # noqa: B901

        mock_runner.run_async.return_value = empty_gen()

        mocker.patch.object(executor, "_build_content", return_value=expected_content)

        await executor._execute_runner(
            runner=mock_runner,
            session=mock_session,
            user_id="user",
            input_text="",
            input_content=expected_content,
        )

        mock_runner.run_async.assert_called_once()
        call_kwargs = mock_runner.run_async.call_args[1]
        assert call_kwargs["new_message"] is expected_content
