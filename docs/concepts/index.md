# Concepts

This section explains **how gepa-adk works** and **why it works that way**. While [Guides](../guides/single-agent.md) show you how to accomplish tasks, these concept documents help you understand the underlying mechanics.

## What You'll Learn

| Document | Question Answered |
|----------|-------------------|
| [GEPA Fundamentals](gepa-fundamentals.md) | What is GEPA and how does evolutionary optimization work? |
| [Single-Agent Evolution](single-agent-evolution.md) | How does evolution work for a single agent? |
| [Multi-Agent Evolution](multi-agent-evolution.md) | How do multiple agents evolve together? |
| [Workflow Agents](workflow-agents.md) | How do workflow structures (Sequential, Loop, Parallel) evolve? |

## How This Relates to Other Documentation

Following the [Diátaxis framework](https://diataxis.fr/), our documentation is organized into four types:

- **Tutorials** ([Getting Started](../getting-started.md)) - Learning-oriented, for newcomers
- **How-to Guides** ([Guides](../guides/single-agent.md)) - Task-oriented, for practitioners
- **Reference** ([API Reference](../reference/index.md)) - Information-oriented, for lookup
- **Explanation** (You are here) - Understanding-oriented, for deeper learning

## When to Read These

Read the concept documents when you want to:

- Understand *why* a feature works the way it does
- Debug unexpected behavior by understanding the mechanics
- Make architectural decisions about how to structure your agents
- Contribute to gepa-adk and need to understand the design

## Quick Concept Overview

**GEPA** (Genetic-Pareto prompt optimizer) improves agent instructions through an evolutionary loop:

```
┌─────────────────────────────────────────────────────┐
│                  Evolution Loop                      │
│                                                      │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│   │ Evaluate │───▶│ Reflect  │───▶│ Propose  │     │
│   └──────────┘    └──────────┘    └──────────┘     │
│        ▲                               │            │
│        │         ┌──────────┐          │            │
│        └─────────│  Accept  │◀─────────┘            │
│                  └──────────┘                       │
└─────────────────────────────────────────────────────┘
```

1. **Evaluate** - Run the agent on training examples, get scores
2. **Reflect** - Analyze what worked and what didn't
3. **Propose** - Generate improved instruction text
4. **Accept/Reject** - Keep improvements, discard regressions

This loop applies to single agents, multi-agent groups, and complex workflow structures—each with specific mechanics explained in the documents below.
