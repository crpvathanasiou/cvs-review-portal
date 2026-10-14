# 05 — Code Quality Standards

## 1. Purpose and Authority

This document defines the project-wide code quality and engineering standards for CVS Review Portal.

> **Applicability note.** General engineering rules in this file (structure, typing, Pydantic, FastAPI factory, errors, logging, tests, Ruff/Pyright) **remain in force**. Examples that mention compliance documents, S3, OpenSearch, boto3, Processing Runs, AWS, or LLM/RAG flows are **inherited illustrations**, not CVS Review Portal product requirements. Product boundaries and Step contracts: [`08_portal_specification.md`](08_portal_specification.md).

It applies to:

* application code;
* tests;
* scripts;
* Docker configuration;
* CI workflows;
* infrastructure integration code;
* task-specific implementations;
* AI-assisted code changes performed through Cursor or another coding assistant.

Its purpose is to ensure that implementation remains:

* understandable;
* testable;
* maintainable;
* secure;
* traceable;
* production-disciplined;
* aligned with the approved functional references (currently `08_portal_specification.md`).

This document defines long-lived engineering rules.

Task-specific requirements belong in:

* Task Definitions;
* Detailed Specifications;
* Definitions of Done;
* Architecture Decision Records.

When a task-specific specification conflicts with this document, the conflict must be explicitly identified and resolved before implementation.

The current product specification (`08_portal_specification.md`) is authoritative for portal functional boundaries. Inherited `00_project_reference.md` content is legacy.

---

## 2. Quality Philosophy

CVS Review Portal follows:

```text
Quality by Design
```

Quality must be introduced through:

* clear contracts;
* controlled dependencies;
* explicit lifecycle rules;
* validation;
* guardrails;
* tests;
* observability;
* review;
* measurable completion criteria.

Quality must not depend only on:

* developer memory;
* manual inspection;
* coding-assistant behaviour;
* production monitoring;
* comments describing intended behaviour.

The preferred engineering sequence is:

```text
Understand Requirement
→ Define Contract
→ Implement Small Capability
→ Validate Behaviour
→ Verify Failure Paths
→ Document Result
```

---

## 3. Core Engineering Principles

### 3.1 Correctness Before Abstraction

The implementation should first solve the approved requirement correctly.

Abstractions should be introduced only when they:

* protect an important boundary;
* support testing;
* isolate an external dependency;
* remove meaningful duplication;
* preserve a stable contract;
* are required by an approved future capability.

The project must avoid:

```text
Interface for every function
Factory for every class
Base class without demonstrated reuse
Generic framework before concrete use
Configuration option without a real requirement
```

### 3.2 Simplicity Before Generality

Prefer the simplest design that satisfies:

* current requirements;
* known near-term requirements;
* production safety;
* maintainability.

The project should not optimize for arbitrary future domains.

The preferred rule is:

```text
Compliance-Specific First
→ Reuse Where Proven
→ Generalize Only When Justified
```

### 3.3 Explicit Over Implicit

Important behaviour must be visible through:

* function signatures;
* models;
* enums;
* contracts;
* configuration;
* lifecycle transitions;
* named error types.

Avoid hidden:

* global state;
* fallback behaviour;
* automatic retries;
* environment assumptions;
* implicit coercion;
* side effects during import.

### 3.4 Immutable Historical State

Completed lifecycle records must not be silently rewritten.

Prefer:

```text
New Processing Run
rather than
Mutating a completed Processing Run
```

```text
Supersede
rather than
Overwrite
```

```text
Disable or Unpublish
rather than
Delete
```

### 3.5 Fail Safely

The system should fail:

* explicitly;
* predictably;
* with sufficient diagnostic context;
* without exposing secrets;
* without creating invalid partial state;
* without silently continuing after a blocking failure.

---

## 4. Technology Baseline

The approved foundation is:

```text
Python: 3.11.4 for local development
Supported Python line: 3.11.x
FastAPI
Poetry
Pydantic v2
Pydantic Settings
Docker
Docker Compose
Ruff
Pyright
pytest
GitHub Actions
```

Dependencies must be:

* justified by an approved task;
* added through Poetry;
* recorded in `pyproject.toml`;
* committed with the updated `poetry.lock`;
* reviewed for maintenance, licensing, and security risk.

Do not add a dependency when the standard library or an existing dependency provides a clear and maintainable solution.

---

## 5. Project Structure

The preferred application layout is:

```text
src/
└── cvs_review_portal/
    ├── api/
    ├── application/
    ├── domain/
    ├── infrastructure/
    ├── config/
    └── main.py

tests/
├── unit/
├── integration/
└── contract/
```

The exact directories should be created only when they contain real responsibilities.

Empty architectural folders should not be created merely to imitate a template.

### 5.1 Responsibility Boundaries

#### API Layer

Responsible for:

* HTTP contracts;
* request parsing;
* response serialization;
* HTTP status codes;
* authentication context;
* dependency resolution;
* conversion of application errors into safe API responses.

The API layer must not contain:

* core lifecycle rules;
* direct SQL;
* direct S3 logic;
* direct OpenSearch query construction;
* document-processing algorithms.

#### Application Layer

Responsible for:

* use-case orchestration;
* transaction coordination;
* calling domain rules;
* calling infrastructure contracts;
* producing application outcomes.

The application layer should describe what the use case does without depending on FastAPI-specific concepts.

#### Domain Layer

Responsible for:

* lifecycle concepts;
* invariants;
* domain value objects;
* state-transition validation;
* domain-specific errors;
* pure deterministic rules.

The domain layer must not depend directly on:

* FastAPI;
* boto3;
* OpenSearch clients;
* database drivers;
* Docker;
* environment variables.

#### Infrastructure Layer

Responsible for implementations of external concerns such as:

* databases;
* S3;
* OpenSearch;
* embedding providers;
* queues;
* external APIs;
* system clocks or identifier providers when abstraction is justified.

Infrastructure implementations should satisfy contracts defined closer to the application or domain layer.

### 5.2 Dependency Direction

The preferred dependency direction is:

```text
API
→ Application
→ Domain

Infrastructure
→ Application or Domain Contracts
```

Domain code must not import infrastructure modules.

Application services should depend on contracts, not concrete external clients, where isolation provides meaningful value.

---

## 6. Python Standards

### 6.1 Type Annotations

All public functions, methods, classes, and module-level contracts must be typed.

Type annotations should also be used for internal functions when they improve:

* readability;
* static verification;
* refactoring safety.

Avoid:

```python
def process(data):
    ...
```

Prefer:

```python
def process(document: NormalizedDocument) -> ProcessingResult:
    ...
```

### 6.2 `Any`

`Any` should not be used as a default escape from typing.

It is acceptable only when:

* interacting with an untyped external library;
* handling deliberately dynamic JSON at an external boundary;
* accompanied by validation or controlled conversion.

Prefer specific structures such as:

```python
dict[str, str]
Mapping[str, object]
Sequence[Chunk]
```

### 6.3 Function Design

Functions should:

* perform one cohesive responsibility;
* use clear names;
* avoid hidden side effects;
* return explicit results;
* raise documented typed errors for exceptional outcomes.

Long functions should be divided when they contain multiple independently understandable operations.

Function length alone is not the quality criterion.

### 6.4 Classes

Use a class when it provides meaningful:

* state;
* lifecycle;
* encapsulation;
* polymorphism;
* dependency coordination.

Do not create classes for simple stateless transformations when a typed function is clearer.

### 6.5 Dataclasses and Pydantic Models

Use:

* Pydantic models at validation and serialization boundaries;
* dataclasses or explicit domain classes for internal domain structures when runtime validation is unnecessary;
* enums for controlled lifecycle values.

Avoid using dictionaries as long-lived domain entities.

### 6.6 Mutable Defaults

Mutable default arguments are prohibited.

Do not use:

```python
def process(items: list[str] = []):
    ...
```

Use:

```python
def process(items: list[str] | None = None):
    resolved_items = items or []
```

or a `default_factory` in models.

### 6.7 Time

Use timezone-aware timestamps.

Prefer UTC for persisted operational timestamps.

Do not use naive `datetime.now()` for persisted lifecycle state.

### 6.8 Identifiers

Use stable application-level identifiers.

External identifiers such as:

* S3 object keys;
* ECS task IDs;
* OpenSearch-generated IDs;
* database sequence numbers;

must not replace domain identity unless explicitly approved.

---

## 7. Pydantic v2 Standards

Pydantic v2 is used for:

* API request and response validation;
* configuration;
* external-service payload validation;
* structured processing outputs;
* controlled serialization.

### 7.1 Boundary Validation

Untrusted or external data must be validated when entering the application.

Examples include:

* HTTP requests;
* environment variables;
* parsed metadata;
* external API responses;
* queue messages;
* model outputs;
* database payloads crossing a contract boundary.

### 7.2 Strictness

Use strict validation where silent coercion could create ambiguity or risk.

For example, a lifecycle status or vector dimension must not be accepted through arbitrary coercion.

### 7.3 Model Configuration

Pydantic models should deliberately define:

* extra-field behaviour;
* aliases;
* serialization rules;
* immutability where useful;
* string normalization where required.

Avoid relying on undocumented default behaviour for critical contracts.

### 7.4 Validation Location

Use:

* field validation for one field;
* model validation for relationships between fields;
* domain services for rules that require external state or multiple entities.

Do not place database calls or infrastructure access inside Pydantic validators.

### 7.5 Transport and Domain Models

API models and persistence models must not automatically become the domain model.

Separate models when their responsibilities differ materially.

Avoid unnecessary duplication when one model accurately serves both purposes without coupling the domain to an external framework.

### 7.6 Settings

Configuration must use Pydantic Settings.

Settings should:

* load from environment variables;
* define explicit types;
* validate required production configuration;
* use safe defaults only for local development where appropriate;
* never contain committed secrets;
* be injectable for tests.

Settings should not be loaded repeatedly across the application.

---

## 8. Async Standards

### 8.1 General Rule

Use async for I/O-bound operations when it provides concurrency value.

Examples include:

* HTTP calls;
* database calls using async drivers;
* S3 or OpenSearch calls through an async-compatible client;
* external embedding or model calls;
* queue operations.

Do not make code async solely because FastAPI supports async endpoints.

### 8.2 Pure Logic

Pure transformations should normally remain synchronous.

Examples include:

* metadata normalization;
* checksum calculation;
* lifecycle validation;
* chunk boundary calculation;
* result aggregation;
* configuration comparison.

### 8.3 Blocking I/O

Blocking I/O must not execute directly inside the event loop.

When only a synchronous library is available, use a controlled strategy such as:

* thread-pool execution;
* background worker;
* synchronous endpoint where justified;
* replacement with an async-compatible adapter.

The strategy must be explicit in the task specification.

### 8.4 Async Signatures

Do not expose async interfaces when the implementation performs no asynchronous work and no approved contract requires it.

### 8.5 Concurrency Safety

Concurrent operations must consider:

* idempotency;
* duplicate submissions;
* race conditions;
* transaction boundaries;
* ordering;
* cancellation;
* timeouts;
* partial completion.

---

## 9. SOLID and Dependency Design

SOLID principles guide design but must not produce unnecessary abstraction.

### 9.1 Single Responsibility Principle

A module or class should have one cohesive reason to change.

This does not mean every function requires a separate file or class.

### 9.2 Open/Closed Principle

Stable contracts may support extension through adapters.

Do not create extension mechanisms before a second implementation or clear near-term requirement exists.

### 9.3 Liskov Substitution Principle

Implementations of a contract must preserve:

* expected inputs;
* outputs;
* errors;
* side effects;
* lifecycle guarantees.

A test double must not behave so differently that it hides production failures.

### 9.4 Interface Segregation Principle

Prefer small, capability-focused Protocols.

Avoid large interfaces that force implementations to provide unrelated methods.

### 9.5 Dependency Inversion Principle

Application logic should depend on stable contracts rather than concrete external clients where this improves:

* testability;
* portability;
* boundary protection.

Example:

```python
class SourceArtifactStore(Protocol):
    async def store(self, request: StoreArtifactRequest) -> StoredArtifact:
        ...
```

Do not create a Protocol for a private helper function with one trivial implementation.

### 9.6 Dependency Injection

Prefer explicit constructor or function injection.

Avoid:

* service locators;
* mutable global dependencies;
* hidden singleton state;
* importing initialized clients throughout the codebase.

FastAPI dependency injection may be used at the API boundary.

Core application code should remain usable outside FastAPI.

---

## 10. FastAPI Standards

### 10.1 Application Factory

The application should be created through:

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    ...
```

A module-level `app` may call the factory for Uvicorn compatibility.

### 10.2 Router Separation

Routers should be grouped by functional capability.

Do not place all endpoints in `main.py`.

### 10.3 Request and Response Models

Endpoints must use explicit request and response models.

Response schemas should not expose internal persistence structures directly.

### 10.4 Status Codes

Use HTTP status codes according to the operation outcome.

Do not return HTTP 200 for every failure.

Error mapping must remain consistent across endpoints.

### 10.5 Health and Readiness

Maintain separate endpoints:

```text
/health
→ Process liveness

/ready
→ Application readiness
```

Liveness should not depend on external systems that may temporarily fail.

Readiness should include only dependencies required for the application instance to serve its approved responsibility.

### 10.6 Endpoint Responsibilities

Endpoints should:

* validate the transport contract;
* call an application use case;
* map the outcome;
* return a response.

Endpoints should not perform complete business workflows directly.

### 10.7 Lifespan Management

Use FastAPI lifespan management for resources requiring controlled startup and shutdown.

Examples include:

* connection pools;
* reusable HTTP clients;
* OpenSearch clients;
* background coordinators.

Do not initialize expensive or failure-prone resources during arbitrary module imports.

---

## 11. Configuration Standards

Configuration must be:

* environment-based;
* typed;
* validated;
* documented;
* safe to expose where appropriate;
* reproducible.

### 11.1 Environment Files

`.env.example` may contain:

* variable names;
* safe example values;
* comments.

It must not contain real secrets.

`.env` must not be committed.

### 11.2 Configuration Ownership

Each configuration value should have:

* one clear meaning;
* one owning component;
* an explicit default policy;
* validation when invalid values could create unsafe behaviour.

### 11.3 Configuration Snapshots

Processing Runs must preserve enough configuration identity to reproduce or investigate the representation they produced.

Runtime configuration changes must not silently change historical Processing Runs.

### 11.4 Feature Flags

Do not add a feature flag unless:

* there is a concrete rollout or operational need;
* both behaviours are supported and tested;
* removal conditions are understood.

---

## 12. Error Handling Standards

### 12.1 Typed Errors

Use meaningful application or domain errors.

Examples include:

```text
ValidationError
ConfigurationError
ArtifactStorageError
DuplicateArtifactError
ProcessingStageError
IndexingError
VerificationError
PublicationNotAllowedError
LifecycleConflictError
ExternalServiceUnavailableError
```

Exact error types should remain task-specific.

### 12.2 Error Translation

External library errors should be translated at the infrastructure boundary into application-relevant errors.

Core application logic should not require knowledge of raw boto3, database-driver, or OpenSearch exceptions.

### 12.3 Broad Exception Handling

Avoid:

```python
except Exception:
    return False
```

Broad exception handling is acceptable only at a controlled boundary where it:

* logs the original exception safely;
* converts it into an explicit failure outcome;
* does not hide programming errors;
* preserves diagnostic context.

### 12.4 Error Context

Errors should preserve safe context such as:

* entity identifier;
* Processing Run identifier;
* stage;
* external operation;
* retryability;
* failure category.

They must not expose:

* credentials;
* tokens;
* connection strings;
* raw sensitive document content;
* unnecessary infrastructure details.

### 12.5 Partial Failure

Partial failure behaviour must be explicitly defined.

The system must not assume that all multi-record operations are atomic.

For batch operations, record:

* attempted count;
* successful count;
* failed count;
* failed-item references where safe;
* recovery strategy.

---

## 13. Guardrail Standards

Guardrails exist at multiple layers.

### 13.1 Input Guardrails

Examples include:

* file type;
* file size;
* empty content;
* malformed metadata;
* unsupported version;
* query length;
* prohibited input patterns.

### 13.2 Contract Guardrails

Examples include:

* required identifiers;
* valid enum values;
* compatible configuration;
* vector dimensions;
* required provenance.

### 13.3 Lifecycle Guardrails

Examples include:

```text
Cannot publish an unverified representation
Cannot activate a disabled Document Version
Cannot mark a failed run as technically ready
Cannot link a Processing Run to an unrelated Source Artifact
```

### 13.4 External-Action Guardrails

Before writing to:

* S3;
* a database;
* OpenSearch;
* another API;

validate:

* required inputs;
* identity;
* authorization;
* idempotency;
* compatibility;
* intended target.

### 13.5 Output Guardrails

Structured outputs from parsers, embedding providers, LLMs, or other external systems must be validated before they affect lifecycle state.

### 13.6 Human Review

Human review must be used when:

* governance judgment is required;
* provenance is ambiguous;
* automatic reconciliation is unsafe;
* confidence is insufficient for a consequential action.

Guardrails should prevent unsafe action, not merely produce warnings after the action occurs.

---

## 14. Logging and Observability Standards

### 14.1 Structured Logging

Application logs should be structured and machine-readable in production.

Each relevant log should include available context such as:

* timestamp;
* level;
* service;
* environment;
* request ID;
* correlation ID;
* Document ID;
* Document Version ID;
* Processing Run ID;
* stage;
* event name;
* safe error category.

### 14.2 Logger Names

Use project namespaces such as:

```text
cvs_review_portal
cvs_review_portal.api
cvs_review_portal.ingest
cvs_review_portal.monitoring
```

Do not retain generic starter logger names.

### 14.3 Log Levels

Use levels consistently:

* `DEBUG` for diagnostic development detail;
* `INFO` for important normal lifecycle events;
* `WARNING` for recoverable or non-blocking concerns;
* `ERROR` for failed operations;
* `CRITICAL` for severe application-level failure.

### 14.4 Sensitive Data

Logs must not contain:

* secrets;
* access tokens;
* passwords;
* complete connection strings;
* private keys;
* unrestricted source-document content;
* raw personal data unless explicitly required and approved.

### 14.5 Lifecycle Events and Logs

Operational logs and Lifecycle Events are separate.

```text
Log
→ Technical diagnostic record

Lifecycle Event
→ Authoritative audit-relevant state change
```

Logs must not be the sole source of truth for lifecycle state.

### 14.6 Measurements

Record task-relevant measurements such as:

* execution duration;
* stage duration;
* record counts;
* retry count;
* external-call latency;
* token or model cost where applicable.

Metrics must not replace authoritative entity records.

---

## 15. Security Standards

### 15.1 Least Privilege

Application components should receive only the permissions required for their approved task.

### 15.2 Secrets

Secrets must be provided through approved secret-management or runtime mechanisms.

Secrets must not be:

* committed;
* placed in source code;
* placed in Docker images;
* printed in logs;
* returned by APIs.

### 15.3 Input Trust

All external input is untrusted until validated.

This includes:

* uploaded files;
* metadata;
* HTTP headers;
* query parameters;
* environment configuration;
* external-service responses;
* model-generated output.

### 15.4 Authorization

Permission checks must be enforced in application or service logic.

Hiding a UI button is not an authorization control.

### 15.5 Source Artifacts

Source Artifact access must be:

* authorized;
* controlled;
* traceable where required;
* separate from unrestricted S3 access.

### 15.6 Dependency Security

Dependency changes should be reviewed for:

* necessity;
* maintenance status;
* known vulnerabilities;
* transitive impact;
* license suitability.

---

## 16. Testing Standards

Testing must focus on behaviour and risks, not only line coverage.

### 16.1 Test Categories

#### Unit Tests

Used for:

* pure domain rules;
* validation;
* transformations;
* error classification;
* lifecycle transitions;
* deterministic helpers.

#### Integration Tests

Used for:

* persistence;
* S3 adapters;
* OpenSearch adapters;
* external-service boundaries;
* migrations;
* transaction behaviour.

#### Contract Tests

Used for:

* API request and response schemas;
* adapter contracts;
* configuration contracts;
* published interface behaviour.

#### End-to-End Tests

Used selectively for critical vertical flows.

Examples include:

```text
Upload
→ Registration
→ Processing
→ Indexing
→ Publication
→ Retrieval
```

### 16.2 Test Independence

Tests must:

* be repeatable;
* avoid dependency on execution order;
* isolate state;
* avoid real production services;
* use deterministic fixtures where possible.

### 16.3 Failure-Path Tests

Each consequential capability must test relevant failures.

Examples include:

* invalid input;
* duplicate request;
* storage failure;
* timeout;
* partial indexing;
* verification mismatch;
* invalid lifecycle transition;
* unavailable external dependency;
* unauthorized action.

### 16.4 Mocking

Mock external boundaries, not internal implementation details.

Avoid tests that assert every private function call.

Prefer asserting:

* returned outcomes;
* state changes;
* emitted lifecycle events;
* external contract interactions.

### 16.5 Test Doubles

Test doubles must preserve the semantics of the real contract.

An in-memory adapter must not silently accept invalid operations that production would reject.

### 16.6 Coverage

Coverage may be measured, but no single percentage proves correctness.

Critical lifecycle rules and failure paths require explicit tests regardless of overall coverage.

---

## 17. Static Quality Gates

The standard local quality commands are:

```powershell
poetry run ruff check .
poetry run ruff format --check .
poetry run pyright
poetry run pytest
```

Where formatting is intentionally performed:

```powershell
poetry run ruff format .
```

The project may provide PowerShell scripts that execute the same commands.

CI must execute the approved quality gates.

A task cannot be marked `DONE` when required quality checks fail.

---

## 18. Ruff Standards

Ruff is the standard linting and formatting tool.

The configuration should detect at least:

* syntax and style errors;
* unused imports;
* import ordering;
* common bug patterns;
* outdated Python constructs.

Rules should be tightened deliberately.

Do not ignore a rule globally only to bypass one local issue.

When an ignore is necessary:

* keep it narrow;
* document the reason where non-obvious;
* remove it when the underlying limitation no longer exists.

---

## 19. Pyright Standards

Pyright is the standard static type checker.

The target mode is:

```text
strict
```

Any transition from `basic` to `strict` must be completed through `TASK-001`.

New code must not introduce avoidable type errors.

Suppressions such as:

```python
# type: ignore
```

must:

* be narrow;
* identify the specific diagnostic where possible;
* have a valid documented reason.

Do not use casts or ignores merely to silence incorrect design.

---

## 20. Docker Standards

### 20.1 Image Design

Docker images should:

* use an approved Python 3.11 base;
* use multi-stage builds where valuable;
* avoid unnecessary build tools in runtime;
* run as a non-root user;
* copy only required files;
* expose no secrets;
* support deterministic dependency installation.

### 20.2 Build Context

`.dockerignore` must exclude:

* virtual environments;
* Git metadata;
* caches;
* local environment files;
* test artifacts;
* unnecessary documentation or temporary files where appropriate.

### 20.3 Runtime Command

The runtime command must be explicit and suitable for the deployment model.

Development-only features such as `--reload` must not be used in production.

### 20.4 Health Checks

Docker or deployment health checks should use the appropriate application endpoint.

Liveness and readiness must not be confused.

### 20.5 Docker Compose

Docker Compose should contain only services required by the current approved local development capability.

Do not retain unused services as speculative placeholders.

---

## 21. CI Standards

GitHub Actions should verify at least:

```text
Dependency installation
→ Ruff
→ Formatting check
→ Pyright
→ pytest
→ Docker build
```

CI should:

* run on relevant pull requests;
* run on protected integration branches where configured;
* fail on quality-gate failure;
* use dependency caching safely;
* avoid long-lived AWS credentials;
* use GitHub OIDC for AWS access when deployment is introduced.

Deployment must remain separate from general quality validation where practical.

---

## 22. Scripts and Developer Commands

Scripts must:

* fail fast;
* execute real commands;
* avoid commented placeholders presented as operational scripts;
* use consistent naming;
* return non-zero status on failure;
* be documented in the README.

Expected commands include:

```text
Development server
Lint
Format check
Type check
Tests
All quality checks
Docker build or Compose startup
```

Scripts must not hide failing commands or continue after a quality failure.

---

## 23. Documentation Standards

Documentation should remain proportional to the responsibility.

### 23.1 Code Comments

Comments should explain:

* why a decision exists;
* why behaviour is non-obvious;
* important risk or invariant;
* external-system constraint.

Comments should not repeat obvious code.

### 23.2 Docstrings

Use docstrings for:

* public contracts;
* non-obvious services;
* important domain behaviour;
* modules with significant responsibility.

Do not require verbose docstrings for trivial private helpers.

### 23.3 Reference Separation

Maintain the distinction:

```text
Reference
→ Critical functional or architectural requirement

Detailed Specification
→ Task-specific technical behaviour

Definition of Done
→ Measurable completion

ADR
→ Material architectural decision

Code Map
→ Implemented responsibility location

Common Handoff
→ Current project and session state
```

### 23.4 Documentation Updates

A task is not complete when it changes project structure or behaviour but leaves relevant documentation stale.

---

## 24. Code Map Standards

`07_code_map.md` must be updated when a task:

* creates a module;
* changes a module responsibility;
* introduces a public contract;
* changes dependency direction;
* removes or replaces an important component.

The Code Map should record:

* path;
* responsibility;
* public contracts;
* important dependencies;
* related task;
* implementation status.

It must not duplicate source code.

---

## 25. Common Handoff Standards

`06_common_handoff.md` must be updated after meaningful implementation work.

It should contain:

* current phase;
* current task;
* completed work;
* decisions;
* files changed;
* tests and verification;
* known issues;
* exact next action;
* Git status.

It must not contain:

* the full conversation;
* duplicated reference documents;
* speculative future implementation detail;
* unresolved assumptions presented as decisions.

---

## 26. AI-Assisted Engineering Standards

Cursor and other coding assistants are implementation tools, not architectural authorities.

### 26.1 Required Workflow

The required flow is:

```text
Approved References
→ Task Definition
→ Detailed Specification
→ Definition of Done
→ Cursor Repository Inspection
→ Cursor Plan
→ Human and ChatGPT Review
→ Approved Implementation
→ Verification
```

### 26.2 Cursor Planning

Before implementation, Cursor must:

* inspect the actual repository;
* summarize current relevant code;
* identify files to create or modify;
* propose ordered implementation steps;
* describe contracts;
* describe tests;
* identify risks;
* identify conflicts with references;
* stop before writing code.

### 26.3 Scope Control

Cursor must not:

* implement unrelated improvements;
* refactor unrelated modules;
* introduce speculative frameworks;
* add unapproved dependencies;
* change architecture silently;
* modify references to justify implementation choices;
* mark a task complete without evidence.

### 26.4 Reviewability

AI-generated changes must remain small enough to review.

Large uncontrolled patches should be divided before approval.

### 26.5 Verification

Claims such as:

```text
Tests pass
Typing passes
Docker builds
```

must be supported by actual command output.

Generated code is not accepted solely because it appears reasonable.

---

## 27. Git and Change Standards

### 27.1 Focused Changes

Each task should produce focused changes aligned with its approved scope.

Avoid mixing:

* feature implementation;
* unrelated refactoring;
* dependency upgrades;
* documentation cleanup;
* formatting of unrelated files.

### 27.2 Commits

Commits should:

* represent coherent work;
* use clear messages;
* avoid secrets;
* include required documentation changes.

### 27.3 Generated and Local Files

Do not commit:

* `.venv`;
* caches;
* local `.env`;
* temporary artifacts;
* local test output;
* IDE-specific state unless intentionally standardized.

### 27.4 Dependency Lock

When dependencies change:

```text
pyproject.toml
+
poetry.lock
```

must remain consistent.

---

## 28. Code Review Checklist

Each implementation review should verify:

### Scope

* Does the change implement only the approved task?
* Are unrelated changes absent or justified?

### Architecture

* Are dependencies flowing in the approved direction?
* Are external systems isolated appropriately?
* Has unnecessary abstraction been avoided?

### Correctness

* Are lifecycle invariants preserved?
* Are edge cases and failure paths handled?
* Is historical state preserved?

### Validation and Guardrails

* Is untrusted input validated?
* Are unsafe state transitions prevented?
* Are external outputs validated?

### Typing and Contracts

* Are public contracts typed?
* Are Pydantic models used at appropriate boundaries?
* Are broad dictionaries and `Any` avoided?

### Async

* Is async used for real I/O concurrency?
* Is blocking I/O kept out of the event loop?

### Errors

* Are errors explicit and classified?
* Are safe details preserved?
* Are secrets and sensitive data protected?

### Tests

* Are normal, edge, and failure cases tested?
* Do tests verify behaviour rather than implementation trivia?

### Observability

* Are important operations traceable?
* Are logs structured and safe?
* Are identifiers and stage context included where needed?

### Documentation

* Are the Code Map and Common Handoff updated?
* Are relevant specifications still accurate?

---

## 29. Exceptions and Architectural Decisions

A standard may be intentionally violated only when:

* the current requirement justifies it;
* the risk is understood;
* the exception is documented;
* the relevant review approves it.

Material exceptions should be recorded in:

* the task Detailed Specification;
* an ADR;
* or both.

Temporary exceptions must include a clear removal condition.

---

## 30. Project-Wide Quality Gates

A task may be considered technically complete only when applicable checks pass:

```text
Poetry dependencies install successfully
Ruff lint passes
Ruff formatting check passes
Pyright passes
pytest passes
Docker image builds
Required integration tests pass
Required contract tests pass
No secrets are committed
No unrelated code changes remain
Code Map is updated
Common Handoff is updated
Definition of Done is verified
```

Not every task requires every infrastructure integration test.

The task Definition of Done must state which gates apply.

---

## 31. Core Code Quality Rules

1. Implement only approved scope.
2. Prefer correctness and clarity over abstraction.
3. Use Python 3.11-compatible typed code.
4. Use Pydantic v2 at validation and serialization boundaries.
5. Preserve explicit dependency direction.
6. Use Protocols only for meaningful boundaries.
7. Use async for I/O-bound concurrency, not by default.
8. Keep pure domain logic independent from frameworks and infrastructure.
9. Validate external input and external output.
10. Preserve lifecycle invariants and historical traceability.
11. Translate external errors into safe application errors.
12. Do not hide failures or rely on logs as lifecycle state.
13. Use structured, safe, contextual logging.
14. Test normal behaviour, edge cases, and failure paths.
15. Enforce Ruff, strict Pyright, pytest, and Docker build in CI.
16. Do not introduce speculative dependencies or services.
17. Keep AI-generated changes focused and reviewable.
18. Update the Code Map and Common Handoff after implementation.
19. Record justified exceptions explicitly.
20. A task is complete only when its measurable Definition of Done passes.

The resulting engineering model is:

```text
Clear Contracts
→ Controlled Dependencies
→ Validated Behaviour
→ Safe Failure Handling
→ Testable Implementation
→ Observable Lifecycle
→ Reviewable Change
→ Production Discipline
```
