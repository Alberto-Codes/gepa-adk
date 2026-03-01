---
stepsCompleted: [1, 2, 3, 4, 5, 6]
status: 'complete'
inputDocuments:
  - '_bmad-output/project-context.md'
  - '_bmad-output/planning-artifacts/research/market-automated-prompt-optimization-research-2026-03-01.md'
  - '_bmad-output/planning-artifacts/research/domain-evolutionary-automated-prompt-optimization-research-2026-03-01.md'
  - '_bmad-output/planning-artifacts/research/technical-hybrid-prompt-optimization-research-2026-03-01.md'
  - 'docs/index.md'
  - 'docs/getting-started.md'
  - 'docs/concepts/gepa-fundamentals.md'
  - 'docs/concepts/single-agent-evolution.md'
  - 'docs/concepts/multi-agent-evolution.md'
  - 'docs/concepts/workflow-agents.md'
  - 'docs/proposals/001-initial-package-proposal.md'
  - 'docs/project-management.md'
  - 'docs/reference/glossary.md'
date: '2026-03-01'
author: 'Alberto-Codes'
---

# Product Brief: gepa-adk

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

gepa-adk automatically improves AI agent systems by evolving their complete definition — not just prompts, but output schemas, generation configurations, and model selections — across multi-agent workflows simultaneously. Built on the GEPA (Genetic-Pareto) algorithm and Google's Agent Development Kit, it provides a progressive API: `evolve()` for single agents, `evolve_group()` for multi-agent pipelines, and `evolve_workflow()` for complex workflow structures. Every evolutionary decision is fully observable through ADK session events, providing enterprise-ready audit trails that are queryable, explainable, and exportable to standard observability platforms.

---

## Core Vision

### Problem Statement

There is no systematic, automated way to improve multi-agent AI systems after deployment. As agent pipelines grow — multiple agents with interconnected instructions, structured outputs, and configuration parameters — the **entanglement problem** emerges: improving one agent's instruction silently degrades downstream agent behavior because agents depend on each other's outputs through shared session state. This cascading dependency means agents cannot be optimized independently; the *system* must be optimized as a whole. The combinatorial explosion of N agents x M components x K parameters creates a search space no human can navigate, and no existing tool addresses.

### Problem Impact

- **Individual ADK developers** are frustrated and demoralized — they know their agent could be better but have no systematic path forward. They spend days hand-tuning a single instruction through trial-and-error, hitting optimization ceilings because other dimensions (schema, config, model) silently constrain them
- **Engineering teams building production pipelines** are flying blind in high-stakes environments. When a 5-agent pipeline scores 0.6, there is no way to determine which agent is the bottleneck, which component needs change, or whether improving one agent will break another. They resort to spreadsheets and gut instinct
- **ML engineers running optimization campaigns** lack the multi-objective tradeoff analysis needed for cost/quality/latency decisions, the checkpointing for long-running jobs, and the experiment tracking to make evolution reproducible and scientific

### Why Existing Solutions Fall Short

**The status quo is manual prompt engineering.** Most teams today don't use any optimization tool — a senior engineer spends days or weeks tweaking prompts by hand, guided by intuition. This doesn't scale beyond single agents and can't address multi-dimensional optimization.

Automated tools partially address the single-agent case but fall short of the full problem:

- **DSPy** compiles and optimizes single-agent prompts through a declarative framework. It now integrates the GEPA algorithm for instruction optimization, but has zero support for evolving agents within workflow structures or optimizing non-instruction surfaces
- **TextGrad** applies gradient-based optimization to prompts. Gradients require differentiable objectives — model selection and schema structure are not differentiable, and multi-agent interaction effects cannot be backpropagated
- **EvoPrompt / PromptBreeder** apply evolutionary search to isolated prompts but lack ADK integration, workflow awareness, or multi-surface evolution

All existing tools treat the instruction as the only evolvable gene. None evolve output schemas, generation configs, or model selection. None preserve workflow topology during optimization. None provide audit trails of optimization decisions.

### Proposed Solution

gepa-adk provides evolutionary optimization that grows with the user's needs:

1. **Multi-surface agent evolution**: Currently evolves instruction text, output schemas (Pydantic models as text with AST validation), and generation configurations (temperature, top_k, etc. as YAML). The architecture is designed to expand to model selection, YAML agent definitions, and additional surfaces through the Protocol-based ComponentHandler interface
2. **Structure-preserving workflow evolution**: SequentialAgent order, LoopAgent iteration counts, ParallelAgent concurrency semantics — all preserved during evolution through recursive cloning with instruction overrides
3. **Reflection-guided mutation**: LLM-powered reflection agents analyze critic feedback and execution trajectories to propose intelligent mutations — not random search, but informed evolution
4. **Multi-objective Pareto frontier**: Track tradeoffs between quality, cost, latency, and any custom objective — surface the full tradeoff landscape instead of forcing a single "best"
5. **Enterprise-ready observability**: ADK session events capture every reasoning step, tool call, and state mutation across evolving agents, critic agents, and reflection agents. Structured logging via structlog produces platform-agnostic output ready for ingestion by Splunk, Arize/Phoenix, Datadog, or any log aggregator. ADK's DatabaseSessionService enables PostgreSQL persistence for audit-grade storage

### Key Differentiators

| Differentiator | What It Means | Why Competitors Can't Follow |
|---|---|---|
| **Multi-surface genotype evolution** | Evolves the complete agent definition (instruction + schema + config), not just prompts. Breaks through single-dimension optimization ceilings | Gradient-based tools require differentiable objectives. Compiler tools require declarative specs. Only evolutionary search navigates mixed continuous/discrete/combinatorial spaces |
| **Workflow-aware topology preservation** | Evolves agents within preserved ADK workflow structures (Sequential, Loop, Parallel, nested). Addresses the multi-agent entanglement problem | No competitor understands workflow semantics. Requires deep ADK integration and structure-preserving cloning that can't be bolted on |
| **Enterprise audit-grade observability** | Full trail of every evolutionary decision — critic reasoning, reflection proposals, trajectory data — queryable and explainable | Academic optimization tools produce results without explanation. gepa-adk shows *why* every change was made, building the trust enterprises require |

### Go-to-Market: Progressive API as Land-and-Expand

The API design is itself a growth wedge:

- **Day 1**: `evolve(agent, trainset)` — developer optimizes one agent's instruction. Immediate value, zero configuration
- **Week 2**: `evolve_group(agents, trainset)` — team optimizes a multi-agent pipeline. Deeper value, growing dependency
- **Month 2**: `evolve_workflow(workflow, trainset, round_robin=True)` — organization optimizes complex workflow structures across multiple surfaces. Maximum value, high switching cost

Each step deeper increases the value delivered and the cost of switching away. The same API surface scales from day-one experimentation to production pipeline optimization

---

## Target Users

### Industry Context

gepa-adk serves organizations in **regulated industries** — finance, healthcare, insurance, government, and similar sectors — where AI agent automation is scaling rapidly but auditability, compliance, and regulatory oversight are non-negotiable. These industries share a common scaling cliff: building a prototype agent for a CTO demo is achievable with craft engineering; scaling optimized agents across tens of thousands of automation use cases cannot be done with people and best guesses alone.

The product also serves the broader developer community through its open-source foundation, ensuring adoptability, maintainability, and ecosystem health.

### Primary Personas

#### Rafael — Enterprise AI Platform Lead

**Role:** Principal Engineer at a large regulated enterprise

**Context:** Rafael has built prototype agents that wow the C-suite — tools-enabled agents with sophisticated context engineering that perform brilliantly in demos. His challenge isn't building one good agent. It's scaling agent quality across tens of thousands of automation use cases without an army of prompt engineers hand-tuning each definition.

**Before gepa-adk:** The CTO demo works. The first 10 production agents work, manually tuned over weeks. But when the organization needs 500 agents across compliance, claims processing, fraud detection, and customer service — each needing different instructions, schemas, and configurations — manual optimization breaks. Teams ship "good enough" agents with sporadic tests and hope for the best. Quality is inconsistent, costs are unpredictable, and nobody knows which agents are performing well and which are limping along. Regulators ask "how did you validate this agent's behavior?" and the answer is "a senior engineer tweaked it until it seemed right."

**With gepa-adk:** Rafael builds the evolution infrastructure into his enterprise's agent platform. Every agent goes through automated optimization with full audit trails. He can answer regulators with session-level evidence of every evolutionary decision. He scales agent quality systematically instead of artisanally.

**Job-to-be-Done:** "Scale agent quality across thousands of use cases with auditable, systematic optimization."

**Adoption role:** Identifies the scaling problem, champions adoption, drives organizational commitment.

---

#### Marcus — Platform Engineer

**Role:** Senior Engineer building agent infrastructure at an enterprise

**Context:** Marcus designs multi-agent workflow templates — intake → process → validate → output — that different use cases plug into. He's the one who turns Rafael's vision into infrastructure.

**Before gepa-adk:** When the workflow template works for loan processing but breaks for compliance review, Marcus can't tell if the problem is the template structure or the use-case-specific components. Every time he improves one agent's instruction, another agent downstream breaks because it was tuned to the old output format. He spends sprints chasing entanglement bugs across multi-agent pipelines.

**With gepa-adk:** Marcus embeds `evolve_workflow()` into the platform's deployment pipeline. Workflow templates are evolved against diverse use cases to identify structural weaknesses vs. content weaknesses. The round-robin evolution cycle discovers which component is the actual bottleneck — often something unexpected like an output schema, not an instruction.

**Job-to-be-Done:** "Build evolution into the platform so teams self-serve quality optimization."

**Adoption role:** Implements the evolution infrastructure, integrates with enterprise tooling.

---

#### Priya — Agent Builder

**Role:** Mid-level software engineer building individual agents for specific automation use cases

**Context:** Priya is technically capable but not an ML specialist. She builds agents for specific business functions — one for document classification, another for data extraction, another for report generation. She's a producer in the agent factory.

**Before gepa-adk:** Each agent takes a week of prompt tuning. She built 12 agents last quarter with manual iteration. She's been asked to build 50 next quarter. That math doesn't work. She knows each agent could be better but has no systematic path from "works okay" to "works great."

**With gepa-adk:** Priya builds the agent skeleton, writes a critic that captures domain quality requirements, runs `evolve(agent, trainset, critic=critic)`, and moves on to the next use case. Her throughput multiplies. Her aha moment: running evolution and seeing a score jump from 0.5 to 0.8 without writing a custom training loop.

**Job-to-be-Done:** "Ship quality agents fast without manual tuning."

**Adoption role:** Daily user of the evolution tools, validates the developer experience.

---

#### Dr. Kenji — Optimization Lead

**Role:** ML/AI Platform Lead responsible for agent quality across the organization

**Context:** Kenji oversees agent performance across the enterprise. His dashboard tracks thousands of agents across dozens of teams. He reports to leadership on quality, cost, and compliance.

**Before gepa-adk:** Agent optimization is artisanal and unreproducible. Different teams use different approaches. There's no way to answer "which agents are underperforming?" or "what's our cost-quality tradeoff across the fleet?" without manually auditing each team's work. Running systematic optimization campaigns is impossible because there's no checkpointing, no experiment tracking, and no multi-objective analysis tooling.

**With gepa-adk:** Kenji runs batch evolution campaigns across agent fleets. The Pareto frontier shows that switching two agents to a cheaper model loses only 3% quality while saving 40% on API costs. Every optimization decision has an audit trail. He presents reproducible, evidence-backed results to leadership and regulators.

**Job-to-be-Done:** "Monitor, optimize, and report on fleet-wide agent quality with reproducible, auditable results."

**Adoption role:** Operationalizes evolution at organizational scale, drives ROI reporting.

### Secondary Personas

| Persona | Role | Value to Product |
|---|---|---|
| **The CTO / Engineering VP** | Budget decision maker at a regulated enterprise | Doesn't use the tool directly. Cares about audit trails, compliance readiness, ROI. Approves adoption based on Rafael's recommendation and Kenji's reports |
| **The Ecosystem Contributor** | Open-source developer extending gepa-adk | Builds new ComponentHandlers, Scorers, Stoppers. Cares about clean Protocol interfaces, good docstrings, hexagonal architecture. Extends the platform's capability surface |
| **The Educator / Content Creator** | Technical content producer (courses, tutorials, talks) | Creates awareness through content. The evolutionary metaphor is universally accessible — "I Let AI Evolve Its Own Prompts" is a compelling narrative. Force multiplier for adoption |
| **The Entry-Level Developer** | Junior developer or hobbyist experimenting with ADK | Validates adoptability and maintainability. If a junior dev can run `evolve()` and get results, the tool is accessible. Important signal even for enterprise buyers evaluating ease of onboarding |

### User Journey

**Adoption sequence:** Rafael (vision) → Marcus (infrastructure) → Priya (daily use) → Kenji (operationalize) → CTO (budget approval)

| Stage | Experience | Key Moment |
|---|---|---|
| **Discovery** | Rafael encounters the scaling cliff — CTO demo works, 10,000 use cases don't. Searches for systematic agent optimization. Finds gepa-adk through open-source community, conference talk, or technical blog |
| **Evaluation** | Marcus runs `evolve()` on a single agent to validate the tool works. Runs `evolve_workflow()` on a small pipeline to test workflow support. Reviews the audit trail in ADK session data |
| **Infrastructure** | Marcus integrates gepa-adk into the agent platform. Configures evolution as part of the deployment pipeline. Connects session persistence to enterprise PostgreSQL |
| **Adoption** | Priya uses evolution as part of her agent development workflow. Ships agents faster with higher quality. Stops hand-tuning prompts |
| **Operationalization** | Kenji runs fleet-wide optimization campaigns. Builds dashboards on Pareto frontier data. Reports cost/quality tradeoffs to leadership |
| **Expansion** | Organization expands from instruction evolution to schema evolution, config evolution, and eventually model selection optimization. Switching cost increases with each surface adopted |

---

## Success Metrics

Success is measured across three layers: product quality (does it work?), user outcomes (are users getting value?), and ecosystem growth (is the project growing?). Metrics are adoption and impact-focused — monetization strategy is a separate decision to be made once adoption validates the category.

### Product Quality Metrics

| Metric | What It Measures | Target |
|---|---|---|
| **Evolution success rate** | % of evolution runs producing measurable improvement | > 80% of runs show score increase |
| **Score improvement magnitude** | Average quality improvement across evolution runs | > 15% average improvement per run |
| **Reliability** | Evolution runs completing without errors | 99%+ for shipped features |
| **Test coverage** | Codebase coverage enforced in CI | 85% floor (current), trending upward |
| **API stability** | Breaking changes per release | Trending to zero as API matures |
| **Contract test coverage** | Every Protocol implementation has a contract test | 100% coverage maintained |

### User Outcome Metrics

| Persona | Success Metric | Measurable Signal | Target |
|---|---|---|---|
| **Entry-level dev** | "I ran evolve() and it just worked" | Time from `pip install` to first successful evolution | < 15 minutes |
| **Priya (Agent Builder)** | "I ship agents faster without hand-tuning" | Agent throughput: agents shipped per quarter, before vs. after | 3x throughput increase |
| **Marcus (Platform Engineer)** | "Evolution is part of the platform" | gepa-adk integrated into CI/CD or platform deployment pipeline | Zero custom glue code required |
| **Kenji (Optimization Lead)** | "I can report fleet health to leadership" | Pareto frontier data used in cost/quality tradeoff reporting | Fleet-level dashboards operational |
| **Rafael (AI Platform Lead)** | "I can answer regulators with evidence" | Evolution audit trails queried and exported in production | Audit-grade session data available |

### Ecosystem Growth Metrics

| Metric | 3-Month Target | 6-Month Target | 12-Month Target |
|---|---|---|---|
| **Monthly PyPI downloads** | 500+ | 2,000+ | 10,000+ |
| **External GitHub issues/discussions** | 5+ (proves real users beyond maintainer) | 20+ | 100+ |
| **External contributions** | First external issue | First external PR merged | 5+ external contributors |
| **Evolution success stories** | 1 published case study | 5 published case studies | 20+ published case studies |
| **Dependent repositories** | Measurable on GitHub | Growing trend | gepa-adk recognized as standard ADK optimization tool |
| **Conference/content presence** | First blog post or talk | Multiple content pieces driving awareness | Regular community references in ADK ecosystem |

### Business Objectives by Timeframe

**3 months — "Proves the tool works, early community signals":**
- gepa-adk stable on PyPI with 3 evolvable surfaces shipped (instruction, output_schema, generate_content_config)
- Getting-started experience validated at under 15 minutes
- Workflow evolution epic complete
- Early adopters providing feedback through issues and discussions

**6 months — "Platform maturity, first enterprise evaluations":**
- Multi-agent and workflow documentation complete with real-world pipeline tutorials
- Enterprise observability documented with PostgreSQL persistence guide
- First enterprise teams evaluating for production use
- Community forming around ADK agent optimization

**12 months — "Default tool for ADK agent optimization":**
- Experiment tracking integration shipped
- Batch evolution capability for fleet optimization
- Model selection evolution shipped
- Multiple organizations using in production
- Category recognition: when someone needs ADK agent optimization, gepa-adk is the default answer

### North Star Metric

**"When someone says 'I need to optimize my ADK agents,' the first thing they reach for is gepa-adk."**

This is category = brand. Measured by: search volume, Stack Overflow mentions, ADK community references, and organic inbound from developers who heard about the tool from peers

---

## MVP Scope

### Strategic Context

gepa-adk is a brownfield project with significant capabilities already shipped and proven. The core evolution engine, hexagonal architecture, Protocol-based interfaces, progressive API, and three evolvable surfaces are built, tested (85%+ coverage), and published on PyPI. The competitive landscape is empty — no tool addresses multi-surface, workflow-aware agent evolution.

**The MVP is a positioning and maturity sprint, not a feature sprint.** The technology is largely here. What's missing is enterprise packaging, ADK version compatibility, and framing that speaks to the C-suite audience.

### C-Suite Framing: Prompt, Context, and Intent Engineering

The C-suite hears escalating buzzwords: "prompt engineering" → "context engineering" → "intent engineering." gepa-adk already addresses all three through its existing evolvable surfaces:

| C-Suite Buzzword | What It Means | gepa-adk Capability (Shipped) |
|---|---|---|
| **Prompt Engineering** | Improving what you tell the agent to do | Instruction text evolution via `evolve()` |
| **Context Engineering** | Structuring what the agent produces and how it's configured | Output schema evolution + GenerateContentConfig evolution |
| **Intent Engineering** | Shaping the complete agent definition to align behavior with business intent | Multi-surface evolution across the full agent definition in symphony |

The CTO pitch: "Automate prompt, context, and intent engineering across your entire agent fleet. Every optimization decision has an audit trail. Works with Google ADK."

### Core Features (MVP — Current State + Polish)

**Already shipped and functional:**
- `evolve()` for single-agent evolution — the entry point for any developer
- `evolve_group()` for multi-agent pipeline evolution — addresses the entanglement problem
- `evolve_workflow()` for workflow structure evolution — preserves SequentialAgent, LoopAgent, ParallelAgent topology
- 3 evolvable surfaces: instruction text, output schema (Pydantic models with AST validation), GenerateContentConfig (temperature, top_k, etc.)
- Critic agents with SimpleCriticOutput and CriticOutput for structured evaluation
- Reflection agents (LiteLLM-based and ADK-based) with component-aware specialization
- Pareto frontier tracking for multi-objective optimization
- Structured logging via structlog — platform-agnostic observability
- Hexagonal architecture with Protocol-based ports — enterprise-grade extensibility
- 85%+ test coverage, CI/CD pipeline, PyPI publishing, MkDocs documentation site

**MVP polish required:**
- **ADK version compatibility** — resolve version mismatch blocking enterprise adoption. Widen supported version range, test against enterprise-deployed ADK versions, fix any API drift
- **Enterprise architecture documentation** — refresh existing docs to tell the enterprise architect story (why hexagonal matters, how Protocols enable extension, how sessions provide audit trails)
- **Enterprise observability guide** — document PostgreSQL session persistence, structured logging to Splunk/Arize/Phoenix/Datadog, trajectory data as audit evidence
- **C-Suite positioning materials** — frame existing capabilities as prompt/context/intent engineering automation at scale with audit trails
- **Getting-started validation** — ensure the 15-minute onboarding experience works on enterprise ADK versions
- **Examples validation** — verify all examples run cleanly on supported ADK version range

### Out of Scope for MVP

| Deferred Item | Rationale | When |
|---|---|---|
| **Model selection evolution** | High value but requires new ModelHandler + capability validator. Architecture supports it; defer until polish sprint proves the pattern | Fast follow |
| **Hybrid optimization (evolutionary + gradient)** | Technical research complete. New adapter, not core engine change. Defer until base is enterprise-validated | Fast follow |
| **YAML agent definition evolution** | Highest ambition surface. Needs robust YAML validator and spec maturity | Future vision |
| **Distributed evolution** | Premature — no enterprise demand signal yet | Future vision |
| **Sub-agent composition evolution** | Complex search space, needs research | Future vision |
| **Full experiment tracking platform** | Build the hooks/interfaces now; W&B/MLflow integration deferred | Future vision |
| **Encrypted session storage** | Separate project; out of scope for gepa-adk core | Separate effort |
| **Tool configuration evolution** | Defer until model evolution proves the expansion pattern | Future vision |

### MVP Success Criteria

The MVP is complete when:

1. **Rafael can pitch it internally** — the multi-surface evolution + observability + audit trail story is documented and demonstrable to a CTO audience
2. **Marcus can integrate it** — ADK version compatibility resolved, platform integration patterns documented
3. **Priya runs it in 15 minutes** — getting-started experience validated on enterprise ADK version
4. **Kenji sees the trajectory** — Pareto data is exportable, batch evolution patterns are documented even if thin wrapper isn't shipped yet
5. **Still alone in the pool** — no competitor has shipped multi-surface, workflow-aware agent evolution

### Fast Follow (Weeks After MVP)

- **Batch evolution wrapper** — thin orchestration layer for fleet optimization use cases
- **Model evolution** — 4th evolvable surface via new ModelHandler with capability-aware validation
- **Multi-agent pipeline tutorial** — Marcus's integration story as a complete walkthrough
- **Hybrid optimization adapter** — combine evolutionary mutation with gradient-like feedback (research completed)

### Future Vision

If gepa-adk succeeds, it becomes the **enterprise agent industrialization platform**:

- **Complete agent genotype evolution** — all 7 surfaces (instruction, schema, config, model, YAML definition, tool configuration, sub-agent composition) evolved simultaneously across multi-agent workflows
- **Fleet-level optimization dashboards** — organizational view of agent quality, cost, and compliance across thousands of automation use cases
- **Hybrid optimization as default** — evolutionary search + gradient-based refinement + compiler-style verification in a unified pipeline
- **Framework expansion** — Protocol-based architecture enables adapters for LangChain, CrewAI, AutoGen, and other agent frameworks beyond Google ADK
- **Community marketplace** — ecosystem of community-contributed ComponentHandlers, Scorers, Critics, and Stoppers
- **Enterprise deployment playbook** — complete guide for regulated industries (finance, healthcare, insurance, government) including compliance frameworks, audit patterns, and cost optimization strategies

The progression: **craft tool → enterprise platform → industry standard.** The open-source foundation ensures adoptability and community trust. The enterprise capabilities ensure organizational value. The category-first positioning ensures long-term defensibility
