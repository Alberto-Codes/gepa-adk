# Model Selection

Which model identifiers this project's documentation, examples, and tests use —
and why they differ by surface.

## Convention

**Docs, examples, and docstrings default to local open-source models.** A vendor
can retire a hosted model out from under a published example; an open-weight
model served locally cannot be. Every example that works with a local model names
one, so the docs stop rotting with each hosted model generation.

The two models the project standardizes on, both already required by
[Getting Started](../getting-started.md):

| Identifier | Where it appears | Reached via |
|---|---|---|
| `ollama_chat/llama3.2:latest` | docs prose and code blocks | LiteLLM → local Ollama |
| `ollama_chat/gpt-oss:20b` | `examples/`, `src/` docstrings, and the default [`EvolutionConfig.reflection_model`][gepa_adk.domain.models.EvolutionConfig] | LiteLLM → local Ollama |

Pull them before running anything:

```bash
ollama pull llama3.2:latest
ollama pull gpt-oss:20b
```

## Passing an open model to an agent

Docs and examples here wrap open models in `LiteLlm`:

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

agent = LlmAgent(
    name="helper",
    model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
    instruction="Be helpful.",
)
```

The wrapper is not the only route. ADK's `LLMRegistry` maps common
`provider/model` prefixes — `ollama_chat/` among them — to LiteLLM, and
`litellm` is a required dependency of this project, so
`model="ollama_chat/gpt-oss:20b"` resolves to the same `LiteLlm` model. How far
past those common prefixes the registry reaches varies by `google-adk` version,
so the docs wrap explicitly: it names the transport at the call site instead of
depending on the registry.

`evolve()`, `evolve_group()`, and `evolve_workflow()` take `LlmAgent` objects,
not model strings, and use each agent's `model` field verbatim — whichever form
you built the agent with is the one they run.

One string is resolved rather than passed through:
[`EvolutionConfig.reflection_model`][gepa_adk.domain.models.EvolutionConfig]
goes to `_resolve_model_for_agent`, which returns Gemini and Vertex AI
identifiers unchanged and wraps every other provider in `LiteLlm`. A `BaseLlm`
instance (for example `LiteLlm(model=..., api_base=...)`) given instead of a
string is passed through unchanged. That
describes what the code does today, not which parameter to reach for — the
field carries a deprecation notice in
[Customizing Reflection Prompts](../guides/reflection-prompts.md), and whether
it is still slated for removal in favour of `reflection_agent` is an open
question tracked in
[Issue #363](https://github.com/Alberto-Codes/gepa-adk/issues/363).

## Surfaces that still name a Gemini model

**Video and other multimodal input** (see
`examples/video_transcription_evolution.py`) needs a Gemini model: the two
Ollama models above are text-only.

Two more surfaces carry a current Gemini identifier in their examples because
they take a model *string* rather than a model object — the reflection-agent
factories (`create_text_reflection_agent`, `create_schema_reflection_agent`,
`create_config_reflection_agent`, `get_reflection_agent`) and the `AgentProvider`
configs in [Extending Agent Providers](../contributing/extending-providers.md).
A string is not a Gemini-only restriction: an `"ollama_chat/..."` identifier
works on both, resolved to LiteLLM by the registry as described above.

## Keeping the Gemini references current

Google publishes shutdown dates on the
[Gemini API deprecations page](https://ai.google.dev/gemini-api/docs/deprecations).
When a generation is retired:

1. Update `GEMINI_TEST_MODEL` in `tests/fixtures/models.py`. It is the single
   model the `requires_gemini` test tier and its availability probe in
   `tests/conftest.py` use — the probe and the tests must never drift apart, or a
   retired model would make the probe fail and silently skip the whole tier.
2. Add the retired generation's prefix to `DEPRECATED_GEMINI_PREFIXES` in the
   same file. It is the single deprecation rule — the guard tests in
   `tests/unit/test_resolve_model_for_agent.py` then fail for anything still
   pointing at that generation, including the default reflection model.
3. Sweep every Gemini-only surface that hardcodes the identifier. No guard test
   covers these, and steps 1 and 2 alone leave them failing at call time with a
   model-not-found error. **A repo-wide search for the retired identifier is the
   authoritative check** — the following are examples, not the full set:
   `examples/video_transcription_evolution.py`, the reflection-agent factories
   and docstring examples in `src/gepa_adk/adapters/agents/`, the
   `_resolve_model_for_agent` docstring in `src/gepa_adk/api.py`, the
   `AgentProvider` config examples in
   `docs/contributing/extending-providers.md`, and
   `docs/adr/ADR-005-three-layer-testing.md`.

   That search also matches two categories that never need changing. Searching
   for every prefix in `DEPRECATED_GEMINI_PREFIXES` returns 166 hits at the time
   of writing: 148 across 57 per-feature design records under `specs/`,
   deliberately frozen so they record decisions as they were made, and the
   remaining 18 in `tests/`, which have to name retired generations in order to
   guard against them — the denylist itself, the `is_deprecated_gemini_model`
   docstring examples, and the parametrized guard cases in
   `tests/unit/test_resolve_model_for_agent.py`. What needs editing is the
   executable and docstring surfaces a user copies from.
