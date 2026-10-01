"""Selection strategies for evolution candidates, components, and evaluation.

Contains candidate selection (Pareto, greedy, epsilon-greedy), component selection
(round-robin, all), and evaluation policy (full, subset) implementations.

Anticipated growth: tournament selection, adaptive selection strategies,
custom evaluation scheduling.

Attributes:
    ParetoCandidateSelector (class): Pareto frontier sampling selector.
    CurrentBestCandidateSelector (class): Greedy best-average selector.
    EpsilonGreedyCandidateSelector (class): Epsilon-greedy exploration selector.
    create_candidate_selector (function): Factory for candidate selectors.
    RoundRobinComponentSelector (class): Cycles through components sequentially.
    AllComponentSelector (class): Selects all components every time.
    create_component_selector (function): Factory for component selectors.
    FullEvaluationPolicy (class): Scores all validation examples every iteration.
    SubsetEvaluationPolicy (class): Scores a configurable subset with round-robin coverage.

Examples:
    Create a candidate selector using the factory:

    ```python
    from gepa_adk.adapters.selection import create_candidate_selector

    selector = create_candidate_selector("pareto")
    ```

    Use a component selector and evaluation policy:

    ```python
    from gepa_adk.adapters.selection import (
        RoundRobinComponentSelector,
        SubsetEvaluationPolicy,
    )

    component_selector = RoundRobinComponentSelector()
    eval_policy = SubsetEvaluationPolicy(subset_size=5)
    ```

See Also:
    - [`gepa_adk.adapters`][gepa_adk.adapters]: Parent adapter layer re-exports.
    - [`gepa_adk.ports.candidate_selector`][gepa_adk.ports.candidate_selector]:
        CandidateSelectorProtocol that candidate selectors implement.
    - [`gepa_adk.ports.component_selector`][gepa_adk.ports.component_selector]:
        ComponentSelectorProtocol that component selectors implement.
    - [`gepa_adk.ports.evaluation_policy`][gepa_adk.ports.evaluation_policy]:
        EvaluationPolicyProtocol that evaluation policies implement.

Notes:
    This package unifies candidate, component, and evaluation selection strategies.
"""

from gepa_adk.adapters.selection.candidate_selector import (
    CurrentBestCandidateSelector,
    EpsilonGreedyCandidateSelector,
    ParetoCandidateSelector,
    create_candidate_selector,
)
from gepa_adk.adapters.selection.component_selector import (
    AllComponentSelector,
    RoundRobinComponentSelector,
    create_component_selector,
)
from gepa_adk.adapters.selection.evaluation_policy import (
    FullEvaluationPolicy,
    SubsetEvaluationPolicy,
)

__all__ = [
    "AllComponentSelector",
    "CurrentBestCandidateSelector",
    "EpsilonGreedyCandidateSelector",
    "FullEvaluationPolicy",
    "ParetoCandidateSelector",
    "RoundRobinComponentSelector",
    "SubsetEvaluationPolicy",
    "create_candidate_selector",
    "create_component_selector",
]
