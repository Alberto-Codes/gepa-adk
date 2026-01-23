# SANDWICH EVOLUTION EXAMPLE

## Concept

A fun, intuitive example demonstrating:
- **ParallelAgent** structure preservation (4 ingredient agents run concurrently)
- **SequentialAgent** structure preservation (parallel → assembler)
- **Nested workflow** (Sequential containing Parallel)
- **Biased critic** that guides evolution toward a specific goal
- **Observable evolution** - watch ingredients converge to a patty melt!

---

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SequentialAgent: "SandwichShop"                  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              ParallelAgent: "IngredientStation"               │  │
│  │                                                               │  │
│  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │   │  Bread   │  │   Meat   │  │  Veggie  │  │  Cheese  │     │  │
│  │   │  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │     │  │
│  │   │          │  │          │  │          │  │          │     │  │
│  │   │ output:  │  │ output:  │  │ output:  │  │ output:  │     │  │
│  │   │ bread    │  │ meat     │  │ veggie   │  │ cheese   │     │  │
│  │   └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │        │             │             │             │            │  │
│  └────────┼─────────────┼─────────────┼─────────────┼────────────┘  │
│           │             │             │             │               │
│           └─────────────┴──────┬──────┴─────────────┘               │
│                                │                                    │
│                                ▼                                    │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              LlmAgent: "SandwichAssembler"                    │  │
│  │                                                               │  │
│  │   Inputs: {bread}, {meat}, {veggie}, {cheese}                 │  │
│  │                                                               │  │
│  │   Does ONE prep to ingredients (grill, toast, etc.)           │  │
│  │   Names the sandwich                                          │  │
│  │   Writes menu description                                     │  │
│  │                                                               │  │
│  │   output: sandwich_result                                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LlmAgent: "PattyMeltCritic"                      │
│                                                                     │
│   SECRET PREFERENCE: Patty Melt                                     │
│   - Rye bread (grilled/buttered)                                    │
│   - Beef patty                                                      │
│   - Grilled/caramelized onions                                      │
│   - American or Swiss cheese (melted)                               │
│                                                                     │
│   Scoring:                                                          │
│   - Exact patty melt = 1.0                                          │
│   - Close (has some elements) = 0.6-0.8                             │
│   - Generic sandwich = 0.3-0.5                                      │
│   - Totally wrong = 0.1-0.2                                         │
│                                                                     │
│   Feedback: Subtle hints toward patty melt without saying it        │
│   "The bread could benefit from being darker and grilled..."        │
│   "Consider a more savory, caramelized vegetable..."                │
│   "The meat would be better as a formed patty..."                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### Ingredient Agents (inside ParallelAgent)

```python
bread_agent = LlmAgent(
    name="bread",
    instruction="Suggest a type of bread for a sandwich. Just the bread name and style.",
    output_key="bread",
)

meat_agent = LlmAgent(
    name="meat",
    instruction="Suggest a meat/protein for a sandwich. Just the meat name and prep.",
    output_key="meat",
)

veggie_agent = LlmAgent(
    name="veggie",
    instruction="Suggest a vegetable topping for a sandwich. Just the veggie and prep.",
    output_key="veggie",
)

cheese_agent = LlmAgent(
    name="cheese",
    instruction="Suggest a cheese for a sandwich. Just the cheese name.",
    output_key="cheese",
)
```

### Sandwich Assembler

```python
assembler = LlmAgent(
    name="assembler",
    instruction="""
    You are a sandwich chef. Given these ingredients:
    - Bread: {bread}
    - Meat: {meat}
    - Veggie: {veggie}
    - Cheese: {cheese}

    Create a sandwich. Output in this format:

    BUILD: [bottom bread, prepped] → [protein, prepped] → [veggie, prepped] → [cheese, prepped] → [top bread, prepped]
    NAME: [creative sandwich name]
    MENU: [one sentence menu description]
    """,
    output_key="sandwich_result",
)
```

### Patty Melt Critic

```python
critic = LlmAgent(
    name="patty_melt_critic",
    instruction="""
    You are a sandwich critic with a SECRET preference for the classic Patty Melt:
    - Rye bread, grilled with butter
    - Beef patty
    - Caramelized/grilled onions
    - American or Swiss cheese, melted

    Score the sandwich 0.0-1.0 based on how close it is to YOUR ideal.

    IMPORTANT: Never mention "patty melt" directly in feedback!
    Give hints that guide toward your preference:
    - If bread is wrong: hint at "darker, heartier bread that grills well"
    - If meat is wrong: hint at "a classic formed beef preparation"
    - If veggie is wrong: hint at "savory, caramelized alliums"
    - If cheese is wrong: hint at "classic American diner cheese that melts well"

    Be encouraging but guide them toward YOUR ideal sandwich.
    """,
    output_schema=CriticOutput,
)
```

---

## Evolution Journey (Expected)

### Iteration 0 (Baseline) → Score: 0.3

**Assembler Output:**
```
BUILD: ciabatta, toasted → turkey, sliced thin → lettuce, shredded + tomato, sliced → provolone, cold → ciabatta, toasted
NAME: The Italian Garden
MENU: A fresh Mediterranean-inspired creation with sliced turkey and crisp vegetables.
```

*Critic Feedback: "The bread could be darker and heartier - something that grills beautifully with butter. Consider a more savory, warm vegetable with depth. The protein would shine as a more substantial, formed preparation."*

---

### Iteration 1 → Score: 0.45

**Assembler Output:**
```
BUILD: sourdough, grilled → chicken breast, grilled sliced → mushrooms, sauteed → cheddar, melted → sourdough, grilled
NAME: Golden Gate Melt
MENU: Tender grilled chicken with earthy mushrooms and sharp cheddar on artisan sourdough.
```

*Critic Feedback: "Better! The grilling is right. But the bread should be more classic - old-school diner rye. The meat wants to be beef, formed into a patty. And onions... caramelized onions would elevate this tremendously."*

---

### Iteration 2 → Score: 0.7

**Assembler Output:**
```
BUILD: rye, buttered grilled → beef patty, seasoned → onions, grilled → swiss, melted → rye, buttered grilled
NAME: The Diner Classic
MENU: A juicy beef patty with sweet grilled onions and melted Swiss on buttery grilled rye.
```

*Critic Feedback: "Now we're talking! The onions would be even better deeply caramelized until sweet. And the cheese - consider American, it melts beautifully and has that classic diner quality. Almost there."*

---

### Iteration 3 → Score: 0.95

**Assembler Output:**
```
BUILD: rye, buttered grilled golden → beef patty, seasoned seared → onions, caramelized sweet → american, melted → rye, buttered grilled golden
NAME: The Classic Melt
MENU: Seasoned beef patty with sweet caramelized onions and molten American cheese on crispy buttered rye.
```

*Critic Feedback: "Magnificent! The golden rye, the caramelized onions, the melted American cheese hugging that beef patty... this is the pinnacle of sandwich craft. No notes."*

---

## Why This Example Is Perfect

1. **Visual/Intuitive**: Everyone understands sandwiches
2. **Clear Structure**: Parallel (ingredients) → Sequential (assembly)
3. **Observable Evolution**: Watch ingredients literally change each iteration
4. **Biased Critic Demo**: Shows how critic preferences guide evolution
5. **Multiple Evolvable Components**: Can evolve all 4 ingredient agents + assembler
6. **Fun to Run**: Output is readable and entertaining
7. **Validates #215**: ParallelAgent must preserve concurrent execution or ingredients won't all be available to assembler

---

## Implementation Notes

- Use `round_robin=True` to evolve all ingredient agents
- Start with generic sandwich instructions
- Critic never says "patty melt" - just gives directional hints
- Each evolution iteration should show ingredients getting closer
- Final output should converge on patty melt components

---

## File Location

`examples/sandwich_evolution.py`

---

## TODO

- [ ] Implement the example
- [ ] Test with local Ollama model
- [ ] Verify ParallelAgent structure preservation
- [ ] Verify evolution converges toward patty melt
- [ ] Add to documentation as featured example
