"""Acceptance tests for checkpoint and resume.

With ``EvolutionConfig.checkpoint_path`` set, the engine writes its state to
that file atomically after the baseline and after every recorded iteration.
With ``resume=True`` the engine restores that state instead of evaluating
the baseline: the iteration count, the stagnation counter, the evaluation
counter, the scored-candidate map, the best candidate's reflection batch and
the random state continue, so a resumed run never re-evaluates a candidate
it has already scored and draws the same minibatch rows an uninterrupted
run would. The trainset rows the cached batch covers are checkpointed too,
so a parent accepted on its minibatch with a separate valset resumes with
those rows, and a file without them reads as the full trainset. A
checkpoint written by 2.5.0, whose iteration records lack ``candidate_id``
and ``parent_ids``, still resumes.

Examples:
    Run these tests:

    ```bash
    uv run pytest tests/unit/engine/test_checkpoint_resume.py -q
    ```

See Also:
    - [`gepa_adk.engine.checkpoint`][gepa_adk.engine.checkpoint]: The
      serialisation and atomic-write helpers the engine uses.
    - [`gepa_adk.domain.models.EvolutionConfig`][gepa_adk.domain.models.EvolutionConfig]:
      Holds ``checkpoint_path`` and ``resume``.

Notes:
    The adapter is a fake that scores by instruction text and records every
    ``evaluate()`` call, so no agent or LLM runs.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from gepa_adk.domain.exceptions import ConfigurationError
from gepa_adk.domain.models import Candidate, EvolutionConfig
from gepa_adk.domain.stopper import StopperState
from gepa_adk.engine import AsyncGEPAEngine
from gepa_adk.ports.adapter import EvaluationBatch

pytestmark = pytest.mark.unit

_SCORES = {"seed": 0.5, "worse": 0.0, "better": 1.0, "best": 1.0}


class CrashAfter(RuntimeError):
    """Raised by the adapter to simulate a crash mid-run.

    Examples:
        ```python
        raise CrashAfter("simulated crash")
        ```
    """


class ScriptedAdapter:
    """Fake adapter that scores by instruction text and scripts proposals.

    Attributes:
        proposals (list[str]): Instruction texts to propose, in order. The
            entry ``"crash"`` raises ``CrashAfter`` instead of proposing.
        calls (list[tuple[list[str], str, bool]]): One entry per
            ``evaluate()`` call: the row inputs, the instruction and
            ``capture_traces``.

    Examples:
        ```python
        adapter = ScriptedAdapter(["worse", "crash"])
        ```
    """

    def __init__(self, proposals: list[str]) -> None:
        """Store the scripted proposals.

        Args:
            proposals: Instruction texts to propose, one per iteration.
        """
        self.proposals = list(proposals)
        self.calls: list[tuple[list[str], str, bool]] = []

    async def evaluate(
        self,
        batch: list[dict[str, str]],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[Any, Any]:
        """Score every row by the candidate's instruction text.

        Args:
            batch: Rows to evaluate.
            candidate: Candidate components.
            capture_traces: Whether traces were requested.

        Returns:
            A batch with one score per row and dict traces when requested.
        """
        instruction = candidate["instruction"]
        inputs = [row["input"] for row in batch]
        self.calls.append((inputs, instruction, capture_traces))
        score = _SCORES[instruction]
        return EvaluationBatch(
            outputs=[f"{instruction}:{i}" for i in inputs],
            scores=[score] * len(batch),
            trajectories=[{"row": i, "tool": "ünïcode"} for i in inputs]
            if capture_traces
            else None,
            inputs=inputs,
            metadata=[{"feedback": f"fb-{i}"} for i in inputs],
        )

    async def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[Any, Any],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        """Expose the batch's outputs so a resumed run proves it kept them.

        Args:
            candidate: Ignored.
            eval_batch: The parent's reflection batch.
            components_to_update: Components to build examples for.

        Returns:
            One example per output for each component.
        """
        return {
            name: [{"output": o} for o in eval_batch.outputs]
            for name in components_to_update
        }

    async def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        """Return the next scripted proposal or crash.

        Args:
            candidate: Ignored.
            reflective_dataset: Recorded on the adapter for inspection.
            components_to_update: Ignored.

        Returns:
            The next instruction text from the script.

        Raises:
            CrashAfter: When the next script entry is ``"crash"``.
        """
        self.last_reflective_dataset = reflective_dataset
        entry = self.proposals.pop(0)
        if entry == "crash":
            raise CrashAfter("simulated crash")
        return {"instruction": entry}


class _Recorder:
    """Stop callback that records the evaluation count it is shown.

    Attributes:
        seen (list[int]): ``total_evaluations`` values observed, one per call.

    Examples:
        ```python
        recorder = _Recorder()
        EvolutionConfig(stop_callbacks=[recorder])
        ```
    """

    def __init__(self) -> None:
        """Start with no observations."""
        self.seen: list[int] = []

    def __call__(self, state: StopperState) -> bool:
        """Record total_evaluations and never stop.

        Args:
            state: Snapshot of engine progress.

        Returns:
            False, so the engine runs to its other limits.
        """
        self.seen.append(state.total_evaluations)
        return False


def _trainset(n: int = 4) -> list[dict[str, str]]:
    """Build a trainset with distinct inputs.

    Args:
        n: Number of rows.

    Returns:
        Rows whose inputs are ``"q0"`` to ``"q{n-1}"``.
    """
    return [{"input": f"q{i}", "expected": "a"} for i in range(n)]


def _engine(
    adapter: ScriptedAdapter,
    path: Path | None,
    *,
    resume: bool = False,
    max_iterations: int = 4,
    patience: int = 10,
    seed: int | None = 3,
    minibatch: int | None = None,
    stop_callbacks: list[Any] | None = None,
    seed_text: str = "seed",
    trainset: list[dict[str, str]] | None = None,
    valset: list[dict[str, str]] | None = None,
    candidate_selector: Any = None,
) -> AsyncGEPAEngine:
    config = EvolutionConfig(
        max_iterations=max_iterations,
        patience=patience,
        min_improvement_threshold=0.0,
        seed=seed,
        reflection_minibatch_size=minibatch,
        checkpoint_path=path,
        resume=resume,
        stop_callbacks=stop_callbacks or [],
    )
    return AsyncGEPAEngine(
        adapter=adapter,
        config=config,
        initial_candidate=Candidate(components={"instruction": seed_text}),
        batch=trainset if trainset is not None else _trainset(),
        valset=valset,
        candidate_selector=candidate_selector,
    )


class TestConfig:
    """The two config fields and their validation.

    Examples:
        ```bash
        uv run pytest "tests/unit/engine/test_checkpoint_resume.py::TestConfig" -q
        ```
    """

    def test_defaults(self) -> None:
        """No checkpointing by default."""
        config = EvolutionConfig()
        assert config.checkpoint_path is None
        assert config.resume is False

    @pytest.mark.parametrize("bad", [True, 123, 2.5, object()])
    def test_rejects_non_path_types(self, bad: Any) -> None:
        """A checkpoint_path that is not None, str or Path is a configuration error."""
        with pytest.raises(ConfigurationError, match="checkpoint_path"):
            EvolutionConfig(checkpoint_path=bad)

    def test_resume_requires_a_path(self) -> None:
        """resume=True without checkpoint_path is a configuration error."""
        with pytest.raises(ConfigurationError, match="checkpoint_path"):
            EvolutionConfig(resume=True)

    def test_path_accepts_str_and_path(self, tmp_path: Path) -> None:
        """A str or Path is stored as a Path."""
        assert EvolutionConfig(
            checkpoint_path=str(tmp_path / "c.json")
        ).checkpoint_path == (tmp_path / "c.json")
        assert EvolutionConfig(checkpoint_path=tmp_path / "c.json").checkpoint_path == (
            tmp_path / "c.json"
        )

    def test_candidate_selector_with_checkpoint_is_rejected(
        self, tmp_path: Path
    ) -> None:
        """Pareto state is not checkpointed yet, so the engine refuses the pair."""
        from gepa_adk.adapters.selection.candidate_selector import (
            ParetoCandidateSelector,
        )

        with pytest.raises(ConfigurationError, match="candidate_selector"):
            _engine(
                ScriptedAdapter([]),
                tmp_path / "c.json",
                candidate_selector=ParetoCandidateSelector(),
            )


class TestCheckpointWrites:
    """The checkpoint file reflects the engine after each recorded iteration.

    Examples:
        ```bash
        uv run pytest "tests/unit/engine/test_checkpoint_resume.py::TestCheckpointWrites" -q
        ```
    """

    @pytest.mark.asyncio
    async def test_file_written_after_run(self, tmp_path: Path) -> None:
        """A completed run leaves one JSON file with the final state and no temp file."""
        path = tmp_path / "run" / "checkpoint.json"
        adapter = ScriptedAdapter(["worse", "better"])
        result = await _engine(adapter, path, max_iterations=2).run()

        assert path.exists()
        assert sorted(p.name for p in path.parent.iterdir()) == ["checkpoint.json"]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["checkpoint_version"] == 1
        assert data["iteration"] == 2
        assert data["stagnation_counter"] == 0
        assert data["best_candidate"]["components"] == {"instruction": "better"}
        assert data["best_score"] == result.final_score == 4.0
        assert data["original_score"] == 2.0
        assert data["total_evaluations"] == 12
        assert len(data["iteration_history"]) == 2
        assert set(data["scored"]) == {
            Candidate(components={"instruction": t}).id
            for t in ("seed", "worse", "better")
        }
        assert (
            data["initial_candidate_id"]
            == Candidate(components={"instruction": "seed"}).id
        )
        assert data["trainset_size"] == 4

    @pytest.mark.asyncio
    async def test_no_checkpoint_path_writes_nothing(self, tmp_path: Path) -> None:
        """Without a path the run leaves the directory untouched."""
        await _engine(ScriptedAdapter(["worse"]), None, max_iterations=1).run()
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.asyncio
    async def test_crash_leaves_the_last_completed_iteration(
        self, tmp_path: Path
    ) -> None:
        """A crash in iteration 3 leaves a checkpoint at iteration 2."""
        path = tmp_path / "checkpoint.json"
        adapter = ScriptedAdapter(["worse", "worse", "crash"])

        with pytest.raises(CrashAfter):
            await _engine(adapter, path, max_iterations=5).run()

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["iteration"] == 2
        assert data["stagnation_counter"] == 2
        assert [r["accepted"] for r in data["iteration_history"]] == [False, False]


class TestResume:
    """A resumed run continues where the checkpoint left off.

    Includes the trainset rows of a parent's cached batch: a minibatch
    parent resumes with its sampled rows, a file without rows with the full
    trainset.

    Examples:
        ```bash
        uv run pytest "tests/unit/engine/test_checkpoint_resume.py::TestResume" -q
        ```
    """

    @pytest.mark.asyncio
    async def test_continues_counts_and_never_re_evaluates(
        self, tmp_path: Path
    ) -> None:
        """Iteration and stagnation continue; scored candidates are not run again."""
        path = tmp_path / "checkpoint.json"
        first = ScriptedAdapter(["worse", "worse", "crash"])
        with pytest.raises(CrashAfter):
            await _engine(first, path, max_iterations=5, patience=3).run()

        recorder = _Recorder()
        second = ScriptedAdapter(["worse", "better", "best"])
        result = await _engine(
            second,
            path,
            resume=True,
            max_iterations=5,
            patience=3,
            stop_callbacks=[recorder],
        ).run()

        # Iteration numbers continue from the checkpoint.
        assert [r.iteration_number for r in result.iteration_history] == [1, 2, 3]
        assert result.total_iterations == 3
        # Stagnation continued: two rejections before, one after, patience 3.
        assert result.evolved_components["instruction"] == "seed"
        # "worse" was scored before the crash: recorded as a duplicate, not run.
        third = result.iteration_history[2]
        assert third.skip_reason == "duplicate"
        assert third.score == 0.0
        assert second.calls == []
        # The evaluation counter continued from the checkpointed 8 (the
        # baseline and one "worse"; the second "worse" was a duplicate).
        assert recorder.seen and recorder.seen[0] == 8
        # The original score and history from before the crash are intact.
        assert result.original_score == 2.0
        assert [r.accepted for r in result.iteration_history] == [False] * 3

    @pytest.mark.asyncio
    async def test_resume_keeps_the_best_candidates_reflection_batch(
        self, tmp_path: Path
    ) -> None:
        """The reflector sees the checkpointed batch; the best is not re-run."""
        path = tmp_path / "checkpoint.json"
        first = ScriptedAdapter(["better", "crash"])
        with pytest.raises(CrashAfter):
            await _engine(first, path, max_iterations=3).run()

        second = ScriptedAdapter(["best"])
        result = await _engine(second, path, resume=True, max_iterations=2).run()

        # No evaluation of "better" (the best) on resume; only the new proposal.
        assert [instr for _, instr, _ in second.calls] == ["best"]
        # The reflective dataset came from the checkpointed batch of "better".
        outputs = [e["output"] for e in second.last_reflective_dataset["instruction"]]
        assert outputs == [f"better:q{i}" for i in range(4)]
        assert result.total_iterations == 2
        assert result.final_score == 4.0

    @pytest.mark.asyncio
    async def test_resumed_run_draws_the_same_minibatch_rows(
        self, tmp_path: Path
    ) -> None:
        """Random state is checkpointed, so resume matches an uninterrupted run."""
        script = ["worse", "worse", "worse", "worse"]
        straight = ScriptedAdapter(list(script))
        await _engine(straight, None, max_iterations=4, seed=11, minibatch=2).run()
        straight_draws = [inputs for inputs, _, _ in straight.calls[1:]]
        assert len(straight_draws) == 4

        path = tmp_path / "checkpoint.json"
        first = ScriptedAdapter(["worse", "worse", "crash"])
        with pytest.raises(CrashAfter):
            await _engine(first, path, max_iterations=4, seed=11, minibatch=2).run()
        second = ScriptedAdapter(["worse", "worse"])
        await _engine(
            second, path, resume=True, max_iterations=4, seed=11, minibatch=2
        ).run()

        resumed_draws = [inputs for inputs, _, _ in first.calls[1:]] + [
            inputs for inputs, _, _ in second.calls
        ]
        assert resumed_draws == straight_draws

    @pytest.mark.asyncio
    async def test_resume_result_has_the_uninterrupted_shape(
        self, tmp_path: Path
    ) -> None:
        """A resumed result round-trips through to_dict like any other."""
        path = tmp_path / "checkpoint.json"
        first = ScriptedAdapter(["worse", "crash"])
        with pytest.raises(CrashAfter):
            await _engine(first, path, max_iterations=2).run()
        result = await _engine(
            ScriptedAdapter(["better"]), path, resume=True, max_iterations=2
        ).run()

        data = result.to_dict()
        assert data["total_iterations"] == 2
        assert type(result).from_dict(data) == result

    @pytest.mark.asyncio
    async def test_a_checkpoint_from_2_5_0_resumes(self, tmp_path: Path) -> None:
        """Records without candidate_id and parent_ids load with None genealogy."""
        path = tmp_path / "checkpoint.json"
        first = ScriptedAdapter(["better", "crash"])
        with pytest.raises(CrashAfter):
            await _engine(first, path, max_iterations=3).run()
        data = json.loads(path.read_text())
        # A 2.5.0 checkpoint: no genealogy keys and a gen-N parent label
        for record in data["iteration_history"]:
            del record["candidate_id"]
            del record["parent_ids"]
        data["best_candidate"]["parent_id"] = "gen-0"
        path.write_text(json.dumps(data))

        result = await _engine(
            ScriptedAdapter(["best"]), path, resume=True, max_iterations=2
        ).run()

        restored, resumed = result.iteration_history
        assert restored.accepted is True
        assert restored.candidate_id is None
        assert restored.parent_ids is None
        better = Candidate(components={"instruction": "better"})
        assert resumed.candidate_id == Candidate(components={"instruction": "best"}).id
        assert resumed.parent_ids == [better.id]

    @pytest.mark.asyncio
    async def test_resume_keeps_the_sampled_rows_of_a_minibatch_parent(
        self, tmp_path: Path
    ) -> None:
        """A parent accepted on its minibatch resumes with those rows only."""
        path = tmp_path / "checkpoint.json"
        valset = [{"input": f"v{i}", "expected": "a"} for i in range(2)]
        first = ScriptedAdapter(["better", "crash"])
        with pytest.raises(CrashAfter):
            await _engine(
                first, path, max_iterations=3, seed=11, minibatch=2, valset=valset
            ).run()
        gate_inputs = first.calls[2][0]
        assert [len(inputs) for inputs, _, _ in first.calls] == [4, 2, 2, 2]
        data = json.loads(path.read_text())
        assert data["last_eval_rows"] == [int(i[1:]) for i in gate_inputs]

        second = ScriptedAdapter(["best"])
        await _engine(
            second,
            path,
            resume=True,
            max_iterations=2,
            seed=11,
            minibatch=2,
            valset=valset,
        ).run()

        # The next gate compares on the checkpointed rows, not a fresh draw
        assert second.calls[0][0] == gate_inputs
        outputs = [e["output"] for e in second.last_reflective_dataset["instruction"]]
        assert outputs == [f"better:{i}" for i in gate_inputs]

    @pytest.mark.asyncio
    async def test_a_checkpoint_without_rows_resumes_as_the_full_trainset(
        self, tmp_path: Path
    ) -> None:
        """A file written before last_eval_rows existed reads as the full batch."""
        path = tmp_path / "checkpoint.json"
        first = ScriptedAdapter(["better", "crash"])
        with pytest.raises(CrashAfter):
            await _engine(first, path, max_iterations=3).run()
        data = json.loads(path.read_text())
        assert data["last_eval_rows"] is None
        del data["last_eval_rows"]
        path.write_text(json.dumps(data))

        second = ScriptedAdapter(["best"])
        await _engine(second, path, resume=True, max_iterations=2, minibatch=2).run()

        outputs = [e["output"] for e in second.last_reflective_dataset["instruction"]]
        assert outputs == [f"better:q{i}" for i in range(4)]
        assert len(second.calls[0][0]) == 2


class TestResumeRefusals:
    """Resume fails loudly instead of silently starting over.

    A missing file, a different initial candidate, a different trainset or
    valset size and an unknown version are each refused.

    Examples:
        ```bash
        uv run pytest "tests/unit/engine/test_checkpoint_resume.py::TestResumeRefusals" -q
        ```
    """

    @pytest.mark.asyncio
    async def test_missing_file(self, tmp_path: Path) -> None:
        """resume=True with no file is a configuration error naming the path."""
        path = tmp_path / "missing.json"
        with pytest.raises(ConfigurationError, match="missing.json"):
            await _engine(ScriptedAdapter([]), path, resume=True).run()

    @pytest.mark.asyncio
    async def test_different_initial_candidate(self, tmp_path: Path) -> None:
        """A checkpoint from another seed candidate is refused."""
        path = tmp_path / "checkpoint.json"
        await _engine(ScriptedAdapter(["worse"]), path, max_iterations=1).run()

        with pytest.raises(ConfigurationError, match="initial candidate"):
            await _engine(
                ScriptedAdapter([]), path, resume=True, seed_text="other"
            ).run()

    @pytest.mark.asyncio
    async def test_different_trainset_size(self, tmp_path: Path) -> None:
        """A checkpoint from a different trainset size is refused."""
        path = tmp_path / "checkpoint.json"
        await _engine(ScriptedAdapter(["worse"]), path, max_iterations=1).run()

        with pytest.raises(ConfigurationError, match="trainset"):
            await _engine(
                ScriptedAdapter([]), path, resume=True, trainset=_trainset(5)
            ).run()

    @pytest.mark.asyncio
    async def test_different_valset_size(self, tmp_path: Path) -> None:
        """A checkpoint from a run with another valset size is refused."""
        path = tmp_path / "checkpoint.json"
        valset = [{"input": "v0"}, {"input": "v1"}]
        await _engine(ScriptedAdapter(["worse"]), path, max_iterations=1).run()

        with pytest.raises(ConfigurationError, match="valset"):
            await _engine(ScriptedAdapter([]), path, resume=True, valset=valset).run()

    @pytest.mark.asyncio
    async def test_unknown_version(self, tmp_path: Path) -> None:
        """A checkpoint with a newer version is refused."""
        path = tmp_path / "checkpoint.json"
        await _engine(ScriptedAdapter(["worse"]), path, max_iterations=1).run()
        data = json.loads(path.read_text(encoding="utf-8"))
        data["checkpoint_version"] = 99
        path.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ConfigurationError, match="version"):
            await _engine(ScriptedAdapter([]), path, resume=True).run()


class TestTrajectorySerialization:
    """Domain trajectories round-trip through to_dict/from_dict.

    Examples:
        ```bash
        uv run pytest "tests/unit/engine/test_checkpoint_resume.py::TestTrajectorySerialization" -q
        ```
    """

    def test_adk_trajectory_round_trip(self) -> None:
        """ADKTrajectory with tool calls, deltas and usage survives a JSON round trip."""
        from gepa_adk.domain.trajectory import (
            ADKTrajectory,
            TokenUsage,
            ToolCallRecord,
        )

        trajectory = ADKTrajectory(
            tool_calls=(
                ToolCallRecord(
                    name="ask_ü", arguments={"q": "x"}, result={"a": 1}, timestamp=1.5
                ),
            ),
            state_deltas=({"k": "v"},),
            token_usage=TokenUsage(input_tokens=3, output_tokens=5, total_tokens=8),
            final_output="done",
            error=None,
        )
        data = json.loads(json.dumps(trajectory.to_dict()))
        assert ADKTrajectory.from_dict(data) == trajectory

    def test_multi_agent_trajectory_round_trip(self) -> None:
        """MultiAgentTrajectory nests ADKTrajectory per agent and survives."""
        from gepa_adk.domain.trajectory import (
            ADKTrajectory,
            MultiAgentTrajectory,
            TokenUsage,
        )

        inner = ADKTrajectory(
            tool_calls=(),
            state_deltas=(),
            token_usage=None,
            final_output="o",
            error="e",
        )
        trajectory = MultiAgentTrajectory(
            agent_trajectories={"a": inner},
            pipeline_output="p",
            total_token_usage=TokenUsage(1, 2, 3),
            error=None,
        )
        data = json.loads(json.dumps(trajectory.to_dict()))
        assert MultiAgentTrajectory.from_dict(data) == trajectory
