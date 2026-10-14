# 02 — Data Monitoring Reference

> **LEGACY DOCUMENT.** Data-monitoring / OpenSearch content from the inherited compliance template. It does **not** describe the CVS Review Portal. Current specification: [`08_portal_specification.md`](08_portal_specification.md).

## 1. Purpose and Document Authority

This document defines the functional and semi-technical reference for the **Data Monitoring** area of CVS Review Portal.

Data Monitoring provides the operational and governance visibility required to understand and control:

* Documents;
* Document Versions;
* Source Artifacts;
* Processing Runs;
* Indexed Representations;
* OpenSearch indexes;
* technical readiness;
* governance status;
* retrieval publication status.

Its purpose is to make the knowledge-base lifecycle observable, traceable, and administratively controllable.

This reference defines:

* the responsibilities and boundaries of Data Monitoring;
* the lifecycle information that must be visible;
* the relationships between monitored entities;
* the required administrative actions;
* the distinction between processing, readiness, governance, publication, and infrastructure status;
* the audit and traceability requirements;
* the decisions that must be resolved before implementation deliverables are created.

This document contains only the critical functional and semi-technical requirements.

Detailed implementation decisions belong in:

* Intermediate Deliverables;
* Technical Specifications;
* Definition of Done;
* Architecture Decision Records.

This document is not:

* a final UI design;
* a final API contract;
* a final database schema;
* a final audit-event schema;
* a CloudWatch dashboard specification;
* an OpenSearch administration manual;
* a detailed retry or rollback procedure;
* an infrastructure-monitoring platform;
* a complete document-management system.

### 1.1 Document hierarchy

The project documentation hierarchy is:

```text
00_project_reference.md
→ Canonical project-wide architectural source of truth

02_data_monitoring_reference.md
→ Detailed functional reference for Data Monitoring

00_project_reference_compact.md
→ Derived compact working context
```

If this document conflicts with the canonical project reference regarding:

* project scope;
* architecture;
* shared entities;
* system boundaries;
* lifecycle invariants;
* security or governance principles;
* AWS architecture direction;

the canonical project reference prevails.

This document may provide additional Data Monitoring detail where the canonical project reference intentionally remains high-level.

A change in this document must also update the canonical project reference when it affects:

* the project MVP boundary;
* shared lifecycle states;
* ownership between Data Ingest, Data Monitoring, and Data Query;
* governance or publication rules;
* project-wide auditability;
* security boundaries;
* project-level success criteria.

The compact project reference is a working context document and is not an architectural source of truth.

### 1.2 Functional authority

Within the boundaries established by the canonical project reference, this document is the primary functional reference for Data Monitoring.

It defines what the system must make visible and controllable.

It does not define exactly how those requirements are implemented.

For example:

```text
Reference requirement
→ Processing Run failures must be visible

Implementation detail
→ Database schema, API endpoint, UI component, pagination, filters, and refresh mechanism
```

The implementation detail belongs in the relevant deliverable, Technical Specification, Definition of Done, or ADR.

### 1.3 Ownership boundary

Data Monitoring consumes lifecycle state produced by Data Ingest and exposes it through operational and governance views.

It does not perform:

* parsing;
* normalization;
* chunking;
* embedding generation;
* OpenSearch indexing;
* retrieval ranking;
* retrieval evaluation.

Data Monitoring may initiate controlled administrative actions such as:

* retry;
* reprocessing;
* reindexing;
* publication;
* disabling;
* superseding;
* rollback.

The execution of the underlying processing remains the responsibility of the relevant functional component.

Data Monitoring is therefore the:

```text
Operational and Governance Control Surface
```

for the document and retrieval-representation lifecycle.

### 1.4 Core status separation

Data Monitoring must preserve the distinction between:

```text
Processing Status
≠ Technical Readiness
≠ Governance Status
≠ Publication Status
≠ OpenSearch Index Health
```

These states may be related, but they must not be collapsed into one generic status.

For example:

```text
Processing Run: SUCCEEDED
Technical Readiness: READY
Governance Status: PENDING_REVIEW
Publication Status: NOT_PUBLISHED
Index Health: GREEN
```

This distinction is a project-level invariant and must remain visible throughout the Data Monitoring design.


## 2. Data Monitoring Objective

The objective of Data Monitoring is to provide a clear, reliable, and traceable view of the document-processing and retrieval-representation lifecycle.

It must allow an authorized user to determine:

* which Documents exist;
* which Document Versions belong to each Document;
* which Source Artifacts are associated with each version;
* which Processing Runs were executed;
* which configuration produced each representation;
* where processing succeeded or failed;
* which OpenSearch index contains each representation;
* whether a representation is technically ready;
* whether it is governance-permitted;
* whether it is published for normal retrieval;
* which representation is currently active;
* what administrative actions or status changes occurred.

The primary monitoring relationship is:

```text
Document
→ Document Version
→ Source Artifact
→ Processing Run
→ Indexed Representation
→ OpenSearch Index
→ Retrieval Publication
```

Data Monitoring must make this relationship understandable without requiring the user to inspect:

* application logs;
* S3 directly;
* OpenSearch records directly;
* ECS tasks;
* database tables;
* internal processing code.

The primary outcome is:

> An authorized user can understand the current and historical state of every document and searchable representation, identify failures or inconsistencies, and perform permitted lifecycle actions without losing provenance or auditability.

Data Monitoring is not limited to displaying whether a process is running or completed.

It must preserve the distinction between:

```text
What source exists
What processing occurred
What representation was produced
Whether that representation is technically valid
Whether it is governance-approved
Whether it is currently available to Data Query
```

The system must support both:

### Current-state visibility

The user can identify:

* the current Document Version;
* the latest Processing Run;
* the active indexed representation;
* the current governance and publication states;
* unresolved failures or warnings.

### Historical traceability

The user can inspect:

* previous Document Versions;
* previous Processing Runs;
* previous configurations;
* failed or replaced representations;
* publication and governance changes;
* administrative actions.

Data Monitoring should expose authoritative lifecycle state from the operational records maintained by the application.

Logs and AWS infrastructure metrics may provide additional diagnostic information, but they must not be the sole source of truth for document, processing, governance, or publication status.

The resulting objective is:

```text
Lifecycle State
→ Clear Operational Visibility
→ Controlled Administrative Action
→ Historical Traceability
→ Reliable Retrieval Governance
```


## 3. Scope

The Data Monitoring MVP covers the visibility and controlled administration of the document and retrieval-representation lifecycle.

The functional scope includes:

1. listing registered Documents;
2. viewing the Document Versions associated with each Document;
3. viewing the Source Artifact associated with each version;
4. viewing Processing Runs and their outcomes;
5. identifying the current processing stage;
6. viewing processing warnings and failures;
7. viewing the configuration associated with each Processing Run;
8. viewing produced Chunk, embedding, and indexing counts;
9. viewing the target OpenSearch index;
10. viewing verification and technical-readiness status;
11. viewing governance status;
12. viewing retrieval-publication status;
13. identifying the currently active representation;
14. identifying previous, replaced, superseded, disabled, or failed representations;
15. viewing registered OpenSearch indexes and their application-level status;
16. tracing Documents and Processing Runs to indexed representations;
17. viewing important lifecycle and administrative events;
18. initiating approved lifecycle actions;
19. detecting incomplete or inconsistent operational states;
20. exposing sufficient information for troubleshooting and audit.

The primary monitored lifecycle is:

```text id="r7m2kd"
Document
→ Document Version
→ Source Artifact
→ Processing Run
→ Indexed Representation
→ Verification
→ Technical Readiness
→ Governance Status
→ Retrieval Publication
```

### 3.1 Monitoring Views

The initial Data Monitoring experience should provide views for:

```text id="q1pn8s"
Documents
Document Details
Document Versions
Processing Runs
Indexed Representations
OpenSearch Indexes
Failures and Warnings
Audit History
```

These views may be implemented as:

* separate pages;
* tabs;
* filtered tables;
* detail panels;
* or another simple UI structure.

The final UI composition belongs in the relevant implementation deliverable.

### 3.2 Administrative Actions

The Data Monitoring area may expose controlled actions such as:

* retrying a recoverable failed operation;
* initiating reprocessing;
* initiating reindexing;
* publishing a technically ready representation;
* disabling a published representation;
* marking a Document Version as superseded;
* selecting a replacement representation;
* initiating rollback to a previous verified representation;
* requesting reconciliation of an inconsistent state.

Displaying an action does not mean that Data Monitoring executes all underlying technical work directly.

The action may submit a controlled command to:

* Data Ingest;
* the processing coordinator;
* the index-management component;
* or another responsible service.

Actions must be available only when the lifecycle state permits them.

### 3.3 Application-Level Index Monitoring

Data Monitoring should expose application-relevant OpenSearch information, including:

* registered index name or identifier;
* index version;
* associated processing configuration;
* vector dimensions;
* indexed Document and Chunk counts;
* representations associated with the index;
* whether the index is selected for retrieval;
* basic readiness or health information;
* known indexing or verification failures.

Data Monitoring is not required to reproduce every OpenSearch administrative or infrastructure metric.

Detailed cluster administration remains outside the application-level monitoring scope.

### 3.4 Lifecycle History

The system must preserve both current and historical state.

Historical visibility includes:

* previous Document Versions;
* previous Source Artifacts;
* previous Processing Runs;
* failed and cancelled runs;
* previous indexed representations;
* previous publication states;
* governance-status changes;
* retries, reprocessing, reindexing, and rollback actions.

Historical records should remain understandable after a newer representation becomes active.

### 3.5 Initial Operating Model

The initial system is internally operated and documents are expected to be ingested infrequently.

Therefore, the MVP may use:

* manually refreshed or periodically refreshed views;
* simple administrative controls;
* basic tables and detail pages;
* lightweight audit history;
* application-level status indicators.

The MVP does not require real-time streaming dashboards, complex alert-routing workflows, or enterprise-scale operations tooling.

### 3.6 Cross-Functional Boundaries

Data Monitoring receives state from Data Ingest, including:

* registered entities;
* processing status;
* current stage;
* configuration references;
* processing counts;
* failures and warnings;
* verification outcomes;
* technical-readiness state.

Data Monitoring provides Data Query with controlled visibility into which representations are eligible for normal retrieval.

The core relationship is:

```text id="8qva47"
Data Ingest
→ Produces lifecycle state and representations

Data Monitoring
→ Exposes and controls lifecycle and publication state

Data Query
→ Uses only permitted published representations
```

### 3.7 Scope Boundary

Data Monitoring is responsible for application-level operational and governance visibility.

It is not responsible for:

* executing document transformation logic;
* determining retrieval relevance;
* calculating retrieval-quality metrics;
* replacing AWS infrastructure monitoring;
* providing unrestricted OpenSearch administration;
* acting as a full enterprise document-management platform.

The resulting scope is:

```text id="lt8h2c"
Lifecycle Records
→ Monitoring Views
→ Controlled Administrative Actions
→ Auditable Retrieval Governance
```


## 4. Non-Goals and Functional Boundaries

The Data Monitoring MVP does not include:

* a complete enterprise document-management system;
* document editing or collaborative authoring;
* legal approval workflows;
* automated legal interpretation;
* automated determination of source authority or applicability;
* complex multi-level approval chains;
* enterprise-scale role and permission management;
* real-time event-streaming dashboards;
* advanced alert-routing or on-call workflows;
* full OpenSearch cluster administration;
* unrestricted manual editing of OpenSearch records;
* direct S3 file management;
* direct database administration;
* automatic infrastructure remediation;
* a replacement for CloudWatch or AWS service monitoring;
* a generic observability platform;
* a generic workflow engine;
* multi-tenant administration;
* configurable lifecycle workflows for arbitrary domains;
* permanent deletion and legal-hold workflows unless explicitly required later.

The initial project should provide only the monitoring and administrative controls required to operate the Compliance document lifecycle safely.

---

### 4.1 Data Ingest Boundary

Data Ingest owns the execution of:

* file validation;
* Source Artifact storage;
* Document and Document Version registration;
* parsing;
* normalization;
* metadata handling;
* chunking;
* embedding generation;
* OpenSearch indexing;
* processing verification.

Data Monitoring consumes the resulting lifecycle state and makes it visible.

Data Monitoring may initiate actions such as:

* retry;
* reprocessing;
* reindexing;
* reconciliation.

However, the underlying processing remains owned by Data Ingest or the processing coordinator.

The boundary is:

```text
Data Monitoring
→ Requests or authorizes processing action

Data Ingest
→ Executes and records processing outcome
```

Data Monitoring must not duplicate document-processing logic inside its UI or API layer.

---

### 4.2 Data Query and Evaluation Boundary

Data Query and Evaluation owns:

* query submission;
* query validation and normalization;
* lexical and vector retrieval;
* metadata filtering;
* ranking and fusion;
* retrieval-result presentation;
* retrieval evaluation;
* golden datasets;
* Precision@K, Recall@K, and nDCG@K;
* experiment comparison.

Data Monitoring may show:

* which representation is published;
* which index is selected;
* whether retrieval publication is active;
* high-level references to evaluation outcomes where useful.

It does not calculate or own retrieval-quality metrics.

The boundary is:

```text
Data Monitoring
→ Records, validates, and enforces which verified representation is eligible for use

Data Query
→ Executes retrieval against the eligible published representation
```

---

### 4.3 Governance Boundary

Data Monitoring exposes and controls governance-related lifecycle state.

It may support actions such as:

* mark active;
* mark superseded;
* disable;
* publish;
* unpublish;
* roll back.

It does not independently determine that a document is:

* legally authoritative;
* legally applicable;
* complete;
* approved by an organization;
* sufficient evidence of compliance.

These decisions require an authorized human or an explicitly defined governance policy.

The system must distinguish:

```text
Governance status recorded by the application
≠ Legal conclusion produced by the application
```

Data Monitoring records and enforces the approved decision. It does not create the legal judgment.

---

### 4.4 OpenSearch Boundary

Data Monitoring may expose application-relevant OpenSearch information such as:

* registered index;
* index version;
* vector dimensions;
* related representations;
* indexed record counts;
* basic health or readiness;
* active retrieval target;
* indexing and verification failures.

It is not intended to expose all OpenSearch administrative capabilities.

The MVP does not require:

* shard relocation controls;
* manual mapping changes;
* unrestricted query-console access;
* cluster tuning;
* node-level diagnostics;
* index-template administration;
* snapshot management;
* security-plugin administration.

These capabilities remain in OpenSearch and AWS administrative tooling.

---

### 4.5 AWS Infrastructure Monitoring Boundary

CloudWatch and AWS service consoles remain responsible for low-level infrastructure visibility, including:

* ECS task and service health;
* CPU and memory;
* container restarts;
* network failures;
* Application Load Balancer health;
* S3 service errors;
* OpenSearch cluster and node health;
* CloudFormation deployment status;
* infrastructure alarms.

Data Monitoring may show a small application-relevant summary when infrastructure state affects document processing or retrieval.

For example:

```text
Processing Run failed
Reason category: OPENSEARCH_UNAVAILABLE
```

The application does not need to reproduce the complete CloudWatch diagnostic view.

---

### 4.6 Audit Boundary

Data Monitoring should preserve a lightweight lifecycle and administrative audit history.

The MVP audit scope may include:

* entity created;
* status changed;
* processing retried;
* reprocessing initiated;
* representation published;
* representation disabled;
* version superseded;
* rollback initiated;
* reconciliation performed.

It does not initially require:

* a generic event-sourcing architecture;
* cryptographically immutable audit storage;
* external regulatory audit certification;
* advanced audit-report generation;
* legal-hold enforcement.

Stronger audit requirements may be added later when justified by the actual compliance context.

---

### 4.7 Administrative Action Boundary

Administrative actions must be controlled by lifecycle rules.

For example:

```text
FAILED Processing Run
→ May allow retry or reprocessing
```

```text
Unverified representation
→ Must not allow publication
```

```text
Published representation
→ May allow disable or replacement
```

The reference defines which actions must exist conceptually.

The following implementation details belong in Deliverables, Technical Specifications, Definition of Done, or ADRs:

* API endpoints;
* authorization checks;
* confirmation dialogs;
* retry limits;
* asynchronous command handling;
* rollback mechanics;
* exact state-transition rules;
* database transactions;
* UI button visibility.

---

### 4.8 Destructive Operations Boundary

The initial Data Monitoring system should prefer reversible lifecycle actions.

Examples include:

* disable rather than delete;
* supersede rather than overwrite;
* unpublish rather than remove historical state;
* create a new Processing Run rather than mutate an old run.

Permanent deletion of:

* Documents;
* Document Versions;
* Source Artifacts;
* Processing Runs;
* indexed representations;
* audit records;

is outside the default MVP scope.

If deletion becomes necessary, it requires an explicit retention and deletion policy.

---

### 4.9 Functional Boundary Summary

Data Monitoring establishes:

```text
Lifecycle Visibility
→ Status Separation
→ Controlled Administrative Actions
→ Publication Governance
→ Historical Traceability
```

It does not establish:

* document-processing implementation;
* retrieval relevance;
* legal authority;
* legal applicability;
* infrastructure administration;
* enterprise document management;
* complex approval automation.

Its responsibility is to make the system’s document and retrieval lifecycle understandable and controllable without expanding into unrelated operational platforms.

## 5. Actors and User Experience

Data Monitoring is primarily used by internal technical and governance users who need to inspect and control the document and retrieval-representation lifecycle.

The MVP should support a small number of clear actor responsibilities without requiring a complex enterprise RBAC model.

---

### 5.1 Primary Actor — Technical Operator

The primary actor is:

```text
AI / Search Engineer acting as Technical Operator
```

The Technical Operator may:

* view registered Documents and Document Versions;
* inspect Source Artifacts;
* inspect Processing Runs;
* identify the current or failed processing stage;
* review warnings and safe failure summaries;
* compare Processing Runs and configurations;
* view Chunk, embedding, indexing, and verification counts;
* identify the target OpenSearch index;
* initiate permitted retry, reprocessing, or reindexing actions;
* inspect technical-readiness and publication status;
* identify the currently active representation.

The Technical Operator is responsible for technical operation and troubleshooting.

This role must not be assumed to have authority to determine:

* legal applicability;
* source authority;
* governance approval;
* whether a Document Version should become the official organizational reference.

---

### 5.2 Governance Actor — Compliance Administrator or Domain Reviewer

A Compliance Administrator or Domain Reviewer may:

* review document identity and version information;
* inspect source authority and jurisdiction;
* review publication and effective dates;
* review provenance;
* assign or update governance status;
* mark a version as active, superseded, or disabled;
* approve or reject retrieval publication;
* select a verified replacement representation;
* initiate rollback to a previously approved representation.

This actor provides the human governance decision that Data Monitoring records and enforces.

The application does not create the legal or compliance judgment independently.

The MVP may represent this actor operationally without implementing a fully separate role and permission model.

---

### 5.3 System Administrator

A System Administrator may:

* inspect registered indexes;
* review application-level index status;
* investigate inconsistent lifecycle states;
* initiate reconciliation;
* manage operational recovery;
* inspect infrastructure references;
* coordinate cleanup of failed or orphaned representations.

Infrastructure-level administration remains primarily in AWS and OpenSearch tooling.

Data Monitoring should expose only the application context necessary to understand how infrastructure conditions affect the document lifecycle.

---

### 5.4 Auditor or Reviewer

An Auditor or Reviewer may inspect:

* Document and Version history;
* Source Artifact provenance;
* Processing Run history;
* configuration references;
* verification outcomes;
* governance changes;
* publication and rollback events;
* responsible actors and timestamps.

This actor is primarily read-only in the initial operating model.

The MVP does not require a separate audit portal, provided that the required history is accessible through the monitoring views.

---

### 5.5 User Experience Principles

The Data Monitoring experience should prioritize:

* lifecycle clarity;
* traceability;
* safe administrative action;
* understandable failure information;
* clear separation of status types;
* visibility of historical state.

The user should not need to inspect internal infrastructure or application logs to understand the normal lifecycle state.

The UI should make it possible to move from:

```text
Document
→ Version
→ Source Artifact
→ Processing Run
→ Indexed Representation
→ Publication State
```

without losing context.

---

### 5.6 Status Presentation

The user experience must present the following as separate fields or concepts:

```text
Processing Status
Technical Readiness
Governance Status
Publication Status
Index Status
```

The interface must not replace these with one ambiguous label such as:

```text
ACTIVE
READY
SUCCESS
```

without showing what that state refers to.

For example:

```text
Processing Run: SUCCEEDED
Technical Readiness: READY
Governance Status: ACTIVE
Publication Status: PUBLISHED
Index Status: AVAILABLE
```

Failures should identify the affected lifecycle area.

For example:

```text
Processing Status: FAILED
Failed Stage: EMBEDDING
Previous Published Representation: AVAILABLE
```

---

### 5.7 Document List Experience

The Document list should allow the user to identify, at minimum:

* Document title;
* source type;
* jurisdiction or authority where available;
* current Version;
* governance status;
* publication status;
* latest Processing Run outcome;
* active representation;
* unresolved warning or failure indicator.

The exact columns, filters, sorting, and pagination belong in the implementation deliverable.

---

### 5.8 Document Detail Experience

The Document detail view should provide access to:

* Document metadata;
* all Document Versions;
* current and historical governance states;
* Source Artifacts;
* Processing Runs;
* indexed representations;
* active retrieval representation;
* relevant audit events.

The user should be able to understand both:

```text
Current operational state
```

and:

```text
Historical lifecycle
```

from the same Document context.

---

### 5.9 Processing Run Experience

The Processing Run view should show:

* related Document and Document Version;
* Source Artifact;
* run status;
* current or failed stage;
* effective configuration reference;
* target index;
* processing counts;
* verification result;
* safe warnings and failures;
* retry or parent-run relationship;
* permitted next actions.

The view should avoid exposing raw stack traces or sensitive infrastructure details.

---

### 5.10 Index Experience

The OpenSearch index view should show application-relevant information such as:

* registered index name or version;
* associated configuration;
* vector dimensions;
* related Processing Runs;
* indexed Document and Chunk counts;
* technical availability;
* publication use;
* known verification or consistency issues.

The user should not need unrestricted OpenSearch administrative access to understand which index supports the application.

---

### 5.11 Administrative Actions

Administrative actions should be presented only when valid for the current lifecycle state.

Examples include:

```text
Failed recoverable Processing Run
→ Retry
```

```text
Existing Document Version
→ Reprocess
```

```text
Technically ready representation
→ Publish, when governance permits
```

```text
Published representation
→ Disable or Replace
```

```text
Inconsistent lifecycle state
→ Reconcile
```

Actions that may affect retrieval availability should clearly communicate their impact before execution.

The exact confirmation workflow and authorization mechanism belong in the implementation deliverables.

---

### 5.12 Navigation Between Functional Areas

Data Monitoring should support controlled navigation to related areas.

Examples include:

```text
Data Ingest upload result
→ Corresponding Processing Run
```

```text
Published representation
→ Data Query testing page
```

```text
Failed Processing Run
→ Related Source Artifact and Document Version
```

The user should not need to manually copy internal identifiers between application pages.

---

### 5.13 MVP User Experience Boundary

The initial experience may use:

* simple tables;
* detail pages;
* status labels;
* manually refreshed views;
* basic filters;
* controlled action buttons.

It does not require:

* real-time streaming updates;
* complex visualization;
* drag-and-drop workflow management;
* customizable dashboards;
* enterprise notification routing;
* multi-step approval interfaces.

The core requirement is:

> An authorized user can understand the current and historical lifecycle state, identify what requires attention, and initiate permitted actions without inspecting internal storage or infrastructure directly.

The resulting user experience is:

```text
Clear Lifecycle Navigation
→ Separate Status Visibility
→ Safe Administrative Action
→ Historical and Audit Traceability
```


## 6. Core Data Monitoring Use Cases

The core Data Monitoring use cases define how authorized users inspect lifecycle state, identify operational problems, and initiate controlled administrative actions.

These use cases focus on:

```text
Visibility
→ Traceability
→ Controlled Action
→ Auditability
```

They do not define the final UI, API endpoints, database schema, or implementation workflow.

---

### 6.1 DM-UC-01 — List Documents

**Primary Actor:** Technical Operator or Compliance Administrator

The user views the registered Documents.

The view should provide enough information to identify:

* the Document;
* the current or latest Document Version;
* governance status;
* publication status;
* latest Processing Run outcome;
* unresolved warnings or failures.

**Expected outcome:** The user can identify the current high-level state of each Document and navigate to its detailed lifecycle.

---

### 6.2 DM-UC-02 — Inspect a Document

**Primary Actor:** Authorized User

The user opens a Document and views:

* document metadata;
* associated Document Versions;
* Source Artifacts;
* Processing Runs;
* indexed representations;
* governance and publication history;
* relevant audit events.

**Expected outcome:** The user can understand the complete current and historical lifecycle of the Document.

---

### 6.3 DM-UC-03 — Inspect Document Versions

**Primary Actor:** Technical Operator or Compliance Administrator

The user views all versions associated with a Document.

The system distinguishes:

* current version;
* previous versions;
* active version;
* superseded versions;
* disabled versions;
* versions pending review.

Each version remains associated with its:

* Source Artifact;
* Processing Runs;
* indexed representations;
* governance state.

**Expected outcome:** The user can identify which source version each searchable representation belongs to and which version is currently approved for use.

---

### 6.4 DM-UC-04 — Inspect a Source Artifact

**Primary Actor:** Technical Operator or Auditor

The user views the Source Artifact associated with a Document Version.

The system exposes authorized metadata such as:

* original filename;
* file type;
* file size;
* checksum;
* upload timestamp;
* storage status;
* related Processing Runs.

**Expected outcome:** The user can confirm which original file was processed without requiring direct access to S3.

---

### 6.5 DM-UC-05 — Inspect Processing Runs

**Primary Actor:** Technical Operator

The user views Processing Runs associated with a Document Version.

Each run should expose:

* status;
* current or failed stage;
* start and completion time;
* configuration reference;
* target index;
* processing counts;
* verification outcome;
* retry or parent-run relationship.

**Expected outcome:** The user can determine which technical representations were attempted, which succeeded, and which failed.

---

### 6.6 DM-UC-06 — Inspect a Processing Failure

**Primary Actor:** Technical Operator

The user opens a failed Processing Run.

The system shows:

* failed stage;
* failure category;
* safe error summary;
* partial processing counts;
* retry eligibility;
* whether a previous published representation remains active.

**Expected outcome:** The user can understand the operational impact of the failure and determine the permitted recovery action.

---

### 6.7 DM-UC-07 — Inspect Processing Warnings

**Primary Actor:** Technical Operator or Reviewer

The user views non-blocking warnings generated during:

* parsing;
* normalization;
* metadata handling;
* chunking;
* indexing;
* verification.

Warnings should identify:

* category;
* severity;
* affected stage;
* related entity or source area where available.

**Expected outcome:** The user can identify quality or processing limitations that did not stop the run but may require review.

---

### 6.8 DM-UC-08 — Inspect an Indexed Representation

**Primary Actor:** Technical Operator

The user views a representation produced by a Processing Run.

The system shows:

* related Document Version;
* Processing Run;
* processing configuration;
* target index;
* expected and indexed record counts;
* verification result;
* technical-readiness status;
* publication status.

**Expected outcome:** The user can determine whether the representation is complete, verified, and eligible for retrieval use.

---

### 6.9 DM-UC-09 — Inspect Registered OpenSearch Indexes

**Primary Actor:** Technical Operator or System Administrator

The user views application-registered OpenSearch indexes.

The system exposes application-relevant information such as:

* index name or version;
* vector dimensions;
* associated configuration;
* related representations;
* indexed Document and Chunk counts;
* basic availability;
* retrieval-selection state;
* known consistency issues.

**Expected outcome:** The user can understand which indexes support the application without using unrestricted OpenSearch administration tools.

---

### 6.10 DM-UC-10 — Trace a Document to an Index

**Primary Actor:** Authorized User

The user traces the relationship:

```text
Document
→ Document Version
→ Processing Run
→ Indexed Representation
→ OpenSearch Index
```

The reverse relationship should also be available where useful:

```text
OpenSearch Index
→ Indexed Representations
→ Processing Runs
→ Document Versions
→ Documents
```

**Expected outcome:** Every published or monitored representation can be traced to its source and processing history.

---

### 6.11 DM-UC-11 — Publish a Verified Representation

**Primary Actor:** Authorized Governance User

The user selects a technically ready representation for normal retrieval.

Publication is allowed only when:

* processing succeeded;
* verification succeeded;
* governance status permits retrieval;
* the representation is compatible with the selected retrieval target.

**Expected outcome:** The selected representation becomes available to Data Query through a controlled and auditable state transition.

---

### 6.12 DM-UC-12 — Disable or Unpublish a Representation

**Primary Actor:** Authorized Governance User

The user removes a published representation from the normal retrieval path without deleting its history or source artifacts.

**Expected outcome:** The representation is no longer available to normal Data Query operations, while its lifecycle and audit history remain preserved.

---

### 6.13 DM-UC-13 — Mark a Document Version as Superseded

**Primary Actor:** Compliance Administrator or Domain Reviewer

The user marks a Document Version as superseded by another version.

The system preserves:

* the previous version;
* its Processing Runs;
* its representations;
* its historical publication state.

The superseded version should not remain active for normal retrieval unless an explicit exception exists.

**Expected outcome:** Historical evidence remains available while the current retrieval path uses the approved replacement version.

---

### 6.14 DM-UC-14 — Retry a Recoverable Failure

**Primary Actor:** Technical Operator

The user retries a failed operation when the failure is classified as recoverable.

The retry preserves:

* source identity;
* Document Version;
* intended configuration;
* previous failure history.

**Expected outcome:** The failed operation is retried without creating uncontrolled duplicate Source Artifacts, Chunks, or OpenSearch records.

---

### 6.15 DM-UC-15 — Initiate Reprocessing

**Primary Actor:** Technical Operator

The user creates a new Processing Run for an existing Document Version.

This may be required because of changes to:

* parser;
* normalization;
* metadata;
* chunking;
* embedding;
* target index.

**Expected outcome:** A new technical representation is created while the Document Version and previous Processing Runs remain unchanged.

---

### 6.16 DM-UC-16 — Initiate Reindexing

**Primary Actor:** Technical Operator or System Administrator

The user initiates reindexing when:

* the target index changes;
* mappings change;
* an index is rebuilt;
* indexed records require replacement.

Reindexing must preserve the source and processing relationships required for traceability.

**Expected outcome:** A new or corrected indexed representation is created without silently replacing historical state.

---

### 6.17 DM-UC-17 — Roll Back to a Previous Representation

**Primary Actor:** Authorized Technical or Governance User

The user selects a previously verified and governance-permitted representation as the active retrieval target.

Rollback may be required when a newer representation:

* performs incorrectly;
* contains incomplete metadata;
* produces retrieval problems;
* was published accidentally.

**Expected outcome:** The previous valid representation becomes active again through a controlled and auditable transition.

---

### 6.18 DM-UC-18 — Detect an Inconsistent State

**Primary Actor:** Technical Operator or System

The system or user identifies a lifecycle inconsistency, such as:

```text
Source Artifact exists
but
Document Version relationship is missing
```

```text
Processing Run succeeded
but
verification result is missing
```

```text
Representation marked published
but
target index is unavailable
```

**Expected outcome:** The inconsistency is clearly marked and the affected representation is not silently treated as healthy or active.

---

### 6.19 DM-UC-19 — Reconcile an Inconsistent State

**Primary Actor:** Technical Operator or System Administrator

The user initiates or reviews a controlled reconciliation action.

Reconciliation may:

* restore a missing operational relationship;
* retry a failed registration;
* verify an external resource;
* mark an orphaned artifact;
* disable an invalid publication;
* request cleanup.

**Expected outcome:** The inconsistency is resolved or moved into a clearly documented failure state without losing audit history.

---

### 6.20 DM-UC-20 — Inspect Audit History

**Primary Actor:** Auditor, Reviewer, or Authorized Operator

The user reviews lifecycle and administrative events, including:

* upload and version creation;
* Processing Run creation;
* retry and reprocessing;
* verification outcome;
* governance changes;
* publication;
* disablement;
* superseding;
* rollback;
* reconciliation.

**Expected outcome:** The user can determine what changed, when it changed, and which actor or system component initiated the change.

---

### 6.21 DM-UC-21 — Navigate to Data Query Testing

**Primary Actor:** Technical Operator

The user navigates from a published or technically ready representation to the Data Query testing area.

The selected representation or index context should be carried into the query-testing workflow where appropriate.

**Expected outcome:** The user can test retrieval against the intended representation without manually copying internal identifiers.

---

### 6.22 Data Monitoring Use-Case Boundary

The Data Monitoring use cases establish:

```text
Lifecycle Visibility
→ Failure and Consistency Inspection
→ Controlled Administrative Action
→ Governance and Publication Control
→ Historical Auditability
```

They do not establish:

* document-processing algorithms;
* retrieval ranking behaviour;
* retrieval-quality metrics;
* legal authority;
* legal applicability;
* unrestricted infrastructure administration;
* permanent deletion policy.

The primary use-case outcome is:

> An authorized user can determine what exists, what happened, what is currently active, what requires attention, and which controlled action may be taken next.

## 7. Monitoring Domain Model

The Monitoring Domain Model defines the core entities and relationships required to understand the document and retrieval-representation lifecycle.

The model must support:

```text
Current-State Visibility
+
Historical Traceability
+
Controlled Lifecycle Actions
+
Auditability
```

It is a logical domain model.

It does not define:

* final database tables;
* ORM models;
* Pydantic schemas;
* API response structures;
* OpenSearch mappings;
* UI view models.

Those details belong in the relevant implementation deliverables and Technical Specifications.

---

### 7.1 Core Monitored Entities

The primary monitored entities are:

```text
Document
Document Version
Source Artifact
Processing Run
Indexed Representation
OpenSearch Index
Configuration Snapshot
Lifecycle Event
```

Each entity represents a different part of the lifecycle and must remain independently identifiable.

---

### 7.2 Core Relationships

The primary relationship is:

```text
Document
└── Document Version
    ├── Source Artifact
    └── Processing Run
        ├── Configuration Snapshot
        └── Indexed Representation
            └── OpenSearch Index
```

Lifecycle Events may be associated with any monitored entity.

The main cardinality expectations are:

```text
One Document
→ Multiple Document Versions

One Document Version
→ One canonical Source Artifact in the MVP

One Document Version
→ Multiple Processing Runs

One Processing Run
→ One resolved Processing Configuration

One Processing Run
→ Zero or more attempted Indexed Representations

One Indexed Representation
→ One target OpenSearch Index

One OpenSearch Index
→ Multiple Indexed Representations
```

A failed Processing Run may produce no valid Indexed Representation.

An indexing attempt that fails verification must not be treated as a technically ready representation.

---

### 7.3 Document

A Document represents the continuing logical compliance source.

Examples include:

* a regulation;
* an official guideline;
* an internal compliance policy;
* a technical standard;
* an organizational procedure.

Data Monitoring should expose:

* stable Document identity;
* descriptive metadata;
* associated Document Versions;
* current or selected Version;
* high-level governance and publication state;
* unresolved lifecycle issues.

The Document is not:

* an uploaded filename;
* an individual source file;
* a Processing Run;
* an OpenSearch record;
* an OpenSearch index.

---

### 7.4 Document Version

A Document Version represents a specific edition, revision, release, or effective state of a Document.

It should remain associated with:

* its parent Document;
* canonical Source Artifact;
* version metadata;
* governance status;
* Processing Runs;
* Indexed Representations;
* lifecycle history.

A Document Version may have multiple Processing Runs because the same source may be processed using different:

* parsers;
* chunking configurations;
* embedding models;
* metadata logic;
* target indexes.

A technical-processing change does not create a new Document Version.

---

### 7.5 Source Artifact

A Source Artifact represents the exact original file accepted by Data Ingest.

Data Monitoring should expose authorized information such as:

* Source Artifact identifier;
* original filename;
* file type;
* file size;
* checksum;
* upload timestamp;
* storage status;
* related Document Version;
* related Processing Runs.

The Source Artifact remains distinct from parsed, normalized, chunked, or indexed representations.

Its existence in S3 does not by itself mean that ingestion completed successfully.

---

### 7.6 Processing Run

A Processing Run represents one technical execution of the ingestion pipeline for one Document Version using one configuration snapshot.

Data Monitoring should expose:

* run identifier;
* related Document Version and Source Artifact;
* overall run status;
* current or failed stage;
* configuration reference;
* target index;
* processing counts;
* warnings;
* failure information;
* verification outcome;
* retry or parent-run relationship;
* start and completion timestamps.

The Processing Run status must remain separate from its current stage.

For example:

```text
Processing Run Status: RUNNING
Current Stage: EMBEDDING
```

The Processing Run status must also remain separate from:

* technical readiness;
* governance status;
* publication status;
* index health.

---

### 7.7 Configuration Snapshot

A Configuration Snapshot identifies the effective processing configuration used by a Processing Run.

It may include references to:

* parser and parser version;
* normalization settings;
* metadata-schema version;
* chunking strategy;
* chunk size and overlap;
* embedding model;
* vector dimensions;
* target index configuration;
* verification settings.

Data Monitoring does not need to display every low-level configuration field by default.

It must provide enough information to:

* identify the configuration;
* compare Processing Runs;
* reproduce or investigate a representation;
* determine whether two runs used materially different settings.

Historical Processing Runs must remain connected to the configuration actually used at execution time.

---

### 7.8 Indexed Representation

An Indexed Representation represents the searchable output produced by a Processing Run for one target index.

It should remain associated with:

* Document Version;
* Processing Run;
* Configuration Snapshot;
* OpenSearch Index;
* expected and indexed record counts;
* verification outcome;
* technical-readiness status;
* publication status.

An Indexed Representation is not the same as the OpenSearch Index.

For example:

```text
OpenSearch Index: compliance-v2

Indexed Representations:
- EU AI Act version 2024 / Processing Run 17
- Internal AI Policy version 3 / Processing Run 22
- Compliance Guideline version 2 / Processing Run 25
```

Multiple representations may exist within one index.

---

### 7.9 OpenSearch Index

An OpenSearch Index represents an application-registered retrieval target.

Data Monitoring should expose application-relevant information such as:

* index identifier or name;
* index version;
* configuration reference;
* vector dimensions;
* associated representations;
* indexed Document and Chunk counts;
* basic availability;
* retrieval-selection state;
* known consistency or verification issues.

The OpenSearch Index is an external retrieval resource.

The application operational records remain authoritative for:

* Document lifecycle;
* Processing Run lifecycle;
* governance status;
* publication decisions;
* audit history.

Observed OpenSearch state may be compared with operational state to detect inconsistencies.

---

### 7.10 Lifecycle Event

A Lifecycle Event records an important state change or administrative action.

Examples include:

* Document created;
* Document Version created;
* Processing Run started;
* Processing Run failed;
* retry initiated;
* reprocessing initiated;
* verification succeeded;
* representation published;
* representation disabled;
* version superseded;
* rollback performed;
* inconsistency reconciled.

A Lifecycle Event should identify, where applicable:

* affected entity;
* action;
* timestamp;
* responsible actor or system component;
* previous state;
* new state;
* reason or safe summary.

The MVP does not require a full event-sourcing architecture.

Lifecycle Events provide audit history and must not replace the current authoritative entity state.

---

### 7.11 Status Ownership

Each status belongs to a specific entity or lifecycle concern.

#### Processing Status

Belongs to the Processing Run.

Indicative values include:

```text
PENDING
RUNNING
SUCCEEDED
FAILED
CANCELLED
```

#### Processing Stage

Belongs to the active or failed Processing Run stage.

Indicative values include:

```text
PARSING
NORMALIZATION
METADATA_HANDLING
CHUNKING
EMBEDDING
INDEXING
VERIFICATION
```

#### Technical Readiness

Belongs to the Indexed Representation.

It indicates whether processing and verification produced a complete usable representation.

#### Governance Status

Belongs primarily to the Document Version.

It indicates whether the version is permitted, pending review, superseded, disabled, or otherwise governed.

#### Publication Status

Belongs to the Indexed Representation’s relationship with the normal retrieval path.

It indicates whether that representation is currently available to Data Query.

#### Index Status

Belongs to the registered OpenSearch Index.

It represents application-relevant availability or consistency, not document governance.

---

### 7.12 Current and Historical State

The domain model must preserve both:

```text
Current selected state
```

and:

```text
Complete historical state
```

Examples of current selections include:

* current Document Version;
* active governance-permitted version;
* published Indexed Representation;
* selected retrieval index.

These selections must not overwrite historical records.

For example:

```text
New Document Version becomes active
→ Previous Version remains historically visible
```

```text
New Indexed Representation is published
→ Previous Representation remains traceable and available for rollback
```

---

### 7.13 Derived Monitoring State

Some monitoring values may be derived from multiple entities.

Examples include:

```text
Document has unresolved failure
```

```text
Document has no published representation
```

```text
Published representation uses a superseded Document Version
```

```text
Processing succeeded but verification is missing
```

Derived states are useful for user visibility and issue detection.

They must remain explainable through the underlying authoritative records.

The UI must not present a derived status without allowing the user to identify the entities and conditions that produced it.

---

### 7.14 External Resource References

The Monitoring Domain Model may reference external resources such as:

* S3 Source Artifacts;
* OpenSearch indexes;
* OpenSearch records;
* ECS or worker execution identifiers;
* CloudWatch logs.

These references support diagnosis and reconciliation.

External infrastructure identifiers must not replace stable application-domain identifiers.

For example:

```text
ECS Task ID
≠ Processing Run ID
```

A Processing Run must remain understandable after the infrastructure task that executed it no longer exists.

---

### 7.15 Model Consistency Requirements

The domain model must prevent or identify invalid relationships such as:

```text
Processing Run without Document Version
```

```text
Indexed Representation without Processing Run
```

```text
Published Representation without successful verification
```

```text
Active Representation associated with a disabled Document Version
```

```text
Document Version without a traceable Source Artifact
```

Such conditions should be marked as inconsistent rather than silently represented as valid lifecycle state.

---

### 7.16 Core Monitoring Domain Rules

1. Document, Document Version, Source Artifact, Processing Run, Indexed Representation, and OpenSearch Index remain separate entities.
2. One Document Version may have multiple Processing Runs.
3. Technical-processing changes do not create a new Document Version.
4. Every Processing Run preserves its effective Configuration Snapshot.
5. Every Indexed Representation remains traceable to one Processing Run and one target index.
6. Processing, readiness, governance, publication, and index statuses remain separate.
7. Current selections do not remove historical versions or representations.
8. Lifecycle Events record important changes but do not replace current entity state.
9. External AWS and OpenSearch identifiers do not replace application-domain identity.
10. Derived monitoring states must remain explainable through authoritative records.
11. Invalid entity relationships must be detected and exposed as inconsistencies.
12. Database and API implementation details belong in the relevant Specs and Definition of Done.

The resulting Monitoring Domain Model is:

```text
Stable Lifecycle Entities
→ Explicit Relationships
→ Separate Status Ownership
→ Current and Historical Visibility
→ Auditable Administrative Control
```


## 8. Document Registry

The Document Registry provides the authoritative application-level view of the logical Documents managed by CVS Review Portal.

Its purpose is to allow authorized users to:

* identify which Documents exist;
* understand their current lifecycle state;
* navigate to their Versions, Source Artifacts, Processing Runs, and Indexed Representations;
* identify unresolved failures, warnings, or governance issues;
* preserve stable Document identity independently of files and technical processing.

The Document Registry is not the storage location for document content.

The primary boundary is:

```text
Logical Document Identity
→ Current Lifecycle Summary
→ Related Versions and Representations
→ Historical Traceability
```

---

### 8.1 Registry Responsibility

The Document Registry is responsible for exposing the logical Document as the top-level monitoring entity.

A registered Document should remain identifiable independently of:

* filename;
* Source Artifact;
* Document Version;
* Processing Run;
* OpenSearch index;
* indexed Chunk.

For example:

```text
One logical Document
→ Multiple Document Versions
→ Multiple Processing Runs
→ Multiple Indexed Representations
```

The registry must not create a new Document entry merely because the same source was processed again.

---

### 8.2 Document Information

The registry should expose the critical information required to identify and manage a Document.

Indicative information includes:

* stable Document identifier;
* title;
* source type;
* source authority;
* jurisdiction;
* official identifier where available;
* creation timestamp;
* current or selected Document Version;
* governance summary;
* publication summary;
* latest Processing Run outcome;
* unresolved issue indicator.

Not every field must be present for every Document.

Missing optional metadata must remain distinguishable from invalid or conflicting metadata.

The final database fields, API schemas, and UI columns belong in the relevant implementation deliverables.

---

### 8.3 Current Lifecycle Summary

Each Document entry should provide a concise summary of its current operational state.

The summary may include:

```text
Current Document Version
Latest Processing Run
Technically Ready Representation
Published Representation
Governance Status
Unresolved Failure or Warning
```

The registry must not collapse these into one ambiguous Document status.

For example:

```text
Current Version: v3
Latest Processing Run: FAILED
Published Representation: v2 / Run 14
Governance Status: ACTIVE
```

This is a valid state: a new run may fail while the previous verified representation remains published.

---

### 8.4 Document List

The Document list should allow an authorized user to:

* identify registered Documents;
* distinguish Documents with similar titles;
* identify the current Version;
* see high-level governance and publication state;
* identify Documents requiring attention;
* navigate to Document details.

The MVP may support basic:

* filtering;
* sorting;
* searching;
* issue indicators.

The exact columns, pagination, search implementation, and refresh behaviour belong in the implementation deliverable.

---

### 8.5 Document Detail

The Document detail view should provide access to:

* canonical Document metadata;
* all Document Versions;
* associated Source Artifacts;
* Processing Runs;
* Indexed Representations;
* active retrieval representation;
* governance and publication history;
* relevant Lifecycle Events.

The user should be able to move through:

```text
Document
→ Document Version
→ Processing Run
→ Indexed Representation
→ OpenSearch Index
```

without manually copying identifiers or inspecting internal storage.

---

### 8.6 Identity Integrity

The registry must preserve stable logical Document identity.

Document identity must not be determined solely by:

* filename;
* title;
* checksum;
* OpenSearch index membership.

Possible duplicate or conflicting Documents should be marked for controlled review rather than silently merged.

The registry must make visible when:

* identity resolution is incomplete;
* duplicate Documents may exist;
* metadata conflicts affect Document identity;
* a Version is associated with an unexpected Document.

Document merge behaviour is not required for the initial MVP unless real data creates that need.

If introduced, merging must preserve historical relationships and audit events.

---

### 8.7 Relationship to Document Versions

A Document may have multiple Document Versions.

The registry should identify, where applicable:

* latest registered Version;
* governance-active Version;
* Version used by the published representation;
* superseded Versions;
* disabled Versions;
* Versions pending review.

These concepts may refer to different Versions.

For example:

```text
Latest Version: v4
Governance-Active Version: v3
Published Representation: v3 / Processing Run 21
```

The registry must not assume that the newest uploaded Version is automatically approved or published.

---

### 8.8 Issue Visibility

The Document Registry should identify high-level conditions requiring attention.

Examples include:

```text
No Document Version registered
No Source Artifact available
Latest Processing Run failed
No technically ready representation
No published representation
Published representation uses superseded Version
Metadata conflict requires review
Lifecycle inconsistency detected
```

Issue indicators should remain explainable through the related entity state.

The Document Registry may summarize the issue, but detailed diagnosis belongs in the relevant:

* Document Version;
* Processing Run;
* Indexed Representation;
* reconciliation view.

---

### 8.9 Administrative Actions

The Document Registry may provide entry points for permitted actions such as:

* open Document details;
* upload a new Version;
* initiate reprocessing of an existing Version;
* review governance state;
* inspect or change publication;
* view failures;
* initiate reconciliation.

The registry itself does not execute parsing, embedding, indexing, or retrieval.

It submits the action to the component that owns the underlying lifecycle operation.

Permanent Document deletion is outside the default MVP scope.

Reversible actions such as disabling or superseding should be preferred.

---

### 8.10 Historical Visibility

A Document must remain visible after:

* a new Version is registered;
* a Version is superseded;
* a representation is replaced;
* processing fails;
* publication changes;
* rollback occurs.

The registry should preserve access to the complete lifecycle rather than showing only the latest successful state.

A Document record should not be overwritten or recreated whenever its current Version or published representation changes.

---

### 8.11 Registry Source of Truth

The Document Registry should use authoritative application operational state.

It must not infer the complete Document lifecycle only from:

* S3 objects;
* OpenSearch records;
* application logs;
* ECS tasks;
* filenames.

External resources may be inspected for reconciliation, but the registry remains the authoritative application view of:

* Document identity;
* Version relationships;
* lifecycle selections;
* governance state;
* publication state.

---

### 8.12 Core Document Registry Rules

1. The Document is the top-level logical monitoring entity.
2. Document identity remains independent of filenames and Processing Runs.
3. One Document may contain multiple Document Versions.
4. The newest Version is not automatically the active or published Version.
5. Latest Processing Run state does not replace publication state.
6. Current lifecycle summaries must remain explainable through related entities.
7. Historical Versions and representations remain accessible.
8. Identity conflicts must be visible and controlled.
9. The registry uses authoritative operational records rather than reconstructing state only from external systems.
10. UI, API, persistence, filtering, and pagination details belong in the implementation Specs and Definition of Done.

The resulting Document Registry boundary is:

```text
Stable Document Identity
→ Current Lifecycle Summary
→ Version and Representation Navigation
→ Issue Visibility
→ Historical and Governance Traceability
```


## 9. Document Version Monitoring

Document Version Monitoring provides visibility into the distinct editions, revisions, releases, or effective states associated with one logical Document.

Its purpose is to allow authorized users to determine:

* which Versions exist;
* which source artifact belongs to each Version;
* which Version is newest;
* which Version is governance-active;
* which Version supports the currently published representation;
* which Versions are pending review, superseded, disabled, or historically retained;
* which Processing Runs and Indexed Representations were created from each Version.

The primary relationship is:

```text
Document
→ Document Version
    ├── Source Artifact
    ├── Governance State
    ├── Processing Runs
    └── Indexed Representations
```

Document Version Monitoring must preserve the distinction between source revision, technical processing, governance approval, and retrieval publication.

---

### 9.1 Version Identity

Each Document Version must have a stable application-level identity.

Version identity should not depend solely on:

* filename;
* upload timestamp;
* source checksum;
* user-provided version label;
* Processing Run;
* OpenSearch representation.

A Document Version represents a distinct state of the source material.

Examples include:

* official publication;
* amendment;
* corrigendum;
* internal policy revision;
* updated technical standard;
* new effective edition.

Reprocessing the same source with a different parser, embedding model, or chunking strategy must not create a new Document Version.

The distinction is:

```text
Source content changed
→ New Document Version

Processing configuration changed
→ New Processing Run
```

---

### 9.2 Version Information

Document Version Monitoring should expose the critical information required to identify and evaluate a Version.

Indicative information includes:

* stable Version identifier;
* parent Document;
* version label or official identifier;
* publication date;
* effective date;
* expiry or withdrawal date where applicable;
* source authority;
* jurisdiction;
* amendment or replacement relationship;
* governance status;
* Source Artifact;
* registration timestamp;
* latest Processing Run;
* technically ready representation;
* publication status;
* unresolved issue indicator.

Not all metadata will be available for every Version.

The system must distinguish:

```text
Metadata not provided
≠ Metadata invalid
≠ Metadata conflicting
```

The final persistence fields, validation rules, and UI layout belong in the relevant implementation specifications.

---

### 9.3 Version List

The Version list for a Document should allow the user to identify:

* all registered Versions;
* their chronological or logical order;
* governance status;
* technical-readiness state;
* publication state;
* latest Processing Run outcome;
* Source Artifact availability;
* unresolved failures or inconsistencies.

The list should make clear that multiple state concepts may refer to different Versions.

For example:

```text
Newest Registered Version: v4
Governance-Active Version: v3
Published Representation: v3 / Processing Run 21
Latest Processing Run: v4 / FAILED
```

The interface must not imply that the newest Version is automatically active or published.

---

### 9.4 Version Detail

The Version detail view should provide access to:

* Version metadata;
* parent Document;
* canonical Source Artifact;
* Processing Runs;
* Configuration Snapshots;
* Indexed Representations;
* verification outcomes;
* governance history;
* publication history;
* related Lifecycle Events.

The user should be able to trace:

```text
Document Version
→ Source Artifact
→ Processing Run
→ Indexed Representation
→ OpenSearch Index
→ Publication State
```

The Version detail must preserve both current and historical technical outcomes.

---

### 9.5 Source Artifact Relationship

Each Document Version should be associated with one canonical Source Artifact in the initial MVP.

The Source Artifact represents the exact file accepted for that Version.

The Version view should expose authorized artifact information such as:

* original filename;
* checksum;
* file type;
* file size;
* upload timestamp;
* storage status.

A Version must not be treated as fully traceable when its canonical Source Artifact relationship is missing or inconsistent.

For example:

```text
Document Version exists
but
Canonical Source Artifact is missing

→ Lifecycle inconsistency
```

Additional derived or intermediate artifacts may exist, but they must not replace the canonical Source Artifact relationship.

---

### 9.6 Processing Run History

One Document Version may have multiple Processing Runs.

The Version view should allow the user to compare runs by:

* execution timestamp;
* status;
* current or failed stage;
* processing configuration;
* parser version;
* chunking configuration;
* embedding model;
* target index;
* processing counts;
* verification outcome;
* technical-readiness result.

Previous runs must remain visible after a newer run succeeds.

A successful new run must not mutate the historical status or configuration of an earlier run.

---

### 9.7 Representation History

A Document Version may have multiple Indexed Representations.

This may occur because of:

* reprocessing;
* reindexing;
* parser changes;
* metadata changes;
* chunking changes;
* embedding-model changes;
* target-index changes;
* failed or replaced indexing attempts.

The Version view should identify:

* technically ready representations;
* failed or incomplete representations;
* published representation;
* previous published representations;
* disabled or replaced representations;
* rollback candidates.

A representation must remain traceable to the exact Processing Run and Configuration Snapshot that produced it.

---

### 9.8 Version State Separation

The system must not collapse Version-related states into one field.

At minimum, it must preserve the distinction between:

```text
Version Recency
Governance Status
Technical Readiness
Publication Status
Latest Processing Outcome
```

Example:

```text
Version: v4
Recency: LATEST
Governance Status: PENDING_REVIEW
Technical Readiness: READY
Publication Status: NOT_PUBLISHED
Latest Processing Outcome: SUCCEEDED
```

Another valid example is:

```text
Version: v3
Recency: PREVIOUS
Governance Status: ACTIVE
Technical Readiness: READY
Publication Status: PUBLISHED
```

These two Version states may coexist.

---

### 9.9 Governance Status

Governance status belongs primarily to the Document Version.

Indicative values may include:

```text
PENDING_REVIEW
APPROVED
ACTIVE
SUPERSEDED
DISABLED
REJECTED
```

The exact state model belongs in the relevant lifecycle specification.

The governance status should indicate whether the Version is organizationally permitted for retrieval or compliance use.

It must not be inferred only from:

* successful processing;
* successful indexing;
* OpenSearch availability;
* publication recency.

A technically successful Version may remain pending governance review.

---

### 9.10 Current, Active, and Published Version

The following concepts must remain distinct:

#### Latest Registered Version

The most recently registered source revision.

#### Governance-Active Version

The Version currently recognized as applicable or approved by the governance process.

#### Published Version

The Version whose representation is available to normal Data Query operations.

#### Current Display Version

The Version selected by the user for inspection.

These may refer to the same Version, but this must not be assumed.

For example:

```text
Latest Registered Version: v5
Governance-Active Version: v4
Published Version: v4
Current Display Version: v3
```

---

### 9.11 Superseding and Replacement Relationships

Document Version Monitoring should expose whether a Version:

* replaces another Version;
* is replaced by another Version;
* amends another Version;
* is superseded;
* remains applicable for historical purposes.

A superseding action must preserve:

* previous Version metadata;
* Source Artifact;
* Processing Runs;
* Indexed Representations;
* historical publication state;
* Lifecycle Events.

Superseding a Version must not permanently delete it.

The Version relationship should remain explicit rather than inferred only from version labels or dates.

---

### 9.12 New Version Registration

When a new Version is registered, the system should:

* preserve the existing Document identity;
* create a new Version identity;
* associate the new canonical Source Artifact;
* preserve all earlier Versions;
* avoid automatically changing governance or publication state;
* make the new Version available for processing and review.

The default relationship is:

```text
New Version Registered
→ Existing Active Version Remains Active
→ New Version Is Processed and Reviewed
→ Publication Changes Only Through Controlled Action
```

This prevents a newly uploaded but unverified source from replacing the current retrieval representation.

---

### 9.13 Version Comparison

Document Version Monitoring may provide entry points for comparing two Versions.

A comparison may include:

* metadata differences;
* publication and effective dates;
* source checksum;
* processing configurations;
* representation counts;
* governance status;
* publication history;
* later, content-level differences.

Detailed semantic or legal change detection is outside the initial monitoring scope unless introduced by a dedicated deliverable.

The MVP may provide a simpler comparison based on metadata and lifecycle state.

---

### 9.14 Version Issues

The system should identify Version-level conditions requiring attention.

Examples include:

```text
Canonical Source Artifact missing
No Processing Run exists
All Processing Runs failed
Technical representation exists but verification is missing
Version approved but no published representation exists
Published representation belongs to a superseded Version
Multiple Versions marked governance-active
Effective-date metadata conflicts
Replacement relationship is incomplete
```

A high-level issue indicator should link to the underlying records responsible for the condition.

---

### 9.15 Administrative Actions

Document Version Monitoring may expose controlled actions such as:

* inspect Source Artifact;
* initiate processing;
* initiate reprocessing;
* review governance status;
* approve or reject the Version;
* mark the Version active;
* mark the Version superseded;
* disable the Version;
* publish a technically ready representation;
* roll back to a previous representation;
* initiate reconciliation.

Actions must be available only when allowed by lifecycle and authorization rules.

The exact transition validation, API commands, confirmation steps, and permission checks belong in the implementation specifications.

---

### 9.16 Historical and Audit Requirements

Every material Version change should remain historically traceable.

Relevant events include:

* Version registered;
* metadata corrected;
* governance status changed;
* Version activated;
* Version superseded;
* Version disabled;
* processing initiated;
* representation published;
* rollback performed.

The history should identify, where applicable:

* timestamp;
* responsible actor or system component;
* previous state;
* new state;
* reason or safe summary.

Correcting metadata should not silently erase the previous material state when the change affects governance, identity, or traceability.

---

### 9.17 Consistency Requirements

Document Version Monitoring must identify invalid or suspicious conditions such as:

```text
Document Version without parent Document
```

```text
Document Version without canonical Source Artifact
```

```text
Processing Run linked to a different Version than its Source Artifact
```

```text
Published representation linked to a disabled Version
```

```text
Multiple governance-active Versions without an explicit exception
```

```text
Superseded Version still used for retrieval without recorded approval
```

Such conditions must be exposed as inconsistencies rather than silently accepted.

---

### 9.18 Core Document Version Monitoring Rules

1. A Document Version represents a distinct source revision, not a technical-processing attempt.
2. Reprocessing creates a new Processing Run, not a new Document Version.
3. Every Version remains associated with its parent Document and canonical Source Artifact.
4. One Version may have multiple Processing Runs and Indexed Representations.
5. The newest, governance-active, and published Versions may differ.
6. Successful processing does not automatically grant governance approval.
7. Registration of a new Version does not automatically replace the currently published Version.
8. Superseded and disabled Versions remain historically visible.
9. All representations remain traceable to their originating Version and Processing Run.
10. Version-level inconsistencies must be visible and explainable.
11. Material governance and publication changes must be auditable.
12. Detailed schemas, APIs, and UI mechanics belong in the implementation Specifications and Definition of Done.

The resulting Document Version Monitoring boundary is:

```text
Stable Version Identity
→ Source and Processing Traceability
→ Separate Governance and Publication State
→ Safe Version Replacement
→ Complete Historical Visibility
```


## 10. Source Artifact Visibility

Source Artifact Visibility allows an authorized user to identify and inspect the exact original file associated with a Document Version.

Its purpose is to preserve:

```text id="sa-core"
Document Version
→ Original Source Artifact
→ Processing Runs
```

The Source Artifact is the immutable file accepted and stored by Data Ingest.

It is distinct from:

* parsed content;
* normalized content;
* Chunks;
* embeddings;
* Indexed Representations;
* temporary processing artifacts.

### 10.1 Required Visibility

Data Monitoring should expose, where authorized:

* Source Artifact identifier;
* related Document and Document Version;
* original filename;
* file type;
* file size;
* checksum;
* upload timestamp;
* storage status;
* related Processing Runs.

The system may provide controlled access to view or download the original file when permitted.

Direct S3 access is not required for normal monitoring use.

### 10.2 Artifact Integrity

The checksum identifies the exact accepted file and supports:

* duplicate detection;
* integrity verification;
* provenance;
* processing reproducibility.

The Source Artifact should not be modified after acceptance.

A corrected or changed source file should create a new Source Artifact and, where the source content represents a new revision, a new Document Version.

### 10.3 Relationship Integrity

Every Processing Run must remain traceable to the Source Artifact it processed.

The expected relationship is:

```text id="sa-relation"
Document Version
├── Canonical Source Artifact
└── Processing Runs referencing that Source Artifact
```

The following conditions must be visible as inconsistencies:

```text id="sa-errors"
Document Version without Source Artifact
Processing Run without Source Artifact reference
Source Artifact linked to an unexpected Document Version
Stored artifact missing or inaccessible
Checksum mismatch
```

### 10.4 Storage and Processing State

Artifact storage state must remain separate from processing state.

For example:

```text id="sa-state"
Source Artifact: STORED
Processing Run: FAILED
```

This means the original source remains safely stored even though downstream processing failed.

Similarly:

```text id="sa-state-2"
Source Artifact: STORED
Processing Run: NOT_STARTED
```

must not be represented as completed ingestion.

### 10.5 Historical Visibility

Source Artifacts must remain traceable after:

* reprocessing;
* reindexing;
* publication changes;
* Document Version superseding;
* rollback.

A newer Processing Run must not overwrite the Source Artifact relationship of previous runs.

### 10.6 Access and Security

Source Artifact visibility must respect authorization and data-sensitivity rules.

Monitoring views should not expose:

* S3 credentials;
* unrestricted bucket access;
* internal storage secrets;
* sensitive infrastructure details.

Access to the original file should be controlled, logged where required, and limited to authorized users.

### 10.7 Core Source Artifact Rules

1. The Source Artifact represents the exact immutable file accepted by Data Ingest.
2. Each Document Version has one canonical Source Artifact in the MVP.
3. Every Processing Run remains traceable to the Source Artifact it processed.
4. Artifact storage status remains separate from processing status.
5. Missing, inaccessible, or mismatched artifacts must be exposed as inconsistencies.
6. Historical Source Artifact relationships must not be overwritten.
7. Direct storage implementation and access mechanics belong in the implementation Specifications.

The resulting boundary is:

```text id="sa-summary"
Immutable Source Provenance
→ Processing Traceability
→ Integrity Verification
→ Controlled Visibility
```



## 11. Processing Run Monitoring

Processing Run Monitoring provides visibility into each technical execution of the ingestion pipeline for a Document Version.

Its purpose is to show:

```text id="prm-core"
What was processed
→ With which configuration
→ Through which stages
→ With what outcome
```

A Processing Run is distinct from the Document Version and Source Artifact.

Reprocessing the same Version creates a new Processing Run.

### 11.1 Required Visibility

Data Monitoring should expose:

* Processing Run identifier;
* related Document Version;
* referenced Source Artifact;
* overall status;
* current or failed stage;
* effective configuration reference;
* target OpenSearch index;
* start and completion timestamps;
* processing counts;
* warnings and failure summary;
* verification outcome;
* parent or retry relationship where applicable.

### 11.2 Status and Stage Separation

Overall Processing Run status must remain separate from the current processing stage.

For example:

```text id="prm-stage"
Processing Status: RUNNING
Current Stage: EMBEDDING
```

Indicative stages include:

```text id="prm-stages"
PARSING
NORMALIZATION
METADATA_HANDLING
CHUNKING
EMBEDDING
INDEXING
VERIFICATION
```

Processing status must also remain separate from:

* Technical Readiness;
* Governance Status;
* Publication Status;
* OpenSearch Index Health.

### 11.3 Processing Counts

The run should expose sufficient counts to understand progress and detect incomplete processing.

Indicative counts include:

* parsed pages or sections;
* normalized units;
* generated Chunks;
* generated embeddings;
* attempted indexed records;
* successfully indexed records;
* verification failures.

The exact metrics depend on the processing configuration and belong in the implementation specification.

### 11.4 Failure and Warning Visibility

A failed run should expose:

* failed stage;
* failure category;
* safe error summary;
* partial processing outcome;
* whether retry or reprocessing is permitted;
* whether an earlier published representation remains available.

Warnings must remain distinguishable from blocking failures.

Raw stack traces, secrets, and sensitive infrastructure details should not be exposed through normal monitoring views.

### 11.5 Retry and Reprocessing History

Retries and reprocessing must preserve historical traceability.

The system should distinguish:

```text id="prm-recovery"
Retry
→ Continued or repeated recovery of a failed operation

Reprocessing
→ New Processing Run for the same Document Version
```

Previous failed or successful runs must not be overwritten.

Each new run must preserve its own:

* configuration;
* timestamps;
* counts;
* outcome;
* relationship to earlier runs.

### 11.6 Consistency Requirements

The following conditions must be visible as inconsistencies:

```text id="prm-errors"
Processing Run without Document Version
Processing Run without Source Artifact reference
SUCCEEDED run without verification outcome
RUNNING run with no active stage
Published representation linked to a failed run
Recorded target index missing or incompatible
```

### 11.7 Core Processing Run Rules

1. Each Processing Run represents one technical execution for one Document Version.
2. Reprocessing creates a new Processing Run.
3. Every run remains traceable to its Source Artifact and configuration.
4. Overall status and processing stage remain separate.
5. Processing success does not automatically imply technical readiness or publication.
6. Failures, warnings, partial outcomes, and recovery relationships remain visible.
7. Historical runs must not be overwritten.
8. Detailed orchestration, persistence, and retry mechanics belong in the implementation Specifications.

The resulting boundary is:

```text id="prm-summary"
Execution Visibility
→ Stage and Failure Traceability
→ Configuration Reproducibility
→ Historical Recovery Context
```



## 12. Stage Progress, Failures, and Warnings

This section defines how Data Monitoring exposes execution progress and processing problems within a Processing Run.

Its purpose is to answer:

```text id="spfw-core"
Where is the run
→ What went wrong
→ What was affected
→ What action is possible
```

### 12.1 Stage Progress

A running Processing Run should expose:

* current stage;
* completed stages;
* stage start time;
* available progress counts;
* latest recorded activity.

Indicative stages include:

```text id="spfw-stages"
PARSING
NORMALIZATION
METADATA_HANDLING
CHUNKING
EMBEDDING
INDEXING
VERIFICATION
```

Progress may be count-based or stage-based.

The MVP does not require precise percentage completion when the processing workload cannot be estimated reliably.

### 12.2 Failure Visibility

A failure should expose:

* failed stage;
* failure category;
* safe error summary;
* affected Document Version and Source Artifact;
* partial processing counts;
* retry or reprocessing eligibility;
* impact on publication and retrieval availability.

A failure in a new run must not imply that an earlier published representation is unavailable.

For example:

```text id="spfw-failure-example"
Latest Processing Run: FAILED
Previous Published Representation: AVAILABLE
```

### 12.3 Warning Visibility

Warnings represent non-blocking conditions that may affect quality, completeness, or future operations.

Examples include:

* pages with low parsing confidence;
* missing optional metadata;
* unusually large or small Chunks;
* skipped content;
* partial indexing retries;
* count differences within accepted tolerance.

Warnings should expose:

* category;
* severity;
* stage;
* safe description;
* affected entity or source location where available.

Warnings must remain distinguishable from blocking failures.

### 12.4 Failure Classification

Failures should be classified sufficiently to support monitoring and recovery.

Indicative categories include:

```text id="spfw-categories"
VALIDATION
PARSING
CONFIGURATION
EXTERNAL_SERVICE
EMBEDDING
INDEXING
VERIFICATION
TIMEOUT
INTERNAL
```

The exact taxonomy belongs in the implementation specification.

Failure classification should support the distinction between:

```text id="spfw-recovery"
Recoverable
Non-Recoverable
Requires Human Review
```

### 12.5 Safe Error Information

Normal monitoring views must not expose:

* raw stack traces;
* credentials or secrets;
* sensitive document content;
* internal network details;
* unrestricted infrastructure identifiers.

Detailed technical diagnostics may remain available through authorized logs and operational tooling.

### 12.6 Stalled and Incomplete Runs

The system should identify runs that appear incomplete or stalled.

Examples include:

```text id="spfw-stalled"
RUNNING status with no recent activity
Stage started but never completed
Run completed without verification outcome
Failure recorded without terminal run status
```

Such conditions should be marked for investigation or reconciliation.

### 12.7 Core Progress and Failure Rules

1. Current stage remains separate from overall Processing Run status.
2. Progress should use reliable stage or count information rather than invented percentages.
3. Failures must identify the affected stage and operational impact.
4. Warnings must remain separate from blocking failures.
5. Recovery eligibility should be visible when known.
6. Previous valid published representations must remain distinguishable from failed newer runs.
7. Stalled or incomplete state must be detectable.
8. Detailed exception handling and alerting mechanics belong in the implementation Specifications.

The resulting boundary is:

```text id="spfw-summary"
Stage Visibility
→ Safe Failure Classification
→ Warning Transparency
→ Recovery Context
→ Incomplete-State Detection
```


## 13. Indexed Representation Monitoring

Indexed Representation Monitoring provides visibility into the searchable output produced by a Processing Run.

An Indexed Representation connects:

```text id="irm-core"
Document Version
→ Processing Run
→ Searchable Records
→ OpenSearch Index
```

It is distinct from both the Processing Run and the OpenSearch Index.

### 13.1 Required Visibility

Data Monitoring should expose:

* Indexed Representation identifier;
* related Document Version;
* originating Processing Run;
* configuration reference;
* target OpenSearch index;
* expected and indexed record counts;
* verification outcome;
* Technical Readiness;
* Publication Status;
* creation timestamp.

### 13.2 Representation State

The representation should preserve separate states for:

```text id="irm-states"
Indexing Outcome
Technical Readiness
Verification Outcome
Publication Status
```

For example:

```text id="irm-example"
Indexing Outcome: SUCCEEDED
Verification Outcome: PASSED
Technical Readiness: READY
Publication Status: NOT_PUBLISHED
```

Successful indexing alone must not imply that the representation is verified or available to Data Query.

### 13.3 Count and Completeness Visibility

The system should expose sufficient counts to identify incomplete or unexpected indexing.

Indicative information includes:

* expected Chunk count;
* attempted records;
* successfully indexed records;
* failed records;
* verified records.

Count differences must be evaluated by verification rules rather than assumed to be acceptable.

### 13.4 Representation History

One Document Version may have multiple Indexed Representations because of:

* reprocessing;
* reindexing;
* configuration changes;
* embedding-model changes;
* target-index changes;
* failed or replaced attempts.

Previous representations must remain historically traceable after a newer one is created or published.

### 13.5 Publication Relationship

Data Monitoring should identify whether a representation is:

```text id="irm-publication"
NOT_PUBLISHED
PUBLISHED
DISABLED
REPLACED
```

Only representations permitted by technical and governance rules may become available to normal Data Query operations.

Disabling or replacing a representation must preserve its historical records.

### 13.6 Consistency Requirements

The following conditions must be visible as inconsistencies:

```text id="irm-errors"
Representation without Processing Run
Representation without target index
Indexed counts incompatible with verification result
Representation marked READY without successful verification
Published representation linked to failed processing
Published representation linked to disabled or superseded Version
```

### 13.7 Core Indexed Representation Rules

1. An Indexed Representation is the searchable output of one Processing Run.
2. It remains traceable to its Document Version, configuration, and target index.
3. Indexing success, verification, Technical Readiness, and publication remain separate.
4. Multiple representations may exist for one Document Version.
5. Historical representations must not be overwritten.
6. Only eligible representations may be published to Data Query.
7. Count or relationship inconsistencies must be visible.
8. Detailed OpenSearch mappings and indexing mechanics belong in the implementation Specifications.

The resulting boundary is:

```text id="irm-summary"
Searchable Output Traceability
→ Completeness Verification
→ Separate Readiness and Publication State
→ Historical Representation Control
```


## 14. OpenSearch Index Registry

The OpenSearch Index Registry provides the application-level record of OpenSearch indexes used by CVS Review Portal.

Its purpose is to identify:

```text id="oir-core"
Which indexes exist
→ What configuration they use
→ Which representations they contain
→ Whether they are eligible for retrieval
```

The registry is not a replacement for OpenSearch or AWS administration tooling.

### 14.1 Required Visibility

Data Monitoring should expose:

* registered index identifier or name;
* index version or generation;
* index purpose;
* configuration reference;
* vector dimensions;
* creation timestamp;
* basic availability or health;
* associated Indexed Representations;
* retrieval-selection state;
* known consistency issues.

### 14.2 Registry and OpenSearch State

The application registry and observed OpenSearch state must remain distinguishable.

For example:

```text id="oir-state"
Registry Status: REGISTERED
Observed OpenSearch State: UNAVAILABLE
```

The registry records the application’s intended relationship with the index.

OpenSearch provides the observed external resource state.

Differences between them should be visible as reconciliation issues.

### 14.3 Index Versioning

A material change to index configuration should create a new index version or generation rather than silently altering the meaning of existing representations.

Material changes may include:

* mappings;
* vector dimensions;
* embedding model compatibility;
* analysis configuration;
* retrieval strategy requirements.

Historical representations must remain associated with the index configuration under which they were created.

### 14.4 Retrieval Selection

The registry should identify which index or indexes are eligible for Data Query.

An index must not be selected for normal retrieval solely because it exists or reports healthy infrastructure status.

Retrieval eligibility also depends on:

* representation Technical Readiness;
* governance permission;
* Publication Status;
* configuration compatibility.

### 14.5 Representation Relationships

Each registered index should expose the Indexed Representations associated with it.

The relationship must support both directions:

```text id="oir-traceability"
Indexed Representation
→ OpenSearch Index

OpenSearch Index
→ Indexed Representations
```

The registry should make incomplete, failed, disabled, and published representations distinguishable.

### 14.6 Consistency Requirements

The following conditions should be visible as inconsistencies:

```text id="oir-errors"
Registered index does not exist in OpenSearch
Observed index exists but is not registered
Index configuration is incompatible with its representations
Published representation points to an unavailable index
Recorded and observed indexed counts differ unexpectedly
Index selected for retrieval contains no eligible representation
```

### 14.7 Core OpenSearch Index Registry Rules

1. The registry records application-level index identity and purpose.
2. Registered state remains separate from observed OpenSearch health.
3. Material configuration changes should create a new index generation.
4. Every Indexed Representation remains traceable to its target index.
5. Infrastructure health alone does not make an index eligible for retrieval.
6. Retrieval selection must respect readiness, governance, publication, and compatibility.
7. Registry-to-OpenSearch inconsistencies must be visible.
8. Detailed cluster, shard, mapping, and operational administration belongs outside Data Monitoring.

The resulting boundary is:

```text id="oir-summary"
Application Index Registry
→ Representation Traceability
→ Retrieval Eligibility
→ External-State Reconciliation
```


## 15. Document-to-Index Traceability

Document-to-Index Traceability ensures that every searchable record can be connected to its original source and processing history.

The required traceability path is:

```text id="diti-core"
Document
→ Document Version
→ Source Artifact
→ Processing Run
→ Indexed Representation
→ OpenSearch Index
```

The reverse path must also be available for investigation:

```text id="diti-reverse"
OpenSearch Index
→ Indexed Representation
→ Processing Run
→ Document Version
→ Document
```

### 15.1 Traceability Requirements

Each Indexed Representation must remain linked to:

* one Document Version;
* its originating Processing Run;
* the Source Artifact processed by that run;
* the effective configuration;
* the target OpenSearch index.

Indexed records should preserve sufficient application identifiers to support source-level traceability without relying only on filenames or text content.

### 15.2 Search-Result Provenance

A result returned by Data Query should be traceable to:

* Document;
* Document Version;
* source location where available;
* Chunk or indexed-record identifier;
* Indexed Representation;
* Processing Run.

This enables the system to explain which source supports a retrieved result.

### 15.3 Historical Traceability

Traceability must remain valid after:

* reprocessing;
* reindexing;
* new Document Version registration;
* representation replacement;
* publication changes;
* rollback.

A newer representation must not overwrite the provenance of older indexed records.

### 15.4 Consistency Requirements

The following conditions must be visible as inconsistencies:

```text id="diti-errors"
Indexed record without Document Version identity
Indexed Representation without Processing Run
Processing Run and Source Artifact linked to different Versions
Published record without traceable representation
Application record exists but OpenSearch record is missing
OpenSearch record exists without authoritative application relationship
```

### 15.5 Core Traceability Rules

1. Every searchable representation must be traceable to its original Document Version and Source Artifact.
2. Traceability must work from source to index and from index back to source.
3. Application-domain identifiers must be used instead of relying solely on filenames or OpenSearch-generated identifiers.
4. Search results must preserve enough provenance to support evidence-based responses.
5. Historical traceability must survive reprocessing, replacement, and rollback.
6. Broken or conflicting relationships must be exposed as inconsistencies.
7. Exact identifier fields and OpenSearch mappings belong in the implementation Specifications.

The resulting boundary is:

```text id="diti-summary"
Source Provenance
→ Processing Lineage
→ Indexed-Record Identity
→ Evidence Traceability
```


## 16. Technical Readiness, Governance, and Publication

This section defines the separate decisions required before an Indexed Representation becomes available to normal Data Query operations.

The required state separation is:

```text id="trgp-core"
Technical Readiness
≠ Governance Status
≠ Publication Status
```

A representation may be technically valid but not governance-approved or published.

### 16.1 Technical Readiness

Technical Readiness indicates whether an Indexed Representation is complete and technically usable.

It should depend on conditions such as:

* Processing Run succeeded;
* indexing completed;
* required records are present;
* verification passed;
* target index is compatible and available;
* no blocking inconsistency exists.

Indicative states may include:

```text id="trgp-readiness"
PENDING
READY
NOT_READY
INVALID
```

Technical Readiness must not imply legal approval or retrieval publication.

### 16.2 Governance Status

Governance Status indicates whether the relevant Document Version is permitted for compliance and retrieval use.

It may reflect decisions such as:

```text id="trgp-governance"
PENDING_REVIEW
APPROVED
ACTIVE
SUPERSEDED
DISABLED
REJECTED
```

Governance decisions must be performed by an authorized user or explicit governance policy.

Successful processing must not automatically change Governance Status.

### 16.3 Publication Status

Publication Status indicates whether an eligible Indexed Representation is available to normal Data Query operations.

Indicative states may include:

```text id="trgp-publication"
NOT_PUBLISHED
PUBLISHED
DISABLED
REPLACED
```

Publication is a controlled application decision, not merely the existence of records in OpenSearch.

### 16.4 Publication Eligibility

A representation may be published only when:

```text id="trgp-eligibility"
Technical Readiness: READY
+
Governance Status permits use
+
Target index is compatible and available
+
No blocking inconsistency exists
```

A newly created representation must remain unpublished until these conditions are satisfied.

### 16.5 Replacement and Rollback

Publishing a replacement representation should:

* make the new eligible representation available;
* preserve the previous representation;
* record the publication transition;
* identify the previous representation as replaced or inactive.

Rollback should select a previously verified and governance-permitted representation without deleting later history.

### 16.6 Invalid State Detection

The following conditions must be visible as inconsistencies:

```text id="trgp-errors"
Published representation not technically READY
Published representation linked to unapproved or disabled Version
Technically READY representation with missing verification
Published representation targeting unavailable index
Multiple active representations without explicit policy
Superseded Version still published without recorded exception
```

### 16.7 Core Readiness, Governance, and Publication Rules

1. Technical Readiness, Governance Status, and Publication Status remain separate.
2. Processing success alone does not make a representation publishable.
3. Governance decisions require authorized human or policy control.
4. OpenSearch presence does not equal publication.
5. Only technically ready and governance-permitted representations may be published.
6. Replacement and rollback must preserve historical traceability.
7. Invalid state combinations must be detected and exposed.
8. Exact state transitions and authorization mechanics belong in the implementation Specifications.

The resulting boundary is:

```text id="trgp-summary"
Technical Validation
→ Governance Permission
→ Controlled Publication
→ Safe Replacement and Rollback
```


## 17. Retry, Reprocessing, Reindexing, and Rollback Actions

Data Monitoring may expose controlled recovery and lifecycle actions.

These actions must remain distinct:

```text id="rrra-core"
Retry
≠ Reprocessing
≠ Reindexing
≠ Rollback
```

### 17.1 Retry

Retry repeats or resumes a recoverable failed operation within the intended Processing Run context.

It should preserve:

* Document Version;
* Source Artifact;
* intended configuration;
* failure history;
* idempotency controls.

Retry must not create uncontrolled duplicate records or hide the original failure.

### 17.2 Reprocessing

Reprocessing creates a new Processing Run for an existing Document Version.

It may be required when changing:

* parser or normalization logic;
* metadata extraction;
* chunking configuration;
* embedding model;
* processing configuration.

Previous Processing Runs and representations remain historically visible.

### 17.3 Reindexing

Reindexing creates or rebuilds an Indexed Representation for a target OpenSearch index.

It may be required because of:

* index-generation changes;
* mapping or configuration changes;
* incomplete indexing;
* index recovery;
* representation replacement.

Reindexing must preserve source, Processing Run, configuration, and index traceability.

### 17.4 Rollback

Rollback selects a previous verified and governance-permitted Indexed Representation for normal retrieval.

Rollback must:

* preserve the newer representation;
* record the previous and new active states;
* avoid deleting lifecycle history;
* verify that the selected index remains available and compatible.

Rollback is a publication action, not a reversal of historical processing.

### 17.5 Action Eligibility

Actions should be available only when lifecycle conditions permit them.

Examples include:

```text id="rrra-examples"
Recoverable failed operation
→ Retry

Existing Document Version requiring new processing
→ Reprocess

Valid source representation requiring a new index target
→ Reindex

Problematic published representation with valid predecessor
→ Rollback
```

Actions affecting retrieval availability must require appropriate authorization.

### 17.6 Audit and Safety

Each action should record:

* action type;
* affected entities;
* initiating actor or system component;
* timestamp;
* reason;
* resulting Processing Run or publication transition.

Recovery actions should prefer immutable history and new execution records over modifying completed historical records.

### 17.7 Core Recovery Action Rules

1. Retry, reprocessing, reindexing, and rollback have different meanings and outcomes.
2. Recovery actions must preserve provenance and historical failures.
3. Retry and reindexing must be idempotent or duplicate-safe.
4. Reprocessing creates a new Processing Run.
5. Rollback changes the active retrieval representation without deleting newer history.
6. Actions must be lifecycle-valid, authorized, and auditable.
7. Exact orchestration, retry limits, and transaction mechanics belong in the implementation Specifications.

The resulting boundary is:

```text id="rrra-summary"
Controlled Recovery
→ Duplicate Safety
→ Historical Preservation
→ Auditable Retrieval Continuity
```


## 18. Reconciliation and Inconsistent States

Reconciliation identifies and resolves differences between authoritative application records and external resources such as S3 and OpenSearch.

Its purpose is:

```text
Expected Lifecycle State
→ Observed External State
→ Difference Detection
→ Controlled Resolution
```

An inconsistent state must not be silently treated as healthy.

### 18.1 Inconsistent State Examples

Examples include:

```text
Source Artifact registered but missing from S3
Processing Run marked SUCCEEDED without verification
Indexed Representation registered but records are missing
OpenSearch records exist without authoritative application ownership
Published representation points to an unavailable index
Document Version and Source Artifact relationships conflict
Multiple representations are published without explicit policy
```

### 18.2 Detection

Inconsistencies may be detected through:

* lifecycle validation;
* periodic reconciliation checks;
* verification after processing;
* administrative inspection;
* failed external-resource access;
* count or configuration comparison.

The detected issue should identify:

* affected entities;
* inconsistency category;
* observed and expected states;
* operational impact;
* whether retrieval remains available;
* permitted next action.

### 18.3 Resolution Actions

A controlled reconciliation action may:

* restore a missing relationship;
* verify an external resource again;
* retry failed registration or indexing;
* mark an artifact or representation as missing;
* disable an invalid publication;
* create a replacement Processing Run;
* register an authorized existing resource;
* mark the issue as requiring human investigation.

Reconciliation must not invent missing provenance or silently alter historical records.

### 18.4 Retrieval Safety

A blocking inconsistency must prevent an affected representation from being newly published or treated as technically ready.

When possible, an earlier valid published representation should remain available.

For example:

```text
New Representation: INCONSISTENT
Previous Published Representation: AVAILABLE
```

### 18.5 Auditability

Each reconciliation action should record:

* issue identifier;
* affected entities;
* action performed;
* initiating actor or system component;
* timestamp;
* previous and resulting state;
* reason or safe summary.

Resolved issues should remain historically visible.

### 18.6 Core Reconciliation Rules

1. Application records define the expected lifecycle state.
2. S3 and OpenSearch provide observed external state.
3. Differences must be exposed as explicit inconsistencies.
4. Blocking inconsistencies must prevent readiness or publication.
5. Reconciliation must preserve provenance and historical records.
6. Automatic repair is allowed only for deterministic and safe cases.
7. Ambiguous conflicts require human review.
8. Detailed reconciliation jobs and repair procedures belong in the implementation Specifications.

The resulting boundary is:

```text
Inconsistency Detection
→ Retrieval Protection
→ Controlled Repair
→ Auditable Resolution
```


## 19. Audit History

Audit History records important lifecycle changes and administrative actions across Data Monitoring.

Its purpose is to answer:

```text id="ah-core"
What changed
→ Who or what changed it
→ When it changed
→ Why it changed
```

### 19.1 Audited Events

Audit History should include material events such as:

* Document and Document Version registration;
* Processing Run creation, completion, failure, retry, or reprocessing;
* verification outcome;
* Technical Readiness change;
* Governance Status change;
* publication, replacement, disablement, or rollback;
* reconciliation action;
* metadata correction affecting identity, governance, or traceability.

Routine technical logs do not need to become audit events.

### 19.2 Required Audit Information

Each audit event should record, where applicable:

* event type;
* affected entity and identifier;
* timestamp;
* actor or system component;
* previous state;
* resulting state;
* reason or safe summary;
* related action or Processing Run.

The exact audit schema belongs in the implementation Specifications.

### 19.3 Historical Integrity

Audit events should be append-only from the application perspective.

A later correction must create a new event rather than silently modifying the historical record.

Audit History must remain available after:

* reprocessing;
* representation replacement;
* Version superseding;
* publication changes;
* rollback;
* reconciliation.

### 19.4 Access and Security

Audit access must be limited to authorized users.

Audit records must not expose:

* credentials;
* secrets;
* raw stack traces;
* unnecessary sensitive document content;
* unrestricted infrastructure details.

### 19.5 Audit Boundary

The MVP requires lifecycle and administrative auditability.

It does not initially require:

* full event sourcing;
* cryptographically immutable storage;
* external audit certification;
* legal-hold workflows;
* advanced regulatory report generation.

Stronger controls may be introduced when required by the project’s compliance context.

### 19.6 Core Audit History Rules

1. Material lifecycle and administrative changes must be auditable.
2. Each event should identify the affected entity, actor, time, and state change.
3. Historical events must not be silently overwritten.
4. Audit History remains separate from operational logs.
5. Audit information must preserve security and data-minimization requirements.
6. Detailed event schemas, retention, and storage mechanics belong in the implementation Specifications.

The resulting boundary is:

```text id="ah-summary"
Material State Change
→ Actor and Timestamp
→ Historical Integrity
→ Controlled Audit Visibility
```


## 20. Operational Metrics and Infrastructure Monitoring Boundary

Data Monitoring should expose only the operational metrics required to understand the document and retrieval lifecycle.

It is not a replacement for AWS infrastructure monitoring.

The boundary is:

```text id="omi-core"
Application Lifecycle Metrics
≠ Infrastructure Metrics
```

### 20.1 Application-Level Metrics

Indicative application metrics include:

* Documents and Document Versions processed;
* Processing Runs by status;
* failures and warnings by stage;
* processing duration;
* generated and indexed Chunk counts;
* technically ready representations;
* published representations;
* unresolved inconsistencies;
* retry and reprocessing outcomes.

Metrics should support operational visibility without becoming the authoritative lifecycle record.

### 20.2 Infrastructure Monitoring

AWS and OpenSearch operational tooling remain responsible for:

* ECS service and task health;
* CPU and memory usage;
* container restarts;
* network and load-balancer health;
* S3 service errors;
* OpenSearch cluster, node, and shard health;
* CloudFormation deployment state;
* infrastructure alarms and logs.

CloudWatch is the primary location for detailed infrastructure diagnostics.

### 20.3 Application Context for Infrastructure Failures

Data Monitoring may expose infrastructure-related failure categories when they affect a lifecycle operation.

For example:

```text id="omi-example"
Processing Run: FAILED
Failed Stage: INDEXING
Failure Category: OPENSEARCH_UNAVAILABLE
```

The monitoring view should explain the application impact without reproducing the complete infrastructure diagnostic data.

### 20.4 Metrics and Lifecycle State

Aggregated metrics must not replace authoritative entity state.

For example:

```text id="omi-state"
Failed Processing Runs: 4
```

does not identify:

* which runs failed;
* which Documents were affected;
* whether previous published representations remain available;
* whether recovery is possible.

Users must be able to navigate from an operational metric to the relevant lifecycle records where appropriate.

### 20.5 Alerts and Notifications

The MVP may support basic indicators for conditions such as:

* repeated processing failures;
* stalled runs;
* unavailable published index;
* unresolved blocking inconsistencies;
* no valid published representation.

Complex alert routing, paging, escalation schedules, and on-call workflows remain outside the initial scope.

### 20.6 Core Operational Monitoring Rules

1. Data Monitoring exposes application-level lifecycle metrics.
2. AWS and OpenSearch tooling own detailed infrastructure monitoring.
3. Infrastructure failures may be summarized through their application impact.
4. Aggregated metrics must not replace authoritative lifecycle records.
5. Blocking operational conditions should be visible.
6. Detailed dashboards, alarms, thresholds, and retention rules belong in the implementation Specifications.

The resulting boundary is:

```text id="omi-summary"
Lifecycle Metrics
→ Application Impact Visibility
→ Infrastructure Diagnostic Handoff
→ Clear Monitoring Ownership
```


## 21. Configuration, Security, and Access

Data Monitoring must expose enough configuration context to support traceability while protecting sensitive operational information.

The boundary is:

```text id="csa-core"
Configuration Traceability
+
Authorized Access
+
Sensitive-Data Protection
```

### 21.1 Configuration Visibility

Each Processing Run and Indexed Representation should remain linked to the effective configuration used to produce it.

Monitoring should expose enough information to identify:

* configuration version;
* parser version;
* chunking configuration;
* embedding model and dimensions;
* target index configuration;
* verification configuration.

Secrets and sensitive runtime values must not be displayed.

### 21.2 Authentication and Authorization

Only authenticated and authorized users may access Data Monitoring.

Access should distinguish, where required:

* read-only monitoring;
* technical recovery actions;
* governance actions;
* publication and rollback actions;
* access to Source Artifacts;
* audit-history access.

The MVP may use a simple role model, provided that sensitive and lifecycle-changing actions remain controlled.

### 21.3 Sensitive Information

Normal monitoring views must not expose:

* credentials;
* API keys;
* database connection strings;
* S3 or OpenSearch secrets;
* raw stack traces;
* unrestricted infrastructure details;
* unnecessary sensitive document content.

Operational errors should use safe summaries, with detailed diagnostics available only through authorized tooling.

### 21.4 Source Artifact Access

Access to original Source Artifacts must be restricted according to authorization and data-sensitivity requirements.

Controlled viewing or download may be supported, but direct unrestricted S3 access is not required.

Material access actions should be auditable where required.

### 21.5 Administrative Action Security

Actions such as:

* retry;
* reprocessing;
* reindexing;
* governance-status change;
* publication;
* disablement;
* rollback;
* reconciliation;

must require appropriate authorization and lifecycle validation.

The system must not rely only on UI visibility to enforce permission rules.

### 21.6 Configuration and Access Auditability

Material configuration references and privileged actions should remain traceable through:

* actor or system identity;
* timestamp;
* affected entity;
* configuration version;
* resulting lifecycle change.

### 21.7 Core Configuration, Security, and Access Rules

1. Processing outcomes remain traceable to the effective configuration used.
2. Sensitive configuration values and secrets must not appear in monitoring views.
3. Authentication and authorization protect monitoring data and administrative actions.
4. Read access and lifecycle-changing permissions may differ.
5. Source Artifact access must be controlled.
6. Permission enforcement must exist beyond the UI layer.
7. Privileged actions and material configuration changes must be auditable.
8. Exact identity provider, role definitions, secret management, and authorization implementation belong in the implementation Specifications.

The resulting boundary is:

```text id="csa-summary"
Reproducible Configuration
→ Controlled Visibility
→ Authorized Lifecycle Actions
→ Secure and Auditable Access
```


## 22. Open Decisions and Success Criteria

This section records the decisions that must be resolved during implementation and the conditions that define a successful Data Monitoring MVP.

### 22.1 Open Decisions

The following decisions remain open:

1. authoritative persistence model for lifecycle and audit records;
2. exact Processing, Readiness, Governance, and Publication state values;
3. permitted state transitions and actor permissions;
4. whether retry continues an existing Processing Run or always creates a related execution record;
5. reconciliation frequency and which checks may repair automatically;
6. whether one or multiple representations may be published concurrently;
7. initial Source Artifact viewing or download policy;
8. required audit-event retention;
9. minimum application-level OpenSearch health information;
10. initial authentication and role model;
11. which alerts or issue indicators belong in the MVP;
12. exact monitoring refresh behaviour.

These decisions should be resolved through implementation deliverables, Technical Specifications, or ADRs when they materially affect architecture or lifecycle guarantees.

### 22.2 MVP Success Criteria

Data Monitoring is successful when an authorized user can:

* list registered Documents and Document Versions;
* inspect Source Artifacts and Processing Runs;
* identify current, completed, failed, and stalled processing;
* understand failures and warnings without inspecting raw infrastructure logs;
* trace every Indexed Representation to its source, configuration, and OpenSearch index;
* distinguish Technical Readiness, Governance Status, Publication Status, and Index Health;
* identify which representation is currently available to Data Query;
* initiate permitted retry, reprocessing, reindexing, publication, disablement, rollback, or reconciliation actions;
* detect important inconsistent states;
* inspect material lifecycle and administrative history.

### 22.3 Safety and Integrity Criteria

The MVP must also ensure that:

* a failed new run does not silently remove a previous valid published representation;
* an unverified or governance-ineligible representation cannot be published;
* lifecycle history is not overwritten by recovery or replacement actions;
* missing or conflicting relationships are exposed as inconsistencies;
* secrets and sensitive operational details are not exposed;
* privileged actions are authorized and auditable;
* Data Query consumes only explicitly eligible published representations.

### 22.4 Operational Criteria

The system should provide enough information to operate the lifecycle without requiring routine direct inspection of:

* application database tables;
* S3 buckets;
* OpenSearch records;
* ECS tasks;
* CloudWatch logs.

These systems remain available for detailed diagnosis but are not required for normal lifecycle monitoring.

### 22.5 Final Success Boundary

The Data Monitoring MVP is complete when it provides:

```text id="odsc-summary"
Clear Lifecycle Visibility
→ Reliable Source-to-Index Traceability
→ Separate Readiness and Governance Control
→ Safe Administrative Actions
→ Inconsistency Detection
→ Auditable Retrieval Publication
```

The MVP does not require a generic observability platform, full infrastructure administration, or enterprise document-management capabilities.










