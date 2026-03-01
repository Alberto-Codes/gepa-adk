---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
classification:
  projectType: 'Developer Tool (Framework Extension Library)'
  domain: 'AI/ML Developer Infrastructure'
  complexity: 'Medium-High'
  projectContext: 'Brownfield'
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-gepa-adk-2026-03-01.md'
  - '_bmad-output/planning-artifacts/research/market-automated-prompt-optimization-research-2026-03-01.md'
  - '_bmad-output/planning-artifacts/research/domain-evolutionary-automated-prompt-optimization-research-2026-03-01.md'
  - '_bmad-output/planning-artifacts/research/technical-hybrid-prompt-optimization-research-2026-03-01.md'
  - '_bmad-output/project-context.md'
  - 'docs/index.md'
  - 'docs/getting-started.md'
  - 'docs/project-management.md'
  - 'docs/concepts/index.md'
  - 'docs/concepts/gepa-fundamentals.md'
  - 'docs/concepts/single-agent-evolution.md'
  - 'docs/concepts/multi-agent-evolution.md'
  - 'docs/concepts/workflow-agents.md'
  - 'docs/guides/single-agent.md'
  - 'docs/guides/multi-agent.md'
  - 'docs/guides/critic-agents.md'
  - 'docs/guides/reflection-prompts.md'
  - 'docs/guides/stoppers.md'
  - 'docs/guides/workflows.md'
  - 'docs/reference/glossary.md'
  - 'docs/reference/index.md'
  - 'docs/adr/index.md'
  - 'docs/adr/ADR-000-hexagonal-architecture.md'
  - 'docs/proposals/001-initial-package-proposal.md'
  - 'docs/contributing/docstring-templates.md'
  - 'docs/contributing/releasing.md'
documentCounts:
  briefs: 1
  research: 3
  brainstorming: 0
  projectDocs: 22
workflowType: 'prd'
---

# Product Requirements Document - gepa-adk

**Author:** Alberto-Codes
**Date:** 2026-03-01
**Status:** Draft — pending final review
**Sections:** 11
**FRs:** 41 (35 MVP, 4 Growth, 2 Vision)
**NFRs:** 16

## Executive Summary

There is no systematic, automated way to improve multi-agent AI systems after deployment. As agent pipelines grow — multiple agents with interconnected instructions, structured outputs, and configuration parameters — the entanglement problem emerges: improving one agent silently degrades downstream behavior because agents depend on each other's outputs through shared session state. The combinatorial explosion of N agents x M components x K parameters creates a search space no human can navigate, and no existing tool addresses.

Evolution doesn't just improve your agents — it reveals what was actually holding them back.

gepa-adk automates this by evolving the complete agent definition — instruction, output schema, and generation configuration — across multi-agent workflows simultaneously. Built on the GEPA (Genetic-Pareto) algorithm and Google's Agent Development Kit, it provides a progressive API: `evolve()` for single agents, `evolve_group()` for multi-agent pipelines, and `evolve_workflow()` for complex workflow structures. The architecture is designed to expand to model selection and additional surfaces through its Protocol-based ComponentHandler interface. Every evolutionary decision is captured in ADK session events, producing audit-grade trails queryable via structured logging or ADK's database session persistence.

The core engine is shipped and published on PyPI; the MVP is a credibility sprint focused on enterprise packaging and positioning (see Project Scoping & Phased Development).

The core insight: instruction optimization has diminishing returns when the output schema constrains the agent's output space or the generation config misaligns with the task. In multi-surface evolution runs, the highest-impact mutation is frequently on a non-instruction component — a schema field the developer didn't know to question, a temperature setting silently degrading quality. Current instruction-only optimizers (DSPy, TextGrad, EvoPrompt, PromptBreeder) cannot produce this result.

### What Makes This Special

**Multi-surface discovery from the first API call.** This is the category-defining differentiator. Even at `evolve()`, gepa-adk evolves instruction, output schema, and generation config simultaneously. When evolution discovers the schema was the bottleneck — not the instruction — that's a result no instruction-only optimizer can produce. DSPy, TextGrad, EvoPrompt, and PromptBreeder all treat the prompt as the single evolvable gene. gepa-adk treats the complete agent definition as the genotype.

Supporting this lead differentiator:

- **Workflow-aware topology preservation.** `evolve_workflow()` recursively clones SequentialAgent, LoopAgent, and ParallelAgent structures while applying instruction overrides. The workflow executes with its original semantics intact — loop iterations, parallel concurrency, agent ordering. No competitor understands workflow structure; this requires deep ADK integration that cannot be bolted on.

- **Enterprise audit-grade observability.** Every evolutionary decision has a trail: which component was evolved, what the reflection agent proposed, whether the mutation was accepted, and why. ADK session events + structlog produce platform-agnostic output ready for Splunk, Arize/Phoenix, Datadog, or any log aggregator. The Pareto frontier surfaces cost/quality/latency tradeoffs as a decision surface, not a single "best" answer.

- **Progressive API as land-and-expand.** The API design itself is the adoption funnel: `evolve()` delivers value on day one with zero configuration. `evolve_group()` addresses multi-agent entanglement as teams scale. `evolve_workflow()` optimizes complex structures across the organization. Each step deeper increases value delivered and cost of switching away.

## Project Classification

| Dimension | Classification |
|-----------|---------------|
| **Project Type** | Developer Tool (Framework Extension Library) |
| **Domain** | AI/ML Developer Infrastructure |
| **Complexity** | Medium-High |
| **Project Context** | Brownfield — core engine shipped, published on PyPI, 85%+ coverage with contract tests for every Protocol |

## Success Criteria

*Discovery drives trust, trust drives adoption, adoption proves the architecture.*

### User Success

**Multi-surface discovery changes how developers think about their agents.** When evolution discovers that the output schema — not the instruction — was the bottleneck, the developer gains an insight no amount of manual prompt engineering would have produced. Success is measured by users who experience this and return for more: users who run multiple evolution cycles exploring different surfaces, rather than treating evolution as a one-shot optimization. The discovery mechanism is validated against three reference scenarios: an over-constrained schema bottleneck, a misaligned temperature/config bottleneck, and a verbose instruction that is the actual bottleneck — proving the engine finds the *real* constraint, whichever component it is.

**First evolution delivers undeniable value.** A developer with no prior gepa-adk experience runs `pip install gepa-adk`, configures a scorer, calls `evolve()`, and sees measurable improvement — all within 15 minutes. The getting-started path requires zero ADK expertise beyond having an existing agent.

**Evolution explains itself.** After every run, the developer understands *why* evolution made each change — which component was mutated, what the reflection agent proposed, and whether the mutation improved or degraded quality. The audit trail is a trust-building mechanism, not a compliance checkbox. Users who trust the explanations go deeper; users who don't, stop at one run.

**Progressive API adoption feels natural.** Developers who start with `evolve()` encounter real multi-agent entanglement problems and reach for `evolve_group()` because the API was already there, not because they were upsold. The transition from single-agent to multi-agent evolution should feel like a natural expansion of capability, not a learning cliff. Qualitative signal: users who transition to `evolve_group()` do not need to re-read the getting-started guide — the documentation scaffolds the transition, not restarts it. Failure signal: users who attempt `evolve_group()` and revert to individual `evolve()` calls.

*When discovery produces trust, users stay. When they stay, they expand.*

### Business Success

**3 months — "The tool works, and people are getting value."**
- First external users report measurable improvement on their own agents (not maintainer-authored examples)
- Getting-started experience validated under 15 minutes on enterprise ADK versions
- Workflow evolution epic complete
- Early adopters providing feedback through GitHub issues and discussions
- 500+ monthly PyPI downloads confirming awareness is growing

**6 months — "Platform teams are evaluating."**
- 5+ published case studies demonstrating multi-surface discovery value
- First enterprise teams evaluating for production use
- Multi-agent and workflow documentation complete with real-world pipeline tutorials
- 2,000+ monthly PyPI downloads
- Community forming around ADK agent optimization

**12 months — "Category = brand."**
- Multiple organizations using in production
- Model selection evolution shipped (4th evolvable surface, proving ComponentHandler extensibility)
- 10,000+ monthly PyPI downloads
- Category recognition: when someone needs ADK agent optimization, gepa-adk is the default answer

**Progressive API adoption as strategic metric.** The land-and-expand strategy succeeds when users who started with `evolve()` adopt `evolve_group()` within 90 days. This is the single strongest signal that the product delivers compounding value beyond one-shot optimization — and that switching costs are real.

**North Star:** "When someone says 'I need to optimize my ADK agents,' the first thing they reach for is gepa-adk." Measured by: search volume, Stack Overflow mentions, ADK community references, and organic inbound from developers who heard about it from peers.

*When adoption scales, it stress-tests the architecture. The architecture must hold.*

### Technical Success

**Extensibility without core changes.** A new evolvable surface (e.g., model selection) ships by implementing the `ComponentHandler` Protocol and registering it — zero modifications to the core evolution engine. If an external contributor needs to modify core code to add a handler, the hexagonal architecture promise is broken.

**Reproducibility and serializability.** Given the same seed, agents, scorer, and reflection model, the evolutionary decisions — which component to mutate, which candidates to keep, Pareto frontier state — are deterministic. Beyond determinism, the decision trace is serializable as a replayable artifact: exportable as JSON and replayable against a new agent version. The audit trail is not just a log — it's a reproducible experiment record.

**Session isolation.** Two concurrent evolution runs with different ADK session IDs never interfere. Shared state patterns in ADK make this non-trivial; it requires an explicit guarantee.

**Performance proportionality.** Evolution wall-clock time scales linearly with population size x generations x pipeline execution time, with no hidden superlinear overhead from the evolution engine itself. The engine's overhead is negligible compared to LLM inference costs — evolution is cheap, LLM calls are expensive. This is the architectural promise that makes multi-agent evolution practical at enterprise scale.

### Measurable Outcomes

**Tier 1 — Automated, CI-Enforced** *(verified on every commit)*

| Metric | Target | Verification |
|--------|--------|-------------|
| Evolution success rate | >80% of runs show score increase | Integration test suite |
| Reliability | 99%+ completion rate for shipped features | CI/CD + error tracking |
| Contract test coverage | 100% Protocol coverage maintained | CI enforcement |
| Test coverage floor | 85%+ maintained, trending upward | CI enforcement |
| Multi-surface discovery | Engine finds actual bottleneck across 3 reference scenarios (schema, config, instruction) | Dedicated integration test suite |

**Tier 2 — Manual Validation, Periodic** *(verified at release milestones)*

| Metric | Target | Verification |
|--------|--------|-------------|
| Score improvement magnitude | >15% average improvement per run | Benchmark suite across reference agents |
| Time to first evolution | <15 minutes from pip install | Getting-started validation at each release |
| Explainability | Users can trace any evolutionary decision from audit log | UX validation of structured log output |
| Progressive API transition | Users of `evolve()` adopt `evolve_group()` without re-reading getting-started guide | Documentation review + user feedback |

**Tier 3 — Ecosystem, Tracked Quarterly** *(reviewed at planning cadence)*

| Metric | 3-Month | 6-Month | 12-Month | Tracking |
|--------|---------|---------|----------|----------|
| Monthly PyPI downloads | 500+ | 2,000+ | 10,000+ | PyPI stats |
| External GitHub engagement | 5+ issues/discussions | 20+ | 100+ | GitHub insights |
| Published case studies | 1 | 5 | 20+ | Content tracking |
| Progressive adoption rate | Baseline | Measurable trend | Target established | Opt-in telemetry or case studies |
| External contributions | First external issue | First external PR merged | 5+ contributors | GitHub insights |

## Product Scope

### MVP — Minimum Viable Product

The MVP is a **positioning and maturity sprint**, not a feature sprint. The core evolution engine is shipped, tested (85%+ coverage), and published on PyPI. The actual engineering work is narrow; the majority of MVP effort is documentation and positioning.

**Technical scope — SHIPPED** ✅
1. `evolve()` for single-agent evolution across 3 surfaces (instruction, output_schema, generate_content_config)
2. `evolve_group()` for multi-agent pipeline evolution addressing the entanglement problem
3. `evolve_workflow()` preserving SequentialAgent, LoopAgent, and ParallelAgent topology
4. Critic agents (SimpleCriticOutput + CriticOutput) for structured evaluation
5. Reflection agents (LiteLLM + ADK-based) with component-aware specialization
6. Pareto frontier tracking for multi-objective optimization
7. Structured logging via structlog for platform-agnostic observability

**Technical scope — ENGINEERING WORK** 🔧
8. ADK version compatibility — widen supported version range, test against enterprise-deployed versions, fix any API drift

**Packaging and positioning scope — DOCUMENTATION WORK** 📝
9. Enterprise architecture documentation — why hexagonal matters, how Protocols enable extension, how sessions provide audit trails
10. Enterprise observability guide — PostgreSQL session persistence, structured logging to Splunk/Arize/Phoenix/Datadog
11. Getting-started experience validated under 15 minutes on enterprise ADK versions
12. All examples validated and running cleanly on supported ADK version range
13. C-Suite positioning: prompt, context, and intent engineering automation at scale with audit trails
14. Competitive differentiation documentation: multi-surface discovery as category-defining capability

For MVP shipping order, time estimates, and risk analysis, see Project Scoping & Phased Development.

**MVP Exit Criteria:** See Project Scoping & Phased Development for the definitive exit criteria, which include the CI engineering gate (all 16 example smoke tests pass on supported ADK version range) in addition to the persona-based criteria below:
- Rafael can pitch it internally
- Marcus can integrate it
- Priya runs it in 15 minutes
- Kenji sees the trajectory
- Still alone in the pool

### Growth Features (Post-MVP)

See Project Scoping & Phased Development: Post-MVP Features for the expanded Growth roadmap with 8 features, measurable triggers, and value justification.

### Vision (Future)

gepa-adk makes agent quality a **measurable, improvable organizational capability.** Today, agent quality is artisanal — it depends on who wrote the prompt. gepa-adk makes it *engineered* — it depends on systematic evolution with provable outcomes. That's the transformation that gets budget at the C-suite level: agent quality as an engineering discipline, not a craft.

The features that deliver this vision:

- **Complete agent genotype evolution** — all 7 surfaces evolved simultaneously
- **Fleet-level optimization dashboards** — organizational view across thousands of use cases
- **Framework expansion** — Protocol-based adapters for LangChain, CrewAI, AutoGen beyond ADK
- **Community marketplace** — community-contributed ComponentHandlers, Scorers, Critics, Stoppers
- **Enterprise deployment playbook** — compliance frameworks for regulated industries

The progression: **craft tool → enterprise platform → industry standard.**

## User Journeys

### Journey 1: Priya — "The Revelation"

**Persona:** Priya, mid-level software engineer building individual agents for specific automation use cases. Technically capable but not an ML specialist. She's a producer in the agent factory.

**Opening Scene.** Priya has spent three days tuning the instruction for a document classification agent. She's rewritten it eleven times. The score hovers at 0.52 — better than the naive version but nowhere near the 0.8 her team lead expects. She's tried few-shot examples, chain-of-thought prompting, output formatting instructions. Nothing moves the needle past 0.55. She knows the agent *should* be better but has no systematic path from "works okay" to "works great." She's been asked to build 50 agents next quarter. At this rate, that math doesn't work.

**Rising Action.** A colleague mentions gepa-adk. Priya runs `pip install gepa-adk`, writes a simple scorer that checks classification accuracy against a labeled dataset, and calls `evolve(agent, trainset, scorer=scorer)`. The call returns an evolution result — a final evolved agent definition with the full generation history logged. She opens the structured log to review what happened across generations.

**Climax.** Best score: 0.83, up from 0.52. Priya expects a better instruction — maybe a clever rephrasing she didn't think of. Instead, the per-component mutation attribution in the log shows: `highest_impact_mutation: output_schema`. Evolution discovered that her Pydantic output schema was over-constraining the agent's output space — a required `confidence_score` field with a tight value range was forcing the model to hedge its classifications. The instruction she spent three days perfecting was fine. The schema she copied from a template without questioning was the bottleneck. She never would have found this manually.

**Resolution.** Priya examines the evolved agent definition — a diff showing the original vs. evolved schema with the constraint relaxed and the instruction barely changed. She ships the evolved agent in an afternoon instead of a week. Her throughput changes: instead of hand-tuning each agent, she builds the skeleton, writes a critic, runs evolution, and moves to the next use case. Three weeks later, she's shipped eight agents. But the deeper shift is how she thinks about agent design: she now treats the complete agent definition — instruction, schema, config — as a system to be evolved, not a prompt to be perfected. She wonders what would happen if she ran evolution on her best-performing agent — the one she thought was already optimal.

**Capabilities Revealed:** Getting-started flow (<15 min), scorer configuration, single-agent evolution, per-component mutation attribution in structured logs, evolved agent definition output with diff view.

---

### Journey 2: Marcus — "The Untangler"

**Persona:** Marcus, senior platform engineer building agent infrastructure at an enterprise. He designs multi-agent workflow templates — intake → process → validate → output — that different use cases plug into.

**Opening Scene.** Marcus has a 4-agent loan processing pipeline: document intake, data extraction, compliance check, decision output. The pipeline scores 0.61 end-to-end. He improves the data extraction agent's instruction — score jumps to 0.68. Two days later, the compliance team reports the compliance check agent is now failing edge cases. Marcus traces the problem: the improved extraction agent produces subtly different output semantics, and the compliance agent's instruction assumed the old phrasing. He's spent three sprints chasing entanglement bugs like this. Improving one agent silently degrades another because they depend on each other's outputs through shared session state.

**Rising Action.** Marcus configures `evolve_group()` with all four agents, their individual scorers, and the end-to-end pipeline scorer. Evolution runs with round-robin agent selection — each generation, a different agent is the mutation target. He reviews the per-agent scores in the structured log after each generation: extraction improves in generation 2, but compliance dips. In generation 4, evolution mutates the compliance agent's instruction to handle the new extraction semantics. Both scores rise together.

**Climax.** Generation 8 finishes. End-to-end score: 0.84. Marcus checks the per-agent breakdown: every agent improved or held steady. No regression anywhere. The Pareto frontier shows three candidate pipelines with different cost/quality profiles. But the real revelation is in the mutation log: evolution discovered that the compliance agent's `generate_content_config` had `temperature: 0.9` — far too high for a compliance task. Marcus set it months ago during prototyping and never revisited it. Evolution reduced it to a value below 0.3 through bounded mutation, and compliance accuracy jumped. The entanglement problem was real, but the *hidden* problem was a config parameter nobody was looking at.

**Resolution.** Marcus embeds `evolve_workflow()` into the platform's deployment pipeline. New workflow templates go through evolution as part of CI before deployment. The entanglement problem is no longer a sprint-killer — evolution handles co-optimization across agents automatically. He writes the internal wiki page: "Stop hand-tuning pipelines. Let evolution find what you're missing."

**Capabilities Revealed:** Multi-agent group evolution, round-robin agent selection, per-agent score tracking in structured logs*, workflow topology preservation (`evolve_workflow()`), cross-agent entanglement resolution, config parameter discovery in multi-agent context.

*\*Per-agent score visibility during `evolve_group()` runs is a requirement surfaced by this journey — validate against current structured log output.*

---

### Journey 3: Rafael + Kenji — "The Evidence"

**Persona:** Rafael, Principal Engineer and AI Platform Lead at a large regulated enterprise. Kenji, ML/AI Platform Lead responsible for agent quality across the organization.

**Opening Scene — Rafael.** Rafael's CTO demo was a triumph: a tools-enabled agent that processes insurance claims with 94% accuracy. The CTO greenlights scaling to 200 automation use cases. Six months later, 200 agents are in production. Some are excellent. Some are limping. Nobody knows which. When the compliance team asks "how did you validate this agent's behavior?", Rafael's honest answer is: "a senior engineer tweaked it until it seemed right." That answer won't survive an audit. He needs systematic optimization with evidence.

Rafael evaluates alternatives. DSPy optimizes single-agent prompts but can't handle his multi-agent pipelines — it has zero support for evolving agents within workflow structures. TextGrad and EvoPrompt are instruction-only optimizers — they can't touch output schemas or generation configs, the surfaces where his team's hidden problems live. Manual optimization campaigns with spreadsheets have already failed to scale past 20 agents. He needs something that evolves complete agent definitions across multi-agent workflows with an audit trail.

**Rising Action — Rafael evaluates.** Rafael has Marcus run `evolve()` on three underperforming agents as a proof of concept. All three improve — one by 30%. The structured logs capture every evolutionary decision: which component was mutated, what the reflection agent proposed, whether the mutation was accepted, and why. Rafael opens the ADK session data and sees the audit trail: timestamped, queryable, exportable. He writes the evaluation memo: "This tool produces the audit evidence our compliance team has been asking for."

**Climax — Kenji operationalizes.** Kenji runs the first fleet-wide optimization campaign across 50 agents using batch evolution. The Pareto frontier across the fleet reveals a pattern: evolution discovered that 8 agents had over-specified temperature settings — configurations copied from prototyping that were far too high for their production tasks. Reducing them saved 15% on token costs with no quality loss. He builds a dashboard on the Pareto data and presents it to the CTO. The CTO stops asking "are our agents good enough?" and starts asking "which quality/cost configuration fits our Q3 budget?" It's the first data-driven agent optimization decision the organization has ever made.

**Resolution.** Evolution becomes part of the enterprise agent lifecycle: build → evolve → audit → deploy → monitor → re-evolve. Kenji reports quarterly on fleet-wide quality trends. Rafael's compliance answer changes from "a senior engineer tweaked it" to "every agent went through automated optimization with session-level evidence of every decision, queryable in our observability platform." The auditors are satisfied. The integration took two sprints to connect session persistence with the enterprise observability stack. But the first compliance review that went smoothly justified the investment. The CTO asks: "Can we do this for the other 300 use cases?"

**Capabilities Revealed:** Audit-grade session event trails, configurable session persistence for enterprise databases, Pareto frontier visualization and export, fleet-wide batch evolution patterns, cost/quality/latency tradeoff analysis, structured logging to enterprise observability platforms (Splunk, Arize/Phoenix, Datadog), regulatory evidence generation.

---

### Journey 4: Failure Recovery — "The Diagnostic"

**Persona:** Any developer (could be Priya, could be Marcus). The product must be intelligent when things go wrong, not just when they go right.

#### Scenario A: Evolution Stalls

**Opening Scene.** A developer runs `evolve()` on a sentiment analysis agent. After 8 generations, the score hasn't moved: 0.62, 0.61, 0.63, 0.62, 0.61, 0.63, 0.62, 0.62. The developer stares at a flat curve and doesn't know what's wrong. Is the agent already optimal? Is evolution broken? Is the scorer wrong?

**Rising Action.** The evolution result summary — the first thing she sees, not buried in verbose logs — highlights the diagnostic findings:
- **Mutation diversity:** All 8 generations mutated the instruction. The component selector never chose output_schema or generate_content_config because the reflection agent scored instruction mutations highest. But the instruction mutations aren't producing improvement — they're semantic paraphrases, not structural changes.
- **Scorer signal analysis:** The scorer produces scores clustered between 0.58 and 0.65 for meaningfully different outputs. The scorer can't distinguish between "okay" and "good" — it only distinguishes "bad" from "not bad."

**Climax.** The evolution result summary surfaces: "Scorer discrimination is low — 87% of candidates score within 0.05 of each other. Consider a more discriminative critic that evaluates specific quality dimensions." The developer realizes: the problem isn't the agent or the evolution engine. The *scorer* was too coarse. She rewrites the scorer to evaluate three dimensions (accuracy, tone, completeness) instead of a single aggregate score. Next evolution run: score jumps from 0.62 to 0.81 in 4 generations.

**Resolution.** The developer learned something valuable even from a failed run: her evaluation methodology was the bottleneck, not her agent. Evolution didn't just fail gracefully — it *diagnosed* why it failed and pointed to the fix. The diagnostic intelligence is the feature: a dumb optimizer would have said "no improvement found" and left her stranded. gepa-adk told her *where to look next.*

#### Scenario B: Multi-Agent Regression

**Opening Scene.** Marcus runs `evolve_group()` on a 3-agent pipeline. After generation 3, the aggregate score drops from 0.72 to 0.65. One agent improved, but two others degraded. The entanglement problem is happening *during evolution*.

**Rising Action.** Marcus checks the per-agent score breakdown in the evolution log:
- Agent A (data extraction): 0.80 → 0.88 (improved)
- Agent B (validation): 0.75 → 0.61 (regressed)
- Agent C (formatting): 0.70 → 0.58 (regressed)

The mutation log shows: generation 3 mutated Agent A's output schema, modifying a field constraint. Agents B and C downstream were sensitive to the semantic change. The Pareto frontier tracked the tradeoff — the candidate with Agent A improved but aggregate worse was recorded, not silently discarded.

**Climax.** The evolution engine's Pareto dominance selection identifies the regression: the candidate with the schema mutation is Pareto-dominated (better on one dimension, worse on aggregate). Dominated candidates are preserved in the frontier for analysis but not selected as parents for the next generation. Evolution explores an alternative path. Generation 5 finds it: a config change to Agent A (lower temperature) that improves extraction accuracy without altering the output schema semantics.

**Resolution.** Marcus sees that evolution detected the regression through Pareto dominance, preserved the evidence in the frontier, and self-corrected by exploring alternative mutation paths. The structured log shows the full decision trace: mutation proposed → aggregate regression observed → candidate Pareto-dominated → alternative path explored → improvement without regression found. He trusts the tool more *because* he saw it handle failure intelligently, not because it never failed.

**Capabilities Revealed:** Scorer signal diagnostics in evolution result summary, mutation diversity analysis, per-component selection tracking, per-agent score breakdown in multi-agent evolution, regression detection via Pareto dominance, dominated candidate preservation for analysis, structured diagnostic output for debugging, evolution as a diagnostic instrument (not just an optimizer).

---

### Journey Requirements Summary

| Journey | Primary Capabilities Revealed |
|---------|------------------------------|
| **Priya — "The Revelation"** | Getting-started flow, scorer configuration, single-agent evolution, per-component mutation attribution, evolved definition diff output |
| **Marcus — "The Untangler"** | Multi-agent group/workflow evolution, round-robin selection, per-agent scoring, workflow topology preservation, cross-agent config discovery |
| **Rafael + Kenji — "The Evidence"** | Audit-grade session trails, configurable session persistence, Pareto frontier export, fleet batch evolution, enterprise observability integration |
| **Failure — "The Diagnostic"** | Scorer signal diagnostics in result summary, mutation diversity tracking, Pareto dominance regression detection, per-agent score breakdown, structured diagnostic output |
| **Ecosystem Contributor** *(relocated)* | Extensibility validation — external developer implements a new `ComponentHandler` without modifying core code. See Domain Requirements for full scenario. |

**Cross-Journey Capability Map:**

| Capability | J1 | J2 | J3 | J4 |
|-----------|:--:|:--:|:--:|:--:|
| Single-agent evolution (`evolve()`) | **X** | | o | **X** |
| Multi-agent evolution (`evolve_group()`) | | **X** | o | **X** |
| Workflow evolution (`evolve_workflow()`) | | **X** | | |
| Structured logging / audit trail | o | **X** | **X** | **X** |
| Per-component mutation attribution | **X** | o | | **X** |
| Pareto frontier tracking | | o | **X** | **X** |
| Enterprise observability integration | | | **X** | |
| Diagnostic / failure intelligence | | | | **X** |
| Evolved definition output / diff | **X** | | | |

**X** = primary coverage  **o** = supporting context

## Domain-Specific Requirements

gepa-adk operates at the intersection of evolutionary optimization, LLM agent infrastructure, and enterprise deployment. This intersection creates domain-specific constraints that don't apply to general-purpose software: the search space can be adversarial, the costs are real money, the results must be explainable, and the competitive window is finite.

| Domain Concern | Core Requirement | Business Risk if Unaddressed |
|---|---|---|
| **Adversarial mutation space** | Developer-declared safety invariants, never violated; evolved definitions interpretable and auditable | Compliance failure — evolved agent behavior cannot be certified as safe |
| **LLM API cost** | Pre-execution cost estimation via dry-run mode with developer-provided pricing | Budget overrun — evolution runs consume unpredictable API spend |
| **ADK dependency** | Workflow agent types accessed through adapter, not directly imported in evolution logic | Vendor lock fragility — ADK updates force emergency engineering cycles |
| **Stochastic reproducibility** | Deterministic evolution decisions; stochastic LLM inference acknowledged | Audit failure — cannot prove evolution decisions were systematic, not random |
| **Competitive pace** | New evolvable surface ships in days via ComponentHandler Protocol | Category erosion — competitors replicate surfaces before we extend the lead |
| **Mutation rationale** | Human-readable explanation surfaced for every mutation in structured log | Review bottleneck — domain experts cannot validate evolved agents efficiently |

### Adversarial Mutation Space & Safety Invariants

Evolution mutates instructions (natural language), output schemas (Pydantic models), and generation configs (numeric parameters). Unlike numerical optimization where parameters have natural bounds, the instruction mutation space is adversarial — natural language can express harmful behavior, and unconstrained evolution could produce instructions that enable prompt injection, schemas that leak internal state, or configs that make agents unusable.

**Domain requirement: evolved agent definitions must not violate safety invariants defined by the developer.** The developer declares constraints — required schema fields, instruction boundary patterns, config value ranges — and evolution operates strictly within them. No evolution run should produce a candidate that fails pre-declared invariants, regardless of how many generations run or how high the fitness score.

This safety cage is backed by existing implementation: `SchemaFieldPreservation` (required fields and type compatibility), `StateGuardTokens` (instruction boundary enforcement), and bounded config mutation ranges in `ConfigHandler`. The PRD commitment is the principle: **the mutation space is bounded by developer-declared invariants, enforced as a hard constraint, not a soft preference.**

Additionally, evolved definitions must be **interpretable and auditable**, not just high-scoring. If evolution produces a 2,000-word instruction that scores 0.95 but nobody can review, maintain, or explain to an auditor, it's a liability in regulated industries. Interpretability is quantified: **when two candidates score within 5% of each other, prefer the candidate with shorter instruction length.** The reflection agent should favor concise, clear mutations over verbose, opaque ones when fitness is comparable. This directly supports Rafael's compliance journey — his team needs to *read and understand* what the evolved agent does, not just see that it scores well.

### LLM API Cost Predictability

Each evolution candidate requires agent execution — real LLM inference calls with real costs. A population of 10 x 8 generations x 4 agents = 320 LLM invocations per run. Uncontrolled evolution on a multi-agent pipeline could burn significant API budget before the developer realizes the cost.

**Domain requirement: evolution cost must be predictable before execution begins.** The user needs a cost estimation mode (dry-run) that calculates expected cost from: population size, generation count, average tokens per agent call (input + output), and **developer-provided per-token pricing** for their LLM provider. The estimate should be within 20% of actual cost for stable workloads. Provider pricing is not hardcoded — the developer supplies it as configuration, ensuring estimates remain accurate as providers change rates.

Budget-aware stoppers already exist in the architecture (feature 197). The domain-specific addition is *pre-execution cost estimation* — answering "how much will this cost?" before the first LLM call fires, not just "stop when we've spent too much."

### ADK Framework Dependency Isolation

gepa-adk deeply integrates with Google ADK internal types: `SequentialAgent`, `LoopAgent`, `ParallelAgent`, `LlmAgent`, `BaseAgent`. These types are core to workflow topology preservation and agent cloning during evolution. However, they are not part of a formally versioned public API surface. A minor ADK release could rename a class, change a constructor signature, or restructure the agent hierarchy.

**Domain requirement: ADK workflow agent types are accessed through an adapter, not directly imported in evolution logic.** The hexagonal architecture already provides the pattern — ports and adapters with Protocol-based interfaces. The domain constraint is to apply this pattern specifically for ADK insulation: evolution logic references abstract agent protocols; the adapter translates to concrete ADK types. When ADK releases a breaking change, the fix is a single adapter update, not a multi-file refactor. Testable: grep evolution logic for direct ADK type imports — zero hits outside the adapter module.

This is critical for enterprise adoption. Marcus's platform team cannot depend on a library that breaks with every ADK minor version. ADK version compatibility is a deployment constraint, not just a packaging concern.

### Reproducibility in a Stochastic Domain

Evolution results depend on the underlying LLM's behavior, and LLM outputs are inherently stochastic — the same prompt to the same model at different times produces different outputs. Reproducibility in gepa-adk has a different meaning than in traditional scientific computing.

**Domain requirement: evolution logic is deterministic; LLM inference is acknowledged as stochastic.** Given the same seed, agents, scorer, and reflection model, the evolutionary *decisions* — which component to mutate, which candidates to select, Pareto frontier state updates — are byte-identical across runs when provided with identical fitness scores. The decision trace is a reproducible experiment record. What is NOT reproducible is the LLM output itself, and the system does not pretend otherwise.

This distinction matters for audit trails: Kenji can prove that the evolution engine made consistent decisions, even if re-running the evolution would produce different LLM outputs and therefore potentially different final agents. The audit records *what happened*, not *what would happen again*.

### Competitive Pace: Surface Addition Speed

gepa-adk's competitive advantage depends on being first to multi-surface, workflow-aware evolution. This advantage is temporal — DSPy already integrates GEPA for instruction optimization, and competitors will eventually add schema/config evolution.

**Domain requirement: the architecture must support adding new evolvable surfaces faster than competitors can copy existing ones.** The `ComponentHandler` Protocol is the mechanism. The benchmark: **the first new surface after MVP — model selection evolution via `ModelHandler` — ships within 2 weeks of starting implementation**, using only the existing `ComponentHandler` Protocol and contract test infrastructure. If it takes longer, the extensibility promise needs investigation. One real measurement beats aspirational statements about pace.

This is not a generic technical criterion — it's a domain-specific pace requirement driven by the speed of the AI/ML infrastructure market. The architecture must outpace the competitor copying cycle.

### Mutation Rationale: Explainable Evolution

When a developer reviews an evolved agent definition, they need to understand *what changed and why*. A diff between original and evolved is necessary but not sufficient.

**Domain requirement: every mutation has a human-readable rationale surfaced as a first-class field in the structured evolution log.** The rationale already exists — the `ADKReflectionAgent` and `LiteLLMReflectionAgent` produce natural language reasoning as part of their mutation proposals, captured in reflection events. The domain requirement is **surfacing**: extracting the rationale from the reflection response and promoting it from buried-in-event to a structured, queryable field in the evolution result summary. Not new capability — better visibility of existing output.

The rationale should explain not just "output_schema was mutated" but *why* — "reflection agent proposed relaxing the confidence_score constraint because candidates performed better when less constrained in expressing uncertainty." This enables domain experts to review evolved agents for domain correctness, not just fitness improvement. A mutation that scores higher but violates an unstated business rule (e.g., the agent now uses informal language in a legal compliance context) must be catchable through human review of the rationale.

This requirement directly supports the "evolution explains itself" user success criterion and Journey 4's diagnostic intelligence — the rationale is what makes evolution a diagnostic instrument, not a black box.

### Cross-References

- **Extensibility validation** (Ecosystem Contributor scenario) is covered in architecture validation testing. Acceptance criterion: the first external `ComponentHandler` contribution compiles, passes contract tests, and integrates without core engine changes. See Technical Success: Extensibility.
- **Session isolation** is committed in Technical Success criteria. See Technical Success: Session Isolation.

These six domain requirements define the safety, cost, and trust boundaries within which evolution operates. They are not constraints on innovation — they are the conditions that make innovation *deployable* in enterprise environments.

## Innovation & Novel Patterns

### The Innovation Thesis

Which surfaces matter for any given agent is unknowable in advance. The system must explore all of them.

A developer hand-tuning an agent assumes the instruction is the bottleneck — because the instruction is the only thing they know how to change. An instruction-only optimizer (DSPy, TextGrad, EvoPrompt) makes the same assumption algorithmically. gepa-adk makes no assumption. It treats the complete agent definition — instruction, output schema, generation config — as the search space and lets evolution discover which surface actually matters for *this specific agent on this specific task.* For the developer, this means every evolution run answers a question they couldn't have asked: *was I optimizing the right thing?*

When evolution finds that instruction was indeed the bottleneck, that's still a discovery — it confirms the developer's intuition with evidence. When evolution finds that the schema or config was the bottleneck, that's a result no other tool can produce. Both outcomes are valuable. The system is useful whether or not multi-surface matters for any particular agent, because it answers the question "where should I focus?" rather than assuming the answer.

This thesis extends along a trajectory of increasing architectural intelligence:

- **Phase 1 (current):** Evolution discovers the non-obvious component bottleneck — the schema constraint or config parameter the developer didn't know to question.
- **Phase 2 (growth):** Evolution discovers cross-agent dependency patterns — the entanglement dynamics that emerge only at multi-agent scale, where improving Agent A's config unlocks Agent B's instruction potential.
- **Phase 3 (research horizon):** Evolution explores architectural patterns — topology reordering, agent decomposition. Speculative; dependent on Phase 2 validation and research into workflow-level mutation operators.

### Validation Milestones

The innovation thesis is validated externally through time-bound milestones, not internal assertions:

| Milestone | Timeframe | Validation Criteria | Measurement Method |
|-----------|-----------|--------------------|--------------------|
| **Independent discovery** | MVP | First external user independently confirms multi-surface discovery — unprompted, not coached by maintainer | GitHub issue/discussion where user reports unexpected non-instruction finding |
| **Discovery frequency** | 6 months | Across published case studies, >30% of evolution runs produce highest-impact mutation on a non-instruction component | Structured log analysis across opt-in case study participants |
| **Outperformance baseline** | 12 months | gepa-adk multi-surface evolution outperforms instruction-only mode by >10% on the same agent sets | Controlled A/B: same agents, multi-surface vs. instruction-only mode, measured delta |

The 12-month validation requires a **controlled comparison mechanism**: gepa-adk should support an instruction-only mode (disable schema and config evolution) so the same evolution can run on the same agents in both configurations. This enables rigorous measurement of the multi-surface delta and doubles as an automated benchmark — if multi-surface underperforms instruction-only on >70% of reference agents, something is broken, independent of the thesis.

If the 6-month milestone shows <10% non-instruction discovery rate, the thesis needs revision — not the architecture. The `ComponentHandler` Protocol makes surface addition/removal a configuration choice. Users who find instruction evolution sufficient simply don't enable schema or config evolution. The product still works; the marketing narrative adjusts.

### Risk & Architectural Response

**Thesis risks — what if multi-surface discovery has diminishing returns?**
- LLMs become so capable that instruction quality dominates — schema and config matter less
- Google builds auto-configuration into ADK itself — reducing the value of config evolution
- The search space explosion from 3+ surfaces makes evolution intractable without exponentially larger populations

**Operational risk — reflection agent quality.**
The quality of mutations depends entirely on the reflection agent's ability to propose meaningful changes across different component types. If the reflection model produces shallow mutations ("try making the instruction more detailed" or "add another field to the schema"), evolution stalls regardless of how many surfaces are available. The thesis could be correct — multi-surface matters — and the implementation could still fail because the reflection agent isn't sophisticated enough to exploit the additional surfaces. Mitigation: reflection prompt specialization per component type (already implemented via component-aware reflection), plus benchmark suite tracking mutation quality and diversity across surfaces.

**Architectural response: the architecture is surface-agnostic.** The `ComponentHandler` Protocol treats each evolvable surface as a pluggable module. If a surface stops adding value, users disable it — no code change, no architecture impact. If a new surface (model selection, YAML definition) becomes high-value, users enable it.

The worst case isn't "the product matches competitors." Even if all three surfaces converge to instruction-only value, gepa-adk still has Protocol-based extensibility, ADK session audit trails, Pareto multi-objective tracking, and workflow topology preservation — capabilities no competitor offers. The floor is: matches DSPy on optimization, exceeds DSPy on architecture, observability, and workflow support. The best case is the thesis validates and gepa-adk owns a category no competitor can enter without rebuilding their optimization stack from scratch.

## Developer Tool Specific Requirements

### Language & Runtime

gepa-adk requires **Python >=3.12, <3.13**. Python 3.12 is the current enterprise standard and the version against which all dependencies are validated.

| Dimension | Specification | Notes |
|-----------|--------------|-------|
| **Runtime** | Python 3.12 | Pinned in `pyproject.toml`: `>=3.12,<3.13` |
| **Python 3.13** | Deferred post-MVP | Blocked on google-adk 3.13 compatibility validation |
| **Dependencies** | google-adk>=1.22.0, litellm>=1.80.13, nest-asyncio>=1.6.0, structlog>=25.5.0 | Minimal dependency surface; all actively maintained |
| **Primary constraint** | google-adk version range | ADK is the deepest integration; ADK version changes are the primary compatibility risk (see Domain Requirements: ADK Dependency Isolation) |

### Installation & Distribution

`pip install gepa-adk` is the sole distribution channel. conda-forge, Docker, and IDE plugins are out of scope — the library integrates into user environments, not the reverse.

### API Surface

The public API has three layers, designed as a progressive adoption funnel that mirrors the user journeys:

**Layer 1 — User-Facing Functions** *(day one — Priya's journey)*

The progressive API entry points. A developer needs only Layer 1 to get value:

- `evolve(agent, trainset, scorer, ...)` — single-agent evolution across all enabled surfaces
- `evolve_group(agents, trainset, scorer, ...)` — multi-agent co-evolution with entanglement resolution
- `evolve_workflow(workflow, trainset, scorer, ...)` — workflow structure evolution preserving topology

**Layer 2 — Configuration Types** *(week one — customizing behavior)*

Types the developer constructs to configure evolution:

- `Scorer` Protocol — user-implemented evaluation function
- `CriticOutput` / `SimpleCriticOutput` — structured evaluation schemas for critic agents
- `Stopper` Protocol — evolution termination conditions (budget, plateau, generation limit)
- `ReflectionPrompt` — customizable reflection agent behavior
- ADK agent types (`LlmAgent`, `SequentialAgent`, `LoopAgent`, `ParallelAgent`) — used as-is from ADK

**Layer 3 — Extension Protocols** *(contributors — Marcus and ecosystem contributors)*

Protocols for extending the evolution engine without modifying core code:

- `ComponentHandler` Protocol — add new evolvable surfaces (e.g., `ModelHandler` for model selection)
- `AgentProviderProtocol` — customize agent creation and cloning
- Reflection agent variants — swap between LiteLLM-based and ADK-based reflection implementations

**Error surface:** Error types and structured log schemas are part of the public API surface. Evolution failures produce typed exceptions; diagnostic output follows structured schemas. Both follow the same stability commitments as Layer 2.

**Stability contract:**

| Version State | Layer 1 (Functions) | Layer 2 (Config Types) | Layer 3 (Extension Protocols) |
|--------------|--------------------|-----------------------|------------------------------|
| **Pre-1.0** (current) | Signature stability maintained | Structural stability maintained | May change with deprecation warnings in prior minor |
| **Post-1.0** | Frozen in major version | Frozen in major version | Frozen in major version; new capabilities via new Protocols (e.g., `ComponentHandlerV2`), not extensions to existing ones |

Pre-1.0, the API is evolving but the commitment is: Layer 1 functions (`evolve`, `evolve_group`, `evolve_workflow`) maintain signature stability. Post-1.0, full semver guarantees apply — breaking changes only in major versions. Layer 3 Protocols are never extended with new methods; new capabilities ship as new Protocol versions, preserving existing implementors.

### Code Examples

**Getting started:** A developer runs their first evolution in under 15 minutes: `pip install gepa-adk`, configure an LLM API key, run `basic_evolution.py`. All 16 examples require an LLM provider API key (Google AI, OpenAI, or other LiteLLM-supported provider). The getting-started guide documents provider options and key configuration.

| Category | Examples | Coverage |
|----------|---------|----------|
| **Single-agent evolution** | basic_evolution, basic_evolution_adk_reflection, custom_reflection_prompt | `evolve()` entry point, reflection variants |
| **Schema evolution** | schema_evolution_example, schema_evolution_critic, schema_reflection_demo | Output schema mutation, critic integration |
| **Config evolution** | config_evolution_demo | GenerateContentConfig mutation |
| **Multi-agent** | multi_agent, multi_agent_component_demo | `evolve_group()`, component-aware evolution |
| **Workflow evolution** | loop_agent_evolution, parallel_agent_evolution, nested_workflow_evolution, sandwich_evolution | All workflow agent types |
| **Integration** | app_runner_integration, critic_agent, video_transcription_evolution | ADK AppRunner, critic patterns, multimodal input |

**Current state:** Examples exist and run manually against real LLM providers. No automated validation in CI.

**MVP requirement:** Automated smoke tests for all 16 examples in CI using mock LLM responses — verifying imports, types, and execution flow without real inference costs. Real-provider validation against the supported ADK version range is manual at release milestones.

### Migration & Versioning

gepa-adk follows **semantic versioning (semver)** with pre-1.0 acknowledgements:

Pre-1.0 (current state), minor versions may include breaking changes to Layer 3 Protocols with deprecation warnings in the prior release. Layer 1 and Layer 2 maintain stability regardless of version state. Post-1.0, full semver guarantees apply across all layers.

The migration path for enterprise users: pin to a specific minor version, test against the next minor in CI, upgrade when validated. ADK version compatibility changes are documented in release notes with migration instructions.

### Documentation Architecture

Documentation is a **first-class product feature**, not an afterthought. It is structured as a progressive learning path that mirrors the progressive API:

| Layer | Purpose | Content | Status |
|-------|---------|---------|--------|
| **Concepts (5 docs)** | Explain *why* | GEPA fundamentals, single-agent evolution, multi-agent evolution, workflow agents | Complete |
| **Guides (6 docs)** | Explain *how* | Single-agent, multi-agent, critic agents, reflection prompts, stoppers, workflows | Complete |
| **Reference** | Provide specifics | Glossary (ezglossary plugin), reference index | Partial — auto-generated API reference from docstrings (mkdocstrings) is MVP doc work |
| **Architecture (2 docs)** | Explain *decisions* | ADR-000 hexagonal architecture, proposals | Complete |
| **Contributing (2 docs)** | Support contributors | Docstring templates, releasing guide | Complete |
| **Examples (16 files)** | Demonstrate | Every major feature with runnable code | Complete; needs enterprise ADK version validation |
| **Enterprise architecture guide** | Speak to platform teams | Why hexagonal matters, how Protocols enable extension, how sessions provide audit trails | MVP packaging work |
| **Enterprise observability guide** | Speak to platform engineers | Session persistence to PostgreSQL, structured logging to Splunk/Arize/Phoenix/Datadog | MVP packaging work |
| **C-suite positioning document** | Speak to decision makers | Prompt, context, and intent engineering automation at scale with audit trails | MVP packaging work |

A developer reads the concept, follows the guide, checks the reference, runs the example. A platform engineer reads the enterprise architecture guide, reviews ADR-000, evaluates the audit trail. The documentation serves both journeys without duplicating content.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Validation-Ready MVP

The core evolution engine is shipped, tested (85%+ coverage), and published on PyPI. The MVP is not a build sprint — it's a credibility sprint. The question is not "what do we build?" but "what's the minimum packaging that makes enterprise evaluators say yes?"

Every scope decision is filtered through one criterion: *does this help an enterprise evaluator say yes?* Example smoke tests help because a broken example makes the evaluator say no. Dry-run cost estimation does not — the evaluator hasn't decided to *use* the tool yet, let alone estimate costs. The MVP packages an existing product for enterprise adoption; it does not build new product capabilities.

**Resource Requirements:** Single maintainer. MVP scope is sized to complete in a focused 4-6 week sprint, not a marathon — minimizing bus factor exposure while the project has no contributors.

### MVP Feature Set (Phase 1)

The Product Scope section defines the complete MVP feature inventory (7 shipped capabilities, engineering tasks, documentation tasks). This section adds what the scoping exercise determined: shipping order, time estimates, and two new engineering items surfaced by domain and developer tool requirements analysis.

**Core User Journeys Supported:**

| Journey | MVP Coverage | Key Enabler |
|---------|-------------|-------------|
| **Priya — "The Revelation"** | Full | Getting-started validation (<15 min on enterprise ADK) |
| **Marcus — "The Untangler"** | Full | Workflow evolution already shipped; documentation enables adoption |
| **Rafael + Kenji — "The Evidence"** | Evaluation-ready | Enterprise architecture guide + audit trail documentation |
| **Failure — "The Diagnostic"** | Partial | Mutation rationale surfacing improves diagnostic visibility |

**Must-Have Capabilities:**

*Engineering work (ship first — unblocks evaluation):*

1. **ADK version compatibility** *(pre-existing from Product Scope)* — widen supported version range, test against enterprise-deployed ADK versions, fix any API drift. *High variance estimate: 1-14 days depending on gap between current pinned version and enterprise versions.*
2. **Automated example smoke tests** *(new — surfaced by Developer Tool Requirements analysis)* — delivered in two phases:
   - **Phase A: Import and type checks** (~2 days) — pytest-parametrized verification that all 16 examples import cleanly and pass type validation on the supported ADK version range. Catches 80% of ADK compatibility failures. Ship this first; it's the minimum viable quality gate.
   - **Phase B: Mock-based execution flow tests** (~3 days) — verify execution flow without real LLM inference costs. Ship after Phase A; can be deferred to post-MVP under time pressure.
3. **Mutation rationale surfacing** *(new — surfaced by Domain Requirements analysis)* — extract reflection agent reasoning from ADK session events and promote to a structured, queryable field in the evolution result summary. Data already exists in the event stream; this is a visibility task, not a build task. *Estimate: ~2 days. Caveat: depends on reflection response format consistency across LiteLLM and ADK reflection implementations; if response structures differ, extraction logic handles both variants.*

*Documentation work (ship second — enables adoption):*

4. **Getting-started experience validation** *(pre-existing)* — verified under 15 minutes on enterprise ADK versions, with documented LLM provider options and key configuration.
5. **Enterprise architecture guide** *(pre-existing)* — why hexagonal matters, how Protocols enable extension, how sessions provide audit trails. Audience: platform teams (Marcus, Rafael).
6. **Enterprise observability guide** *(pre-existing)* — session persistence to PostgreSQL, structured logging to Splunk/Arize/Phoenix/Datadog. Audience: platform engineers.
7. **Competitive differentiation brief** *(pre-existing, clarified)* — standalone 2-3 page document for Rafael's evaluation memo: multi-surface discovery as category-defining capability, with evidence from reference scenarios, head-to-head positioning against DSPy/TextGrad/EvoPrompt. Audience: technical decision makers evaluating the tool against alternatives. Lives in `docs/` alongside enterprise guides.
8. **C-suite positioning document** *(pre-existing)* — prompt, context, and intent engineering automation at scale with audit trails. Audience: decision makers. *Lowest priority — cut first under time pressure.*

**MVP Exit Criteria:**
- Rafael can pitch it internally — multi-surface evolution + observability + audit trail story documented and demonstrable
- Marcus can integrate it — ADK version compatibility resolved, platform integration patterns documented
- Priya runs it in 15 minutes — getting-started experience validated on enterprise ADK version
- Kenji sees the trajectory — Pareto data exportable, batch evolution patterns documented
- Still alone in the pool — no competitor has shipped multi-surface, workflow-aware agent evolution
- **All 16 example smoke tests (Phase A minimum) pass in CI on the supported ADK version range** — the engineering gate that prevents documentation from describing a broken product

**MVP Shipping Order:** Engineering items (1-3) first to unblock evaluation, then documentation (4-8) to enable adoption. If time runs short, cut from the bottom of the list. Under extreme time pressure, smoke test Phase B defers to post-MVP while Phase A remains non-negotiable.

### Post-MVP Features

**Phase 2 (Growth) — triggered by external demand and validation milestones:**

| Feature | Trigger | Value |
|---------|---------|-------|
| **Model selection evolution** | First external request for 4th evolvable surface | Proves ComponentHandler extensibility; ships within 2 weeks using existing Protocol |
| **Dry-run cost estimation mode** | Enterprise users running fleet-wide evolution need budget predictability | Pre-execution cost calculation from population size, generation count, developer-provided per-token pricing |
| **Instruction-only comparison mode** | 12-month innovation thesis validation milestone | Controlled A/B: multi-surface vs. instruction-only on same agents; doubles as automated benchmark |
| **Batch evolution wrapper** | Enterprise user needs fleet optimization across 50+ agents | Thin orchestration for parallel pipeline optimization |
| **Multi-agent pipeline tutorial** | Marcus persona's integration story validated with real enterprise users | Complete walkthrough driving platform adoption |
| **Hybrid optimization adapter** | Technical research validated in production scenarios | Combine evolutionary mutation with gradient-like feedback |
| **Python 3.13 support** | google-adk validates 3.13 compatibility | Widen runtime support for users on latest Python |
| **conda-forge distribution** | 10+ GitHub issues requesting conda support from distinct users | Alternative distribution channel for enterprise environments requiring conda |

**Phase 3 (Vision) — organizational capability transformation:**

- **Complete agent genotype evolution** — all 7 surfaces (instruction, schema, config, model, YAML definition, tool configuration, sub-agent composition) evolved simultaneously
- **Fleet-level optimization dashboards** — organizational view of agent quality, cost, and compliance across thousands of automation use cases
- **Framework expansion** — Protocol-based adapters for LangChain, CrewAI, AutoGen beyond ADK
- **Community marketplace** — ecosystem of community-contributed ComponentHandlers, Scorers, Critics, and Stoppers
- **Enterprise deployment playbook** — compliance frameworks for regulated industries (finance, healthcare, insurance, government)

### Risk Mitigation Strategy

**Execution Risks:**

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **ADK breaking changes during MVP** | Medium-High | High — blocks enterprise evaluation | Adapter pattern (ADR-000) isolates ADK types. Pre-1.0 stability contract permits Layer 3 Protocol changes with deprecation warnings; Layers 1-2 maintain stability regardless (see Developer Tool Requirements: Stability Contract). If gap is larger than expected, scope to most common enterprise version first, widen later. |
| **Single-maintainer bus factor** | Permanent until contributors join | Critical — project stalls entirely | MVP sized for 4-6 week focused sprint. Documentation + architecture decisions recorded in PRD and ADRs, enabling future contributors to onboard without oral knowledge transfer. |
| **Scope of issues discovered by smoke tests** | Medium — examples were written against a specific ADK version and never tested in CI; running against a wider range *will* surface issues | Medium — extends MVP timeline | Phase A (import/type checks) ships first and catches 80% of failures in ~2 days. Phase B (execution flow) ships second. Known issue count from Phase A determines whether Phase B stays in MVP or defers. |

**Market Risks:**

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Competitive window closes** | Medium (estimated 6-12 months based on competitor release cadence — DSPy's recent releases focus on instruction optimization and RAG pipelines; EvoPrompt and TextGrad are research publications without active product roadmaps; no public signals of schema/config evolution from any competitor as of March 2026) | High — differentiation narrows | MVP documentation establishes category ownership before competitors notice. Visibility (blog posts, case studies) is the market risk mitigation — the product must be *findable* before competitors replicate. |
| **Enterprise evaluators need Growth features** | Medium | Medium — delays adoption | Progressive API means evaluators get value from `evolve()` alone. Growth features are triggers, not blockers — if an evaluator needs model selection, that signals demand and justifies the engineering investment. |

**Resource Risks:**

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **50% less time than planned** | Low-Medium | High — MVP incomplete | **Minimum viable minimum contingency:** cut C-suite positioning document, enterprise observability guide, and smoke test Phase B. Keep: ADK compat, smoke test Phase A (import checks, ~2 days), rationale surfacing, getting-started validation, enterprise architecture guide, competitive differentiation brief. 3 engineering tasks + 3 doc tasks = absolute floor for credible enterprise evaluation. |
| **ADK version compat balloons to 2+ weeks** | Low-Medium | Medium — delays everything else | Scope to single most common enterprise ADK version. Document known incompatibilities with other versions as "tested" vs. "untested" rather than blocking MVP on full range support. |

## Functional Requirements

This section defines the **capability contract** for the entire product. UX designers will only design what's listed here. Architects will only support what's listed here. Epic breakdown will only implement what's listed here. If a capability is missing, it will not exist in the final product.

Each FR states WHAT capability exists, not HOW it's implemented. Each is testable, implementation-agnostic, and uses generic actors. Phase tags indicate when each capability is targeted for delivery.

**Note:** Many MVP FRs formalize capabilities that are already shipped and tested (85%+ coverage). Downstream epic breakdown should distinguish "verify and document" from "build" for each MVP FR.

**Conscious omission:** Evolution resume (restarting from a mid-run checkpoint after interruption) is out of scope. If demand surfaces, it becomes a Growth consideration.

### Single-Agent Evolution

- **FR1** [MVP]: A developer can evolve a single agent's definition across all enabled surfaces (instruction, output schema, generation config) by providing the agent, a training set, and a scorer.
- **FR2** [MVP]: A developer receives a structured evolution result containing the evolved agent definition, generation history, and summary statistics.
- **FR3** [MVP]: A developer can view a diff between the original and evolved agent definition, showing what changed across each component.
- **FR4** [MVP]: A developer can view per-component mutation attribution in the evolution result, identifying which surface produced the highest-impact change.
- **FR5** [MVP]: The system identifies which evolvable surface produced the highest-impact mutation for a given evolution run.
- **FR6** [MVP]: A developer can use each API entry point independently — `evolve()` requires no knowledge of `evolve_group()` or `evolve_workflow()`, and each is usable as a standalone capability.
- **FR7** [Growth]: A developer can run evolution with specific surfaces disabled (e.g., instruction-only mode) to compare multi-surface vs. single-surface outcomes on the same agent.

### Multi-Agent & Workflow Evolution

- **FR8** [MVP]: A developer can evolve a group of agents simultaneously by providing individual agent scorers and an aggregate pipeline scorer.
- **FR9** [MVP]: The system applies round-robin agent selection across generations during group evolution, ensuring each agent is a mutation target.
- **FR10** [MVP]: The system's final evolution result does not include agents whose scores are below their pre-evolution baseline.
- **FR11** [MVP]: A developer can view per-agent score breakdown during and after group evolution.
- **FR12** [MVP]: A developer can evolve a workflow structure while preserving the topology of SequentialAgent, LoopAgent, and ParallelAgent compositions.
- **FR13** [MVP]: The system can operate across a defined and documented ADK version range, including enterprise-deployed versions.
- **FR14** [Growth]: A developer can run evolution across a fleet of agents using batch orchestration.

### Evolution Control & Extensibility

- **FR15** [MVP]: A developer can implement a custom scorer by conforming to the Scorer Protocol.
- **FR16** [MVP]: A developer can use critic agents (SimpleCriticOutput, CriticOutput) for structured multi-dimensional evaluation.
- **FR17** [MVP]: A developer can configure evolution termination using stoppers (budget limit, plateau detection, generation limit).
- **FR18** [MVP]: A developer can choose between reflection agent implementations (LiteLLM-based, ADK-based) for mutation generation.
- **FR19** [MVP]: A developer can customize the reflection prompt to control mutation behavior.
- **FR20** [MVP]: The system applies component-aware reflection specialization, producing mutations tailored to each surface type (instruction vs. schema vs. config).
- **FR21** [MVP]: A contributor can add a new evolvable surface by implementing the ComponentHandler Protocol and registering it — without modifying the core evolution engine.
- **FR22** [MVP]: A contributor can customize agent creation and cloning by implementing the AgentProviderProtocol.
- **FR23** [Growth]: A contributor can add model selection as an evolvable surface via the ComponentHandler Protocol.
- **FR24** [Growth]: A developer can estimate evolution cost before execution by providing population parameters and per-token pricing configuration.
- **FR25** [Vision]: A contributor can implement an adapter for a non-ADK agent framework via a framework adapter Protocol.

### Observability & Audit

- **FR26** [MVP]: The system emits structured log events for every evolution decision (mutation proposed, mutation accepted/rejected, score change, generation summary).
- **FR27** [MVP]: The system captures every evolutionary event as an ADK session event, producing an audit trail queryable via session persistence.
- **FR28** [MVP]: A developer can view a human-readable mutation rationale as a structured, queryable field in the evolution result summary — explaining not just what was mutated but why.
- **FR29** [MVP]: The system surfaces scorer signal diagnostics in the evolution result summary, including scorer discrimination analysis and mutation diversity tracking.
- **FR30** [MVP]: A platform engineer can configure session persistence to an external backend (e.g., PostgreSQL) for enterprise audit requirements.

### Pareto & Multi-Objective Optimization

- **FR31** [MVP]: The system tracks a Pareto frontier across multiple objectives (e.g., quality, cost, latency) during evolution.
- **FR32** [MVP]: The system classifies candidates as dominated or non-dominated on the Pareto frontier, using dominance relationships for selection.
- **FR33** [MVP]: The system detects regression during multi-agent evolution via Pareto dominance — candidates that improve one dimension but worsen the aggregate are recorded but not selected as parents.
- **FR34** [MVP]: A developer can export Pareto frontier state as structured data (JSON) for external analysis, dashboards, or organizational reporting.
- **FR35** [Vision]: A platform engineer can view fleet-level optimization dashboards showing agent quality, cost, and compliance across the organization.

### Safety & Invariant Enforcement

- **FR36** [MVP]: A developer can declare schema field preservation constraints (required fields, type compatibility) that evolution never violates, regardless of generation count or fitness score.
- **FR37** [MVP]: A developer can declare instruction boundary patterns (StateGuardTokens) that constrain the mutation space for instructions.
- **FR38** [MVP]: The system enforces bounded mutation ranges for generation config parameters, preventing evolution from producing unusable configurations.
- **FR39** [MVP]: When candidates have comparable scores, the system prefers the candidate with more concise, interpretable definitions — favoring auditable evolved agents over opaque high-scoring ones.
- **FR40** [MVP]: The system guarantees deterministic evolutionary decisions (component selection, candidate selection, Pareto state updates) given the same seed, agents, scorer, and fitness scores — independent of stochastic LLM inference.
- **FR41** [MVP]: Two concurrent evolution runs with different session IDs never interfere with each other's state or results.

### FR Summary

| Capability Area | MVP | Growth | Vision | Total |
|----------------|:---:|:------:|:------:|:-----:|
| Single-Agent Evolution | 6 | 1 | — | 7 |
| Multi-Agent & Workflow Evolution | 6 | 1 | — | 7 |
| Evolution Control & Extensibility | 8 | 2 | 1 | 11 |
| Observability & Audit | 5 | — | — | 5 |
| Pareto & Multi-Objective Optimization | 4 | — | 1 | 5 |
| Safety & Invariant Enforcement | 6 | — | — | 6 |
| **Total** | **35** | **4** | **2** | **41** |

35 MVP FRs formalize the shipped engine plus MVP sprint deliverables. 4 Growth FRs are triggered by external demand. 2 Vision FRs are directional. Log routing to enterprise observability platforms (Splunk, Arize/Phoenix, Datadog) is deferred to Non-Functional Requirements as a deployment integration concern.

## Non-Functional Requirements

NFRs define how well the system performs, not what it does. Only categories relevant to gepa-adk as a developer tool library are included. Security (authentication, encryption), scalability (user traffic), and accessibility (UI) are not applicable and are omitted.

These NFRs provide measurable targets for the quality attributes established in Technical Success criteria and Domain Requirements. Where the same concept appears across sections, Success Criteria states the strategic intent, Domain Requirements explains the domain context, FRs define the capability, and NFRs define the quality target.

### Performance

**Engine Overhead Proportionality.** The evolution engine's processing time (mutation selection, Pareto frontier update, candidate management, generation bookkeeping) is negligible relative to LLM inference costs. For evolution runs where LLM inference accounts for >90% of wall-clock time, engine overhead is <1% of total generation time. This proportionality guarantee is what makes multi-agent evolution practical at enterprise scale — the engine is cheap, LLM calls are expensive.

For workloads where LLM inference is <90% of wall-clock time (trivial scorers, mock-based testing), engine overhead is bounded but not proportionally negligible. Target: absolute engine processing time per generation remains <500ms for populations up to 50. This target is subject to benchmark validation before it becomes a hard guarantee.

**Evolution Scale Characteristics.** Evolution state (population, Pareto frontier, generation history, per-agent score tracking) for population sizes up to 50 and generation counts up to 30 occupies <100MB of heap memory, excluding LLM response caching. Beyond documented scale limits, the system may degrade in performance but does not silently corrupt state — it raises an explicit error if memory constraints are exceeded.

### Integration

**Structured Log Schema Stability.** The structured log event schema (field names, types, event names) is documented, versioned, and stable across minor releases. Platform engineers building integrations against log output can rely on schema compatibility within a major version. The schema is part of the public API surface and follows the same stability contract as Layer 2 configuration types (see Developer Tool Requirements: Stability Contract).

**Session Persistence Compatibility.** Evolution session events are compatible with ADK's session persistence interface. Any backend that implements ADK's session storage contract can receive evolution events without gepa-adk-specific adapters.

**Enterprise Observability Routing.** Structured log output is routable to enterprise observability platforms (Splunk, Arize/Phoenix, Datadog) via structlog's standard formatter pipeline. No custom adapters are required — standard structlog processors and formatters produce output consumable by enterprise log aggregators.

**Credential Redaction.** LLM provider API keys, authentication tokens, and other credentials are never included in structured log output, evolution results, or session events. A redaction filter in the logging pipeline ensures sensitive values cannot leak into audit trails or diagnostic output, regardless of whether credentials appear in session state or LLM responses. *(MVP engineering work — redaction filter not yet implemented.)*

### Reliability

**Explicit Completion Semantics.** Evolution runs complete fully or fail explicitly — no silent partial completion where some generations succeed and others silently drop. If evolution fails at any point, the system raises a typed exception identifying the failure generation and cause. All session state and temporary objects are properly cleaned up on failure.

**Typed Exception Coverage.** Every failure mode produces a gepa-adk-specific typed exception. The developer never encounters a raw traceback without a wrapping exception type that identifies the failure category (evolution stall, scorer failure, reflection failure, ADK compatibility error, resource exhaustion).

**Diagnostic Error Messages.** Every typed exception includes a diagnostic message suggesting the most likely cause and the next investigation step. The difference between `EvolutionStalled("no improvement")` and `EvolutionStalled("No improvement after 8 generations. Scorer discrimination is low — 87% of candidates within 0.05. Consider a more discriminative critic that evaluates specific quality dimensions.")` is the difference between a tool and a diagnostic instrument.

**Observability Completeness.** Structured log events are emitted synchronously with evolution execution. No event is lost or delayed due to buffering, batching, or async failures. If an audit trail has gaps, the compliance story collapses — every evolutionary decision must have a corresponding log event, and the event count must match the decision count. Directly testable: run an evolution, count decisions from the evolution result, count events from the session log, assert equality.

### Maintainability

**Test Coverage Floor.** 85%+ test coverage maintained, trending upward. Enforced in CI on every commit. Coverage regression blocks merge.

**Protocol Contract Tests.** Every public Protocol (Scorer, ComponentHandler, AgentProviderProtocol, Stopper) has a corresponding contract test suite that validates conformance. Adding a new Protocol requires adding its contract tests. Adding a new Protocol implementation requires passing the existing contract test suite.

**Architectural Boundary Enforcement.** Evolution logic has zero direct imports from ADK types outside the adapter module. Enforced via CI static analysis (import scanning). If a direct ADK import appears in evolution logic, the hexagonal architecture promise is broken and the CI check fails. This is the maintainability guarantee that makes ADK version isolation real.

### Compatibility

**Python Version.** Python >=3.12, <3.13. Python 3.13 support deferred post-MVP pending google-adk compatibility validation.

**ADK Version Range.** The system operates across a documented and CI-tested ADK version range, including enterprise-deployed versions. Compatibility breakage on a supported ADK version blocks release until resolved.

**LLM Provider Diversity.** Any LLM provider supported by LiteLLM works for reflection agent inference without gepa-adk code changes. Provider-specific behavior differences are handled by LiteLLM, not by gepa-adk.

### NFR Summary

| Category | NFRs | Key Measurable Target |
|----------|:----:|----------------------|
| **Performance** | 2 | Engine overhead <1% of generation time (when LLM >90% of wall-clock); <100MB heap for population 50 x 30 generations |
| **Integration** | 4 | Log schema stable across minor versions; credential redaction with zero leakage |
| **Reliability** | 4 | 100% explicit failure semantics; event count = decision count for audit completeness |
| **Maintainability** | 3 | 85%+ coverage; zero ADK imports outside adapter; contract tests for every Protocol |
| **Compatibility** | 3 | ADK version breakage blocks release; any LiteLLM provider works without code changes |
| **Total** | **16** | |

## Traceability Cross-Reference

This table maps the critical capability chains from vision through verification, covering the moat-defining capabilities that downstream architecture, epic breakdown, and QA will prioritize.

| Theme | Success Criterion | Journey | FRs | NFR Category | Verification |
|-------|------------------|---------|-----|-------------|--------------|
| **Multi-surface discovery** | Multi-surface discovery changes how developers think | J1 (Priya) — schema bottleneck revelation | FR1, FR4, FR5 | Performance (proportionality) | Integration test: 3 reference scenarios (schema, config, instruction bottleneck) |
| **Workflow topology preservation** | Extensibility without core changes | J2 (Marcus) — workflow evolution in CI | FR10, FR12 | Compatibility (ADK version range) | Integration test: round-trip clone + evolve + execute for each workflow agent type |
| **Entanglement resolution** | Progressive API adoption feels natural | J2 (Marcus) — 4-agent pipeline co-optimization | FR8, FR9, FR10, FR11 | Reliability (explicit completion) | Integration test: group evolution where individual improvement causes aggregate regression; verify Pareto self-correction |
| **Audit-grade observability** | Evolution explains itself | J3 (Rafael) — compliance evidence | FR26, FR27, FR28 | Integration (log schema stability), Reliability (observability completeness) | Integration test: event count = decision count; all events parseable against documented schema |
| **Diagnostic intelligence** | First evolution delivers undeniable value | J4 (Failure) — scorer discrimination diagnosis | FR2, FR29 | Reliability (diagnostic error messages) | Integration test: evolution with low-discrimination scorer surfaces diagnostic in result summary |
| **Safety invariants** | Extensibility without core changes | Domain Req: Adversarial Mutation Space | FR36, FR37, FR38 | — | Contract test: no candidate in population violates declared invariants across 1000-generation stress test |
| **ComponentHandler extensibility** | Extensibility without core changes | Domain Req: Competitive Pace | FR19, FR21 | Maintainability (architectural boundary enforcement) | Integration test: new ComponentHandler registered and producing mutations without core code changes |
| **Pareto multi-objective** | Evolution explains itself | J3 (Kenji) — fleet optimization dashboard | FR31, FR32, FR33, FR34 | Performance (scale characteristics) | Integration test: Pareto frontier export matches expected dominated/non-dominated classification |
