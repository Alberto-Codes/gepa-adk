"""Doc-snippet tests for the multi-agent guide.

The Markdown file is the oracle: each test extracts fenced Python blocks from
``docs/guides/multi-agent.md`` and runs them through the validation that
``evolve_group()`` applies, so a snippet that would raise at runtime fails here.

See Also:
    [gepa_adk.adapters.evolution.multi_agent.MultiAgentAdapter][]: The
        adapter whose components validation the snippet must pass.

Examples:
    ```bash
    uv run pytest tests/unit/docs/test_multi_agent_doc_snippets.py -q
    ```
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pytest
from google.adk.agents import LlmAgent

from gepa_adk.adapters.evolution.multi_agent import MultiAgentAdapter

pytestmark = pytest.mark.unit

GUIDE = Path(__file__).resolve().parents[3] / "docs" / "guides" / "multi-agent.md"
_FENCE = re.compile(r"```python\n(.*?)```", re.DOTALL)


def _first_python_block(heading: str) -> str:
    """Find the first fenced Python block that follows a heading.

    Args:
        heading: The full Markdown heading line, for example ``## Usage``.

    Returns:
        The source text inside the fence.
    """
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index(f"\n{heading}\n")
    match = _FENCE.search(text, start)
    assert match is not None, f"no python block after {heading!r}"
    return match.group(1)


def _assigned_dict(source: str, name: str) -> ast.Dict:
    """Find the dict display assigned to a name in a snippet.

    Args:
        source: Snippet source; top-level ``await`` is allowed.
        name: The assignment target to look for.

    Returns:
        The AST node of the assigned dict display.

    Raises:
        AssertionError: If the snippet assigns no dict display to ``name``.
    """
    flags = ast.PyCF_ONLY_AST | ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
    tree = compile(source, "<snippet>", "exec", flags=flags)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
            and isinstance(node.value, ast.Dict)
        ):
            return node.value
    raise AssertionError(f"no dict assigned to {name!r} in snippet")


class _StubScorer:
    """Scorer stand-in; components validation never calls it."""

    def score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Score nothing.

        Args:
            input_text: Ignored.
            output: Ignored.
            expected: Ignored.

        Returns:
            A zero score with empty metadata.
        """
        return 0.0, {}

    async def async_score(
        self, input_text: str, output: str, expected: str | None = None
    ) -> tuple[float, dict[str, Any]]:
        """Score nothing.

        Args:
            input_text: Ignored.
            output: Ignored.
            expected: Ignored.

        Returns:
            A zero score with empty metadata.
        """
        return 0.0, {}


def test_components_snippet_passes_adapter_validation() -> None:
    """The per-agent ``components`` example matches the guide's ``pipeline_agents``."""
    agents_node = _assigned_dict(
        _first_python_block("### Step 1: Create Pipeline Agents"), "pipeline_agents"
    )
    agent_names = [ast.literal_eval(key) for key in agents_node.keys if key]
    pipeline_agents = {
        name: LlmAgent(name=name, instruction="placeholder") for name in agent_names
    }
    components = ast.literal_eval(
        _assigned_dict(
            _first_python_block("## Per-Agent Component Configuration"), "components"
        )
    )

    adapter = MultiAgentAdapter(
        agents=pipeline_agents,
        primary="generator2",
        components=components,
        scorer=_StubScorer(),
        proposer=object(),
    )

    assert agent_names == ["generator1", "generator2"]
    assert adapter.components == components
    assert set(components) == set(pipeline_agents)
