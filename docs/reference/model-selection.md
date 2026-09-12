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

ADK's `LLMRegistry` recognizes only a subset of LiteLLM providers, so a bare
`"ollama_chat/..."` string handed to `LlmAgent` fails with "Model not found".
Wrap it:

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

agent = LlmAgent(
    name="helper",
    model=LiteLlm(model="ollama_chat/gpt-oss:20b"),
    instruction="Be helpful.",
)
```

Wrapping is required for every agent you construct. `evolve()`,
`evolve_group()`, and `evolve_workflow()` take `LlmAgent` objects, not model
strings, and use each agent's `model` field verbatim — a bare
`"ollama_chat/..."` string there raises "Model not found".

One string is handled for you:
[`EvolutionConfig.reflection_model`][gepa_adk.domain.models.EvolutionConfig].
It routes through `_resolve_model_for_agent`, which returns Gemini and Vertex AI
identifiers unchanged and wraps everything else in `LiteLlm`.

## Surfaces that still require a Gemini model

Three places name a current Gemini model rather than an open one, because an
open model genuinely does not work there:

- **`create_text_reflection_agent`, `create_schema_reflection_agent`,
  `create_config_reflection_agent`, `get_reflection_agent`** — these take
  `model: str` and pass it to `LlmAgent` unchanged, with no wrapping step. Only
  ADK-native identifiers work. Use `EvolutionConfig.reflection_model` to reflect
  with an open model.
- **`AgentProvider` configs** — a serialized config (JSON, YAML) can carry only a
  model string, and a LiteLLM-backed model needs a `LiteLlm` object that does not
  serialize.
- **Video and other multimodal input** (see `examples/video_transcription_evolution.py`)
  — the Ollama models above are text-only.

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
