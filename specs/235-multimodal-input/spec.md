# Feature Specification: Multimodal Input Support for Trainset/Valset

**Feature Branch**: `235-multimodal-input`
**Created**: 2026-01-27
**Status**: Draft
**Input**: GitHub Issue #235 - Add multimodal input support (video blobs) for trainset/valset

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evolve Video Transcript Agent (Priority: P1)

As an ML engineer evolving video analysis agents, I want to provide video files in trainset examples alongside a text prompt, so that GEPA can evolve agent instructions to produce better video transcripts.

**Why this priority**: This is the primary use case - enabling multimodal evolution with videos. Without this, users cannot use GEPA to optimize video analysis agents at all.

**Independent Test**: Can be fully tested by providing a trainset with video paths and verifying the evolved agent produces improved transcripts. Delivers immediate value for video analysis workflows.

**Acceptance Scenarios**:

1. **Given** I have a video file and a trainset with `{"input": "transcribe this lecture", "videos": ["/path/to/lecture.mp4"]}`, **When** I call `evolve(agent, trainset)`, **Then** the video content is processed alongside the text prompt and GEPA evolves the instruction based on transcript quality.

2. **Given** I have a critic agent that evaluates transcript quality, **When** evolution completes, **Then** the evolved instruction produces transcripts with improved critic scores compared to the original.

---

### User Story 2 - Maintain Backward Compatibility (Priority: P1)

As a developer with existing text-only trainsets, I want my current evolution workflows to continue working unchanged, so that adopting multimodal support doesn't break my existing code.

**Why this priority**: Breaking existing workflows would be a critical regression. This must be guaranteed alongside multimodal support.

**Independent Test**: Can be tested by running existing text-only trainsets through evolution and verifying identical behavior to current implementation.

**Acceptance Scenarios**:

1. **Given** I have an existing text-only trainset `[{"input": "What is 2+2?", "expected": "4"}]`, **When** I call `evolve(agent, trainset)`, **Then** evolution works exactly as before with no changes to behavior or results.

2. **Given** I have a trainset without any `videos` field, **When** the system processes the trainset, **Then** no video-related processing occurs and performance is unchanged.

---

### User Story 3 - Multiple Videos Per Example (Priority: P2)

As a developer building comparison agents, I want to provide multiple video files in a single trainset example, so that my agent can learn to analyze and compare multiple videos.

**Why this priority**: Important extension of the core feature, but not required for initial value delivery. Enables more sophisticated use cases like video comparison and multi-source analysis.

**Independent Test**: Can be tested by providing an example with multiple video paths and verifying all videos are processed together in a single agent invocation.

**Acceptance Scenarios**:

1. **Given** I have a trainset example with `{"input": "compare these videos", "videos": ["/path/to/video1.mp4", "/path/to/video2.mp4"]}`, **When** I call `evolve(agent, trainset)`, **Then** both videos are provided to the agent in a single request.

2. **Given** I have an example with three video files, **When** the system processes the example, **Then** all three videos are included in the agent's input content.

---

### User Story 4 - Video-Only Input Without Text (Priority: P3)

As a developer building video-first agents, I want to provide video files without requiring companion text, so that I can evolve agents that operate purely on visual content.

**Why this priority**: Nice-to-have flexibility. Most use cases will include text prompts, but supporting video-only input provides complete flexibility.

**Independent Test**: Can be tested by providing a trainset with only the `videos` field (no `input` field) and verifying the video is processed correctly.

**Acceptance Scenarios**:

1. **Given** I have a trainset example with `{"videos": ["/path/to/video.mp4"]}` and no `input` field, **When** I call `evolve(agent, trainset)`, **Then** the video is processed without any text prompt.

---

### Edge Cases

- What happens when a video file path does not exist? System must provide a clear error message identifying the missing file.
- What happens when a video file exceeds the 2GB size limit? System must reject the file with a descriptive error before attempting to load it into memory.
- What happens when a video file has an unsupported MIME type? System must validate that the file is a video format and reject non-video files.
- What happens when both `input` and `videos` fields are empty/missing? System must require at least one valid input (text or video).
- What happens when the same video is referenced multiple times in a single example? System must handle duplicates gracefully (process once or process each reference).
- What happens when video files are very large and multiple examples use videos? System must manage memory efficiently during batch processing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support an optional `videos` field in trainset/valset examples containing a list of file paths to video files.
- **FR-002**: System MUST convert video files to inline data blobs suitable for multimodal agent processing.
- **FR-003**: System MUST combine text input (if provided) with video content into a single multimodal message for agent execution.
- **FR-004**: System MUST maintain full backward compatibility with text-only trainsets (no `videos` field).
- **FR-005**: System MUST validate that video file paths exist and are readable before processing.
- **FR-006**: System MUST validate that video files do not exceed 2GB in size (provider constraint).
- **FR-007**: System MUST validate that files referenced in `videos` field are video MIME types (video/*).
- **FR-008**: System MUST support multiple video files per trainset example.
- **FR-009**: System MUST support video-only examples (no `input` text field required when `videos` is present).
- **FR-010**: System MUST require at least one of `input` (text) or `videos` to be present in each trainset example.
- **FR-011**: System MUST provide clear, actionable error messages for all validation failures.

### Key Entities

- **Trainset Example**: A dictionary containing input data for evolution. Extended to support optional `videos` field (list of file paths) alongside existing `input` (text) and `expected` (reference output) fields.
- **Video Blob**: Binary video content converted to a format suitable for multimodal agent input. Contains the video bytes and associated MIME type.
- **Multimodal Content**: Combined representation of text and video parts for agent input. Assembles multiple content types into a single message.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully evolve agents using trainsets containing video files within standard evolution timeframes (accounting for video processing overhead).
- **SC-002**: Existing text-only trainsets produce identical results to the current implementation (100% backward compatibility).
- **SC-003**: Users receive clear error messages within 1 second when providing invalid video paths, oversized files, or non-video files.
- **SC-004**: System successfully processes trainset examples with up to 5 videos per example.
- **SC-005**: Evolution with video inputs completes without memory errors for standard video sizes (under 500MB per video).

## Assumptions

- Video files are stored on the local filesystem accessible to the process running evolution.
- The underlying model provider (e.g., Gemini) supports multimodal inputs with video content.
- Video files are in standard formats supported by the model provider (e.g., MP4, MOV, AVI).
- The 2GB file size limit is derived from Gemini API constraints and may be adjusted based on provider documentation.
- Users are responsible for ensuring video files are appropriately sized for their use case and available memory.

## Scope Boundaries

### In Scope

- Video file support in trainset/valset examples
- Conversion of video files to inline data blobs
- Combining text and video content for agent execution
- Validation of video file paths, sizes, and types
- Backward compatibility with text-only trainsets

### Out of Scope

- Image file support (may be added in future iteration)
- Audio-only file support (may be added in future iteration)
- Video streaming or URL-based video inputs
- Video preprocessing (resizing, compression, format conversion)
- Remote video file storage (S3, GCS, etc.)
- Video caching across evolution iterations (may be added as optimization)
