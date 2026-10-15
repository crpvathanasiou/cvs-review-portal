# 01 — Data Ingest Reference

> **LEGACY DOCUMENT.** Data-ingest / OpenSearch content from the inherited compliance template. It does **not** describe the CVS Review Portal. Reading order: [`../../README.md`](../../README.md). Current specification: [`08_portal_specification.md`](08_portal_specification.md).

## 1. Purpose and Document Authority

This document defines the functional and semi-technical reference for the **Data Ingest** area of CVS Review Portal.

Data Ingest is responsible for the controlled transformation of a supported source document into a verified, traceable, and potentially retrievable representation in OpenSearch.

This reference describes:

* the responsibilities and boundaries of Data Ingest;
* the supported ingestion workflows;
* the document-processing lifecycle;
* the information and artifacts created during processing;
* the required failure, retry, traceability, and verification behaviour;
* the configuration areas that influence processing;
* the decisions that must be resolved before detailed implementation deliverables are defined.

This document is not:

* a low-level Python implementation specification;
* a final API contract;
* a final database schema;
* a final OpenSearch mapping;
* a CloudFormation implementation plan;
* an intermediate-deliverable plan;
* a Definition of Done;
* a generic ingestion framework for arbitrary domains.

### 1.1 Document hierarchy

The project documentation hierarchy is:

```text
00_project_reference.md
→ Canonical project-wide architectural source of truth

01_data_ingest_reference.md
→ Detailed functional reference for Data Ingest

00_project_reference_compact.md
→ Derived compact implementation context
```

If this document conflicts with the canonical project reference regarding project scope, architecture, system boundaries, or project-wide invariants, the canonical project reference prevails.

This document may provide additional Data Ingest detail where the canonical reference intentionally remains high-level.

A change in this document must also update the canonical project reference when that change affects:

* the project MVP boundary;
* shared domain entities;
* cross-functional responsibilities;
* project-wide lifecycles;
* security or governance invariants;
* AWS architecture direction;
* project-level success criteria.

The compact project reference is a working context document. It is not an architectural source of truth.

---

## 2. Data Ingest Objective

The objective of Data Ingest is to create a controlled and reproducible path from an uploaded compliance source document to a verified searchable representation.

The required high-level transformation is:

```text
Source Document
    ↓
Validated Source Artifact
    ↓
Registered Document and Document Version
    ↓
Parsed and Normalized Representation
    ↓
Traceable Chunks
    ↓
Embedding Vectors
    ↓
Indexed OpenSearch Representation
    ↓
Verified Processing Outcome
```

Data Ingest must ensure that processing is not treated as a simple:

```text
File → Text → Embedding → Vector Database
```

pipeline.

Instead, every processed representation must remain connected to:

* the logical Document;
* the specific Document Version;
* the original Source Artifact;
* the Processing Run;
* the effective processing configuration;
* the generated Chunks;
* the target OpenSearch index;
* the verification outcome.

The primary outcome of Data Ingest is not merely that records exist in OpenSearch.

The primary outcome is:

> A supported compliance document has been safely stored, identified, processed, indexed, verified, and made traceable through the complete processing lifecycle.

Data Ingest does not independently determine whether content is legally authoritative, applicable, approved, or active for normal user retrieval.

Technical processing readiness and compliance-governance approval remain separate concerns.

---

## 3. Scope

The Data Ingest MVP covers the controlled ingestion of the following source formats:

* TXT;
* Markdown;
* DOCX.

The functional scope includes:

1. receiving a supported source file;
2. receiving or generating the required upload metadata;
3. validating the file and request;
4. calculating a content checksum or equivalent identity signal;
5. detecting relevant duplicate conditions;
6. storing the original Source Artifact in AWS S3;
7. registering or resolving the logical Document;
8. creating or resolving the Document Version;
9. creating a Processing Run;
10. parsing the source document into a common internal representation;
11. normalizing the parsed representation;
12. handling required document and section metadata;
13. dividing the normalized document into traceable Chunks;
14. generating embedding vectors for the Chunks;
15. writing searchable text, vectors, metadata, and provenance fields to OpenSearch;
16. detecting partial and failed writes;
17. verifying the indexed representation;
18. recording the processing outcome;
19. exposing sufficient status and evidence for Data Monitoring;
20. making successfully verified content eligible for controlled retrieval publication.

The Data Ingest area owns the processing workflow up to the point where the indexed representation has been technically verified.

The actual inclusion of a Document Version in the normal retrieval path also depends on its governance status.

### 3.1 Initial processing model

The initial processing model is a deterministic pipeline.

Indicative stages are:

```text
VALIDATION
STORAGE
PARSING
NORMALIZATION
METADATA_HANDLING
CHUNKING
EMBEDDING
INDEXING
VERIFICATION
```

The stages represent explicit processing responsibilities and observable lifecycle boundaries.

They do not imply that every stage must be:

* a separate microservice;
* a separate ECS service;
* a separate queue;
* a separate Python package;
* or a separately persisted database entity.

The initial implementation may use a modular monolith and may represent some stages within one Processing Run record, provided that failures and processing progress remain sufficiently traceable.

### 3.2 Supported user interaction

The initial Data Ingest experience may provide:

* a web upload page;
* a FastAPI upload endpoint;
* or both.

The UI technology is not part of the Data Ingest architectural commitment.

The UI must communicate through backend API contracts and must not directly access:

* S3;
* OpenSearch;
* the operational state store;
* internal processing-worker interfaces.

---

## 4. Non-Goals and Functional Boundaries

The Data Ingest MVP does not include:

* PDF ingestion;
* scanned-document ingestion;
* OCR;
* HTML ingestion;
* spreadsheets;
* images, audio, or video;
* arbitrary file-format plugins;
* web crawling;
* automatic downloading of regulatory sources;
* automatic monitoring of external regulatory websites;
* automatic amendment detection;
* automatic superseding-version detection;
* automatic determination of source authority;
* automatic legal classification;
* autonomous approval of document governance status;
* model fine-tuning;
* generic support for arbitrary vector databases;
* generic support for arbitrary embedding providers;
* workflow definitions loaded dynamically from configuration;
* multi-agent processing;
* LangGraph orchestration without a concrete requirement;
* a complete document-management system;
* document editing or collaborative authoring;
* approval signatures;
* retention and legal-hold workflows;
* enterprise content-management integration.

The following responsibilities belong primarily to other functional areas:

### Data Monitoring

Data Monitoring owns user-facing visibility into:

* Documents;
* Document Versions;
* Processing Runs;
* failed stages;
* produced artifacts;
* Indexing Runs;
* registered indexes;
* active, superseded, or disabled states;
* reprocessing and reindexing status.

Data Ingest produces the state and events required for this visibility, but it does not own the complete monitoring user experience.

### Data Query and Evaluation

Data Query and Evaluation owns:

* query submission;
* query validation;
* retrieval execution;
* metadata filters;
* ranking and fusion;
* retrieval-result presentation;
* provenance display for query results;
* golden-dataset execution;
* retrieval metrics;
* baseline comparison.

Data Ingest produces the searchable representation required by Query and Evaluation, but it does not own query-time ranking behaviour.

### AWS infrastructure monitoring

Infrastructure monitoring remains the responsibility of AWS operational services such as CloudWatch and the relevant AWS service consoles.

Data Ingest may emit:

* structured logs;
* metrics;
* correlation identifiers;
* run and stage identifiers;
* failure categories.

It does not replace visibility into:

* ECS task health;
* CPU and memory;
* OpenSearch domain health;
* S3 service health;
* networking;
* CloudFormation stack status.

---

## 5. Actors and User Experience

### 5.1 Primary actor

The primary Data Ingest actor in the MVP is:

```text
AI / Search Engineer acting as Technical Operator
```

The Technical Operator may:

* select a supported document;
* provide required document metadata;
* submit an upload;
* view validation results;
* view duplicate warnings;
* initiate processing;
* identify the created Document and Document Version;
* identify the Processing Run;
* monitor the initial processing outcome;
* inspect failure information;
* retry a failed run where permitted;
* initiate a new Processing Run using an updated configuration;
* identify the target OpenSearch index.

The ability to upload or technically process a document does not establish that the user is a domain authority.

The Technical Operator must not be assumed to have authority to declare that a document is:

* legally authoritative;
* applicable to a specific organization;
* officially approved;
* the active regulatory version;
* sufficient evidence of compliance.

### 5.2 Secondary and future actors

Future or partially represented actors may include:

#### Compliance Administrator or Domain Reviewer

May review:

* document identity;
* source authority;
* jurisdiction;
* publication and effective dates;
* version labels;
* governance status;
* whether a Document Version should become active for normal retrieval.

#### System Administrator

May manage:

* processing infrastructure;
* indexes;
* worker operation;
* reprocessing;
* administrative recovery;
* reconciliation and cleanup.

#### Auditor or Reviewer

May inspect:

* source provenance;
* upload and processing history;
* configuration history;
* governance events;
* processing outcomes.

These actors inform the architecture but do not require separate RBAC roles in the first MVP.

### 5.3 Data Ingest page

The initial Data Ingest page should prioritize functional clarity rather than final visual design.

The page should eventually make it possible to:

* select or drag and drop a supported file;
* view accepted file types and size constraints;
* provide required metadata;
* submit the upload;
* receive a clear accepted or rejected outcome;
* view duplicate-detection information;
* view the generated identifiers;
* view the initial Processing Run status;
* navigate to the corresponding Data Monitoring record.

The page must distinguish:

```text
Upload request accepted
from
Source artifact successfully stored
from
Processing started
from
Processing completed
from
Content indexed
from
Content verified
from
Content active for retrieval
```

These states must not be presented as interchangeable versions of “upload successful.”

---

## 6. Core Data Ingest Use Cases

### 6.1 DI-UC-01 — Upload a supported document

**Primary Actor:** Technical Operator

The user selects a TXT, Markdown, or DOCX file and supplies the required metadata.

The system validates the request and either:

* accepts it for source storage and subsequent processing;
* or rejects it with a clear reason.

**Expected outcome:** A valid upload request proceeds into the controlled ingestion lifecycle. An invalid request does not enter downstream processing.

---

### 6.2 DI-UC-02 — Reject an unsupported or invalid document

**Primary Actor:** Technical Operator

The uploaded file is unsupported, empty, unreadable, too large, incorrectly declared, or missing required metadata.

The system rejects the upload before processing.

The rejection response identifies the relevant validation category without exposing sensitive internal implementation details.

**Expected outcome:** No invalid source is treated as successfully ingested, and no downstream parsing, chunking, embedding, or indexing is initiated.

---

### 6.3 DI-UC-03 — Store the canonical Source Artifact

**Primary Actor:** System

After validation, the system stores the original file in the approved S3 location.

The stored artifact is associated with:

* stable identifiers;
* original filename;
* detected or declared media type;
* file size;
* checksum;
* upload timestamp;
* storage reference.

**Expected outcome:** The original file is durably stored before downstream processing is considered valid.

---

### 6.4 DI-UC-04 — Resolve Document identity

**Primary Actor:** Technical Operator and System

The system determines whether the upload represents:

* an existing logical Document;
* or a new logical Document.

The resolution may use user-selected identity, approved metadata, existing registry records, and duplicate-detection signals.

Filename equality alone must not define Document identity.

**Expected outcome:** The Source Artifact is associated with one explicit logical Document.

---

### 6.5 DI-UC-05 — Resolve Document Version

**Primary Actor:** Technical Operator and System

The system determines whether the uploaded source represents:

* an existing Document Version;
* a new version or edition of an existing Document;
* or an ambiguous version requiring explicit user resolution.

Reprocessing an existing source using a different technical configuration does not create a new Document Version.

**Expected outcome:** Source version identity remains independent from processing configuration and indexing representation.

---

### 6.6 DI-UC-06 — Detect duplicate content or request

**Primary Actor:** Technical Operator and System

The system identifies relevant duplicate conditions, which may include:

* the exact same file already stored;
* the same checksum associated with the same Document Version;
* the same upload request being retried;
* an already successful Processing Run being resubmitted;
* chunks from a previous attempt already existing in the target representation.

The system applies a controlled policy such as:

* reject;
* reuse;
* link to the existing record;
* require operator confirmation;
* create a new Processing Run without creating a new source version.

**Expected outcome:** Retries and repeated uploads do not create uncontrolled duplicate source records or indexed chunks.

---

### 6.7 DI-UC-07 — Process a Document Version

**Primary Actor:** Technical Operator and System

The system creates a Processing Run and executes the approved pipeline:

```text
Parsing
→ Normalization
→ Metadata Handling
→ Chunking
→ Embedding
→ Indexing
→ Verification
```

Each stage receives an explicit input and produces either:

* a valid output;
* or a controlled failure.

**Expected outcome:** The Processing Run produces a verified indexed representation or terminates with a traceable failure state.

---

### 6.8 DI-UC-08 — Handle a failed processing stage

**Primary Actor:** Technical Operator and System

A stage fails due to invalid source content, parser failure, invalid configuration, model failure, OpenSearch failure, partial writes, or another controlled error.

The system records:

* the failed stage;
* failure category;
* safe failure summary;
* attempt information;
* relevant identifiers;
* whether retry is permitted.

**Expected outcome:** The run is not marked as successful, incomplete content is not presented as ready, and the failure can be diagnosed through Data Monitoring.

---

### 6.9 DI-UC-09 — Retry a failed Processing Run

**Primary Actor:** Technical Operator

The user retries a recoverable failed run.

The system preserves:

* the original Source Artifact;
* the Document;
* the Document Version;
* the previous failed-run history.

The retry may:

* create a new attempt within the same Processing Run;
* or create a new Processing Run linked to the previous run.

The exact persistence model remains a technical decision.

**Expected outcome:** The retry is controlled, observable, and idempotent, and it does not create uncontrolled duplicate indexed content.

---

### 6.10 DI-UC-10 — Reprocess with a changed configuration

**Primary Actor:** Technical Operator

The user starts a new Processing Run for an existing Document Version using a changed:

* parser version;
* normalization configuration;
* metadata logic;
* chunking configuration;
* embedding configuration;
* target index.

The source Document Version remains unchanged.

**Expected outcome:** A new derived representation is produced and remains explicitly associated with the configuration that created it.

---

### 6.11 DI-UC-11 — Verify indexed content

**Primary Actor:** System

After indexing, the system verifies the target representation.

Verification includes, as applicable:

* target index existence and readiness;
* mapping compatibility;
* embedding-dimension compatibility;
* expected and successful chunk counts;
* absence or controlled recovery of failed writes;
* presence of required provenance and filter fields;
* basic retrievability of indexed records.

**Expected outcome:** The indexed representation is not considered successfully completed until verification passes.

---

### 6.12 DI-UC-12 — Hand off verified content for retrieval publication

**Primary Actor:** System

After successful processing and verification, Data Ingest marks the representation as technically ready and exposes the required representation, governance, and index references to the publication controls owned by Data Monitoring or an authorized governance function.

**Expected outcome:** The verified representation is available for a separate controlled publication decision. Data Ingest does not independently approve or activate the Document Version for normal retrieval.

---

### 6.13 DI-UC-13 — Trace an indexed Chunk to its source

**Primary Actor:** Any Authorized User

The system allows an indexed Chunk to be traced through:

```text
Chunk
→ Processing Run
→ Document Version
→ Document
→ Source Artifact
→ Processing Configuration
→ Target Index
```

**Expected outcome:** No indexed retrieval unit exists without sufficient provenance to identify its source and processing history.

---

### 6.14 Data Ingest use-case boundary

The Data Ingest use cases establish:

```text
Controlled Source Acceptance
→ Stable Source and Version Identity
→ Deterministic Processing
→ Verified Search Representation
→ Traceable Handoff to Monitoring and Query
```

They do not establish:

* legal authority;
* legal applicability;
* regulatory interpretation;
* compliance approval;
* retrieval relevance;
* final answer correctness.


## 7. End-to-End Ingestion Lifecycle

The Data Ingest lifecycle defines how a supported source document is accepted, processed, indexed, verified, and made eligible for retrieval.

The lifecycle must preserve traceability between:

```text
Document
→ Document Version
→ Source Artifact
→ Processing Run
→ Chunks
→ OpenSearch Index
```

A document is not considered successfully ingested merely because the file was uploaded or because some records were written to OpenSearch.

Successful ingestion requires completion of the mandatory processing stages and verification of the indexed representation.

---

### 7.1 Main Lifecycle

The expected end-to-end flow is:

```text
Upload
→ Validate
→ Store Source Artifact in S3
→ Resolve Document and Document Version
→ Create Processing Run
→ Parse
→ Normalize
→ Handle Metadata
→ Chunk
→ Generate Embeddings
→ Index in OpenSearch
→ Verify
→ Mark Technically Ready
```

This is a logical lifecycle.

The stages do not need to be implemented as separate microservices, ECS services, queues, or database tables.

The initial implementation may use a modular monolith, provided that:

* the current processing stage is observable;
* failures can be attributed to the correct stage;
* retries do not create uncontrolled duplicates;
* partial processing is not represented as successful completion;
* the final indexed content remains traceable to its source and configuration.

---

### 7.2 Upload and Validation

The lifecycle begins when a user submits a supported file together with the required metadata.

Initial supported formats are:

```text
TXT
Markdown
DOCX
```

The request is validated before downstream processing begins.

Validation includes, at a minimum:

* supported file type;
* file-size limits;
* non-empty and readable content;
* safe filename handling;
* required metadata;
* availability of the required processing configuration.

A rejected file must not enter parsing, embedding, or indexing.

Acceptance of the upload request means only that the source may proceed to storage and processing. It does not mean that ingestion has completed successfully.

---

### 7.3 Source Storage

After validation, the original file is stored in AWS S3 as the canonical Source Artifact.

The Source Artifact must remain associated with:

* a stable identifier;
* original filename;
* file type;
* file size;
* content checksum;
* upload timestamp;
* S3 object reference.

OpenSearch is the retrieval layer and must not become the only storage location for the original source document.

If source storage fails, downstream processing must not continue.

---

### 7.4 Document, Version, and Processing Identity

The lifecycle distinguishes three core concepts:

```text
Document
≠ Document Version
≠ Processing Run
```

A **Document** represents the logical compliance source.

A **Document Version** represents a specific edition or source version of that Document.

A **Processing Run** represents one technical execution of the ingestion pipeline for one Document Version.

For example:

```text
Existing Document Version
+ different chunking configuration
= new Processing Run
```

It does not create a new Document Version.

Similarly, changing:

* the parser;
* the embedding model;
* the vector dimensions;
* the target index;
* the chunk size;

creates a new technical representation, not a new source version.

Ambiguous document or version identity must not be resolved solely from the filename.

---

### 7.5 Processing Configuration

Before processing begins, the effective configuration for the Processing Run is resolved and preserved.

It may include:

* parser version;
* normalization settings;
* metadata-handling settings;
* chunking strategy;
* chunk size and overlap;
* embedding model;
* vector dimensions;
* target OpenSearch index;
* verification settings.

Historical Processing Runs must remain associated with the configuration that actually produced them.

A later change to the project configuration must not alter the recorded meaning of an earlier run.

---

### 7.6 Processing Run

A Processing Run executes the transformation pipeline for one Document Version.

The initial high-level statuses may be:

```text
PENDING
RUNNING
SUCCEEDED
FAILED
```

For monitoring purposes, the run may also expose a `current_stage`, such as:

```text
PARSING
NORMALIZATION
METADATA_HANDLING
CHUNKING
EMBEDDING
INDEXING
VERIFICATION
```

The overall run status and the current stage must remain separate concepts.

For example:

```text
status: RUNNING
current_stage: EMBEDDING
```

The initial reference does not require a separate persisted status model for every internal operation.

---

### 7.7 Document Transformation

The main transformation path is:

```text
Source Artifact
→ Parsed Representation
→ Normalized Representation
→ Metadata-Enriched Representation
→ Chunks
→ Embedded Chunks
```

Each stage must produce a controlled output that can be consumed by the next stage.

#### Parsing

Transforms the source format into a common internal document representation.

#### Normalization

Cleans and standardizes the parsed content while preserving useful document structure and meaning.

#### Metadata Handling

Adds or validates metadata required for:

* provenance;
* compliance filtering;
* document inspection;
* governance;
* traceability.

#### Chunking

Creates ordered retrieval units while preserving their relationship to the source document and relevant structural context.

#### Embedding

Generates vector representations using the Processing Run configuration.

Detailed behaviour for these stages is defined in their corresponding chapters.

---

### 7.8 OpenSearch Indexing

The indexed representation must support:

* lexical retrieval;
* vector retrieval;
* metadata filtering;
* source provenance;
* result inspection.

Each indexed Chunk must remain traceable to:

```text
Document
→ Document Version
→ Processing Run
→ Source Artifact
```

Stable chunk or record identifiers must be used so that retries do not create uncontrolled duplicate OpenSearch records.

Successful submission of an OpenSearch indexing request is not by itself sufficient to mark ingestion as successful.

---

### 7.9 Verification

Verification confirms that the expected searchable representation was created correctly.

Initial verification should check, at minimum:

* expected chunks were produced;
* required chunks received embeddings;
* embedding dimensions match the index configuration;
* required records were written successfully;
* indexed records contain the required provenance fields;
* the indexed representation can be retrieved from the intended index.

The normal MVP expectation is complete processing.

Partial indexing must not silently pass as successful ingestion.

If verification fails:

* the Processing Run becomes `FAILED`;
* the representation is not considered technically ready;
* the failure remains visible through Data Monitoring;
* controlled retry or reprocessing may be initiated.

---

### 7.10 Technical Readiness and Retrieval Eligibility

A successfully verified representation may be marked as technically ready.

Technical readiness means that:

* the source is stored;
* the document and version are registered;
* processing completed;
* indexing completed;
* verification passed;
* provenance and configuration traceability are available.

However:

```text
Technically Ready
≠ Automatically Active for Normal Retrieval
```

Normal retrieval may also depend on the Document Version’s governance status, such as:

* active;
* superseded;
* disabled;
* pending review.

Data Ingest produces the verified representation.

Data Monitoring and governance controls determine whether that representation is active for normal query use.

---

### 7.11 Failure and Retry Principles

If a mandatory stage fails:

* dependent stages stop;
* the Processing Run is not marked successful;
* the failed stage and a safe error summary are recorded;
* partial indexed content is not treated as complete;
* the new representation is not activated for retrieval.

Retries must not create uncontrolled duplicate:

* Source Artifacts;
* Processing Runs;
* Chunks;
* OpenSearch records.

Reprocessing an existing Document Version creates a new Processing Run and preserves the history of previous runs.

The exact retry and idempotency implementation is defined later in the relevant chapter or deliverable specification.

---

### 7.12 Handoff to Data Monitoring

Data Ingest must expose enough state for Data Monitoring to show:

* Document;
* Document Version;
* Source Artifact;
* Processing Run;
* current stage;
* final outcome;
* target index;
* produced chunk counts;
* verification result;
* configuration reference;
* failure information.

Logs alone must not be the authoritative source for lifecycle state.

---

### 7.13 Handoff to Data Query

Data Query may use an indexed representation through the normal retrieval path only when:

```text
Processing Run succeeded
AND
Verification succeeded
AND
Representation is technically ready
AND
Governance status permits retrieval
```

The existence of records in OpenSearch must not automatically make them available to normal queries.

---

### 7.14 Core Lifecycle Rules

The following rules apply throughout the ingestion lifecycle:

1. Mandatory validation occurs before downstream processing.
2. The original source document is stored outside OpenSearch.
3. Every Processing Run belongs to one Document Version.
4. Every Processing Run preserves its effective configuration.
5. Reprocessing does not automatically create a new Document Version.
6. Every indexed Chunk preserves source provenance.
7. Partial processing is not treated as success.
8. Failed or unverified representations are not activated.
9. Retries must not create uncontrolled duplicates.
10. Technical readiness remains separate from governance activation.

The resulting lifecycle is:

```text
Validated Source
→ Controlled Processing
→ Verified Index Representation
→ Governed Retrieval Eligibility
```


## 8. Upload Input and Request Contract

The Upload Input and Request Contract defines the information required to submit a source document into the Data Ingest lifecycle.

The contract must be explicit enough to support:

* validation;
* source storage;
* Document and Document Version resolution;
* duplicate handling;
* traceability;
* processing configuration selection;
* clear user feedback.

This chapter defines the functional contract.

The final:

* FastAPI endpoint;
* request schema;
* Pydantic models;
* HTTP status codes;
* multipart implementation;
* authentication mechanism;

will be defined in the relevant implementation deliverable.

---

### 8.1 Upload Request Overview

An upload request contains two primary parts:

```text
Upload Request
├── Source File
└── Upload Metadata
```

It may also contain optional processing and request-control information:

```text
Upload Request
├── Source File
├── Document Metadata
├── Version Metadata
├── Existing Document Reference
├── Processing Configuration Reference
├── Idempotency Key
└── Request Context
```

The request contract must distinguish between:

* information supplied by the user;
* information detected from the file;
* information generated by the system;
* information resolved during subsequent processing.

The client must not be required to provide identifiers or technical metadata that the system can safely generate.

---

### 8.2 Source File Input

The upload request must contain exactly one source file in the initial MVP.

Supported formats are:

```text
TXT
Markdown
DOCX
```

The file input includes or allows the system to determine:

* original filename;
* file extension;
* declared media type;
* detected media type;
* file size;
* file content;
* content checksum.

The system-generated checksum is used as a technical identity and duplicate-detection signal.

The checksum alone does not determine:

* logical Document identity;
* legal source identity;
* Document Version identity;
* governance status.

A valid source file must not be accepted based only on its filename extension. The system should also validate the detected file type or structure where practical.

---

### 8.3 Required Upload Metadata

The initial upload request should require only metadata that is necessary to identify and process the source correctly.

Indicative required fields are:

```text
title
source_type
```

Depending on the Compliance MVP dataset, additional required fields may include:

```text
jurisdiction
source_authority
document_category
```

The exact required field set remains an open metadata-schema decision.

The initial contract should avoid requiring users to populate large numbers of uncertain compliance fields before upload.

Metadata should be divided into:

#### User-provided metadata

Information explicitly supplied by the uploader.

Examples:

* document title;
* source authority;
* jurisdiction;
* source URL;
* publication date;
* version label.

#### System-detected metadata

Information derived directly from the uploaded file or request.

Examples:

* filename;
* file type;
* file size;
* checksum;
* upload timestamp.

#### Processing-derived metadata

Information produced during parsing or metadata handling.

Examples:

* headings;
* section titles;
* detected language;
* document structure;
* chunk positions.

The origin of important metadata should remain traceable.

---

### 8.4 Document and Version References

The upload request may represent one of the following cases:

```text
New Document
→ New Document Version
```

```text
Existing Document
→ New Document Version
```

```text
Existing Document
→ Existing Document Version
→ New Processing Run
```

The request may therefore include an optional existing `document_id`.

It may also include version information such as:

* external version label;
* publication date;
* effective date;
* amendment identifier;
* source edition.

The user should not be required to provide an existing `document_version_id` unless they intentionally want to reprocess a previously registered version.

If no existing Document reference is supplied, the system may:

* create a new Document;
* suggest a possible existing match;
* or stop for explicit resolution when identity is ambiguous.

Filename equality must not automatically resolve Document or Version identity.

---

### 8.5 Processing Configuration Reference

The upload request may optionally specify which approved processing configuration should be used.

For example:

```text
processing_profile: compliance-default
```

or:

```text
processing_config_id: config-2026-001
```

The client should not submit arbitrary parser classes, embedding implementations, or executable configuration.

The request may select only from configurations already supported and approved by the application.

If no configuration is supplied, the system uses the current default Data Ingest configuration.

Before the Processing Run begins, the effective configuration is resolved and preserved as a historical snapshot.

---

### 8.6 Idempotency and Request Traceability

The upload contract should support an optional or required idempotency key.

Example logical field:

```text
idempotency_key
```

The idempotency key allows the client to repeat the same upload request safely when:

* the network connection fails;
* the response is lost;
* the client times out;
* the user accidentally submits twice.

The same idempotency key with the same request should return or reconnect to the existing operation.

The same idempotency key with materially different content should be rejected as a conflict.

The system should also generate:

* request identifier;
* correlation identifier;
* upload timestamp.

These identifiers allow the upload request to be traced through:

```text
Upload Request
→ Source Artifact
→ Document Version
→ Processing Run
```

The idempotency key is not a substitute for file checksum or Document identity.

---

### 8.7 Upload Acceptance Response

The upload response must describe what the system has actually completed.

It must not return a generic success message that implies the complete ingestion pipeline has finished.

An accepted upload response may include:

* request identifier;
* source-artifact identifier;
* Document identifier, when resolved;
* Document Version identifier, when resolved;
* Processing Run identifier, when created;
* current status;
* current or next stage;
* duplicate-handling outcome;
* monitoring reference.

Indicative response:

```text
request_status: ACCEPTED
processing_status: PENDING
source_storage_status: SUCCEEDED
```

The exact field names remain an implementation decision.

The response must clearly distinguish:

```text
Request accepted
≠ Processing succeeded
≠ Content indexed
≠ Content active for retrieval
```

If processing is asynchronous, the response should direct the user to the corresponding Data Monitoring record.

---

### 8.8 Duplicate and Existing-Content Response

When the system detects existing content, the response must explain the relevant outcome.

Possible outcomes include:

```text
NEW_SOURCE_ACCEPTED
EXISTING_REQUEST_RETURNED
EXISTING_SOURCE_REUSED
EXISTING_DOCUMENT_MATCH_FOUND
EXISTING_VERSION_REPROCESSING_STARTED
CONFLICT_REQUIRES_RESOLUTION
```

The exact enum values are not fixed by this reference.

The important requirement is that duplicate handling must not be invisible.

The user must be able to understand whether the system:

* created a new source;
* reused an existing source;
* created a new Document Version;
* started a new Processing Run;
* rejected a conflicting request;
* requires manual identity resolution.

---

### 8.9 Rejected Request Response

A rejected request must provide a safe and actionable reason.

Indicative validation categories include:

```text
UNSUPPORTED_FILE_TYPE
FILE_TOO_LARGE
EMPTY_FILE
UNREADABLE_FILE
INVALID_METADATA
MISSING_REQUIRED_FIELD
IDEMPOTENCY_CONFLICT
DOCUMENT_IDENTITY_CONFLICT
PROCESSING_CONFIGURATION_UNAVAILABLE
UNAUTHORIZED_REQUEST
```

The response should include:

* error category;
* user-readable summary;
* affected field where applicable;
* request or correlation identifier;
* whether the request may be corrected and resubmitted.

Internal stack traces, secrets, storage paths, or sensitive infrastructure information must not be returned to the user.

---

### 8.10 Synchronous and Asynchronous Boundary

The upload endpoint is responsible for accepting and registering the ingestion request.

It should not be assumed that the complete pipeline finishes within the upload HTTP request.

The expected boundary is:

```text
Upload Request
→ Validate
→ Store or Register Durable Intent
→ Return Accepted Response
→ Continue Processing
```

The exact point at which the API returns depends on the selected execution model.

An `ACCEPTED` response may be returned only after the Source Artifact has been durably stored and sufficient durable operational state has been recorded to recover or continue the ingestion operation after application or worker failure.

* safely stored the Source Artifact;
* or recorded sufficient durable intent to recover the upload operation.

Whether source storage and Processing Run creation occur synchronously or through a background workflow remains an open technical decision.

---

### 8.11 Request Security and Input Protection

The upload contract must support:

* authenticated or controlled access;
* file-size limits;
* supported-type allowlists;
* safe filename handling;
* metadata length limits;
* rejection of malformed requests;
* prevention of path traversal;
* prevention of direct client-controlled S3 object paths;
* protection against arbitrary processing configuration injection.

Original filenames may be preserved as metadata, but they should not directly determine internal storage keys.

The application must generate controlled S3 object paths and internal identifiers.

Uploaded document content must not be written indiscriminately to application logs.

---

### 8.12 Contract Boundaries

The Upload Input and Request Contract defines:

* what the client may submit;
* what the system must validate;
* what identities may be referenced;
* how duplicate and replay signals are supplied;
* what an acceptance response means;
* how the request becomes traceable.

It does not yet define:

* final endpoint paths;
* final HTTP methods;
* final Pydantic field names;
* final required compliance metadata;
* authentication and authorization implementation;
* file-size thresholds;
* synchronous versus asynchronous execution;
* exact duplicate-resolution policy.

These decisions will be resolved through the corresponding technical decision or implementation deliverable.

The core contract principle is:

> The upload request must provide enough information to accept, identify, trace, and process the source safely, without requiring the user to understand the internal ingestion implementation.


## 9. File Validation

File Validation determines whether an uploaded source file is safe, supported, and sufficiently well-formed to enter the Data Ingest pipeline.

Validation occurs before parsing, chunking, embedding, or indexing.

A file that fails a mandatory validation rule must not continue to downstream processing.

Validation success means:

> The file is acceptable for storage and processing under the current Data Ingest rules.

It does not guarantee that parsing, metadata extraction, or indexing will complete successfully.

---

### 9.1 Validation Layers

Validation should be performed through several logical layers:

```text
Upload Request Validation
→ Basic File Validation
→ File-Type and Structure Validation
→ Metadata Validation
→ Security Validation
→ Processing Compatibility Validation
```

The implementation may combine these checks, but the failure category should remain identifiable.

#### Upload Request Validation

Confirms that the request contains:

* exactly one source file;
* required request fields;
* valid metadata structure;
* valid identifiers or configuration references;
* an acceptable idempotency key where applicable.

#### Basic File Validation

Confirms that the file:

* is present;
* is not empty;
* does not exceed the configured size limit;
* has a valid filename representation;
* can be read by the application.

#### File-Type and Structure Validation

Confirms that the file is one of the supported formats and is structurally compatible with the expected parser.

#### Metadata Validation

Confirms that required user-provided metadata is present and correctly formatted.

#### Security Validation

Rejects unsafe filenames, malformed content, unsupported archive behaviour, or inputs that may bypass controlled storage and processing rules.

#### Processing Compatibility Validation

Confirms that the application has an approved parser and processing configuration for the detected file type.

---

### 9.2 Supported File Types

The initial supported file types are:

```text
TXT
Markdown
DOCX
```

The file must be validated using more than the filename extension where practical.

Validation may compare:

* declared media type;
* filename extension;
* detected file type;
* internal file structure.

A file named with a supported extension must still be rejected when its detected content is incompatible with that format.

Examples include:

```text
document.docx containing non-DOCX binary data
document.txt containing unsupported binary content
document.md that cannot be decoded as text
```

The final detection library and MIME-validation approach remain implementation decisions.

---

### 9.3 File Presence, Size, and Readability

The system must reject a file when:

* no file content was provided;
* the file contains zero bytes;
* the file exceeds the configured maximum size;
* the upload stream cannot be read;
* the file is truncated or structurally incomplete;
* the file cannot be processed safely within the supported limits.

File-size limits must be configuration-driven.

The limit may differ between:

* the application upload boundary;
* the reverse proxy or load balancer;
* FastAPI;
* S3 upload handling;
* the document parser.

These limits must be aligned so that the user receives a predictable rejection rather than an unexplained infrastructure failure.

A readable file is not necessarily a semantically useful document. Detection of low-quality or meaningless content may occur during parsing or normalization rather than initial file validation.

---

### 9.4 Filename Validation

The original filename may be preserved as metadata for user recognition and provenance.

It must not directly control:

* the S3 object path;
* local filesystem paths;
* parser selection without additional validation;
* internal identifiers;
* Document identity.

Filename handling must protect against:

* path traversal;
* absolute paths;
* control characters;
* unsupported encoding;
* excessively long filenames;
* misleading or multiple extensions;
* empty or unusable filenames.

The system should generate controlled internal storage keys independently of the original filename.

A sanitized display filename may be stored in addition to the original value when needed.

---

### 9.5 TXT and Markdown Validation

TXT and Markdown files must be decodable using the supported text-encoding policy.

Validation should identify cases such as:

* unsupported or invalid encoding;
* binary content presented as text;
* unreadable byte sequences;
* content consisting only of whitespace;
* content exceeding configured processing limits.

The system may attempt a small approved set of encodings, but it should not silently transform ambiguous content without recording the detected encoding.

Markdown validation does not require the document to follow a specific writing style.

Malformed Markdown should normally remain processable as text unless it creates a concrete parsing or security problem.

The initial MVP does not require full Markdown semantic validation.

---

### 9.6 DOCX Validation

A DOCX file must be confirmed as a structurally valid DOCX package before parsing begins.

Validation should detect cases such as:

* invalid ZIP-based package structure;
* missing required internal document parts;
* corrupted package content;
* encrypted or password-protected documents;
* unsupported embedded content;
* files that cannot be opened by the approved parser.

The initial MVP may reject password-protected or encrypted DOCX files.

The treatment of embedded objects, images, comments, tracked changes, headers, footers, and tables belongs primarily to the parsing strategy rather than basic file validation.

However, the validator should identify unsupported structures when they make reliable processing impossible.

---

### 9.7 Metadata Validation

The file is validated together with the required upload metadata.

Metadata validation may include:

* required fields are present;
* values use supported formats;
* text fields remain within configured length limits;
* identifiers reference existing permitted records;
* dates are syntactically valid;
* controlled vocabulary values are supported;
* URLs are structurally valid where supplied;
* processing profile references are approved.

Metadata validation should distinguish between:

```text
Invalid metadata
Missing metadata
Unverified metadata
```

A value may be structurally valid but not yet confirmed as legally accurate.

For example, a user-provided `effective_date` may pass input validation while still requiring later domain review.

File Validation checks whether metadata can enter the system. It does not automatically establish the truth or authority of the metadata.

---

### 9.8 Duplicate Signals During Validation

After the file passes the minimum checks required to read its content, the system should calculate a content checksum.

The checksum supports:

* exact-content duplicate detection;
* idempotent request handling;
* source traceability;
* integrity verification after storage.

Duplicate detection may identify that:

* the same source file already exists;
* the same request was previously accepted;
* the file belongs to an existing Document Version;
* the user is attempting to reprocess existing content.

Detection of a duplicate does not always require rejection.

The outcome may be:

```text
Reject
Reuse existing source
Return existing request
Create a new Processing Run
Require identity resolution
```

The detailed duplicate-resolution policy belongs to the Document Identity, Versioning, and Duplicate Handling chapter.

File Validation is responsible for producing reliable duplicate signals, not for resolving every business case.

---

### 9.9 Security Validation

The upload boundary must treat all files as untrusted input.

Validation must prevent or reduce risks including:

* path traversal;
* malformed multipart requests;
* oversized uploads;
* parser abuse;
* decompression or archive expansion abuse;
* arbitrary executable content;
* client-controlled storage paths;
* malicious filenames;
* uncontrolled metadata injection;
* secrets or credentials embedded in request fields.

The initial system supports documents as data, not executable files.

Uploaded content must never be executed.

File content should not be written to logs except through an explicitly approved and redacted diagnostic process.

Malware scanning may be introduced depending on deployment and compliance requirements. It is not automatically required for the first local development increment but should remain an explicit production-security decision.

---

### 9.10 Validation Outcome

The validator produces one of two primary outcomes:

```text
VALID
INVALID
```

A valid result should include information required by the next stages, such as:

* detected file type;
* file size;
* checksum;
* validated filename metadata;
* detected encoding where relevant;
* selected parser compatibility;
* validated upload metadata;
* validation timestamp.

An invalid result should include:

* validation category;
* safe error summary;
* affected field or rule where applicable;
* request or correlation identifier;
* whether the request can be corrected and resubmitted.

Indicative error categories include:

```text
FILE_MISSING
EMPTY_FILE
FILE_TOO_LARGE
UNSUPPORTED_FILE_TYPE
FILE_TYPE_MISMATCH
INVALID_ENCODING
CORRUPTED_FILE
ENCRYPTED_FILE
UNREADABLE_FILE
INVALID_FILENAME
MISSING_METADATA
INVALID_METADATA
CONFIGURATION_UNAVAILABLE
SECURITY_VALIDATION_FAILED
```

The exact enum and response schema will be defined during implementation.

---

### 9.11 Validation Failure Behaviour

When mandatory validation fails:

* the file does not proceed to parsing;
* no embeddings are generated;
* no OpenSearch records are created;
* the request is not represented as successfully ingested;
* the user receives a safe and actionable response;
* sufficient validation evidence is recorded for monitoring and audit.

The implementation should avoid creating incomplete Document or Document Version records for requests rejected before the identity-registration boundary.

Where temporary upload data has already been created, it must be removed or retained through an explicit controlled policy.

Validation failures caused by user input are normally not automatically retried.

Infrastructure-related failures during validation may be retryable, but they must remain distinguishable from invalid files.

---

### 9.12 Validation Configuration

The following validation rules should be configurable:

* supported extensions;
* supported media types;
* maximum file size;
* accepted text encodings;
* filename length;
* metadata field limits;
* required metadata fields;
* DOCX encrypted-file policy;
* parser compatibility mapping;
* optional malware-scanning requirement.

Configuration should expose approved values and limits.

It should not allow users to inject arbitrary validation code or parser implementations through the upload request.

Each Processing Run or upload record should remain traceable to the effective validation configuration or configuration version used.

---

### 9.13 Validation Boundaries

File Validation confirms that a file is safe and supported enough to enter processing.

It does not guarantee:

* accurate parsing;
* meaningful document content;
* correct compliance classification;
* correct legal metadata;
* successful chunking;
* successful embedding;
* successful indexing;
* retrieval relevance;
* governance approval.

Some failures can only be discovered during later stages.

For example:

```text
Valid DOCX structure
→ Parsing succeeds
→ Document contains no usable body text
→ Processing fails or requires review
```

The validator should not attempt to absorb all downstream quality checks.

Its responsibility is to reject clearly invalid or unsupported inputs early and pass a controlled, well-described input to the parsing stage.

---

### 9.14 Core Validation Rules

The following rules apply:

1. Validation occurs before downstream document transformation.
2. Extension alone is not sufficient evidence of file type.
3. File-size and input limits are configuration-driven.
4. Original filenames do not control internal paths or identifiers.
5. Uploaded content is treated as untrusted data.
6. Validation failures do not initiate parsing or indexing.
7. Duplicate signals are generated without assuming the final duplicate policy.
8. Structurally valid metadata is not automatically legally verified metadata.
9. Validation results remain traceable to the upload request and configuration.
10. Validation should remain focused on early input acceptance, not downstream retrieval quality.

The resulting validation boundary is:

```text
Untrusted Upload
→ Controlled Validation
→ Supported and Traceable Source Input
→ Source Storage and Processing
```



## 10. Source Artifact Storage

Source Artifact Storage defines how the original uploaded document is stored, identified, protected, and linked to the rest of the Data Ingest lifecycle.

AWS S3 is the canonical storage layer for original source files.

OpenSearch is the retrieval layer and must not be treated as the authoritative location of the original document.

The primary storage principle is:

```text id="sr101"
Original Source File
→ Stored Once as a Controlled Source Artifact
→ Referenced by Document Version and Processing Runs
```

---

### 10.1 Source Artifact Definition

A Source Artifact represents the original file accepted by the ingestion system.

Examples include:

* the uploaded TXT file;
* the uploaded Markdown file;
* the uploaded DOCX file.

The Source Artifact is distinct from:

* the logical Document;
* the Document Version;
* parsed text;
* normalized content;
* generated Chunks;
* embeddings;
* OpenSearch records.

A single Document Version should normally reference one canonical Source Artifact.

The same Source Artifact may be reused by multiple Processing Runs when the source content remains unchanged.

---

### 10.2 Storage Responsibility

Data Ingest is responsible for:

* generating a controlled Source Artifact identity;
* generating the internal S3 object reference;
* uploading the original file;
* verifying that the storage operation succeeded;
* recording the relationship between the artifact and its lifecycle entities;
* preventing client-controlled storage paths;
* preserving integrity and provenance metadata.

The client provides the file content and original filename.

The client must not directly determine:

* the S3 bucket;
* the final S3 object key;
* the internal artifact identifier;
* encryption settings;
* retention policy;
* storage class.

These remain application and infrastructure responsibilities.

---

### 10.3 Canonical Source Preservation

The stored Source Artifact should preserve the original accepted file content without applying document-processing transformations.

Operations such as:

* text normalization;
* heading extraction;
* removal of formatting;
* chunking;
* embedding generation;

must not modify the canonical source object.

Derived representations should be stored separately when they need to be retained.

This preserves the ability to:

* reprocess the source later;
* reproduce previous processing runs;
* investigate parsing problems;
* compare different processing configurations;
* verify source provenance.

---

### 10.4 Source Artifact Identity

Each Source Artifact must have a stable system-generated identifier.

The artifact record should be associated with:

* `source_artifact_id`;
* original filename;
* detected file type;
* declared media type where available;
* file size;
* content checksum;
* upload timestamp;
* S3 bucket reference;
* S3 object key;
* uploader or request reference;
* related Document Version.

The original filename is descriptive metadata.

It must not be used as the unique artifact identity because:

* different files may have the same filename;
* the same file may be uploaded with different filenames;
* filenames may change without changing content;
* filenames may contain unsafe characters.

---

### 10.5 S3 Object Keys

S3 object keys must be generated by the application using controlled internal identifiers.

An indicative logical structure may be:

```text id="sr102"
source-artifacts/
└── {document_id}/
    └── {document_version_id}/
        └── {source_artifact_id}/
            └── original-file
```

The exact key format remains an infrastructure and implementation decision.

The object key should:

* avoid direct dependence on the original filename;
* support traceability;
* avoid collisions;
* remain stable after storage;
* not expose unnecessary user or domain information;
* support lifecycle and cleanup operations.

The original filename may be preserved as object metadata or in the operational registry.

---

### 10.6 Storage Integrity

Before or during storage, the system calculates a content checksum.
When Document or Document Version identity has not yet been resolved, the Source Artifact may initially be registered against the Upload Request or another temporary ingestion reference. It must be linked to the resolved Document Version before a Processing Run begins. An unresolved artifact must remain incomplete and must not be treated as successfully ingested.

After the upload operation, the system must confirm that:

* the S3 write completed successfully;
* the expected object reference exists;
* the stored object corresponds to the accepted source;
* the artifact record contains the required integrity metadata.

The checksum may be used for:

* duplicate detection;
* corruption detection;
* source verification;
* reconciliation;
* audit traceability.

A successful API call without a usable stored object must not be treated as successful source storage.

---

### 10.7 Storage and Operational State Consistency

S3 storage and operational metadata updates are separate operations.

The system must handle cases such as:

```text id="sr103"
S3 upload succeeds
but
Operational record creation fails
```

or:

```text id="sr104"
Operational intent is created
but
S3 upload fails
```

The MVP does not require distributed transactions across S3 and the operational state store.

It does require that inconsistent states are:

* detectable;
* visible through monitoring;
* recoverable through retry, reconciliation, or cleanup;
* not represented as successful ingestion.

An artifact stored without a valid registry relationship should be treated as an orphaned or incomplete artifact until reconciled.

---

### 10.8 Source Artifact Reuse

If the same accepted source content already exists, the system may reuse the existing Source Artifact according to the duplicate policy.

Possible cases include:

```text id="sr105"
Same Source Artifact
→ Same Document Version
→ New Processing Run
```

or:

```text id="sr106"
Same Request Replay
→ Return Existing Source Artifact and Operation
```

Reusing a Source Artifact does not automatically mean reusing:

* the previous Processing Run;
* the previous chunks;
* the previous embeddings;
* the previous OpenSearch representation.

A new processing configuration may require a new Processing Run while preserving the same source object.

---

### 10.9 Derived Artifacts

The processing pipeline may produce derived artifacts such as:

* parsed document representation;
* normalized text;
* extracted metadata;
* serialized chunks;
* evaluation exports;
* processing reports.

These artifacts may also be stored in S3 when they are required for:

* reproducibility;
* troubleshooting;
* audit;
* experiment comparison;
* recovery.

An indicative separation is:

```text id="sr107"
source-artifacts/
→ Original accepted files

processed-artifacts/
→ Parsed or normalized representations

evaluation-artifacts/
→ Evaluation datasets and reports
```

The MVP does not require every intermediate representation to be stored permanently.

The retention of derived artifacts should be decided based on operational value, reproducibility, cost, and compliance requirements.

---

### 10.10 Security and Access

Source Artifacts must be private by default.

Access should be controlled through:

* AWS IAM roles;
* least-privilege permissions;
* application-mediated access;
* encryption in transit;
* encryption at rest;
* controlled bucket policies.

Application users should not receive unrestricted direct access to the S3 bucket.

When temporary direct access is required, such as through a presigned URL, it must be:

* time-limited;
* scoped to the required object and action;
* authorized by the application;
* auditable.

Sensitive bucket names, keys, credentials, or internal storage details must not be exposed unnecessarily through user-facing responses.

---

### 10.11 Retention and Deletion

Source Artifact retention must remain separate from:

* Document governance status;
* retrieval activation;
* OpenSearch deletion;
* Processing Run cleanup.

For example:

```text id="sr108"
Document Version disabled for retrieval
≠
Source Artifact automatically deleted
```

Similarly:

```text id="sr109"
OpenSearch representation replaced
≠
Original Source Artifact deleted
```

The initial MVP should avoid destructive automatic deletion.

Deletion or retention rules should later define:

* who may request deletion;
* whether historical versions are retained;
* whether audit requirements prevent deletion;
* how OpenSearch and derived artifacts are cleaned up;
* whether S3 versioning is enabled;
* whether soft deletion is required.

---

### 10.12 Versioning and Immutability

A stored canonical Source Artifact should normally be treated as immutable.

If the source document changes, the preferred lifecycle is:

```text id="sr110"
Existing Document
→ New Document Version
→ New Source Artifact
```

The existing S3 object should not be silently overwritten with changed content.

S3 object versioning may be used as an additional infrastructure safeguard, but it does not replace the application-level Document Version model.

Application version identity must remain understandable independently of S3 internal object versions.

---

### 10.13 Monitoring and Traceability

Data Monitoring must be able to show, where authorized:

* Source Artifact identifier;
* original filename;
* file type;
* file size;
* checksum;
* upload time;
* storage status;
* related Document;
* related Document Version;
* associated Processing Runs;
* storage or reconciliation failures.

The application should expose logical artifact information.

It does not need to expose raw internal S3 object keys to normal users unless operationally necessary.

Structured logs should include identifiers and outcomes, but should not include complete document content.

---

### 10.14 Failure Behaviour

If source storage fails:

* no downstream Processing Run should continue;
* the request must not be represented as successfully stored;
* the storage failure must be recorded;
* retry may be allowed for recoverable infrastructure errors.

If storage succeeds but registration fails:

* the artifact must remain detectable;
* downstream processing must not begin until the relationship is reconciled;
* the system may retry registration or mark the artifact for cleanup.

If checksum or integrity verification fails:

* the artifact must not be accepted as canonical;
* processing must stop;
* the failed object should be removed or isolated through a controlled policy.

---

### 10.15 Configuration Boundary

The following storage settings should be configurable through approved application or deployment configuration:

* AWS region;
* source-artifact bucket;
* derived-artifact bucket or prefix;
* object-key prefix;
* encryption configuration;
* maximum upload size;
* presigned URL expiration where used;
* S3 versioning policy;
* retention or lifecycle policy;
* checksum algorithm;
* allowed storage classes.

Users must not be able to supply arbitrary bucket names or object keys through the upload request.

Infrastructure-specific secrets and credentials must not be stored in project configuration files.

---

### 10.16 Core Storage Rules

The following rules apply:

1. S3 is the canonical storage layer for original source files.
2. OpenSearch is not the canonical source store.
3. The original accepted file is preserved without processing transformations.
4. Source Artifact identity is system-generated and independent of filename.
5. S3 object keys are application-controlled.
6. Each artifact remains traceable to its Document Version.
7. Processing may reuse an existing Source Artifact without creating a new Document Version.
8. A new source version creates a new Source Artifact rather than overwriting the previous one.
9. Storage and operational-state inconsistencies must be detectable and recoverable.
10. Retrieval or governance changes must not automatically delete the canonical source.

The resulting storage boundary is:

```text id="sr111"
Validated File
→ Controlled S3 Storage
→ Verified Source Artifact
→ Registered Document Version
→ Reproducible Processing
```


## 11. Document Identity, Versioning, and Duplicate Handling

This chapter defines how the system distinguishes between:

```text
Document
Document Version
Source Artifact
Processing Run
Upload Request
```

These concepts must remain separate because they represent different kinds of identity.

The system must avoid creating unnecessary duplicates while preserving valid historical versions and processing experiments.

---

### 11.1 Core Identity Model

The primary relationships are:

```text
Document
└── Document Version
    ├── Source Artifact
    └── Processing Runs
        ├── Processing Run 1
        ├── Processing Run 2
        └── Processing Run 3


Processing Run
├── document_version_id
├── source_artifact_id
├── processing_config_id
├── Chunks
└── Indexing Run
```

An **Upload Request** initiates or reconnects to this lifecycle but is not itself a Document.

#### Document

Represents the continuing logical source.

Examples:

* EU Artificial Intelligence Act;
* an internal AI governance policy;
* a regulatory technical guideline;
* an organizational compliance procedure.

#### Document Version

Represents a specific edition, revision, release, or effective state of that Document.

#### Source Artifact

Represents the exact accepted file associated with a Document Version.

#### Processing Run

Represents one technical execution of the ingestion pipeline for that Document Version.

These identities must not be collapsed into one record or identifier.

#### Indexing Run

Represents one controlled attempt to write the output of a Processing Run into one target OpenSearch index.

The MVP may persist Indexing Run information as part of the Processing Run rather than as a separate database entity, provided that the following remain separately traceable:

* target index;
* expected record count;
* successful record count;
* failed record count;
* verification status;
* start and completion timestamps;
* safe failure summary.

---

### 11.2 New Document

A new Document should be created when the uploaded source represents a logically distinct compliance source that is not already registered.

Document identity may consider:

* official title;
* issuing authority;
* jurisdiction;
* source type;
* official identifier;
* source URL;
* user-selected existing Document reference.

Filename equality or difference alone must not determine Document identity.

For example:

```text
eu-ai-act.docx
ai-act-final.docx
```

may represent the same logical Document.

Similarly, two files named:

```text
policy.docx
```

may represent entirely different Documents.

When identity cannot be determined reliably, the system should request explicit operator resolution rather than silently creating or merging records.

---

### 11.3 New Document Version

A new Document Version should be created when the source content represents a new edition or meaningful source revision of an existing Document.

Examples include:

* a newly published revision;
* an amended regulation;
* a new effective version;
* a corrected official release;
* an updated internal policy;
* a new authority-issued edition.

Version identity may use:

* official version label;
* publication date;
* effective date;
* amendment identifier;
* edition number;
* source checksum;
* user-provided version context.

A changed checksum is evidence that the file content differs, but it does not automatically prove that the content represents a valid new business version.

---

### 11.4 Existing Version Reprocessing

A new Processing Run should be created when the source version remains the same but the technical processing changes.

Examples include changes to:

* parser;
* normalization rules;
* metadata extraction;
* chunking strategy;
* chunk size or overlap;
* embedding model;
* vector dimensions;
* OpenSearch mapping;
* target index.

The rule is:

```text
Same source meaning and same Document Version
+ different technical processing
= New Processing Run
```

It must not create a new Document Version.

This distinction allows multiple retrieval experiments to be performed against the same source version without corrupting document history.

---

### 11.5 Exact Source Duplicate

An exact source duplicate exists when an uploaded file has the same content checksum as an existing Source Artifact.

Possible outcomes include:

* return the existing upload operation;
* reuse the existing Source Artifact;
* associate the artifact with an already known Document Version;
* create a new Processing Run;
* request operator confirmation;
* reject an invalid duplicate request.

The correct outcome depends on the request intent.

An exact checksum match does not automatically mean that the system should reject the upload.

For example, the user may intentionally want to reprocess the same source with a different embedding model.

---

### 11.6 Request Replay

A request replay occurs when the same upload operation is submitted again, commonly because:

* the client timed out;
* the response was lost;
* the user submitted twice;
* a network retry occurred.

The system should use an idempotency key or equivalent request identity to reconnect the repeated request to the existing operation.

Expected behaviour:

```text
Same idempotency key
+ same request content
→ Return existing result or operation
```

```text
Same idempotency key
+ different request content
→ Reject as conflict
```

A request replay must not create duplicate:

* Source Artifacts;
* Documents;
* Document Versions;
* Processing Runs.

---

### 11.7 Duplicate Detection Signals

Duplicate handling may use several signals together:

* request idempotency key;
* source checksum;
* file size;
* original filename;
* Document identifier;
* Document Version identifier;
* official source identifier;
* publication or effective date;
* source authority;
* source URL;
* previous Processing Runs.

No single weak signal should be treated as universally authoritative.

For example:

```text
Same filename
```

is a weak signal.

```text
Same checksum
+ same Document Version
```

is a strong source-duplicate signal.

```text
Same official identifier
+ later publication date
+ different checksum
```

may indicate a new Document Version.

---

### 11.8 Ambiguous Identity

Some uploads cannot be classified automatically with sufficient confidence.

Examples include:

* same title but different issuing authority;
* same checksum uploaded under conflicting metadata;
* changed content without a declared version;
* same official identifier but incompatible dates;
* possible duplicate Document records;
* source content that appears to combine multiple documents.

In these cases, the system should produce a clear resolution state such as:

```text
IDENTITY_REVIEW_REQUIRED
VERSION_REVIEW_REQUIRED
DUPLICATE_CONFLICT
```

The exact state names remain an implementation decision.

Ambiguous identity must not silently result in:

* merging unrelated Documents;
* overwriting an existing Document Version;
* activating an unverified version;
* creating uncontrolled duplicates.

---

### 11.9 Version and Artifact Immutability

A registered Document Version should normally be treated as historically stable.

If the source content changes materially, the preferred approach is:

```text
Existing Document
→ New Document Version
→ New Source Artifact
```

The previous Source Artifact should not be overwritten.

Corrections to descriptive metadata may be allowed without creating a new version when they do not change the source content or business meaning.

Examples may include correcting:

* a typographical error in a display title;
* an incorrectly entered source URL;
* a non-authoritative administrative label.

Changes to legally or operationally meaningful metadata may require a new version or explicit audit event.

The detailed metadata-correction policy remains an open governance decision.

---

### 11.10 Processing Representation Identity

Each Processing Run must produce a distinguishable technical representation.

The representation must remain traceable to:

* Document Version;
* Source Artifact;
* Processing Run;
* effective processing configuration;
* target index.

Stable chunk identities should prevent uncontrolled duplication during retries.

A chunk identifier may be derived from controlled inputs such as:

```text
Document Version
+ Processing Run
+ Chunk Position or Stable Chunk Content
```

The exact chunk-identity algorithm will be defined in the Chunking or Indexing deliverable.

Processing output from different configurations must not be mixed without explicit control.

---

### 11.11 Duplicate Handling Outcomes

The system should support a small set of clear logical outcomes.

Indicative outcomes include:

```text
CREATE_NEW_DOCUMENT
CREATE_NEW_VERSION
REUSE_EXISTING_SOURCE
RETURN_EXISTING_REQUEST
CREATE_NEW_PROCESSING_RUN
REQUIRE_IDENTITY_REVIEW
REJECT_CONFLICT
```

The user-facing response should clearly communicate what happened.

For example:

```text
Existing Document found
New Document Version created
Processing Run started
```

or:

```text
Exact source already exists
Existing Source Artifact reused
New Processing Run started
```

Duplicate handling must not remain hidden inside internal logs.

---

### 11.12 Monitoring and Auditability

Data Monitoring should be able to show:

* all versions belonging to a Document;
* the Source Artifact associated with each version;
* Processing Runs associated with each version;
* duplicate or replay outcomes;
* identity-resolution decisions;
* previous and current active versions;
* configuration used by each Processing Run.

Important identity or version changes should preserve an audit record containing:

* previous state;
* new state;
* action or decision;
* timestamp;
* responsible actor or system component;
* reason where available.

---

### 11.13 Core Identity and Duplicate Rules

The following rules apply:

1. A Document represents a logical source, not a filename.
2. A Document Version represents source evolution, not processing changes.
3. A Source Artifact represents the exact accepted file.
4. A Processing Run represents one technical transformation of one Document Version.
5. The same Document Version may have multiple Processing Runs.
6. A new embedding or chunking configuration does not create a new Document Version.
7. Request replay must return or reconnect to the existing operation.
8. Exact source duplicates may be reused rather than stored repeatedly.
9. Ambiguous identity must require controlled resolution.
10. Existing Source Artifacts and versions must not be silently overwritten.
11. Duplicate handling outcomes must remain visible and auditable.
12. Historical processing and version relationships must remain traceable.

The resulting identity model is:

```text
Logical Source Change
→ New Document Version

Technical Processing Change
→ New Processing Run

Repeated Identical Request
→ Existing Operation

Exact Existing Source
→ Reuse or Controlled Reprocessing
```


## 12. Processing Run and Pipeline Coordination

A Processing Run represents one controlled execution of the Data Ingest pipeline for one Document Version using one resolved processing configuration.

Its purpose is to coordinate:

* processing stages;
* lifecycle state;
* failure handling;
* retry behaviour;
* produced artifacts;
* indexing and verification;
* traceability toward Data Monitoring.

The initial pipeline is deterministic and does not require agentic orchestration.

```text id="prpc01"
Document Version
+ Source Artifact
+ Processing Configuration
→ Processing Run
→ Verified Search Representation
```

---

### 12.1 Processing Run Responsibility

A Processing Run is responsible for tracking one technical transformation of a Document Version.

It should remain associated with:

* Document;
* Document Version;
* Source Artifact;
* processing configuration snapshot;
* target OpenSearch index;
* creation and completion timestamps;
* current status;
* current stage;
* produced artifact references;
* processing counts;
* verification result;
* failure information.

A Processing Run is not:

* a Document Version;
* an upload request;
* an OpenSearch index;
* a worker process;
* a queue message;
* a user session.

A worker or ECS task may execute a Processing Run, but the run must remain identifiable independently of the infrastructure process that executes it.

---

### 12.2 Pipeline Stages

The initial processing pipeline contains the following logical stages:

```text id="prpc02"
PARSING
→ NORMALIZATION
→ METADATA_HANDLING
→ CHUNKING
→ EMBEDDING
→ INDEXING
→ VERIFICATION
```

Each stage should have:

* defined input;
* defined output;
* clear responsibility;
* success condition;
* failure outcome.

The initial pipeline is sequential because later stages depend on the outputs of earlier stages.

For example:

```text id="prpc03"
Embedding cannot begin
until
Chunks have been produced and validated
```

The implementation may internally use batch processing or controlled parallelism, but the logical stage dependencies must remain explicit.

---

### 12.3 Run Status and Current Stage

The high-level Processing Run status should remain simple.

Indicative statuses are:

```text id="prpc04"
PENDING
RUNNING
SUCCEEDED
FAILED
CANCELLED
```

The current stage is recorded separately.

Example:

```text id="prpc05"
status: RUNNING
current_stage: EMBEDDING
```

This avoids creating a large overall status enum containing values such as:

```text id="prpc06"
PARSING
CHUNKING
EMBEDDING
INDEXING
```

which are processing stages rather than final run outcomes.

The initial implementation does not require a separate persisted state machine for every internal function.

It does require enough state to determine:

* whether processing has started;
* which stage is currently running;
* whether processing completed;
* where processing failed;
* whether retry or reprocessing is possible.

---

### 12.4 Processing Configuration Snapshot

Before the pipeline begins, the effective processing configuration must be resolved and associated with the run.

This may include:

* parser and parser version;
* normalization settings;
* metadata-handling settings;
* chunking strategy;
* chunk size and overlap;
* embedding model;
* vector dimensions;
* embedding batch size;
* target index;
* verification settings.

The run must preserve the effective values used at execution time.

It should not depend only on the latest version of a mutable configuration file.

This supports:

* reproducibility;
* troubleshooting;
* experiment comparison;
* reprocessing;
* auditability.

A configuration change creates a new Processing Run when the Document Version is reprocessed.

It does not alter the history of previous runs.

---

### 12.5 Stage Coordination

The pipeline coordinator is responsible for:

1. loading the Processing Run and its configuration;
2. confirming that the Source Artifact is available;
3. starting the next eligible stage;
4. passing the validated output of one stage to the next;
5. recording progress and produced artifacts;
6. stopping the pipeline when a blocking failure occurs;
7. initiating indexing only after required processing outputs exist;
8. completing the run only after verification succeeds.

The coordinator should not contain all processing logic itself.

Its role is to coordinate components such as:

```text id="prpc07"
Parser
Normalizer
Metadata Handler
Chunker
Embedding Provider
OpenSearch Indexer
Verifier
```

Each component remains responsible for its own processing behaviour and output validation.

---

### 12.6 Execution Model

The initial implementation may use a modular monolith with:

* one FastAPI application;
* one shared Python codebase;
* one background worker process;
* or different container commands using the same image.

Indicative deployment:

```text id="prpc08"
FastAPI Service
→ accepts and registers ingestion requests

Processing Worker
→ executes Processing Runs
```

The exact background-execution mechanism remains open.

Possible implementations include:

* an application-managed background worker;
* a queue-based worker;
* AWS-native messaging;
* Redis-backed coordination;
* another durable execution mechanism.

The reference does not require:

* LangGraph;
* multiple microservices;
* one queue per stage;
* one ECS service per processing component;
* a distributed workflow engine.

The selected model must provide sufficient durability for the agreed MVP.

In particular, an application restart should not cause accepted Processing Runs to disappear without trace.

---

### 12.7 Durable Processing Intent

Before asynchronous processing begins, the system should record durable processing intent.

At minimum, this means that the system can recover:

* which run was requested;
* which Document Version should be processed;
* which Source Artifact should be used;
* which configuration applies;
* which target index is intended;
* whether the run has started or completed.

The system must not rely only on:

* in-memory Python objects;
* FastAPI background tasks;
* application logs;
* the continued lifetime of one ECS task.

The exact durable store remains an implementation decision.

PostgreSQL, a queue, or another state mechanism should be introduced only when its responsibility is clear.
A queue may preserve and deliver processing commands, but it must not be treated as the sole authoritative registry for Processing Run lifecycle state. The operational state mechanism must still preserve the current status, stage, configuration reference, outcome, and failure information required by Data Monitoring.
---

### 12.8 Stage Outputs and Artifacts

Each stage produces an output consumed by the next stage.

Indicative flow:

```text id="prpc09"
Source Artifact
→ Parsed Document
→ Normalized Document
→ Metadata-Enriched Document
→ Chunks
→ Embedded Chunks
→ Indexed Records
→ Verification Result
```

Not every intermediate output must be stored permanently.

However, the system should preserve enough information to support:

* failure diagnosis;
* processing counts;
* reprocessing;
* configuration comparison;
* source-to-index traceability.

Intermediate artifacts may be:

* held temporarily during execution;
* stored in S3;
* registered through metadata records;
* recreated from the Source Artifact.

The retention decision for each artifact type will be made during the corresponding deliverable.

---

### 12.9 Failure Coordination

When a mandatory stage fails:

* the current stage is recorded;
* dependent stages do not continue;
* the Processing Run becomes `FAILED`;
* a safe failure category and summary are stored;
* partial output is not treated as a successful representation;
* the new representation remains unavailable to normal retrieval.

Indicative failure categories may include:

```text id="prpc10"
PARSING_FAILED
NORMALIZATION_FAILED
METADATA_FAILED
CHUNKING_FAILED
EMBEDDING_FAILED
INDEXING_FAILED
VERIFICATION_FAILED
CONFIGURATION_INVALID
INFRASTRUCTURE_UNAVAILABLE
```

The exact error model will be defined during implementation.

Failures should distinguish between:

* invalid source or configuration;
* application defects;
* temporary infrastructure failures;
* partial external-service operations.

This distinction supports correct retry behaviour.

---

### 12.10 Retry and Reprocessing

Retry and reprocessing are related but distinct.

#### Retry

A retry attempts to complete a failed Processing Run or failed operation without changing the intended source and processing configuration.

It is appropriate for recoverable failures such as:

* temporary OpenSearch unavailability;
* transient embedding-provider failure;
* worker interruption;
* temporary network failure.

#### Reprocessing

Reprocessing creates a new Processing Run.

It is appropriate when:

* the configuration changes;
* the parser changes;
* chunking changes;
* the embedding model changes;
* metadata is corrected;
* the previous representation must be rebuilt.

The general rule is:

```text id="prpc11"
Same intended execution after transient failure
→ Retry

New technical representation
→ New Processing Run
```

The precise retry-attempt model will be defined later.

---

### 12.11 Idempotent Coordination

Pipeline coordination must prevent retries from creating uncontrolled duplicates.

The coordinator should use stable identities for:

* Processing Run;
* stage execution where required;
* Chunks;
* OpenSearch records;
* indexing batches where practical.

Repeated execution of a stage should either:

* safely reuse an existing valid output;
* replace the incomplete output;
* or fail clearly when the existing state is incompatible.

For example:

```text id="prpc12"
Retry INDEXING
→ write the same stable chunk identifiers
→ no duplicate OpenSearch records
```

The coordinator must not assume that every external operation is transactional.

S3, the operational store, the embedding provider, and OpenSearch may complete independently.

Partial states must therefore remain detectable.

---

### 12.12 Cancellation

A Processing Run may support cancellation where operationally practical.

Cancellation should:

* prevent unstarted stages from beginning;
* stop active work where safe;
* preserve processing history;
* keep the Source Artifact and Document Version;
* prevent the incomplete representation from becoming active.

Cancellation does not automatically delete:

* source artifacts;
* successful outputs from earlier runs;
* historical monitoring records.

Full cancellation behaviour may be deferred if it introduces unnecessary complexity into the initial MVP.

---

### 12.13 Processing Counts

The Processing Run should expose high-level counts needed for monitoring and verification.

Indicative counts include:

* parsed sections;
* produced chunks;
* successfully embedded chunks;
* failed embedding items;
* attempted index records;
* successfully indexed records;
* failed index records;
* verified records.

These counts help detect incomplete processing.

For example:

```text id="prpc13"
produced_chunks: 120
embedded_chunks: 120
indexed_chunks: 117
```

must not be treated as successful completion unless an explicit approved tolerance policy exists.

For the initial MVP, complete processing should be the default expectation.

---

### 12.14 Handoff to Verification

The coordinator initiates verification only after all mandatory processing and indexing operations report completion.

Verification determines whether the produced representation satisfies the required integrity conditions.

The coordinator then applies the result:

```text id="prpc14"
Verification succeeded
→ Processing Run SUCCEEDED
→ Representation technically ready
```

```text id="prpc15"
Verification failed
→ Processing Run FAILED
→ Representation inactive
```

The coordinator must not mark the run successful before verification completes.

---

### 12.15 Monitoring and Observability

Data Monitoring should be able to inspect:

* Processing Run identifier;
* Document and Document Version;
* Source Artifact;
* status;
* current stage;
* configuration reference;
* target index;
* processing counts;
* start and completion timestamps;
* failure category;
* safe failure summary;
* retry or parent-run relationship;
* verification outcome.

Structured logs should include:

* run identifier;
* stage;
* correlation identifier;
* outcome;
* duration;
* error category.

Logs supplement operational state.

They must not be the only source of truth for run status.

---

### 12.16 Core Coordination Rules

The following rules apply:

1. One Processing Run processes one Document Version using one configuration snapshot.
2. The pipeline is deterministic unless a concrete future requirement justifies conditional orchestration.
3. Run status and current stage remain separate.
4. Mandatory stages execute according to explicit dependencies.
5. A blocking stage failure stops dependent stages.
6. Successful indexing does not complete the run until verification passes.
7. Processing intent and run state must survive application-process failure.
8. Retry must not create uncontrolled duplicate outputs.
9. Changed processing configuration creates a new Processing Run.
10. Infrastructure workers execute runs but do not define their identity.
11. Monitoring state must be stored explicitly rather than inferred only from logs.
12. LangGraph or a workflow engine should be introduced only when the processing flow requires capabilities that a simple coordinator cannot provide.

The resulting coordination model is:

```text id="prpc16"
Durable Processing Intent
→ Deterministic Stage Coordination
→ Controlled Failure and Retry
→ Verified Completion
→ Observable Processing History
```


## 13. Parsing

Parsing transforms a validated Source Artifact into a common internal document representation that can be consumed by the remaining ingestion stages.

The parser is responsible for interpreting the source format while preserving the document content and useful structure.

The parsing boundary is:

```text
Validated Source Artifact
→ Format-Specific Parser
→ Parsed Document
```

Parsing does not perform:

* final text normalization;
* retrieval chunking;
* embedding generation;
* OpenSearch indexing;
* legal interpretation;
* governance approval.

---

### 13.1 Parsing Objective

The objective of parsing is to produce a consistent representation across the supported source formats:

```text
TXT
Markdown
DOCX
```

Downstream components should not need to understand the original file format.

They should receive a common representation containing, where available:

* document text;
* sections;
* headings;
* paragraphs;
* lists;
* tables or table text;
* source order;
* structural metadata;
* parser warnings.

The parser should preserve enough structure to support later:

* heading-aware chunking;
* source traceability;
* result inspection;
* citation context;
* metadata propagation.

---

### 13.2 Common Parsed Document Representation

The parser output should follow a shared logical contract.

Indicative structure:

```text
Parsed Document
├── Document and Version References
├── Parser Information
├── Detected Language
├── Ordered Content Blocks
├── Document-Level Metadata
└── Parsing Warnings
```

A content block may represent:

* heading;
* paragraph;
* list item;
* table;
* quote;
* code block;
* other supported structural element.

Each block should preserve, where practical:

* block type;
* source order;
* text content;
* heading hierarchy;
* structural context;
* source location;
* format-specific metadata.

The final Pydantic models will be defined during implementation.

---

### 13.3 Source Order and Structure

The parser must preserve the logical reading order of the source document.

For example:

```text
Heading
→ Paragraph
→ List
→ Subheading
→ Paragraph
```

must not be returned as an unordered set of text fragments.

Document structure should be preserved when it is useful and reliably available.

Examples include:

* Markdown headings;
* DOCX heading styles;
* numbered sections;
* paragraph order;
* list hierarchy;
* table placement.

The parser should not invent structural hierarchy when the source does not provide sufficient evidence.

---

### 13.4 TXT Parsing

TXT parsing is primarily concerned with:

* decoding the file using the validated encoding;
* preserving paragraph boundaries;
* preserving line order;
* identifying obvious blank-line section boundaries;
* producing a usable text representation.

TXT files normally provide limited structural metadata.

The parser may identify simple structural signals, but it should avoid unreliable assumptions based only on formatting patterns.

For example, uppercase text should not automatically be treated as a heading unless an approved heuristic exists.

---

### 13.5 Markdown Parsing

Markdown parsing should preserve useful semantic elements such as:

* headings and heading levels;
* paragraphs;
* ordered and unordered lists;
* block quotes;
* code blocks;
* links;
* tables where supported.

Markdown syntax should be interpreted for structure while preserving the user-visible text required for retrieval.

The parser should distinguish between:

```text
Document content
and
Markdown formatting syntax
```

For example, heading markers may define hierarchy but should not remain as meaningless retrieval noise.

Malformed Markdown may still be parsed as text where a useful representation can be produced.

---

### 13.6 DOCX Parsing

DOCX parsing should preserve document content and useful structural information where reliably available.

Indicative elements include:

* paragraphs;
* headings and styles;
* ordered and unordered lists;
* tables;
* document order;
* headers and footers where included by policy.

The treatment of the following remains a parsing-policy decision:

* tables;
* hyperlinks;
* footnotes;
* endnotes;
* comments;
* tracked changes;
* headers and footers;
* text boxes;
* embedded images;
* embedded files.

The MVP should support the common textual structures required by the initial Compliance dataset rather than attempting complete DOCX feature coverage.

Unsupported elements should be ignored, extracted in simplified form, or reported as warnings according to an explicit policy.

---

### 13.7 Tables

Tables can contain important compliance information and should not be discarded without visibility.

Where supported, the parser should preserve:

* row and column order;
* header relationships;
* cell text;
* table position within the document.

The parsed representation may use:

* structured rows and cells;
* a normalized textual representation;
* or both.

The initial implementation does not require advanced table understanding.

However, it should avoid flattening a table into text in a way that destroys obvious relationships between headers and values.

---

### 13.8 Source Position and Provenance

Parsed content should retain source-position information where the format supports it.

Examples include:

* paragraph index;
* block index;
* section path;
* heading path;
* table index;
* page number when supported in future formats.

For TXT, Markdown, and DOCX, reliable page numbers may not exist.

The system must not invent page references where the source format does not provide stable pagination.

Source-position metadata should allow later Chunks to be traced back to their originating parsed blocks.

---

### 13.9 Parser Selection and Versioning

The parser is selected according to the validated file type and the effective Processing Configuration.

The Processing Run must record:

* parser identifier;
* parser version;
* relevant parser settings.

A parser change may alter:

* extracted text;
* heading structure;
* table representation;
* block boundaries;
* metadata.

Therefore, reprocessing with a different parser or parser version creates a new Processing Run.

It does not create a new Document Version.

---

### 13.10 Parsing Quality Checks

Parsing should not be considered successful merely because no exception occurred.

Basic output checks should confirm that:

* a Parsed Document was produced;
* content blocks remain in a valid order;
* required identifiers are present;
* extracted text is not unexpectedly empty;
* block types are supported;
* source references are valid;
* severe parser warnings are handled.

Indicative suspicious outcomes include:

```text
Non-empty source file
→ Parsed document contains no usable text
```

```text
Large DOCX document
→ Only one short paragraph extracted
```

Such outcomes may fail the stage or produce a review warning, depending on the agreed policy.

---

### 13.11 Parsing Warnings

Some issues may not justify immediate failure.

Examples include:

* unsupported embedded image;
* skipped header or footer;
* simplified table extraction;
* unrecognized style;
* malformed Markdown block;
* missing optional metadata.

The parser should return controlled warnings rather than hiding these conditions.

Warnings should include:

* warning category;
* safe summary;
* affected block or source area where available;
* severity.

The distinction between blocking errors and non-blocking warnings will be refined during implementation.

---

### 13.12 Parsing Failure Behaviour

Parsing fails when the system cannot produce a usable and controlled Parsed Document.

Indicative failure conditions include:

* parser cannot open the source;
* source structure is corrupted;
* required document content cannot be extracted;
* parser configuration is invalid;
* output violates the Parsed Document contract;
* an unsupported structure prevents reliable processing.

When parsing fails:

* the Processing Run becomes `FAILED`;
* downstream stages do not begin;
* the Source Artifact remains preserved;
* the parser and failure category are recorded;
* the failure is visible through Data Monitoring.

Parser failures caused by temporary infrastructure conditions may be retryable.

Failures caused by unsupported or corrupted source content normally require source correction or a different parser.

---

### 13.13 Parsed Artifact Retention

The Parsed Document may be:

* passed directly to the next stage;
* stored temporarily;
* serialized to S3;
* or recreated from the Source Artifact.

The MVP does not require permanent storage of every parsed representation.

Permanent retention may be useful for:

* debugging;
* reproducibility;
* parser comparison;
* audit;
* avoiding repeated parsing.

The retention choice should balance:

* storage cost;
* operational value;
* reproducibility;
* document sensitivity.

---

### 13.14 Configuration Boundary

The following parsing settings may be configurable:

* parser selected for each supported file type;
* parser version;
* text-encoding policy;
* heading detection;
* table extraction policy;
* list preservation;
* header and footer policy;
* tracked-change policy;
* unsupported-element policy;
* minimum usable-text threshold;
* warning severity rules.

Configuration should select only supported parsing behaviours.

It should not allow arbitrary executable parser code to be injected through an upload request.

---

### 13.15 Core Parsing Rules

The following rules apply:

1. Parsing begins only after file validation and source storage succeed.
2. Each supported format produces a common Parsed Document representation.
3. Source order and useful structure should be preserved.
4. Parsers must not invent unsupported provenance or hierarchy.
5. Parsing output remains traceable to the Source Artifact and Processing Run.
6. Parser identity and version remain part of the Processing Configuration.
7. Parsing success requires usable output, not only absence of exceptions.
8. Blocking parsing failures stop downstream stages.
9. Non-blocking limitations should be exposed as controlled warnings.
10. Parsing remains separate from normalization, chunking, and legal interpretation.

The resulting parsing boundary is:

```text
Format-Specific Source
→ Controlled Structural Extraction
→ Common Parsed Document
→ Normalization and Metadata Handling
```


## 14. Normalization

Normalization transforms the Parsed Document into a cleaner and more consistent representation for metadata handling, chunking, and retrieval.

The normalization boundary is:

```text
Parsed Document
→ Controlled Text and Structure Cleanup
→ Normalized Document
```

Normalization should improve consistency without changing the document’s intended meaning.

It does not perform:

* legal interpretation;
* document classification;
* retrieval chunking;
* embedding generation;
* summarization;
* content rewriting.

---

### 14.1 Normalization Objective

The objective is to reduce format-specific noise and inconsistencies introduced by:

* the original source;
* formatting conventions;
* parser behaviour;
* encoding;
* whitespace;
* repeated structural elements.

The output should provide predictable content for downstream processing while preserving:

* substantive text;
* section order;
* heading hierarchy;
* list relationships;
* table meaning;
* source provenance.

Normalization must not make the document appear more precise or authoritative than the original source.

---

### 14.2 Normalized Document Representation

The Normalized Document should preserve the main structure of the Parsed Document.

Indicative content includes:

```text
Normalized Document
├── Document and Version References
├── Normalization Configuration
├── Ordered Content Blocks
├── Structural Metadata
├── Normalization Warnings
└── Source-to-Normalized Mapping
```

Each normalized block should remain traceable to one or more parsed source blocks.

The final implementation contract will be defined through the relevant Pydantic models and deliverables.

---

### 14.3 Text Cleanup

Text cleanup may include:

* normalizing line endings;
* removing unnecessary repeated whitespace;
* normalizing paragraph spacing;
* removing invalid control characters;
* standardizing supported Unicode representations;
* joining parser-created line breaks where meaning is preserved;
* preserving meaningful paragraph and list boundaries.

Normalization must avoid destructive cleanup.

For example:

```text
"Article 10(2)"
```

must not be changed in a way that loses its legal reference structure.

Likewise, whitespace inside:

* identifiers;
* article numbers;
* dates;
* formulas;
* tables;
* code or configuration examples;

should not be modified without a reliable rule.

---

### 14.4 Structural Normalization

Structural normalization may standardize how downstream stages represent:

* headings;
* heading levels;
* paragraphs;
* list items;
* table blocks;
* section paths.

For example, format-specific heading styles may be mapped into a common hierarchy:

```text
DOCX Heading 1
Markdown #
Detected top-level section
→ Normalized heading level 1
```

Normalization should preserve the original structural evidence and avoid inventing missing hierarchy.

When heading levels are inconsistent, the system may:

* preserve the detected level;
* apply a controlled correction;
* or emit a warning.

---

### 14.5 Headers, Footers, and Repeated Content

Repeated headers, footers, navigation text, or boilerplate may create retrieval noise.

Where reliably detected, normalization may remove or separately mark repeated content such as:

* document headers;
* document footers;
* repeated confidentiality notices;
* repeated navigation elements;
* repeated page labels.

Removal must be conservative.

Content must not be removed merely because it appears multiple times, since repeated legal clauses or definitions may be meaningful.

The exact repeated-content policy depends on the supported formats and available source structure.

---

### 14.6 Lists and Numbered Sections

Lists and numbered legal structures must retain their relationships.

Normalization should preserve:

* list order;
* nesting;
* item labels;
* article and subsection numbering;
* association with the surrounding heading or paragraph.

For example:

```text
Article 12
1. Providers shall...
2. The documentation shall...
```

must not be flattened into unrelated text blocks.

Numbering should remain available to metadata handling, chunking, and result provenance.

---

### 14.7 Table Normalization

When the parser produces table content, normalization should create a consistent representation while preserving:

* row order;
* column order;
* headers;
* cell relationships;
* table position.

A normalized textual representation may be created for retrieval and embeddings.

However, it should not replace the structured table representation when that structure is needed for traceability or later processing.

Advanced semantic interpretation of tables is outside the initial MVP.

---

### 14.8 Character and Unicode Handling

Normalization should apply a controlled Unicode policy.

This may include:

* consistent Unicode normalization;
* replacement or removal of unsupported control characters;
* preservation of Greek, accented, and non-Latin text;
* normalization of visually equivalent punctuation where safe;
* preservation of legally meaningful symbols.

The system must not transliterate or translate source text as part of normalization.

Language translation is a separate capability and is outside the initial Data Ingest scope.

---

### 14.9 Content Preservation

Normalization must preserve the substantive meaning of the source.

It must not:

* summarize paragraphs;
* paraphrase legal text;
* remove qualifications or exceptions;
* replace technical terminology;
* resolve ambiguous wording;
* infer obligations;
* change dates, numbers, or identifiers;
* merge distinct provisions without clear structural evidence.

The original Source Artifact remains the canonical reference when normalized content is disputed.

---

### 14.10 Source Mapping and Provenance

Normalized content should remain traceable to the Parsed Document and Source Artifact.

Where practical, each normalized block should preserve:

* source block identifiers;
* original order;
* heading path;
* source position;
* transformation notes where content was materially altered.

The purpose is not to create a character-level diff for every transformation.

The purpose is to maintain enough provenance to explain:

* where a Chunk came from;
* which source section it represents;
* which normalization rules affected it.

---

### 14.11 Normalization Quality Checks

Normalization success should confirm that:

* required identifiers are present;
* block order remains valid;
* usable content remains available;
* substantive content was not unintentionally removed;
* structural relationships remain internally consistent;
* output conforms to the Normalized Document contract.

Useful high-level checks may compare:

* parsed and normalized block counts;
* parsed and normalized text length;
* removed-content volume;
* warning counts.

Large unexplained content loss should result in a warning or failure.

For example:

```text
Parsed text length: 50,000 characters
Normalized text length: 5,000 characters
```

should not pass without an explicit and explainable reason.

---

### 14.12 Normalization Warnings

Non-blocking issues may include:

* inconsistent heading hierarchy;
* repeated content that could not be classified reliably;
* malformed list nesting;
* simplified table normalization;
* unsupported characters;
* unusually large content reduction.

Warnings should identify:

* category;
* severity;
* affected block or section where available;
* safe summary.

Warnings remain associated with the Processing Run and are visible through Data Monitoring where useful.

---

### 14.13 Failure Behaviour

Normalization fails when the system cannot produce a valid and usable Normalized Document.

Indicative failure conditions include:

* invalid Parsed Document input;
* loss of required source references;
* empty or unusable normalized content;
* invalid structural output;
* configuration failure;
* unexpected destructive transformation.

When normalization fails:

* the Processing Run becomes `FAILED`;
* metadata handling and downstream stages do not begin;
* the Parsed Document and Source Artifact remain available according to their retention policy;
* the failure category and safe summary are recorded.

A normalization failure caused by deterministic transformation rules will normally require configuration or code correction rather than automatic retry.

---

### 14.14 Configuration Boundary

The following normalization behaviours may be configurable:

* whitespace policy;
* Unicode-normalization form;
* control-character handling;
* repeated header and footer handling;
* paragraph and line-break joining;
* heading-level normalization;
* list preservation;
* table-text representation;
* minimum usable-content threshold;
* warning thresholds;
* content-loss tolerance.

Configuration must use approved options.

It should not permit arbitrary text-transformation code to be supplied through an upload request.

The Processing Run must remain associated with the effective normalization configuration.

---

### 14.15 Core Normalization Rules

The following rules apply:

1. Normalization operates on the Parsed Document, not directly on the uploaded file.
2. It improves consistency without changing substantive meaning.
3. Useful structure and source order remain preserved.
4. Legal numbering, identifiers, dates, and qualifications must not be altered carelessly.
5. Content removal must be conservative and explainable.
6. Normalized blocks remain traceable to parsed source blocks.
7. Large or suspicious content changes produce warnings or failure.
8. Normalization does not perform summarization, translation, or legal interpretation.
9. Blocking failures stop downstream stages.
10. The original Source Artifact remains the canonical reference.

The resulting normalization boundary is:

```text
Parsed Document
→ Meaning-Preserving Cleanup
→ Consistent Normalized Representation
→ Metadata Handling and Chunking
```


## 15. Metadata Handling

Metadata Handling validates, enriches, and propagates the information required to identify, govern, filter, inspect, and trace document content.

The metadata boundary is:

```text
Normalized Document
+ Upload Metadata
+ System Metadata
→ Validated Metadata-Enriched Document
```

Metadata Handling does not perform:

* legal interpretation;
* final governance approval;
* retrieval ranking;
* automatic determination of legal applicability;
* unrestricted LLM-based enrichment;
* correction of the original source content.

Its purpose is to produce controlled metadata that downstream chunking, indexing, monitoring, and query operations can rely on.

---

### 15.1 Metadata Objectives

Metadata supports several distinct responsibilities:

* Document and Document Version identification;
* source provenance;
* compliance-specific filtering;
* document governance;
* chunk traceability;
* retrieval-result inspection;
* processing reproducibility;
* operational monitoring.

The system should collect only metadata that has a clear functional purpose.

It should avoid creating a large generic schema containing fields that are not used by:

* ingestion;
* monitoring;
* query filtering;
* evaluation;
* governance;
* or audit.

---

### 15.2 Metadata Categories

Metadata should be grouped according to its origin and responsibility.

#### User-Provided Metadata

Supplied during upload or review.

Examples:

* title;
* source authority;
* jurisdiction;
* document category;
* publication date;
* effective date;
* version label;
* source URL.

#### System-Generated Metadata

Created by the ingestion system.

Examples:

* Document identifier;
* Document Version identifier;
* Source Artifact identifier;
* Processing Run identifier;
* checksum;
* upload timestamp;
* file type;
* file size;
* target index;
* configuration reference.

#### Processing-Derived Metadata

Extracted or derived during parsing and normalization.

Examples:

* detected language;
* heading path;
* section title;
* article number;
* paragraph order;
* content-block type;
* document structure.

#### Governance Metadata

Used to determine whether content is allowed in normal retrieval.

Examples:

* governance status;
* active or superseded state;
* review status;
* approval timestamp;
* reviewing actor.

Governance metadata may be initialized during ingestion but should not be treated as automatically verified merely because processing succeeded.

---

### 15.3 Initial Compliance Metadata

The first implementation should use a focused Compliance metadata schema rather than a fully dynamic domain-independent schema.

Indicative document-level fields include:

```text
title
source_authority
jurisdiction
document_category
official_identifier
source_url
publication_date
effective_date
version_label
language
governance_status
```

Not every field must be mandatory.

The final required and optional fields should be based on:

* the initial Compliance document collection;
* retrieval-filtering needs;
* monitoring needs;
* governance requirements;
* availability and reliability of source information.

The MVP should avoid requiring uncertain metadata only to make the schema appear complete.

---

### 15.4 Document-Level and Chunk-Level Metadata

Metadata must distinguish between information that belongs to the complete Document Version and information that belongs to an individual Chunk.

#### Document-Version Metadata

Examples:

* title;
* authority;
* jurisdiction;
* official identifier;
* publication date;
* effective date;
* version label;
* source URL;
* governance status.

#### Chunk Metadata

Examples:

* chunk identifier;
* chunk order;
* section title;
* heading path;
* article or subsection reference;
* source-block range;
* Processing Run identifier;
* target-index representation.

Relevant document-level metadata may be copied into each OpenSearch chunk record to support efficient filtering.

The canonical ownership of that metadata should remain clear even when values are duplicated in the retrieval index.

---

### 15.5 Metadata Validation

Metadata must be validated before it is accepted into the enriched document representation.

Validation may include:

* required fields are present;
* controlled values are supported;
* dates use valid formats;
* identifiers are well formed;
* URLs are structurally valid;
* text values remain within configured limits;
* relationships between fields are consistent.

For example:

```text
effective_date earlier than publication_date
```

may require a warning or review, depending on the source and policy.

Metadata validation confirms structural and logical usability.

It does not necessarily confirm that a value is legally correct or authoritative.

---

### 15.6 Metadata Provenance

Important metadata should preserve its origin.

Indicative provenance values include:

```text
USER_PROVIDED
SYSTEM_GENERATED
PARSER_EXTRACTED
RULE_DERIVED
REVIEWER_CONFIRMED
```

Where useful, metadata should also record:

* extraction or assignment timestamp;
* Processing Run;
* extraction rule or component;
* confidence or review status;
* previous value when changed.

This allows the system to distinguish between:

```text
source_authority entered by uploader
```

and:

```text
source_authority confirmed by authorized reviewer
```

These values may be identical but do not have the same evidential status.

---

### 15.7 Metadata Extraction

Some metadata may be extracted automatically from document structure or content.

Examples include:

* heading titles;
* article numbers;
* section paths;
* language;
* document identifiers explicitly present in the source.

The initial implementation should prefer deterministic extraction when reliable.

LLM-assisted metadata extraction may be considered later for fields that cannot be captured effectively through deterministic rules.

Any LLM-derived metadata must remain:

* traceable to the model and prompt configuration;
* distinguishable from verified metadata;
* reviewable where materially important;
* unable to silently overwrite authoritative user- or reviewer-confirmed values.

---

### 15.8 Metadata Conflicts

Conflicts may occur between:

* user-provided metadata;
* existing Document records;
* source-extracted metadata;
* previously confirmed metadata;
* version information.

Examples include:

```text
Uploaded jurisdiction: EU
Extracted jurisdiction: UK
```

or:

```text
Existing official identifier differs from uploaded identifier
```

The system must not silently resolve material conflicts using an arbitrary priority rule.

Possible outcomes include:

* accept the authoritative existing value;
* preserve both values with provenance;
* issue a warning;
* require user review;
* fail identity or version resolution.

The detailed conflict-resolution policy may differ by field and should be defined only for metadata used by the MVP.

---

### 15.9 Metadata Propagation

After metadata is validated, relevant fields are propagated to:

* Document records;
* Document Version records;
* Processing Run records;
* Chunks;
* OpenSearch index records;
* monitoring views;
* retrieval-result provenance.

Propagation should follow explicit ownership rules.

For example:

```text
jurisdiction
→ owned by Document Version
→ copied to Chunks for filtering
```

A metadata correction should update the canonical record first.

Derived OpenSearch representations may then require:

* metadata update;
* reindexing;
* or a new Processing Run;

depending on whether the metadata affects retrieval, chunking, embedding, or governance.

---

### 15.10 Metadata and Processing Identity

A metadata change does not always create a new Document Version.

Administrative corrections may include:

* fixing a display-title typo;
* correcting a source URL;
* adding missing descriptive information.

A source-meaningful change may require a new Document Version.

Examples include changes to:

* official version label;
* legally meaningful effective date;
* document authority;
* source content;
* official identifier.

A processing-derived metadata change may require a new Processing Run when it changes:

* chunk boundaries;
* retrieval filters;
* indexed provenance;
* article or section attribution.

The exact decision depends on the field’s ownership and effect.

---

### 15.11 Governance Metadata

Governance metadata remains distinct from technical-processing status.

For example:

```text
Processing Run: SUCCEEDED
Governance Status: PENDING_REVIEW
```

This means the representation is technically valid but not yet available through the normal retrieval path.

Indicative governance values may include:

```text
PENDING_REVIEW
ACTIVE
SUPERSEDED
DISABLED
DELETED
```

The final governance workflow belongs primarily to Data Monitoring.

Data Ingest must ensure that governance fields are present and propagated correctly to indexed records.

---

### 15.12 Metadata Quality Checks

Before chunking or indexing, Metadata Handling should confirm that:

* required identifiers are present;
* required document-level fields are available;
* controlled values are valid;
* provenance is available for important fields;
* chunk-filter fields can be propagated;
* conflicting metadata has been resolved or explicitly flagged.

Warnings may be produced for:

* missing optional fields;
* unverified extracted values;
* suspicious date relationships;
* inconsistent heading or article metadata;
* low-confidence derivation;
* conflicts that do not block processing.

Missing metadata should become a blocking failure only when downstream correctness or governance depends on it.

---

### 15.13 Failure Behaviour

Metadata Handling fails when the system cannot produce a valid metadata-enriched representation required for downstream processing.

Indicative failure conditions include:

* missing mandatory identity fields;
* invalid metadata schema;
* unresolved material conflict;
* invalid controlled value;
* loss of provenance relationships;
* configuration failure;
* inability to associate metadata with the correct Document Version.

When Metadata Handling fails:

* chunking and downstream stages do not begin;
* the Processing Run becomes `FAILED`;
* the failure category and safe summary are recorded;
* the Source Artifact and previous processing outputs remain preserved.

Non-blocking metadata limitations should be recorded as warnings rather than hidden.

---

### 15.14 Configuration Boundary

The following metadata behaviours may be configurable:

* required and optional fields;
* controlled vocabularies;
* default values;
* field-length limits;
* extraction rules;
* propagation rules;
* conflict policies;
* warning thresholds;
* governance default status;
* fields included in OpenSearch;
* fields available for metadata filtering.

Configuration should use a focused approved schema.

The MVP does not require:

* arbitrary metadata-schema plugins;
* user-defined executable extraction logic;
* fully dynamic OpenSearch field generation;
* unrestricted custom fields submitted through the upload request.

Schema changes affecting OpenSearch mappings must be coordinated with index versioning and reindexing decisions.

---

### 15.15 Core Metadata Rules

The following rules apply:

1. Metadata must have a clear operational, retrieval, governance, or audit purpose.
2. Metadata origin should remain traceable.
3. Structurally valid metadata is not automatically authoritative metadata.
4. Document-level and Chunk-level metadata remain distinct.
5. Relevant document metadata may be duplicated in OpenSearch for filtering.
6. Canonical metadata ownership must remain clear.
7. Material conflicts must not be silently resolved.
8. LLM-derived metadata must remain distinguishable and reviewable.
9. Governance metadata remains separate from technical-processing status.
10. Missing optional metadata should not unnecessarily block ingestion.
11. Metadata changes must be evaluated according to whether they require correction, reindexing, reprocessing, or a new Document Version.
12. Metadata included in indexed records must preserve source and processing provenance.

The resulting metadata boundary is:

```text
Validated Document Information
+ System and Processing Context
→ Controlled Metadata-Enriched Document
→ Traceable Chunking, Filtering, Monitoring, and Governance
```


## 16. Chunking

Chunking transforms the normalized document into smaller retrieval units that can be embedded and indexed in OpenSearch.

The chunking boundary is:

```text
Normalized Document
→ Chunking Strategy
→ Ordered and Traceable Chunks
```

The objective is to create chunks that are:

* large enough to preserve useful context;
* small enough for accurate retrieval;
* traceable to the original document structure;
* reproducible for the same configuration.

---

### 16.1 Chunk Structure

Each Chunk should contain at least:

* `chunk_id`;
* `document_id`;
* `document_version_id`;
* `processing_run_id`;
* chunk text;
* chunk order;
* relevant heading or section path;
* source-block references;
* chunking configuration reference.

Relevant document metadata may also be copied into the Chunk for OpenSearch filtering.

The final Pydantic model will be defined during implementation.

---

### 16.2 Initial Chunking Strategy

The initial Compliance implementation should use one simple approved strategy.

The preferred starting direction is:

```text
Heading-aware recursive chunking
```

This means:

1. preserve document sections and headings where possible;
2. split large sections into smaller chunks;
3. avoid splitting short sections unnecessarily;
4. use a configurable overlap where useful.

The exact strategy, tokenizer, chunk size, and overlap remain open technical decisions.

The MVP does not need:

* arbitrary chunking plugins;
* multiple active chunking strategies;
* semantic chunking using an LLM;
* agent-selected chunking;
* dynamic chunk size per query.

Additional strategies should be introduced only for retrieval experiments with measurable value.

---

### 16.3 Structural Context

Chunks should preserve useful context such as:

* document title;
* section title;
* heading hierarchy;
* article or subsection identifier;
* list or table context where available.

A Chunk should not contain isolated text that becomes unclear without its parent heading.

Where appropriate, heading text may be included in the embedding input even when it is stored separately as metadata.

---

### 16.4 Chunk Size and Overlap

The following parameters should be configurable:

```text
chunk_size
chunk_overlap
minimum_chunk_size
```

The configuration should use the tokenizer associated with the selected embedding model where practical.

Chunk size should not be selected only by intuition.

Different values may later be compared using:

* Precision@10;
* Recall@10;
* nDCG@10;
* retrieval latency;
* average retrieved-context size.

The reference does not define the final values.

---

### 16.5 Chunk Identity and Reproducibility

Chunk generation must be deterministic for the same:

* Document Version;
* normalized content;
* chunking configuration;
* chunker version.

Stable Chunk identifiers are required so that retries do not create duplicate OpenSearch records.

A different chunking configuration creates a new Processing Run and a new technical representation.

It does not create a new Document Version.

---

### 16.6 Special Content

Lists and numbered compliance sections should remain together where practical.

Tables may be:

* kept as one chunk when small;
* split into controlled row groups when large;
* represented with their title and column context.

The initial implementation does not need advanced table-aware or semantic chunking.

Unsupported or unusually large structures may produce a warning and use a documented fallback strategy.

---

### 16.7 Chunk Quality Checks

Chunking should verify that:

* at least one usable Chunk was created;
* no required source content was silently lost;
* chunk order is valid;
* required provenance fields are present;
* chunks do not exceed the configured maximum;
* empty or whitespace-only chunks are removed;
* duplicate Chunk identifiers are not produced.

Large differences between normalized-text volume and total chunk-text volume should be visible during processing verification.

---

### 16.8 Failure Behaviour

Chunking fails when:

* the Normalized Document is invalid;
* no usable chunks can be produced;
* required provenance is missing;
* the chunking configuration is invalid;
* generated chunks violate the expected contract.

When chunking fails:

* embedding and indexing do not begin;
* the Processing Run becomes `FAILED`;
* the failure is visible through Data Monitoring.

Detailed retry behaviour and acceptance thresholds belong in the implementation Spec and Definition of Done.

---

### 16.9 Configuration Boundary

The initial configurable values may include:

* chunking strategy;
* chunk size;
* overlap;
* minimum chunk size;
* tokenizer;
* heading inclusion;
* table-handling option.

Only approved strategies should be selectable.

The initial project does not require a generic dynamic chunking framework.

---

### 16.10 Core Chunking Rules

1. Chunking operates on the Normalized Document.
2. Useful headings and section context should be preserved.
3. Every Chunk remains traceable to its source and Processing Run.
4. Chunk generation should be deterministic.
5. Different chunking settings create a new Processing Run.
6. Empty and invalid chunks are not embedded or indexed.
7. Chunking parameters are evaluated through retrieval metrics.
8. Detailed implementation rules belong in the relevant Spec and DoD.

The resulting boundary is:

```text
Normalized Document
→ Controlled Structural Splitting
→ Traceable Retrieval Chunks
→ Embedding Generation
```

## 17. Embedding Generation

Embedding Generation transforms retrieval Chunks into vector representations that can be indexed and searched in OpenSearch.

The embedding boundary is:

```text
Traceable Chunks
→ Embedding Model
→ Embedded Chunks
```

The objective is to produce consistent vectors while preserving the relationship between each vector, its Chunk, and the configuration that generated it.

---

### 17.1 Embedding Input

The embedding input is based on the Chunk text and may include useful structural context such as:

* document title;
* section title;
* heading path;
* article or subsection identifier.

For example:

```text
Document Title
Section Heading
Chunk Text
```

The embedding input should preserve useful retrieval context without adding unnecessary metadata or prompt text.

The original Chunk text must remain separately available for result display and provenance.

---

### 17.2 Initial Embedding Model

The initial implementation should use one approved embedding model.

The final selection will consider:

* retrieval quality;
* supported languages;
* vector dimensions;
* model size;
* execution cost;
* latency;
* local or managed deployment;
* OpenSearch compatibility.

The MVP does not require:

* multiple embedding providers active at the same time;
* dynamic model selection per document;
* automatic model routing;
* embedding-model fine-tuning;
* a generic provider plugin framework.

Alternative models may later be evaluated through controlled Processing Runs.

---

### 17.3 Embedding Configuration

The effective configuration may include:

```text
model_name
model_version
vector_dimensions
batch_size
normalization
device_or_provider
input_prefix
```

The configuration used must be preserved with the Processing Run.

Changing the model, dimensions, or material embedding settings creates a new Processing Run and a new indexed representation.

It does not create a new Document Version.

---

### 17.4 Vector Dimensions and Index Compatibility

The generated vector dimensions must match the OpenSearch index mapping.

For example:

```text
Embedding dimensions: 768
OpenSearch vector field dimensions: 768
```

A mismatch must stop indexing rather than create an invalid or partially usable representation.

A change in vector dimensions normally requires:

* a compatible new index;
* re-embedding of the relevant Chunks;
* a new Processing Run.

Existing vectors must not be relabelled as outputs of a different model or configuration.

---

### 17.5 Batch Processing

Chunks may be embedded in batches to improve execution efficiency.

Batch processing should preserve:

* Chunk order where needed;
* Chunk-to-vector association;
* successful and failed item counts;
* traceability to the Processing Run.

A batch failure must not make it unclear which Chunks received valid embeddings.

The exact batch size, concurrency, timeout, and retry settings belong in the implementation Spec.

---

### 17.6 Embedding Quality Checks

Before indexing, the system should verify that:

* every required Chunk has one vector;
* vectors contain the expected number of dimensions;
* vectors contain valid numeric values;
* no Chunk-to-vector association is lost;
* the model and configuration identifiers are available;
* empty Chunk text was not submitted.

For the initial MVP, the expected rule is:

```text
Produced Chunks
=
Successfully Embedded Chunks
```

Partial embedding should not silently pass as successful processing.

---

### 17.7 Reproducibility

Each embedded Chunk must remain traceable to:

* Chunk identifier;
* Document Version;
* Processing Run;
* embedding model;
* model version where available;
* vector dimensions;
* effective embedding configuration.

Embedding services may not always produce perfectly identical floating-point values across all hardware or provider versions.

The system should preserve configuration and model identity sufficiently to reproduce the intended technical representation.

---

### 17.8 Failure Behaviour

Embedding Generation fails when:

* the embedding configuration is invalid;
* the model is unavailable;
* input exceeds supported model limits;
* vectors have incorrect dimensions;
* one or more required Chunks remain unembedded;
* the provider returns invalid outputs.

When embedding fails:

* indexing does not begin;
* the Processing Run becomes `FAILED`;
* the failure category and affected counts are recorded;
* controlled retry may be allowed for transient failures.

Detailed retry limits and provider-specific error handling belong in the implementation Spec and DoD.

---

### 17.9 Security and Data Handling

Chunk content may be sent to an external embedding provider only when that provider is explicitly approved.

The selected deployment must consider:

* document sensitivity;
* data-retention policies;
* provider data-usage terms;
* network security;
* credential handling.

API keys and credentials must not be stored in source code or committed configuration files.

A local or AWS-hosted embedding model may be preferred when document confidentiality requires it.

---

### 17.10 Configuration Boundary

The initial configurable values may include:

* embedding model;
* model version or deployment reference;
* vector dimensions;
* batch size;
* vector normalization;
* request timeout;
* retry limit;
* input prefix or formatting template.

Only supported and tested model configurations should be selectable.

The project does not require a generic abstraction for every possible embedding provider.

---

### 17.11 Core Embedding Rules

1. Embeddings are generated from validated and traceable Chunks.
2. Useful heading context may be included in the embedding input.
3. Every required Chunk must produce one valid vector.
4. Vector dimensions must match the target OpenSearch index.
5. Model and configuration identity must remain traceable.
6. A material embedding change creates a new Processing Run.
7. Partial embedding is not treated as success.
8. Sensitive content is sent only to approved embedding infrastructure.
9. Model comparison is performed through retrieval evaluation metrics.
10. Provider-specific details belong in the implementation Spec and DoD.

The resulting boundary is:

```text
Traceable Chunks
→ Controlled Vector Generation
→ Validated Embedded Chunks
→ OpenSearch Indexing
```



## 18. OpenSearch Indexing

OpenSearch Indexing writes validated Chunk text, embeddings, metadata, and provenance into the target OpenSearch index.

The indexing boundary is:

```text
Embedded Chunks
→ OpenSearch Indexing
→ Searchable and Traceable Records
```

The objective is to create a complete retrieval representation that supports:

* lexical search;
* vector search;
* metadata filtering;
* source inspection;
* retrieval evaluation.

---

### 18.1 Indexed Record

Each OpenSearch record represents one Chunk.

It should contain at least:

* `chunk_id`;
* `document_id`;
* `document_version_id`;
* `processing_run_id`;
* Chunk text;
* embedding vector;
* chunk order;
* heading or section context;
* relevant compliance metadata;
* governance or retrieval-eligibility fields;
* processing configuration reference.

The exact OpenSearch mapping will be defined during implementation.

---

### 18.2 Index Structure

The initial implementation should use one approved index structure for the Compliance project.

The index must support:

```text
BM25 / lexical retrieval
Vector retrieval
Metadata filters
```

The MVP does not require:

* arbitrary index schemas;
* one index per uploaded document;
* multiple vector databases;
* dynamic field creation;
* a generic index-management platform.

Indexes should represent controlled technical configurations rather than individual upload requests.

---

### 18.3 Index Compatibility

Before indexing begins, the system must confirm that the target index is compatible with the Processing Run configuration.

Important compatibility checks include:

* expected vector dimensions;
* vector similarity configuration;
* required field mappings;
* supported metadata fields;
* index availability.

For example:

```text
Embedding dimensions: 768
Target index dimensions: 768
```

A material mapping incompatibility should stop indexing and normally require a new compatible index.

Existing indexes should not be modified in ways that make historical representations ambiguous or unusable.

---

### 18.4 Stable Record Identity

OpenSearch records must use stable identifiers.

A retry of the same indexing operation should update or replace the intended record rather than create an additional duplicate.

A Chunk record identity should remain associated with:

```text
Document Version
+ Processing Run
+ Chunk Identity
```

The exact identifier algorithm belongs in the implementation Spec.

Different Processing Runs may create different representations of the same Document Version and must remain distinguishable.

---

### 18.5 Batch Indexing

Chunks may be written using OpenSearch bulk operations.

Batch indexing should track:

* expected records;
* attempted records;
* successful records;
* failed records;
* retry outcomes.

The system must inspect individual bulk-operation results.

A successful HTTP response from the bulk endpoint does not guarantee that every record was indexed successfully.

Batch size, concurrency, timeout, and retry values will be defined in the implementation Spec and DoD.

---

### 18.6 Metadata and Provenance

Indexed records must preserve enough metadata to support filtering and result inspection.

Indicative metadata includes:

* title;
* source authority;
* jurisdiction;
* document category;
* publication or effective date;
* version label;
* heading path;
* article or section identifier;
* governance status.

Every indexed Chunk must remain traceable through:

```text
OpenSearch Record
→ Chunk
→ Processing Run
→ Document Version
→ Source Artifact
```

OpenSearch may contain duplicated metadata for retrieval efficiency, but it is not the canonical owner of the source document or operational lifecycle.

---

### 18.7 Indexing Outcome

Each indexing execution, whether persisted as a separate Indexing Run entity or represented within the Processing Run, should produce an explicit outcome containing:

* Indexing Run identifier;
* target index;
* expected record count;
* successful record count;
* failed record count;
* indexing timestamp;
* Processing Run reference.

For the initial MVP, the expected rule is:

```text
Embedded Chunks
=
Successfully Indexed Records
```

Partial indexing must not silently pass as successful completion.

The Processing Run remains incomplete until the indexing result is verified in Chapter 19.

---

### 18.8 Failure and Retry Behaviour

Indexing fails when:

* the target index is unavailable;
* mappings are incompatible;
* vector dimensions are incorrect;
* required fields are missing;
* one or more mandatory records cannot be written;
* bulk-operation results contain unresolved failures.

When indexing fails:

* the Processing Run becomes `FAILED`;
* verification does not mark the representation ready;
* failure counts and a safe error summary are recorded;
* controlled retry may be allowed.

Retries must use stable record identifiers so that previously successful records are not duplicated.

Detailed cleanup and retry thresholds belong in the implementation Spec and DoD.

---

### 18.9 Index Versioning and Replacement

Changes to the following may require a new index:

* vector dimensions;
* field mappings;
* analyzer configuration;
* retrieval-relevant metadata schema;
* incompatible OpenSearch settings.

A new index should be created when changing the existing index would make rollback, comparison, or historical traceability unsafe.

A previously active index should normally remain available until the replacement representation:

* finishes indexing;
* passes verification;
* is explicitly selected for retrieval.

The exact index alias or activation strategy remains an implementation decision.

---

### 18.10 Configuration Boundary

The initial configurable values may include:

* index name or index version;
* text fields;
* vector field;
* vector dimensions;
* similarity metric;
* analyzer settings;
* batch size;
* request timeout;
* retry limit;
* refresh behaviour.

Only approved mappings and configurations should be selectable.

The project does not require a generic index-schema generator.

---

### 18.11 Core Indexing Rules

1. One OpenSearch record represents one traceable Chunk.
2. Indexed records support lexical, vector, and metadata-based retrieval.
3. Vector dimensions must match the target index mapping.
4. Stable record identifiers prevent duplicate records during retry.
5. Individual bulk-operation results must be inspected.
6. Partial indexing is not treated as success.
7. OpenSearch remains the retrieval layer, not the canonical source store.
8. Materially incompatible mapping changes normally require a new index.
9. Previous active representations remain available until replacements are verified.
10. Detailed retry, mapping, and performance criteria belong in the implementation Spec and DoD.

The resulting indexing boundary is:

```text
Validated Embedded Chunks
→ Controlled OpenSearch Writes
→ Complete Search Representation
→ Verification
```

## 19. Verification and Retrieval Publication Handoff

Data Ingest owns verification and the transition to technical readiness.

The decision to publish, activate, disable, supersede, or roll back a technically ready representation belongs to Data Monitoring and the authorized governance controls. This chapter defines the required handoff and publication invariants, not ownership of the governance decision.

The boundary is:

```text
Indexed Representation
→ Verification
→ Technically Ready
→ Retrieval Publication
→ Available to Data Query
```

Indexing success alone is not sufficient for publication.

---

### 19.1 Verification Objective

Verification should confirm that:

* the expected Chunks were created;
* required Chunks received embeddings;
* required records were indexed;
* vector dimensions match the index;
* required metadata and provenance fields exist;
* the representation can be retrieved from the intended index.

For the initial implementation, the expected relationship is:

```text
Produced Chunks
=
Embedded Chunks
=
Indexed Records
=
Verified Records
```

Partial completion must not silently pass as successful ingestion.

---

### 19.2 Verification Inputs

Verification uses information from:

* the Processing Run;
* Chunking output;
* Embedding Generation output;
* OpenSearch Indexing outcome;
* target-index configuration;
* expected record counts.

The verifier should not rely only on logs or on a successful OpenSearch HTTP response.

It must use the recorded processing state and the actual indexed representation.

---

### 19.3 Basic Verification Checks

Initial checks should include:

* target index exists and is accessible;
* required mappings are compatible;
* expected and indexed counts match;
* records contain stable identifiers;
* required provenance fields are present;
* embedding vectors have the expected dimensions;
* sample records can be retrieved by identifier or basic search;
* no unresolved indexing failures remain.

Advanced retrieval-quality evaluation does not belong to this stage.

Metrics such as Precision@10, Recall@10, and nDCG@10 belong to Data Query and Evaluation.

---

### 19.4 Verification Outcome

Verification produces one of two primary outcomes:

```text
SUCCEEDED
FAILED
```

A successful outcome should record:

* Processing Run;
* target index;
* verified record count;
* verification timestamp;
* verification configuration or version;
* warnings where applicable.

A failed outcome should record:

* failed check;
* safe failure summary;
* expected and actual values where useful;
* whether retry or reprocessing may resolve the issue.

---

### 19.5 Technical Readiness

When verification succeeds, the representation may be marked:

```text
TECHNICALLY_READY
```

Technical readiness means that the representation:

* was created from a registered Document Version;
* is complete according to the processing contract;
* is compatible with the target index;
* preserves required provenance;
* can be used technically by the retrieval layer.

Technical readiness does not mean that the source has been legally reviewed or approved.

---

### 19.6 Retrieval Publication

Retrieval Publication determines whether a technically ready representation is included in the normal Data Query path.

Publication may depend on:

* successful Processing Run;
* successful verification;
* permitted Document Version governance status;
* selected active index or index alias;
* representation not being disabled or superseded.

The core rule is:

```text
Technically Ready
+
Governance Permitted
+
Selected Retrieval Target
=
Published for Normal Retrieval
```

Because the system is internally operated and documents are updated infrequently, publication may initially be a simple controlled administrative action.

A complex approval workflow is not required for the MVP.

---

### 19.7 Replacement and Rollback

When a new Processing Run creates a replacement representation, the existing published representation should remain available until the new one:

* completes processing;
* passes verification;
* is explicitly published.

Publication should avoid a period where the retrieval system unintentionally contains:

* no active representation;
* both old and new representations without filtering;
* an incomplete replacement.

The exact mechanism may use:

* an OpenSearch alias;
* an active-index configuration;
* governance filters;
* or another simple controlled approach.

This decision belongs in the implementation Spec.

---

### 19.8 Failure Behaviour

If verification fails:

* the Processing Run becomes `FAILED`;
* the representation is not technically ready;
* it is not published for normal retrieval;
* the previous published representation remains unaffected where possible;
* the failure is visible through Data Monitoring.

A failed representation may be retried, cleaned up, or replaced through a new Processing Run.

Detailed cleanup procedures belong in the implementation Spec and DoD.

---

### 19.9 Monitoring and Traceability

Data Monitoring should show:

* verification status;
* expected and verified record counts;
* target index;
* technical-readiness status;
* publication status;
* publication timestamp;
* currently active representation;
* previous or superseded representation;
* verification failure information.

Data Query should use explicit publication state rather than assuming that every record present in OpenSearch is valid for normal retrieval.

---

### 19.10 Core Verification and Publication Rules

1. Indexing completion does not automatically mean ingestion success.
2. Verification checks completeness, compatibility, and provenance.
3. Partial indexing is not treated as successful verification.
4. Retrieval-quality metrics are evaluated separately.
5. Successful verification creates technical readiness.
6. Technical readiness does not automatically create retrieval publication.
7. Only explicitly published representations enter the normal query path.
8. Previous working representations remain active until replacements are verified.
9. Failed representations do not replace published content.
10. Detailed checks, thresholds, cleanup, and activation mechanics belong in the implementation Spec and DoD.

The resulting boundary is:

```text
Complete Indexed Representation
→ Verified Technical Readiness
→ Controlled Retrieval Publication
→ Safe Data Query Availability
```



## 20. Failure Handling, Retry, and Idempotency

Failure Handling ensures that ingestion problems remain visible, controlled, and recoverable without producing incomplete or duplicated representations.

The boundary is:

```text
Processing Failure
→ Record Failure State
→ Stop Dependent Work
→ Retry or Reprocess
→ Verify Final Outcome
```

A failed or partially completed operation must not be represented as successful ingestion.

---

### 20.1 Failure Categories

Failures should be classified broadly as:

#### Input or Configuration Failures

Examples:

* invalid source file;
* unsupported format;
* missing metadata;
* incompatible vector dimensions;
* invalid processing configuration.

These normally require correction before processing can continue.

#### Processing Failures

Examples:

* parsing failure;
* invalid normalized output;
* chunking failure;
* invalid embedding output;
* verification failure.

These may require code, data, or configuration correction.

#### Transient Infrastructure Failures

Examples:

* temporary S3 failure;
* embedding service timeout;
* OpenSearch unavailability;
* network interruption;
* worker termination.

These may be suitable for controlled retry.

The exact error categories will be defined in the implementation Spec.

---

### 20.2 Failure Recording

When a mandatory stage fails, the system should record:

* Processing Run identifier;
* failed stage;
* failure category;
* safe error summary;
* timestamp;
* retry eligibility;
* relevant processing counts.

Sensitive document content, secrets, stack traces, and infrastructure credentials must not be exposed through user-facing errors.

Logs may contain additional technical details, but operational status must not depend only on logs.

---

### 20.3 Failure Behaviour

A blocking failure must:

* stop dependent stages;
* mark the Processing Run as `FAILED`;
* prevent technical readiness;
* prevent retrieval publication;
* preserve the Source Artifact;
* keep previous successful representations unaffected where possible.

Partial outputs may remain temporarily for investigation or retry, but they must not be treated as complete or active.

---

### 20.4 Retry

A retry repeats a failed operation using the same intended:

* Document Version;
* Source Artifact;
* Processing Configuration;
* target representation.

Retry is appropriate mainly for transient failures.

Examples include:

```text
Temporary OpenSearch failure
→ Retry indexing
```

```text
Embedding request timeout
→ Retry failed batch
```

Invalid input or incompatible configuration should not be retried automatically without correction.

Retry limits, delay, and backoff belong in the implementation Spec and DoD.

---

### 20.5 Reprocessing

Reprocessing creates a new Processing Run.

It is appropriate when:

* the parser changes;
* normalization changes;
* metadata is corrected;
* chunking changes;
* the embedding model changes;
* the index mapping changes;
* the previous representation must be rebuilt.

The distinction is:

```text
Same intended execution after transient failure
→ Retry

Changed technical representation
→ New Processing Run
```

A new Processing Run does not automatically create a new Document Version.

---

### 20.6 Idempotency

Idempotency ensures that repeating the same intended operation does not create uncontrolled duplicates.

The system should use stable identifiers for:

* upload requests;
* Source Artifacts;
* Processing Runs;
* Chunks;
* OpenSearch records.

Examples:

```text
Same idempotency key
+ same upload request
→ Return existing operation
```

```text
Retry indexing
+ same Chunk identifiers
→ Replace or reuse intended records
```

The same idempotency key with materially different content should be rejected as a conflict.

---

### 20.7 Partial External Operations

S3, the operational state store, embedding infrastructure, and OpenSearch do not form one atomic transaction.

The system must therefore detect states such as:

```text
Source stored
but
registration failed
```

or:

```text
Some OpenSearch records written
but
indexing stage failed
```

These states must be:

* visible;
* inactive;
* retryable or cleanable;
* reconciled before successful completion.

The MVP does not require a complex distributed-transaction mechanism.

---

### 20.8 Retry Safety

A retry must not create duplicate:

* Source Artifacts;
* Processing Runs;
* Chunks;
* vectors;
* OpenSearch records.

Where possible, a stage retry should:

* reuse valid existing output;
* repeat only failed work;
* replace incomplete output;
* preserve previous attempt history.

The exact stage-level retry strategy will be defined only where required by the implementation.

---

### 20.9 Previous Active Representation

A failed new Processing Run must not disable or replace an existing successful representation.

The expected behaviour is:

```text
Existing published representation
+
New failed Processing Run
→ Existing representation remains active
```

Replacement occurs only after the new representation passes verification and is explicitly published.

---

### 20.10 Monitoring

Data Monitoring should show:

* failed stage;
* failure category;
* safe error summary;
* retry eligibility;
* retry count;
* previous or parent Processing Run;
* partial processing counts;
* final resolution.

The internal UI may provide simple retry or reprocess actions where safe.

A complex operational recovery console is not required for the initial project.

---

### 20.11 Core Failure and Idempotency Rules

1. Mandatory-stage failure stops dependent processing.
2. Failed or partial work is not marked successful.
3. Transient failures may be retried.
4. Invalid data or configuration normally requires correction.
5. Changed processing settings require a new Processing Run.
6. Stable identifiers prevent duplicate outputs.
7. Partial external operations must remain detectable.
8. Failed replacements do not affect the previous active representation.
9. Retry details and limits belong in the implementation Spec and DoD.
10. The initial project requires simple, reliable recovery rather than a generic workflow-recovery platform.

The resulting boundary is:

```text
Controlled Failure State
→ Safe Retry or Reprocessing
→ No Duplicate Representation
→ Verified Recovery
```


## 21. Configuration, Traceability, and Observability

This chapter defines how ingestion behaviour is configured, how each Processing Run remains reproducible, and which operational information must be visible.

The objective is:

```text id="cto01"
Controlled Configuration
→ Reproducible Processing
→ Traceable Outputs
→ Simple Operational Visibility
```

The project does not require a generic configuration platform or a complex observability system.

---

### 21.1 Configuration Scope

The main ingestion parameters should be stored in approved configuration files or environment settings.

Indicative configurable areas include:

```text id="cto02"
file validation
parsing
normalization
metadata handling
chunking
embedding
OpenSearch indexing
verification
retry limits
```

Examples include:

* supported file types;
* maximum file size;
* chunk size and overlap;
* embedding model and dimensions;
* batch size;
* target index;
* retrieval-relevant metadata fields;
* retry and timeout values.

Only parameters likely to change between experiments or environments should be configurable.

Implementation details that are stable and specific to this project may remain in code.

---

### 21.2 Configuration Boundaries

Configuration should select from supported application behaviour.

It should not allow:

* arbitrary Python module loading;
* executable code from YAML;
* unrestricted parser plugins;
* arbitrary embedding providers;
* arbitrary OpenSearch mappings;
* user-controlled AWS resource names.

Infrastructure values such as:

* AWS region;
* S3 bucket;
* OpenSearch endpoint;
* log level;

should be supplied through environment or deployment configuration.

Secrets must not be stored in repository configuration files.

---

### 21.3 Processing Configuration Snapshot

Every Processing Run must remain associated with the effective configuration used during execution.

The recorded snapshot should identify the important values that affect the produced representation, such as:

* parser version;
* normalization settings;
* metadata schema version;
* chunking configuration;
* embedding model;
* vector dimensions;
* target index;
* verification configuration.

A later configuration change must not alter the historical meaning of an earlier Processing Run.

A lightweight configuration hash or version identifier may be used for comparison.

---

### 21.4 End-to-End Traceability

The system must preserve the relationship:

```text id="cto03"
Document
→ Document Version
→ Source Artifact
→ Processing Run
→ Configuration Snapshot
→ Chunk
→ Indexing Run
→ OpenSearch Record
```

This makes it possible to determine:

* which source produced a retrieved Chunk;
* which processing settings were used;
* which index contains the representation;
* whether the run completed successfully;
* whether the representation is currently published.

Traceability should rely on stable identifiers and operational records, not only on logs.

---

### 21.5 Structured Logging

Application logs should be structured and include relevant identifiers such as:

* request or correlation identifier;
* Document Version identifier;
* Processing Run identifier;
* current stage;
* target index;
* outcome;
* duration;
* failure category.

Logs should avoid storing:

* full document content;
* complete Chunk text;
* credentials;
* secrets;
* sensitive request data.

Detailed logging requirements and retention periods belong in the implementation Spec and DoD.

---

### 21.6 Processing Visibility

Data Monitoring should be able to show:

* Processing Run status;
* current or failed stage;
* start and completion time;
* configuration reference;
* produced Chunk count;
* embedded and indexed counts;
* verification result;
* target index;
* safe failure summary.

Because ingestion is infrequent and internally operated, the MVP does not require real-time dashboards or complex alerting.

A simple status page and structured logs are sufficient initially.

---

### 21.7 Basic Operational Metrics

Useful initial metrics include:

* number of uploaded documents;
* successful and failed Processing Runs;
* processing duration;
* number of generated Chunks;
* embedding duration;
* indexing duration;
* failed indexing items;
* verification failures.

AWS infrastructure metrics such as:

* ECS health;
* CPU and memory;
* OpenSearch cluster health;
* S3 errors;

should remain primarily in CloudWatch and AWS service monitoring.

The application UI should show only operational information useful for managing documents and runs.

---

### 21.8 Audit History

Important lifecycle actions should remain traceable, including:

* document upload;
* version creation;
* Processing Run creation;
* retry or reprocessing;
* verification outcome;
* retrieval publication;
* disabling or superseding a representation.

The audit history may initially be simple.

It should record:

* action;
* affected entity;
* timestamp;
* responsible user or system component;
* previous and new state where relevant.

A full compliance-grade audit platform is outside the initial scope.

---

### 21.9 Failure Visibility

When processing fails, the system should expose enough information to determine:

* which stage failed;
* the general failure category;
* whether retry is appropriate;
* whether partial outputs exist;
* whether a previous active representation remains available.

User-facing monitoring should provide a safe summary.

Detailed technical diagnostics may remain in structured logs.

---

### 21.10 Core Configuration and Observability Rules

1. Only meaningful and changeable behaviour should be configurable.
2. Configuration must not become an arbitrary plugin framework.
3. Every Processing Run preserves its effective configuration.
4. Indexed records remain traceable to source, version, run, and configuration.
5. Operational status is stored explicitly and not inferred only from logs.
6. Logs use stable identifiers and avoid document content and secrets.
7. The MVP requires simple status visibility, not a complex monitoring platform.
8. AWS infrastructure metrics remain primarily in CloudWatch.
9. Important lifecycle changes preserve a lightweight audit history.
10. Detailed thresholds, dashboards, and log-retention rules belong in the Specs and DoD.

The resulting boundary is:

```text id="cto04"
Approved Configuration
→ Traceable Processing Run
→ Observable Outcome
→ Reproducible Search Representation
```


## 22. Security, Open Decisions, and Success Criteria

This chapter summarizes the minimum security expectations, the technical decisions that remain open, and the criteria for considering the Data Ingest reference complete and implementable.

The project is an internally operated system with infrequent document ingestion.

The objective is therefore:

```text
Practical Security
→ Clear Remaining Decisions
→ Measurable Data Ingest Outcome
```

The project does not require enterprise-scale workflow, multi-tenancy, or customer-facing security complexity in the initial version.

---

### 22.1 Security Baseline

The Data Ingest implementation should follow these baseline principles:

* uploaded files are treated as untrusted input;
* only approved file types are accepted;
* upload size and metadata limits are enforced;
* original filenames do not control internal paths;
* source files are stored privately in S3;
* S3 and OpenSearch access use AWS IAM roles;
* application secrets are not stored in the repository;
* data is encrypted in transit and at rest;
* document content is not written unnecessarily to logs;
* only approved processing configurations may be selected;
* OpenSearch and internal AWS resources should not be publicly accessible.

Because ingestion is performed by the internal project team, a simple controlled authentication mechanism may be sufficient for the MVP.

The exact authentication and authorization approach will be selected during implementation.

---

### 22.2 Data and Model Security

Document content may be sent to an external embedding or LLM provider only when that provider is explicitly approved.

The decision must consider:

* document sensitivity;
* provider retention policies;
* provider data-usage terms;
* cost;
* operational simplicity.

Where confidentiality requires it, embeddings may be generated using a local or AWS-hosted model.

Credentials must be provided through:

* AWS Secrets Manager;
* environment configuration;
* IAM roles;
* or another approved secret-management mechanism.

Credentials, access keys, and tokens must not be committed to Git.

---

### 22.3 Operational Security

The initial AWS direction should follow:

```text
Public Entry Point, if required
→ Controlled FastAPI Access
→ Private S3 and OpenSearch Resources
```

The implementation should use least-privilege permissions.

For example:

* the ingestion application may write only to the required S3 prefixes;
* the processing worker may access only approved source artifacts and indexes;
* normal users should not receive direct unrestricted S3 or OpenSearch access.

Detailed IAM policies, networking, scanning, and infrastructure hardening belong in the infrastructure Spec and DoD.

---

### 22.4 Open Technical Decisions

The following decisions remain open and should be resolved before or during the relevant implementation deliverable.

#### Processing Execution

* synchronous or background ingestion;
* whether a dedicated worker is required;
* whether a queue is required;
* whether Redis remains necessary;
* whether PostgreSQL is required for operational state.

#### Parsing and Normalization

* TXT and Markdown parser implementation;
* DOCX parser library;
* table-handling policy;
* retention of parsed and normalized artifacts.

#### Chunking

* final chunking strategy;
* tokenizer;
* chunk size;
* overlap;
* heading inclusion;
* table fallback behaviour.

#### Embeddings

* embedding model;
* deployment location;
* vector dimensions;
* supported languages;
* batch size;
* vector-normalization policy.

#### OpenSearch

* dense-only or hybrid retrieval preparation;
* vector engine;
* similarity metric;
* index mapping;
* index naming and versioning;
* activation or alias strategy.

#### Metadata and Identity

* minimum required compliance metadata;
* Document identity rules;
* Document Version rules;
* duplicate-resolution policy;
* governance-status workflow.

#### Security and Deployment

* internal authentication mechanism;
* AWS network topology;
* secret-management approach;
* S3 bucket and retention configuration;
* OpenSearch sizing;
* UI technology.

These decisions should be documented only when they become necessary.

A separate ADR is appropriate only for decisions with meaningful alternatives or long-term consequences.

---

### 22.5 Data Ingest Success Criteria

The Data Ingest baseline is considered successful when the system can complete the following end-to-end flow:

```text
Upload TXT, Markdown, or DOCX
→ Validate
→ Store Source Artifact in S3
→ Register Document and Version
→ Execute Processing Run
→ Parse and Normalize
→ Create Chunks
→ Generate Embeddings
→ Index in OpenSearch
→ Verify
→ Mark Technically Ready
```

The implementation should demonstrate that:

1. supported documents can be uploaded and processed;
2. unsupported or invalid files are rejected clearly;
3. the original source remains stored in S3;
4. Document, Document Version, and Processing Run remain distinct;
5. each Processing Run preserves its effective configuration;
6. every Chunk remains traceable to its source;
7. embedding dimensions match the OpenSearch index;
8. complete indexing is verified before success;
9. failed processing does not activate incomplete content;
10. retries do not create uncontrolled duplicates;
11. processing status and failures are visible;
12. a verified representation can be used by the Data Query area.

---

### 22.6 Reference Completion Criteria

This Data Ingest reference is complete when it provides sufficient direction to create:

* intermediate implementation deliverables;
* technical Specs;
* Definition of Done criteria;
* architecture decisions where needed;
* Cursor implementation handoffs.

The reference does not need to define:

* every Python class;
* every API field;
* every retry threshold;
* every OpenSearch setting;
* every AWS resource;
* every test case.

Those details belong in the implementation deliverables.

---

### 22.7 Core Final Rules

1. Security should be proportional to an internal, low-frequency ingestion system.
2. Source files and retrieval infrastructure remain private by default.
3. Secrets and credentials are never stored in source control.
4. External model use requires explicit approval.
5. Open technical decisions are resolved when their deliverable requires them.
6. The project should not create abstractions for hypothetical future domains.
7. Success is measured through a working, traceable, and verified ingestion flow.
8. Detailed implementation criteria belong in Specs and Definition of Done.

The final Data Ingest objective is:

```text
Supported Compliance Document
→ Secure and Controlled Processing
→ Traceable Search Representation
→ Verified Readiness for Query
```













