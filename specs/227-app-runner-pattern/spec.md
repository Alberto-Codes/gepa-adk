# Feature Specification: Support ADK App/Runner Pattern for Evolution

**Feature Branch**: `227-app-runner-pattern`
**Created**: 2026-01-24
**Status**: Draft
**Input**: User description: "Support ADK App/Runner pattern for evolution (GitHub issue #227)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Existing Infrastructure Integration (Priority: P1)

As a developer with an existing production agent application, I want to pass my pre-configured application instance to the evolution system, so that evolution uses my existing plugins, artifact service, memory service, and session configuration without requiring me to reconfigure everything.

**Why this priority**: This is the core value proposition - enabling seamless integration with existing infrastructure. Without this, users must duplicate configuration or abandon their existing setup, creating friction and potential inconsistencies.

**Independent Test**: Can be fully tested by configuring an application with custom services (artifact storage, session management) and verifying that evolution operations use those services rather than creating new defaults.

**Acceptance Scenarios**:

1. **Given** I have an application configured with custom artifact and session services, **When** I invoke evolution with my application instance, **Then** evolution stores artifacts using my artifact service and manages sessions using my session service.
2. **Given** I have an application with plugins configured (e.g., monitoring, logging), **When** I invoke evolution with my application instance, **Then** evolution respects and triggers my configured plugins during execution.
3. **Given** I have an application with memory services configured, **When** I invoke evolution with my application instance, **Then** evolution can access and utilize long-term memory through my configured service.

---

### User Story 2 - Runner-Based Evolution (Priority: P2)

As a developer who manages agent execution through a Runner, I want to pass my Runner directly to the evolution system, so that I maintain control over session creation and service configuration while leveraging evolution capabilities.

**Why this priority**: Runners provide fine-grained control over execution. This is valuable for users who need specific session management or have custom service configurations but don't need the full application abstraction.

**Independent Test**: Can be tested by creating a Runner with specific session and artifact services, passing it to evolution, and verifying that sessions are created and artifacts are stored through the Runner's configured services.

**Acceptance Scenarios**:

1. **Given** I have a Runner configured with custom session and artifact services, **When** I invoke evolution with my Runner instance, **Then** evolution uses my Runner's services for all operations.
2. **Given** I have a Runner instance, **When** I invoke evolution with my Runner, **Then** evolution creates all sessions through my Runner rather than creating its own.

---

### User Story 3 - Backward Compatible Direct Workflow (Priority: P3)

As an existing user of the evolution system, I want my current integration (passing workflow agents directly) to continue working unchanged, so that I don't need to modify my existing code when upgrading.

**Why this priority**: Backward compatibility ensures smooth upgrades and protects existing users' investments. This maintains trust and reduces upgrade friction.

**Independent Test**: Can be tested by running existing code that passes workflow agents directly and verifying identical behavior to previous versions.

**Acceptance Scenarios**:

1. **Given** I have existing code that passes a workflow agent directly, **When** I upgrade to the new version and run my code unchanged, **Then** the behavior is identical to the previous version.
2. **Given** I pass a workflow agent without any application or runner configuration, **When** I invoke evolution, **Then** the system uses default services as it does today.

---

### Edge Cases

- What happens when a user provides both an application instance AND a Runner? The system should have clear precedence rules and communicate which configuration is used.
- What happens when an application instance is provided but its services are not properly initialized? The system should provide clear error messages.
- What happens when a Runner's underlying services become unavailable during evolution? The system should handle service failures gracefully with appropriate error reporting.
- What happens when the provided application or Runner has incompatible configuration (e.g., missing required services)? The system should validate configuration and provide actionable feedback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an optional application instance parameter that provides access to configured services (session, artifact, memory, plugins).
- **FR-002**: System MUST accept an optional Runner instance parameter that provides direct access to session and artifact services.
- **FR-003**: System MUST continue to accept workflow agents directly for backward compatibility.
- **FR-004**: System MUST define and document clear precedence when multiple configuration sources are provided (Runner takes precedence over application, which takes precedence over direct workflow).
- **FR-005**: When an application instance is provided, system MUST use the application's session service for all session operations.
- **FR-006**: When an application instance is provided, system MUST use the application's artifact service for all artifact storage operations.
- **FR-007**: When an application instance is provided, system MUST respect and trigger the application's configured plugins.
- **FR-008**: When a Runner is provided, system MUST use the Runner's session service for session management.
- **FR-009**: When a Runner is provided, system MUST use the Runner's artifact service for artifact operations.
- **FR-010**: System MUST validate that provided application or Runner instances have the required services configured before proceeding.
- **FR-011**: System MUST provide clear error messages when configuration is invalid or services are unavailable.
- **FR-012**: When no application or Runner is provided, system MUST fall back to existing default behavior.

### Key Entities

- **Application Instance**: A configured application object that encapsulates agent configuration along with associated services (session, artifact, memory) and plugins. Represents the recommended production deployment pattern.
- **Runner Instance**: An execution controller that manages agent invocations with specific session and artifact service configurations. Provides fine-grained control over execution without the full application abstraction.
- **Session Service**: A service responsible for creating, managing, and persisting agent sessions. Enables features like resumability and session history.
- **Artifact Service**: A service responsible for storing and retrieving files and binary data produced during agent execution.
- **Plugin**: An extension point that allows custom pre-processing and post-processing logic during agent execution (e.g., monitoring, logging, context caching).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users with existing application infrastructure can integrate evolution capabilities without duplicating any service configuration (zero configuration redundancy).
- **SC-002**: Users can verify their custom services are being used by evolution within one test execution (immediate validation).
- **SC-003**: Existing integrations using direct workflow passing continue to work with no code changes (100% backward compatibility).
- **SC-004**: Invalid configurations are detected and reported with actionable error messages before evolution begins (fail-fast validation).
- **SC-005**: Integration documentation enables a new user to configure and use the application/runner pattern within 15 minutes of reading.

## Assumptions

- Users providing application or Runner instances are expected to have properly initialized their services before passing them to evolution.
- The existing evolution API surface remains stable; only new optional parameters are added.
- Service failures during evolution will be handled by the user's configured error handling mechanisms, consistent with their application's behavior elsewhere.
- Plugin execution order and behavior follows the application's existing plugin configuration.

## Dependencies

- This feature depends on the session service parameter exposure (GitHub issue #226) being completed first.
