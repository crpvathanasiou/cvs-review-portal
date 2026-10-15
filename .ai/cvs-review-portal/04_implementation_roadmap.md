# 04 — Implementation Roadmap

> **LEGACY ROADMAP.** Phases and tasks here target the inherited compliance/AWS/OpenSearch product. They are **not** the current portal roadmap. Reading order: [`../../README.md`](../../README.md). Current portal scope and behavior: [`08_portal_specification.md`](08_portal_specification.md).

## 1. Purpose

This document defines the implementation roadmap for CVS Review Portal.

It translates the approved project and functional references into:

* implementation phases;
* executable tasks;
* task dependencies;
* expected deliverables;
* verification checkpoints;
* MVP completion criteria.

The roadmap is intended to control implementation order and prevent:

* premature complexity;
* speculative infrastructure;
* unrelated refactoring;
* undocumented architectural changes;
* implementation before requirements are sufficiently defined;
* loss of context between ChatGPT and Cursor sessions.

This document does not replace:

* `00_project_reference.md`;
* `00_project_reference_compact.md`;
* `01_data_ingest_reference.md`;
* `02_data_monitoring_reference.md`;
* task-specific Detailed Specifications;
* task-specific Definitions of Done;
* Architecture Decision Records;
* the shared project handoff;
* the Code Map.

The canonical project reference remains the project-wide architectural source of truth.

---

## 2. Implementation Control Model

Implementation follows the sequence:

```text
Functional Reference
→ Implementation Roadmap
→ Task Definition
→ Detailed Specification
→ Definition of Done
→ Cursor Planning Prompt
→ Cursor Repository Inspection and Plan
→ Plan Review
→ Approved Implementation
→ Verification
→ Code Map and Handoff Update
```

No implementation task should begin before:

1. its scope is defined;
2. its dependencies are understood;
3. its Detailed Specification exists;
4. its Definition of Done is measurable;
5. Cursor has inspected the current repository;
6. the Cursor implementation plan has been reviewed and approved.

The repository must not be modified merely because a potential improvement was identified during planning.

Identified improvements become implementation work only through an approved task.

---

## 3. Current Repository Baseline

At the creation of this roadmap, the repository already contains a FastAPI starter foundation.

The current baseline includes:

```text
Python 3.11
FastAPI
Poetry
Docker
Docker Compose
Pydantic Settings
pytest
Ruff
Pyright
Redis dependency
Basic health endpoint
PowerShell helper scripts
```

The current application uses:

```text
app/
tests/
pyproject.toml
poetry.lock
Dockerfile
docker-compose.yaml
pyrightconfig.json
scripts/
```

The current starter requires controlled refinement rather than complete replacement.

Known foundation changes include:

* standardizing project and package identity;
* migrating from the generic `app` package to a `src/cvs_review_portal` layout;
* introducing a FastAPI application factory;
* separating liveness and readiness;
* strengthening configuration validation;
* introducing structured application logging;
* removing Redis until a concrete task requires it;
* changing Pyright from basic to strict mode;
* correcting and completing development scripts;
* adding GitHub Actions;
* expanding foundation tests;
* updating the README.

These changes are planned under `TASK-001`.

They must not be implemented before the task package and Cursor plan are approved.

---

## 4. Locked Technology Baseline

The current project baseline is:

```text
Language: Python 3.11.4 for local development
Supported Python line: Python 3.11.x

API framework: FastAPI
Dependency and packaging tool: Poetry
Validation and settings: Pydantic v2 and Pydantic Settings
Containerization: Docker
Local container orchestration: Docker Compose
Linting and formatting control: Ruff
Static type checking: Pyright
Testing: pytest
Primary cloud direction: AWS
Source-artifact storage direction: Amazon S3
Retrieval engine direction: Amazon OpenSearch
Application deployment direction: Amazon ECS Fargate
Container registry direction: Amazon ECR
Infrastructure-as-code direction: AWS CloudFormation
```

Additional technologies must be introduced only when a concrete task requires them.

Examples include:

```text
PostgreSQL
Redis
background queues
LangGraph
external embedding providers
local embedding models
additional AWS services
```

The existence of a possible future use case is not sufficient justification for adding a dependency to the foundation.

---

## 5. Implementation Principles

### 5.1 Deliver Vertical Value

Tasks should produce independently verifiable value.

The preferred implementation direction is:

```text
Small Complete Capability
→ Verified Behaviour
→ Stable Contract
→ Next Capability
```

The project should avoid creating a large collection of unused abstractions before a working lifecycle exists.

### 5.2 Contract First

External and cross-layer contracts must be defined before implementation.

Examples include:

* API request and response models;
* storage protocols;
* repository protocols;
* lifecycle commands;
* processing outcomes;
* error categories;
* configuration contracts.

Contracts must remain small and aligned with current requirements.

### 5.3 Historical Traceability

Implementation must preserve:

```text
Document
→ Document Version
→ Source Artifact
→ Processing Run
→ Indexed Representation
→ OpenSearch Index
```

Retries, reprocessing, reindexing, publication changes, and rollback must not erase historical relationships.

### 5.4 Status Separation

The implementation must preserve:

```text
Processing Status
≠ Processing Stage
≠ Technical Readiness
≠ Governance Status
≠ Publication Status
≠ OpenSearch Index Health
```

These concepts must not be compressed into one generic status.

### 5.5 No Premature Platform Engineering

CVS Review Portal is a compliance-focused application.

The implementation must not become:

* a generic ingestion platform;
* a generic document-management system;
* a generic workflow engine;
* a generic observability platform;
* a multi-domain RAG framework;
* a configurable low-code platform.

Reusable components are permitted when they directly reduce duplication inside the approved scope.

### 5.6 Explicit Dependency Direction

The preferred dependency direction is:

```text
API / Entry Points
→ Application Services
→ Domain Contracts and Rules
← Infrastructure Adapters
```

Business and lifecycle rules must not depend directly on:

* FastAPI;
* boto3;
* OpenSearch clients;
* database drivers;
* container runtime details.

### 5.7 Async Where It Adds Value

Async should be used for I/O-bound application boundaries such as:

* HTTP requests;
* database operations;
* S3 operations;
* OpenSearch operations;
* external model calls.

Pure transformations and deterministic domain rules do not need to be async.

### 5.8 Safe Failure Behaviour

Failures must be:

* explicit;
* classified;
* traceable;
* safe to expose;
* distinguishable as retryable or non-retryable where known.

The implementation must not silently continue after a failed critical operation.

---

## 6. Project-Wide Implementation Documents

Before or during `TASK-001`, the following long-lived control documents must be created:

```text
05_code_quality_standards.md
06_common_handoff.md
07_code_map.md
```

### 6.1 Code Quality Standards

`05_code_quality_standards.md` defines project-wide rules for:

* Python;
* FastAPI;
* Pydantic v2;
* async usage;
* SOLID principles;
* dependency inversion;
* Protocol interfaces;
* error handling;
* logging;
* guardrails;
* tests;
* security;
* code review;
* scope control.

### 6.2 Common Handoff

`06_common_handoff.md` is the shared handoff for:

* the current ChatGPT session;
* future ChatGPT sessions;
* the current Cursor session;
* future Cursor sessions.

It records current implementation state and the exact next action.

It must not become a duplicate project reference or conversation transcript.

### 6.3 Code Map

`07_code_map.md` records:

* important source paths;
* module responsibilities;
* public contracts;
* dependencies;
* related tasks;
* implementation status.

It is updated after each implementation task.

---

# 7. Implementation Phases

## Phase 1 — Application Foundation

### TASK-001 — Project and Application Foundation

**Objective**

Convert the existing generic FastAPI starter into a clean, tested, production-disciplined CVS Review Portal application foundation.

**Primary scope**

* standardize package and application identity;
* move to `src/cvs_review_portal`;
* introduce a FastAPI application factory;
* define configuration loading and validation;
* define logging initialization;
* separate `/health` and `/ready`;
* remove unjustified Redis integration;
* establish strict Pyright;
* establish Ruff and pytest commands;
* correct PowerShell scripts;
* add a single-service Docker Compose baseline;
* add GitHub Actions;
* update README instructions;
* expand foundation tests.

**Indicative subtasks**

```text
1.1 Repository and package identity
1.2 Application factory and API structure
1.3 Settings and logging
1.4 Health and readiness
1.5 Quality tooling and scripts
1.6 Docker and Docker Compose
1.7 GitHub Actions
1.8 Foundation tests and README
```

**Dependencies**

```text
04_implementation_roadmap.md
05_code_quality_standards.md
06_common_handoff.md
07_code_map.md
```

**Expected result**

A clean application foundation on which source ingestion can be implemented without immediate restructuring.

---

## Phase 2 — Authoritative Operational Persistence

### TASK-002 — Lifecycle Persistence Foundation

**Objective**

Introduce the authoritative operational persistence required for:

* Documents;
* Document Versions;
* Source Artifacts;
* Processing Runs;
* Indexed Representations;
* lifecycle status;
* audit history.

**Primary scope**

* confirm the persistence technology through a task-level decision;
* establish connection and configuration handling;
* establish migrations;
* define transaction boundaries;
* define repository contracts;
* create the minimum initial persistence models;
* add integration-test infrastructure.

The expected relational persistence direction is PostgreSQL, but the task specification must confirm the decision before implementation.

**Non-goals**

* complete Data Monitoring query APIs;
* complete audit-report generation;
* all future lifecycle tables;
* generic repository framework.

**Dependencies**

```text
TASK-001
```

---

## Phase 3 — Durable Source Intake

### TASK-003 — Source Artifact Storage

**Objective**

Provide durable, traceable storage for accepted original source files.

**Primary scope**

* Source Artifact storage contract;
* S3 adapter;
* checksum calculation;
* immutable artifact identity;
* storage-result contract;
* safe failure classification;
* local and integration testing strategy.

**Important invariant**

```text
Upload accepted
→ Source Artifact durably stored
→ Sufficient operational state recorded
```

S3 is storage, not lifecycle authority and not retrieval.

**Dependencies**

```text
TASK-001
TASK-002
```

---

### TASK-004 — Document, Version, and Artifact Registration

**Objective**

Register the logical source relationships:

```text
Document
→ Document Version
→ Canonical Source Artifact
```

**Primary scope**

* Document registration;
* Document Version registration;
* Source Artifact registration;
* identity and duplicate handling;
* provenance metadata;
* operational status;
* upload API contract;
* idempotency behaviour;
* validation errors;
* lifecycle events.

**Indicative subtasks**

```text
4.1 Upload request validation
4.2 Source identity resolution
4.3 Document and Version registration
4.4 Source Artifact registration
4.5 Idempotency and duplicate handling
4.6 Upload API and contract tests
```

**Dependencies**

```text
TASK-002
TASK-003
```

---

### TASK-005 — Processing Run Lifecycle Foundation

**Objective**

Create the Processing Run lifecycle required to coordinate technical processing.

**Primary scope**

* Processing Run identity;
* status and stage separation;
* configuration snapshot reference;
* Source Artifact reference;
* stage progression;
* timestamps;
* warnings;
* failure classification;
* retry and parent-run relationships;
* lifecycle event recording.

**Important invariant**

```text
Document Version
├── Canonical Source Artifact
└── Processing Runs referencing the Source Artifact
```

**Dependencies**

```text
TASK-002
TASK-004
```

---

## Phase 4 — Document Processing Pipeline

### TASK-006 — Parsing and Normalization

**Objective**

Convert the canonical Source Artifact into a normalized internal document representation.

**Primary scope**

* parser contract;
* initial supported source type;
* parsing output model;
* page or section provenance;
* normalization rules;
* parsing warnings;
* parsing failures;
* stage updates;
* intermediate artifact policy;
* deterministic tests.

The initial task should support only the document format justified by the immediate MVP.

**Dependencies**

```text
TASK-005
```

---

### TASK-007 — Metadata and Chunking

**Objective**

Produce traceable retrieval units from the normalized document.

**Primary scope**

* metadata schema;
* required and optional metadata;
* document-level metadata;
* chunk-level metadata;
* chunk identity;
* chunking strategy;
* overlap behaviour;
* source-location preservation;
* chunk-validation guardrails;
* chunk statistics.

**Important invariant**

Every Chunk must remain traceable to:

```text
Document
→ Document Version
→ Source Artifact
→ Processing Run
→ Source Location
```

**Dependencies**

```text
TASK-006
```

---

### TASK-008 — Embedding Generation

**Objective**

Generate embeddings for eligible Chunks through a controlled embedding contract.

**Primary scope**

* embedding-provider Protocol;
* embedding request and result contracts;
* model identity;
* dimensions;
* batching;
* timeout behaviour;
* retry behaviour;
* partial failure handling;
* cost and latency recording where applicable;
* embedding-count verification.

The first implementation should support one approved embedding provider.

Provider abstraction must remain minimal and contract-focused.

**Dependencies**

```text
TASK-007
```

---

### TASK-009 — OpenSearch Index Foundation

**Objective**

Create and register the OpenSearch retrieval target required by CVS Review Portal.

**Primary scope**

* OpenSearch client adapter;
* index naming and generation;
* application index registry;
* mappings;
* vector dimensions;
* lexical fields;
* metadata fields;
* configuration compatibility;
* basic health and availability checks;
* local or integration-test strategy.

**Important invariant**

```text
Application Index Registry
≠ Observed OpenSearch State
```

**Dependencies**

```text
TASK-002
TASK-008
```

---

### TASK-010 — Indexing, Verification, and Technical Readiness

**Objective**

Create an Indexed Representation and verify that it is technically usable.

**Primary scope**

* indexed representation identity;
* bulk indexing;
* duplicate-safe indexing;
* expected and observed record counts;
* indexing outcome;
* verification outcome;
* Technical Readiness;
* representation-to-index traceability;
* blocking inconsistency detection;
* publication handoff.

**Important invariant**

```text
Indexing Succeeded
≠ Verification Passed
≠ Technical Readiness READY
≠ Published
```

**Dependencies**

```text
TASK-008
TASK-009
```

---

## Phase 5 — Data Monitoring Read Capabilities

### TASK-011 — Document and Version Monitoring

**Objective**

Expose authorized read capabilities for:

* Documents;
* Document Versions;
* Source Artifacts;
* current lifecycle summaries;
* historical relationships;
* unresolved issues.

**Primary scope**

* list Documents;
* inspect Document;
* inspect Versions;
* inspect Source Artifact metadata;
* current and historical state;
* basic filters and pagination;
* monitoring response contracts.

**Dependencies**

```text
TASK-004
TASK-005
TASK-010
```

---

### TASK-012 — Processing and Representation Monitoring

**Objective**

Expose technical lifecycle visibility for:

* Processing Runs;
* stages;
* warnings;
* failures;
* configurations;
* Indexed Representations;
* OpenSearch indexes;
* technical readiness;
* inconsistencies.

**Primary scope**

* Processing Run list and detail;
* failure and warning views;
* processing counts;
* representation list and detail;
* index registry visibility;
* source-to-index traceability;
* safe operational summaries.

**Dependencies**

```text
TASK-005
TASK-009
TASK-010
```

---

## Phase 6 — Governance and Administrative Control

### TASK-013 — Governance and Publication Control

**Objective**

Introduce controlled governance and retrieval-publication state transitions.

**Primary scope**

* governance-status commands;
* publication eligibility;
* publish;
* disable or unpublish;
* replace;
* supersede;
* rollback;
* authorization guardrails;
* lifecycle validation;
* audit events.

**Important invariant**

A representation may be published only when:

```text
Technical Readiness: READY
+
Governance Status permits use
+
Target index is compatible and available
+
No blocking inconsistency exists
```

**Dependencies**

```text
TASK-010
TASK-011
TASK-012
```

---

### TASK-014 — Recovery, Reconciliation, and Audit

**Objective**

Provide controlled recovery and inconsistency-management actions.

**Primary scope**

* retry;
* reprocessing initiation;
* reindexing initiation;
* reconciliation checks;
* safe deterministic repair;
* human-review states;
* audit-history queries;
* operational issue indicators.

**Important invariant**

```text
Retry
≠ Reprocessing
≠ Reindexing
≠ Rollback
```

**Dependencies**

```text
TASK-005
TASK-010
TASK-013
```

---

## Phase 7 — Data Query and Retrieval Evaluation

Before this phase begins, the project should create the just-in-time functional reference:

```text
03_data_query_reference.md
```

The reference should be limited to the retrieval capabilities that are about to be implemented.

### TASK-015 — Query and Retrieval Foundation

**Objective**

Execute traceable retrieval against explicitly eligible published representations.

**Primary scope**

* query request contract;
* validation;
* normalization;
* retrieval-target resolution;
* metadata filters;
* lexical retrieval;
* vector retrieval;
* result provenance;
* no-result and failure distinction.

**Important invariant**

```text
OpenSearch Record Exists
≠ Record Is Eligible for Retrieval
```

**Dependencies**

```text
TASK-013
```

---

### TASK-016 — Hybrid Retrieval and Ranking

**Objective**

Combine lexical and semantic candidates into a stable ranked result set.

**Primary scope**

* BM25 candidates;
* vector candidates;
* hybrid fusion;
* initial Reciprocal Rank Fusion;
* ranking configuration;
* top-k behaviour;
* optional reranking decision;
* deterministic configuration recording.

**Dependencies**

```text
TASK-015
```

---

### TASK-017 — Retrieval Testing Experience

**Objective**

Allow a Technical Operator to test retrieval against an eligible or explicitly selected test representation.

**Primary scope**

* query-testing endpoint or interface;
* selected representation context;
* provenance presentation;
* scores and rank visibility;
* filter visibility;
* execution timing;
* safe failure behaviour.

**Dependencies**

```text
TASK-015
TASK-016
```

---

### TASK-018 — Retrieval Evaluation Framework

**Objective**

Measure retrieval quality and detect regressions.

**Primary scope**

* Golden Cases;
* Reject Cases;
* Edge Cases;
* Evaluation Runs;
* experiment configurations;
* Recall@K;
* Precision@K;
* nDCG@K;
* MRR@K;
* Coverage;
* latency;
* regression comparison;
* failed-case inspection.

**Dependencies**

```text
TASK-016
```

---

## Phase 8 — Deployment and Production Hardening

Deployment work may begin earlier when required for a vertical slice, but production completion belongs in this phase.

### TASK-019 — AWS Deployment Baseline

**Objective**

Deploy the approved application components through reproducible infrastructure.

**Primary scope**

* ECR;
* ECS Fargate;
* Application Load Balancer where required;
* IAM task roles;
* environment configuration;
* secret references;
* CloudFormation;
* GitHub OIDC;
* deployment workflow;
* health and readiness integration.

Existing infrastructure files must be audited before replacement or extension.

**Dependencies**

```text
TASK-001
Approved AWS architecture from canonical reference
```

---

### TASK-020 — Production Observability and Operational Hardening

**Objective**

Provide production-level application observability and operational safety.

**Primary scope**

* structured logs;
* correlation identifiers;
* Processing Run identifiers;
* stage timings;
* failure categories;
* CloudWatch integration;
* application metrics;
* alarms for blocking conditions;
* timeout configuration;
* retry limits;
* resource limits;
* security review;
* backup and recovery requirements;
* operational runbook.

**Dependencies**

```text
Relevant implemented application tasks
TASK-019
```

---

## 8. Task Package Structure

Each implementation task should use:

```text
tasks/
└── TASK-NNN-task-name/
    ├── 01_task_definition.md
    ├── 02_detailed_specification.md
    ├── 03_definition_of_done.md
    └── 04_cursor_plan_prompt.md
```

### 8.1 Task Definition

The Task Definition contains:

* objective;
* justification;
* scope;
* non-goals;
* dependencies;
* expected outputs;
* major risks;
* subtasks where useful.

### 8.2 Detailed Specification

The Detailed Specification contains:

* required behaviour;
* components;
* contracts;
* domain rules;
* lifecycle rules;
* error behaviour;
* edge cases;
* security;
* observability;
* tests;
* expected files or package boundaries;
* explicit exclusions.

### 8.3 Definition of Done

The Definition of Done contains measurable checks.

Examples include:

```text
poetry install succeeds
Ruff passes
Pyright passes
pytest passes
Docker image builds
Required API contract tests pass
No secrets are committed
Code Map is updated
Common Handoff is updated
```

### 8.4 Cursor Plan Prompt

The Cursor prompt must instruct Cursor to:

```text
Read the references
Inspect the repository
Explain the current state
Propose an implementation plan
List affected files
Identify risks and conflicts
Define the testing approach
Stop before implementation
```

Cursor must not implement until the plan is reviewed and approved.

---

## 9. Task Sizing and Subtasks

A task should be split when it contains independently verifiable outcomes or materially different responsibilities.

A subtask is useful when it has:

* a clear output;
* a separate verification step;
* a meaningful dependency;
* enough implementation size to require focused review.

Subtasks should not be created for every file or small function.

The preferred task size is:

```text
Large enough to produce meaningful value
Small enough to review completely
```

When a task becomes too large to verify confidently, it must be divided before implementation begins.

---

## 10. Status Model

Each task may use:

```text
NOT_DEFINED
DRAFT
READY_FOR_SPECIFICATION
READY_FOR_CURSOR_PLAN
PLAN_UNDER_REVIEW
APPROVED_FOR_IMPLEMENTATION
IN_PROGRESS
IMPLEMENTED
VERIFICATION_FAILED
DONE
BLOCKED
DEFERRED
```

A task reaches `DONE` only when:

1. implementation is complete;
2. its Definition of Done passes;
3. unrelated changes are absent or explicitly justified;
4. documentation is updated;
5. the Code Map is updated;
6. the Common Handoff is updated;
7. the Git state is recorded.

---

## 11. Current Roadmap State

At the creation of this roadmap:

```text
Project References: COMPLETE FOR CURRENT IMPLEMENTATION SCOPE

00_project_reference.md
→ Available

00_project_reference_compact.md
→ Available

01_data_ingest_reference.md
→ Available

02_data_monitoring_reference.md
→ Available

03_data_query_reference.md
→ Deferred until Data Query implementation approaches

04_implementation_roadmap.md
→ Current document

05_code_quality_standards.md
→ NEXT

06_common_handoff.md
→ PLANNED

07_code_map.md
→ PLANNED

TASK-001 — Project and Application Foundation
→ READY FOR TASK DEFINITION AFTER CONTROL DOCUMENTS
```

No application code changes are approved by this roadmap alone.

---

## 12. Change Control

The roadmap may change as implementation reveals new constraints.

A roadmap change should be recorded when it affects:

* phase ordering;
* task boundaries;
* major dependencies;
* MVP scope;
* infrastructure direction;
* lifecycle guarantees;
* governance ownership;
* production architecture.

A task-level discovery does not automatically require changing the canonical project reference.

The canonical reference must be updated when the discovery changes a project-wide architectural rule or boundary.

Implementation must not silently diverge from approved references.

When a conflict is found:

```text
Stop affected implementation
→ Record the conflict
→ Resolve it in the appropriate reference, specification, or ADR
→ Update the plan
→ Continue
```

---

## 13. MVP Completion Boundary

The CVS Review Portal MVP is complete when the system can perform the following end-to-end lifecycle:

```text
Accept Source Artifact
→ Register Document and Document Version
→ Create Processing Run
→ Parse and Normalize
→ Create Chunks and Metadata
→ Generate Embeddings
→ Index in OpenSearch
→ Verify Indexed Representation
→ Mark Technical Readiness
→ Apply Governance Decision
→ Publish Eligible Representation
→ Retrieve Traceable Evidence
→ Evaluate Retrieval Quality
→ Monitor and Audit the Lifecycle
```

The MVP must also ensure that:

* an original source remains durably stored;
* every searchable representation is traceable to its source;
* processing history is not overwritten;
* failed new processing does not remove a previous valid publication;
* unverified content cannot be published;
* governance state remains distinct from technical state;
* Data Query uses only explicitly eligible representations;
* blocking inconsistencies are visible;
* privileged actions are authorized and auditable;
* quality checks execute locally and in CI;
* production deployment is reproducible.

The MVP does not require:

* generic multi-domain ingestion;
* autonomous legal judgment;
* complex enterprise approval workflows;
* generic observability tooling;
* multi-tenancy;
* advanced document collaboration;
* unrestricted OpenSearch administration;
* speculative agent orchestration.

---

## 14. Immediate Next Steps

The approved immediate sequence is:

```text
1. Create 05_code_quality_standards.md
2. Create 06_common_handoff.md
3. Create 07_code_map.md
4. Create TASK-001/01_task_definition.md
5. Create TASK-001/02_detailed_specification.md
6. Create TASK-001/03_definition_of_done.md
7. Create TASK-001/04_cursor_plan_prompt.md
8. Submit the task package to Cursor
9. Review the Cursor implementation plan
10. Approve or refine the plan
11. Begin implementation
12. Verify against the Definition of Done
13. Update Code Map and Common Handoff
```

Until the `TASK-001` Cursor plan is approved:

```text
Existing Application Files
→ Remain Unchanged
```
