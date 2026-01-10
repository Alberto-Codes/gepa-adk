---
applyTo: "**/*architecture*.md"
description: "Mermaid diagram best practices - use diagrams liberally but appropriately to visualize complex concepts, processes, and relationships"
---

# Mermaid Diagram Guidelines

Use Mermaid diagrams to make documentation clearer, more maintainable, and easier to understand. Mermaid enables text-based diagrams that can be version-controlled alongside code.

## Core Principle: Visualize for Clarity

**Use Mermaid diagrams when:**
- Visual representation makes concepts clearer than prose alone
- Showing relationships, flows, or structures
- Documenting processes, architectures, or interactions
- Explaining complex logic or decision trees
- Illustrating system behavior or state transitions

**Avoid diagrams when:**
- Simple text or a list is equally clear
- The diagram would be overly complex (>20 nodes typically)
- Information is better suited for tables or code examples

---

## Diagram Types and Use Cases

### Flowcharts
**Purpose:** Visualize processes, algorithms, decision logic, and workflows

**Use flowcharts for:**
- Algorithm steps and control flow
- Business processes and procedures
- Decision trees and conditional logic
- System workflows and pipelines
- Troubleshooting guides
- User journeys through features

**Syntax:**
```mermaid
flowchart TD
    A[Start] --> B{Decision?}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
```

**Best practices:**
- Use `TD` (top-down) or `LR` (left-right) based on content flow
- Keep nodes descriptive but concise
- Use shapes meaningfully: rectangles for steps, diamonds for decisions, rounded for start/end
- Limit branches to maintain readability
- Add labels to edges for clarity on decision paths

---

### Sequence Diagrams
**Purpose:** Show interactions between actors/systems over time

**Use sequence diagrams for:**
- API request/response flows
- Authentication/authorization workflows
- Service-to-service communication
- Multi-step processes with multiple actors
- Error handling and edge cases
- Message passing between components

**Syntax:**
```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant Database
    
    Client->>Server: POST /api/users
    activate Server
    Server->>Database: INSERT user
    Database-->>Server: User ID
    Server-->>Client: 201 Created
    deactivate Server
```

**Best practices:**
- Order participants logically (left to right by call frequency)
- Use `activate`/`deactivate` to show processing time
- Add `autonumber` for step references
- Use notes for important context: `Note over Server: Validates input`
- Show both success and error paths with `alt`/`else`
- Use `par` for parallel operations
- Group related actors with `box`

---

### Class Diagrams
**Purpose:** Model object-oriented structure, relationships, and data models

**Use class diagrams for:**
- Code architecture and class structure
- Database schema visualization
- API data models
- Design patterns
- Inheritance hierarchies
- Interface definitions

**Syntax:**
```mermaid
classDiagram
    class User {
        +String username
        +String email
        -String passwordHash
        +login()
        +logout()
    }
    class Post {
        +String title
        +String content
        +DateTime createdAt
    }
    User "1" --> "*" Post: creates
```

**Best practices:**
- Use visibility modifiers: `+` public, `-` private, `#` protected
- Show key attributes and methods only (avoid clutter)
- Indicate relationships clearly: inheritance `<|--`, composition `*--`, aggregation `o--`
- Add cardinality for relationships: `"1"`, `"*"`, `"0..1"`
- Group related classes
- Use interfaces/abstract classes with `<<interface>>`

---

### State Diagrams
**Purpose:** Visualize state machines and transitions

**Use state diagrams for:**
- Application state management
- Order/workflow status
- UI component states
- Connection states (connected/disconnected/error)
- Document approval workflows
- Game states
- Protocol state machines

**Syntax:**
```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Review: Submit
    Review --> Approved: Accept
    Review --> Draft: Reject
    Approved --> Published: Publish
    Published --> [*]
```

**Best practices:**
- Start with `[*]` for initial state
- Label transitions clearly
- Use notes for complex conditions
- Consider composite states for nested state machines
- Keep states at similar abstraction levels

---

### Gantt Charts
**Purpose:** Project timelines, schedules, and task dependencies

**Use Gantt charts for:**
- Project planning and milestones
- Release schedules
- Task dependencies and timelines
- Sprint planning visualization
- Roadmap communication

**Syntax:**
```mermaid
gantt
    title Project Timeline
    dateFormat YYYY-MM-DD
    section Development
    Design          :done, des1, 2024-01-01, 2024-01-05
    Implementation  :active, dev1, 2024-01-06, 10d
    Testing         :test1, after dev1, 5d
    section Deployment
    Staging         :after test1, 3d
    Production      :2024-01-24, 1d
```

**Best practices:**
- Use clear section names for grouping
- Mark completed tasks as `:done`
- Show active tasks with `:active`
- Use `after` for dependencies
- Set realistic date formats
- Add milestones with `:milestone`

---

### Entity Relationship Diagrams (ERD)
**Purpose:** Database schema design and relationships

**Use ER diagrams for:**
- Database schema documentation
- Data model design
- Entity relationships and cardinality
- Schema evolution tracking

**Syntax:**
```mermaid
erDiagram
    USER ||--o{ POST : creates
    POST ||--o{ COMMENT : has
    USER ||--o{ COMMENT : writes
    
    USER {
        int id PK
        string username
        string email UK
    }
    POST {
        int id PK
        int user_id FK
        string title
        text content
    }
```

**Best practices:**
- Use cardinality correctly: `||--||` one-to-one, `||--o{` one-to-many, `}o--o{` many-to-many
- Mark primary keys with `PK`
- Mark foreign keys with `FK`
- Mark unique constraints with `UK`
- Keep entity names singular and uppercase

---

### Git Graphs
**Purpose:** Visualize Git branching and merging strategies

**Use Git graphs for:**
- Explaining branching strategies
- Documenting Git workflows
- Release management processes
- Merge/rebase demonstrations

**Syntax:**
```mermaid
gitGraph
    commit
    branch develop
    checkout develop
    commit
    branch feature
    checkout feature
    commit
    commit
    checkout develop
    merge feature
    checkout main
    merge develop
```

**Best practices:**
- Show realistic workflows
- Use `commit id: "message"` for important commits
- Demonstrate branch naming conventions
- Show merge vs rebase patterns
- Keep graphs focused on key concepts

---

### User Journey Diagrams
**Purpose:** Map user experiences and satisfaction through processes

**Use user journey diagrams for:**
- UX research documentation
- Customer experience mapping
- Feature adoption flows
- Onboarding processes

**Syntax:**
```mermaid
journey
    title User Onboarding Experience
    section Registration
      Visit landing page: 5: User
      Fill form: 3: User
      Verify email: 4: User
    section First Use
      Complete tutorial: 4: User
      Create first project: 5: User
```

---

### Pie and XY Charts
**Purpose:** Simple data visualization

**Use charts for:**
- Proportional data (pie)
- Metrics and statistics
- Trend visualization (XY)
- Quick data insights

**Syntax:**
```mermaid
pie title Distribution
    "API Calls" : 45
    "Page Loads" : 30
    "Background Jobs" : 25
```

---

## General Best Practices

### When to Create Diagrams
- **Documentation**: Explain architecture, APIs, processes
- **Planning**: Design before implementation
- **Communication**: Share complex ideas with team
- **Debugging**: Map out system behavior
- **Onboarding**: Help new team members understand systems

### Diagram Quality Standards
1. **Clarity over completeness**: Show what matters, hide details
2. **Consistent naming**: Use project terminology
3. **Appropriate abstraction**: Match detail level to audience
4. **Self-documenting**: Diagram should be understandable without extensive external explanation
5. **Keep it simple**: If diagram has >20 nodes, consider breaking it up

### Formatting Conventions
- Use descriptive node/entity names
- Add notes for important context
- Apply consistent styling within project
- Use subgraphs/sections to organize large diagrams
- Include titles for context: `---\ntitle: My Diagram\n---`

### Comments and Maintenance
```mermaid
flowchart TD
    %% This is a comment - explains diagram purpose
    A[Start] --> B[Process]
```

- Add comments to explain complex logic
- Update diagrams when code changes
- Date-stamp significant diagram updates in comments
- Include diagram purpose in comment header

---

## Common Patterns

### API Documentation Pattern
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Auth
    participant DB
    
    Client->>API: GET /resource
    API->>Auth: Verify token
    Auth-->>API: Valid
    API->>DB: Query data
    DB-->>API: Results
    API-->>Client: 200 OK
```

### State Machine Pattern
```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Processing: start()
    Processing --> Success: complete()
    Processing --> Failed: error()
    Success --> [*]
    Failed --> Idle: retry()
    Failed --> [*]: abort()
```

### System Architecture Pattern
```mermaid
flowchart TB
    subgraph Client
        Web[Web App]
        Mobile[Mobile App]
    end
    subgraph Backend
        API[API Gateway]
        Auth[Auth Service]
        DB[(Database)]
    end
    Web --> API
    Mobile --> API
    API --> Auth
    API --> DB
```

### Decision Tree Pattern
```mermaid
flowchart TD
    Start{Has Account?}
    Start -->|Yes| Login[Login]
    Start -->|No| Signup[Sign Up]
    Login --> Check{Credentials Valid?}
    Check -->|Yes| Success[Dashboard]
    Check -->|No| Error[Show Error]
    Error --> Login
    Signup --> Verify[Verify Email]
    Verify --> Success
```

---

## Integration Tips

### In Markdown Files
Use code blocks with `mermaid` language:

````markdown
```mermaid
flowchart LR
    A --> B
```
````

### In Code Comments
For languages supporting markdown in comments:
```python
"""
Process flow:

```mermaid
flowchart TD
    Input --> Validate --> Process --> Output
```
"""
```

### In Documentation Sites
Most documentation platforms support Mermaid natively:
- GitHub/GitLab markdown
- Notion
- Confluence (with plugins)
- Documentation generators (MkDocs, Docusaurus, etc.)

---

## Accessibility Considerations

- Provide text descriptions alongside complex diagrams
- Use descriptive node labels, not just symbols
- Ensure sufficient contrast in custom themes
- Include diagram purpose in surrounding text
- Consider providing both visual diagram and text-based alternative

---

## Quick Reference: Choosing Diagram Type

| Need to Show... | Use This Diagram Type |
|----------------|----------------------|
| Step-by-step process | Flowchart |
| System interactions over time | Sequence Diagram |
| Object structure and relationships | Class Diagram |
| State transitions | State Diagram |
| Project timeline | Gantt Chart |
| Database schema | ER Diagram |
| Git workflow | Git Graph |
| User experience journey | User Journey |
| Data proportions | Pie Chart |

---

## Resources

- Official documentation: https://mermaid.js.org/
- Live editor for testing: https://mermaid.live/
- Syntax reference: https://mermaid.js.org/intro/syntax-reference.html

## Summary

Use Mermaid diagrams liberally to:
- Make complex concepts visual and clear
- Keep documentation close to code
- Enable easy updates and version control
- Improve team communication
- Reduce misunderstandings

Choose diagram types based on what you're communicating, keep diagrams focused and clear, and update them as systems evolve.