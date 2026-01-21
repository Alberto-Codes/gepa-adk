# Feature Specification: ComponentHandler Protocol and Registry

**Feature Branch**: `162-component-handlers`
**Created**: 2026-01-20
**Status**: Draft
**Input**: User description: "GitHub Issue #162 - [Refactor] Create ComponentHandler protocol and registry"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define Component Handling Contract (Priority: P1)

As a GEPA maintainer, I want a ComponentHandler protocol that defines a clear contract for component serialization and application, so that all component handlers follow a consistent interface.

**Why this priority**: This is the foundational contract that all handlers must implement. Without the protocol definition, no handlers can be created or validated.

**Independent Test**: Can be fully tested by creating a mock implementation that satisfies the protocol and verifying type compliance. Delivers the core abstraction that enables extensibility.

**Acceptance Scenarios**:

1. **Given** the ComponentHandler protocol, **When** I examine its interface, **Then** it defines a serialize method that extracts component values from an agent as a string
2. **Given** the ComponentHandler protocol, **When** I examine its interface, **Then** it defines an apply method that sets evolved values on an agent and returns the original value
3. **Given** the ComponentHandler protocol, **When** I examine its interface, **Then** it defines a restore method that reinstates the original value on an agent
4. **Given** a class that implements all three methods, **When** I check protocol compliance, **Then** the class is recognized as a valid ComponentHandler

---

### User Story 2 - Lookup Registered Handlers (Priority: P1)

As a GEPA maintainer, I want a registry that allows handler lookup by component name, so that the adapter can retrieve the appropriate handler for each component type.

**Why this priority**: Registry lookup is essential for the adapter to use handlers at runtime. Without this, the protocol is defined but unusable.

**Independent Test**: Can be fully tested by registering handlers and verifying they are retrievable by name. Delivers the mechanism to access handlers dynamically.

**Acceptance Scenarios**:

1. **Given** registered handlers for "instruction" and "output_schema" components, **When** I request the handler for "instruction", **Then** I receive the correct InstructionHandler instance
2. **Given** a registered handler for a component, **When** I request a handler for an unregistered component, **Then** I receive a clear error indicating the handler is not found
3. **Given** the registry, **When** I check if a handler exists for a component name, **Then** I receive a boolean indicating its presence

---

### User Story 3 - Extend Registry with Custom Handlers (Priority: P2)

As a GEPA developer, I want to register custom handlers for new component types, so that I can extend the system without modifying core adapter code.

**Why this priority**: Extensibility is the primary goal of this refactoring, but depends on the protocol and registry existing first.

**Independent Test**: Can be fully tested by creating a custom handler, registering it, and verifying it can be retrieved and used. Delivers the Open/Closed principle benefit.

**Acceptance Scenarios**:

1. **Given** a custom handler for "my_component" component type, **When** I register it with the registry, **Then** subsequent lookups for "my_component" return my custom handler
2. **Given** an existing registered handler for a component, **When** I register a new handler for the same component, **Then** the new handler replaces the old one
3. **Given** a registered custom handler, **When** I use it to serialize, apply, and restore values, **Then** it behaves according to the ComponentHandler contract

---

### Edge Cases

- What happens when requesting a handler for an empty string component name? System returns a clear error indicating invalid component name.
- What happens when requesting a handler for a None component name? System returns a clear error indicating invalid component name.
- How does the registry handle registering a handler that doesn't implement the protocol? System raises an error at registration time if the handler doesn't satisfy the protocol.
- What happens when serialize is called on an agent without the component set? Handler returns an empty string or sensible default without raising an error.
- What happens when restore is called with a None original value? Handler handles gracefully by resetting the component to its default state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define a ComponentHandler protocol with serialize, apply, and restore methods
- **FR-002**: The serialize method MUST accept an agent and return the component's current value as a string
- **FR-003**: The apply method MUST accept an agent and a string value, apply the value to the agent, and return the original value for later restoration
- **FR-004**: The restore method MUST accept an agent and the original value, restoring the agent to its previous state
- **FR-005**: System MUST provide a ComponentHandlerRegistry class for storing and retrieving handlers
- **FR-006**: The registry MUST support registering handlers by component name
- **FR-007**: The registry MUST support retrieving handlers by component name
- **FR-008**: The registry MUST support checking whether a handler exists for a given component name
- **FR-009**: System MUST provide a default registry instance for global access
- **FR-010**: System MUST provide convenience functions (get_handler, register_handler) that operate on the default registry
- **FR-011**: The protocol MUST be runtime-checkable for type validation

### Key Entities

- **ComponentHandler**: A protocol defining the contract for component serialization, application, and restoration. Has three methods: serialize, apply, and restore.
- **ComponentHandlerRegistry**: A container that maps component names to their handlers. Provides registration, lookup, and existence-checking capabilities.
- **Default Registry**: A singleton instance of ComponentHandlerRegistry used by convenience functions for global handler management.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New component types can be added by implementing a handler class and calling register_handler, without modifying any existing adapter code
- **SC-002**: All existing component handling behavior (instruction, output_schema) remains functionally identical after migration to handlers
- **SC-003**: 100% of handler implementations pass protocol compliance validation at runtime
- **SC-004**: Handler lookup operations complete in constant time regardless of the number of registered handlers
- **SC-005**: All edge cases (missing handlers, invalid inputs) produce clear, actionable error messages

## Assumptions

- The system uses Python's Protocol typing for interface definitions
- Handlers are registered once at startup and remain constant during execution
- Component values can be meaningfully represented as strings for evolution purposes
- The LlmAgent class from google.adk.agents is the primary agent type handlers work with
- Handler registration order does not affect behavior (last registration wins for duplicates)
