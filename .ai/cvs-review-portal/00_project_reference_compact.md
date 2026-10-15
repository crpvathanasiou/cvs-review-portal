# CVS Review Portal — Compact Project Reference

> **LEGACY DOCUMENT.** Compact summary of the inherited compliance/OpenSearch/AWS template. **Not** the current portal specification. Reading order: [`../../README.md`](../../README.md). Current specification: [`08_portal_specification.md`](08_portal_specification.md). The note below about `00_project_reference.md` is historical only.

```text
This document is a derived compact reference for implementation and AI-assisted development.

It is not the architectural source of truth.

The canonical source of truth is:
.ai/cvs-review-portal/00_project_reference.md

If this compact reference conflicts with, omits, or ambiguously represents the canonical reference, the canonical reference prevails.
```

---

## 1. Project Purpose and Product Boundary

**CVS Review Portal** is a compliance-first system for ingesting, monitoring, searching, and evaluating regulatory and related documents (regulations, standards, internal policies, procedures, guidance).

The Compliance-first objective: create a controlled, traceable, and **measurable** knowledge base — not a naive `Document → Embedding → Vector Search → LLM Answer` pipeline. The problem is decomposed into three functional areas:

```text
Data Ingest
→ Data Monitoring
→ Data Query and Evaluation
```

**Primary MVP value:** a reliable, traceable, measurable retrieval foundation. A compliance document can be ingested, stored, processed, converted into indexed chunks, monitored, queried, and evaluated end to end.

**What the project is not** (initial scope): not an autonomous compliance decision system, not a legal advice engine, not a multi-agent application, not a generic document management platform or multi-domain SaaS, not a complete production conversational assistant, and not a compliance certification of anything.

**Retrieval support vs. legal judgment boundary:** the system locates and presents evidence with provenance. Final compliance or legal judgment remains the responsibility of a qualified human expert. Retrieved results must never be presented as legal opinions, compliance approval, or proof of compliance. Retrieval relevance ≠ legal applicability.

Detail: canonical Chapters 1–2, 4.

---

## 2. Goals, Non-Goals, and MVP Scope

### End-to-End MVP Lifecycle

```text
Upload → Validation → Source Storage → Parsing → Normalization
→ Metadata Handling → Chunking → Embedding → Indexing
→ Verification → Monitoring → Querying → Evaluation
```

### Supported Formats

TXT, Markdown, DOCX. Unsupported formats must be rejected explicitly, never partially processed. PDF/OCR/HTML/spreadsheets/media are excluded from the MVP.

### Initial Users

Primary MVP user: **AI / Search Engineer acting as Technical Operator** (combines AI/Search Engineer, System Administrator, and selected Compliance Administrator capabilities). Secondary: **Compliance User / Query User** (submits queries, inspects evidence and provenance). Future roles (Compliance Administrator, Reviewer/Domain Expert, Auditor) inform design but are not implemented as separate authorization roles in the MVP. Full RBAC is deferred; the MVP may use two practical access levels: Technical Operator and Query User.

Key role principle: **Technical User ≠ Domain Authority.** The ability to ingest/index a document does not grant authority to classify it as active, official, or authoritative.

### Core MVP Capabilities

* Controlled upload with validation (file type, size, empty file, readability, required metadata), clear rejection reasons.
* Canonical source storage in S3 before processing, with checksum and stable identifiers.
* Document / Document Version / Processing Run identity and duplicate handling (retries must not create duplicate indexed content).
* Parsing (structure-preserving where available), controlled normalization (must not silently remove legally meaningful content), metadata handling (user-supplied, file-derived, deterministic rules, or manual — fully automated extraction not required).
* At least one approved chunking strategy (candidates: fixed-size, recursive, heading-aware recursive); no plugin framework.
* One configurable embedding model; recorded model, dimensions, normalization, batch size.
* OpenSearch indexing with verification (index exists, dimensions match mapping, expected chunk count indexed, failed writes detected; not available before indexing succeeds).
* Monitoring of documents, versions, processing runs (statuses e.g. `RECEIVED … INDEXING, INDEXED, FAILED`), governance states, indexes, and Document→Version→Processing Run→Indexing Run→Index traceability.
* Query interface: natural-language query, metadata filters, ranked results with rank/scores/provenance, distinct no-result vs. failure outcomes. At least one baseline retrieval mode (BM25, vector, hybrid architecture-supported); at least two configurations comparable in evaluation.
* Versioned golden evaluation dataset; Precision@10, Recall@10, nDCG@10; evaluation runs recorded with configuration snapshot; baseline comparison (structured report is sufficient — no experiment platform).
* Three UI pages: Data Ingest, Data Monitoring, Data Query (functionality over final design; UI framework not an MVP commitment).
* Operational discipline: structured logs, health/readiness endpoints, configuration validation, non-root containers, automated tests, CloudFormation provisioning.

### Explicitly Deferred (grouped)

* **Content:** PDF/OCR, web crawling, automatic regulatory updates, automatic amendment/superseding detection, automatic source-authority determination.
* **AI:** final LLM answer generation, automatic citation validation, query rewriting/decomposition, HyDE, reranking, parent-child retrieval, knowledge graphs, agentic/multi-agent workflows, model fine-tuning.
* **Platform:** generic multi-domain RAG platform, plugin framework, arbitrary vector databases, multi-cloud, microservice decomposition, premature PostgreSQL/Redis/LangGraph (each requires a concrete justification).
* **Enterprise:** multi-tenancy, SSO/enterprise IAM, document-level access policies, DMS features (editing, approval workflows, signatures, retention/legal-hold), scale optimization for unproven workloads.

### Minimum Completion Boundary (Ch. 6.15)

MVP complete when: full vertical slice works for at least one format and TXT+MD+DOCX before final completion; source artifacts preserved in S3; documents/versions distinguishable; processing states visible; indexed chunks preserve provenance; retrieval returns inspectable ranked results; inactive content excludable; evaluation datasets executable; Precision@10/Recall@10/nDCG@10 calculated correctly; runs connected to configuration snapshots; deployable via Docker + CloudFormation; critical workflows covered by automated tests.

**Scope-control principle:** a capability enters the MVP only when it is necessary to prove or protect the end-to-end lifecycle.

Detail: canonical Chapters 3–6.

---

## 3. Functional Areas

These are workflow and responsibility boundaries, **not** microservices. The initial implementation may be a modular monolith with clearly separated modules.

* **Data Ingest** — upload/validation, source storage, document and version identification, parsing, normalization, metadata, chunking, embedding, OpenSearch indexing, processing verification. Detail: `01_data_ingest_reference.md`.
* **Data Monitoring** — visibility into documents, versions, processing runs and failures, indexing runs, indexes, configuration snapshots, governance states. Application/knowledge-lifecycle monitoring only — it does not replace AWS infrastructure monitoring (CloudWatch, service consoles). Detail: `02_data_monitoring_reference.md`.
* **Data Query and Evaluation** — query submission/validation, metadata filtering, lexical/vector/hybrid retrieval, ranked-result inspection, provenance display, golden-dataset execution, Precision@K / Recall@K / nDCG@K, baseline comparison. Detail: `03_data_query_reference.md`.

**Shared responsibilities:** configuration validation, identifiers and data contracts, structured logging, security, error handling, auditability, configuration traceability, testing — implemented consistently without merging area responsibilities.

**Functional boundary principle:** each area has clear inputs, outputs, responsibilities, and failure states; cross-area dependencies use explicit contracts, not internal implementation access.

Detail: canonical Chapters 7–8 (Chapter 8 lists use cases UC-01…UC-15).

---

## 4. System Context and Logical Architecture

### Application Boundary

```text
Users
  ▼
CVS Review Portal Application (Ingest | Monitoring | Query and Evaluation)
  ├── AWS S3 (canonical + retained artifacts)
  ├── OpenSearch (serving/retrieval layer)
  └── Optional Operational State Store (PostgreSQL likely)
```

Inside the boundary: upload/validation, document identity and version management, parsing/normalization, metadata, chunking, embedding, indexing, monitoring, retrieval, result inspection, evaluation, configuration traceability.

### Responsibilities (Logical Components, Ch. 10)

* **UI** — three pages (Ingest, Monitoring, Query); communicates only through API contracts; must not access S3, OpenSearch, or the state store directly; owns no authoritative state.
* **Application API (FastAPI)** — validation, authorization, routing, stable response contracts, domain-error translation.
* **Processing** — Upload/Validation component, Document Registry, Artifact Storage component (hides S3), Processing Orchestrator (deterministic stage execution; LangGraph not required), Parsers (TXT/MD/DOCX → common contract), Normalization, Metadata, Chunking, Embedding, Index Management, Indexing (batch writes, partial-failure detection, count verification).
* **Retrieval/Evaluation** — Query Processing, Retrieval component (excludes inactive content; distinguishes failure from empty result), Result Assembly (stable contracts; no raw OpenSearch structures leaking to UI), Evaluation Dataset component, Evaluation Engine (independently testable metrics), Baseline Comparison.
* **Cross-cutting** — Governance component (state transitions), Configuration component (validation + immutable snapshots), Operational State component (state must survive restarts; not memory-only), Observability component.

### Deployment Direction

Modular monolith; optional Processing Worker boundary. Likely mapping: FastAPI app (API, upload, monitoring, query, evaluation APIs) + Processing Worker (orchestrator, parsers, normalization, metadata, chunking, embeddings, indexing) sharing the same codebase and container image with different startup commands. This is a likely direction, not a final commitment.

### External AWS Systems

S3 (durable artifact layer; not a query interface), OpenSearch (derived serving layer; rebuildable), optional operational state store (PostgreSQL likely, not confirmed mandatory), embedding model (in-container, external service, or separate inference component — open), CloudWatch etc. No MVP integrations with external regulatory sites, DMS, identity providers, or legal databases.

### Infrastructure-Monitoring Boundary

Application monitoring (documents, versions, runs, indexes, configuration, retrieval/evaluation results) lives in CVS Review Portal. Infrastructure monitoring (ECS task health, CPU/memory, cluster health, restarts, alerts) stays in CloudWatch/AWS consoles. Neither replaces the other.

### Trust Boundaries

```text
User Input → Application Validation
Application → AWS Services
Source Artifact → Derived Processing Output
Operational Metadata → Search Index
Retrieved Result → Human Interpretation
```

Each boundary requires validation, authorization, logging, and traceability. The system does not own source legal authority, unreviewed metadata correctness, or final legal/compliance decisions.

Detail: canonical Chapters 9–10.

---

## 5. Core Domain Entities

Conceptual boundaries — not final tables, Pydantic models, mappings, or API schemas (Ch. 11).

| Entity | Purpose | Key relationships | Distinction that must not be lost |
| --- | --- | --- | --- |
| **Document** | Logical compliance source (e.g. EU AI Act, internal policy) | Has many Document Versions; current active-version reference | Not searchable content itself; identity independent of any file |
| **Document Version** | Specific edition / amendment state / uploaded source revision | Belongs to Document; has Source Artifact, Processing Runs, governance status (`ACTIVE`, `SUPERSEDED`, `DISABLED`, `DELETED`) | Reprocessing does not create a new version; a new Processing Run ≠ new Document Version |
| **Source Artifact** | Original file stored in S3 (filename, media type, size, checksum, S3 key) | Belongs to a Document Version | Canonical input; must remain independent of indexes and derived outputs |
| **Processing Run** | One execution of the processing pipeline for a Document Version (statuses: `PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED`) | References Document Version, Configuration Snapshot, target index; produces Chunks and an Indexing Run | Processing success ≠ content active for retrieval |
| **Processing Stage** (Stage Execution) | State of one stage (`VALIDATION, STORAGE, PARSING, NORMALIZATION, METADATA_HANDLING, CHUNKING, EMBEDDING, INDEXING, VERIFICATION`) with attempt number, error category | Belongs to Processing Run | Enables stage-level retries and diagnosis; may be simplified into the Run initially |
| **Chunk** | Traceable retrieval unit (text, section/heading, sequence, checksum, chunking config) | References Document, Document Version, Processing Run | Chunk identity distinguishes logical source content from a specific processed representation; new chunking config → new chunk IDs, not a new version |
| **Index Record** | Application-level view of an OpenSearch index (logical/physical name, alias, mapping version, embedding+chunking config, counts; lifecycle `BUILDING/READY/ACTIVE/INACTIVE/FAILED/DEPRECATED`) | Registered in the application; may contain many Documents/Versions | The application owns the index's meaning and lifecycle; OpenSearch owns only the physical index |
| **Indexing Run** | One controlled attempt to write chunks to an index (expected/successful/failed counts, verification status) | References Processing Run and Index Record | Separates processing success from search-index publication; version not retrievable until verification succeeds |
| **Configuration Snapshot** | Immutable effective configuration used by a run (parser, chunking, embedding, mapping, retrieval, evaluation settings, checksum, app version) | Referenced by Processing/Indexing/Retrieval/Evaluation Runs | Current configuration ≠ historical run configuration; historical runs never depend on mutable files |
| **Query Request** | Validated user input (text, filters, top-k, mode, target index) | Produces Retrieval Runs | Raw user request vs. normalized retrieval representation stay distinguishable |
| **Retrieval Run** | One execution of a query against a specific index + configuration (status, latency, result count) | References Query Request, Index Record, Configuration Snapshot | Same query may yield multiple Retrieval Runs across configs; technical success ≠ relevance |
| **Search Result** | One ranked Chunk from a Retrieval Run (rank, lexical/vector/fused scores, provenance) | References Chunk and its Document Version | Derived output, not a canonical record |
| **Evaluation Dataset** | Versioned golden collection of queries + judgments (statuses `DRAFT/REVIEWED/APPROVED/ARCHIVED`) | Contains Evaluation Queries and Relevance Judgments | Metric results are only comparable when dataset version is known; dataset change → new version |
| **Evaluation Query** | One predefined realistic information need (category, difficulty, no-answer designation) | Belongs to Evaluation Dataset | Should reflect a real user need, not source wording |
| **Relevance Judgment** | Grades relevance of a target (`DOCUMENT/DOCUMENT_VERSION/SECTION/CHUNK`) to an Evaluation Query (binary or graded 0–3) | Belongs to Evaluation Query | Semantic similarity alone ≠ relevance; granularity must be consistent within a design |
| **Evaluation Run** | One execution of a dataset against an index + configuration (query/failed-query counts, aggregate metrics) | References dataset version, Index Record, Configuration Snapshot | Must remain connected to the exact dataset AND exact configuration |
| **Metric Result** | Calculated value (metric name `PRECISION/RECALL/NDCG`, K value, aggregate/query-level, calculation version) | Belongs to Evaluation Run | Meaningless without dataset version, corpus, index, config, and metric-implementation version |
| **Governance Event** | Change to usability/authority state of a Document Version (previous state, new state, actor, reason) | References Document Version | Governance history is required context; the current status alone is insufficient |
| **Audit Event** | Significant user or system action (actor, action, entity, previous/new state, outcome, correlation ID) | May reference any entity | Audit records ≠ debug logs; different retention and integrity requirements |

Status-model note:

The canonical reference currently contains different indicative
vocabularies for high-level ingestion lifecycle state, Processing Run
state, and Processing Stage state.

These must not be merged directly into one enum.

The final run, stage, and document-processing status models remain an
open technical decision.

Governance-state note:

ACTIVE, SUPERSEDED, DISABLED, and DELETED are the current core states.
DRAFT appears as an indicative possible pre-activation state in the
canonical reference. The final governance state model remains open.

**Entity identity principles:** stable identifiers not derived solely from filenames, titles, row numbers, OpenSearch IDs, or S3 paths. Checksums support duplicate detection but do not replace explicit identifiers.

**Versioning must stay separate:** Document Version ≠ Processing Configuration Version ≠ Index Version ≠ Evaluation Dataset Version ≠ Application Version — never one generic version field.

**Canonical vs. derived:** canonical = Document, Document Version, Source Artifact, confirmed governance metadata (also approved datasets/judgments and run history). Derived = parsed/normalized output, Chunk, Embedding, index content, Search Result, Metric Result. Derived data may be regenerated; canonical identity and governance history must survive independently.

**Minimum likely persistent MVP set:** Document, Document Version, Source Artifact, Processing Run, Chunk or Chunk Manifest, Index Record, Indexing Run, Configuration Snapshot, Evaluation Dataset, Evaluation Run. Stage Execution, Governance Event, Audit Event, and Metric Result records may use simplified representations initially.

Detail: canonical Chapter 11.

---

## 6. Core Lifecycles

### 6.1 Document Lifecycle (Ch. 12)

```text
Upload → Validate → Store Source Artifact → Register Document and Version
→ Process → Index → Verify → Activate for Retrieval → Monitor
→ Reprocess or Supersede → Disable or Delete
```

* **Upload/validation:** file type, size, non-empty, readability, required metadata, checksum, duplicate detection. Failed validation stops the lifecycle before the file counts as ingested.
* **Canonical storage:** S3 storage confirmed before downstream processing; the original artifact is the canonical processing input and is never replaced by derived content.
* **Version registration:** a new Document Version is created when source content or authoritative edition changes; reprocessing with different technical configuration does not create a new version.
* **Processing:** each execution creates a Processing Run (stages `VALIDATION → PARSING → NORMALIZATION → METADATA_HANDLING → CHUNKING → EMBEDDING → INDEXING → VERIFICATION`). Parsing failure fails the run. Normalization must not silently remove meaningful content. Partial embedding batches are not complete unless failures are identified and recovered.
* **Indexing + verification:** record expected/actual counts; verify chunk counts, required metadata fields, vector-dimension compatibility, absence of failed bulk writes, retrievability. Only after verification may the run succeed.
* **Activation:** retrieval availability = Technical Readiness **+** Governance Status. Indexed and verified content may still await activation, be superseded, or be disabled.
* **Superseding:** newer version becomes active; previous version marked `SUPERSEDED` (preserving previous/replacement version, timestamp, actor, reason). No immediate deletion required.
* **Disabling:** reversible exclusion from retrieval without deleting the canonical artifact.
* **Reprocessing:** new Processing Run for the existing version → new derived artifacts → new/updated index representation → verification → controlled activation. The prior successful representation stays available until the replacement is verified. Reindexing follows: build new index → verify → compare → switch alias/active reference → retain/retire previous. Exact alias/migration strategy is open.
* **Deletion boundary:** removal from retrieval ≠ removal from OpenSearch ≠ removal of derived artifacts ≠ removal of canonical source ≠ removal of operational metadata. These never occur automatically together; MVP may implement logical deletion/disablement; permanent deletion requires a controlled process.
* **Monitoring must distinguish:** `Uploaded / Processed / Indexed / Verified / Active` — never used interchangeably.
* Lifecycle invariants (Ch. 12.30): version requires document; run requires version; chunk requires run+version; indexing run not successful with failed required writes; not retrievable before verification; superseded/disabled excluded from normal retrieval; reprocessing never modifies the canonical artifact; config changes never create false source versions; deleting an index never deletes the source; every retrieved chunk traceable to its source version.

### 6.2 Query Lifecycle (Ch. 13)

```text
Submit Query → Validate Input → Resolve Retrieval Configuration → Normalize Query
→ Validate Metadata Filters → Select Target Index → Generate Query Representation
→ Retrieve Candidates → Rank or Fuse → Apply Result Rules
→ Assemble Provenance → Return Inspectable Results
```

* **Validation:** non-empty text, length limit, supported mode/filters, valid top-k, available index, compatible embedding config, permitted governance scope. Invalid queries return a clear error — never a misleading empty result.
* **Configuration resolution:** every Retrieval Run uses an explicit validated configuration captured as/linked to an immutable Configuration Snapshot; no undocumented runtime defaults.
* **Index selection:** via active-index reference, alias, explicit operator selection, or evaluation configuration; verified as registered, ready, compatible, permitted. Compliance queries use the active approved index; engineers may query experimental indexes explicitly.
* **Filtering:** validated filters (jurisdiction, authority, type, title, governance status, dates, version). Distinguish unsupported filter vs. invalid value vs. valid filter with zero candidates. Normal retrieval excludes disabled/deleted (and superseded, for current-only retrieval) content — enforced by backend, not UI.
* **Retrieval modes:** lexical BM25 (exact terms, article numbers, defined phrases), vector (paraphrase/semantic; similarity ≠ legal relevance), hybrid (RRF, weighted combination, or another approved method — recorded in configuration; hybrid superiority must be proven by evaluation, not assumed). Query/document embeddings must be compatible (model, dimensions, normalization); no silent embedding-model fallback.
* **Ranking/assembly:** candidate count may exceed top-k for fusion/dedup; deduplication must be deterministic and must not remove distinct evidence; stable rank ordering. Results are assembled into stable Search Result contracts (rank, chunk/document/version IDs, title, section, content, metadata, governance status, scores, source reference) — raw OpenSearch responses never leak to the UI.
* **Provenance:** every result traceable via `Search Result → Chunk → Processing Run → Document Version → Source Artifact`; Query Users may see simplified provenance, engineers the full trace.
* **Outcome distinctions (mandatory):** invalid query ≠ retrieval execution failure ≠ valid no-result ≠ weak result ≠ successful retrieval. No-result must not fabricate evidence. Weak-result detection is a heuristic; raw scores are never calibrated confidence. Retries only for transient failures — bounded, observable, safe.
* Query invariants (Ch. 13.30): valid ≠ succeeded ≠ relevant ≠ complete ≠ legally correct.

### 6.3 Evaluation Lifecycle (Ch. 14)

```text
Versioned Golden Evaluation Dataset → Evaluation Queries → Relevance Judgments
→ Controlled Retrieval Execution → Precision@10, Recall@10, nDCG@10
→ Stored Evaluation Report → Baseline Comparison
```

* **Golden dataset:** versioned collection of realistic queries (categories: exact-term, paraphrase, article lookup, obligation, jurisdiction/date/version/authority-sensitive, multi-evidence, no-answer; optional difficulty EASY/MEDIUM/HARD), judged evidence, and approval metadata. Judgment granularity (Document / Section / Chunk / source span) must match the objective; section-level or source spans are more stable across chunking experiments.
* **Relevance judgments:** binary (0/1) or graded (0–3 indicative scale) with written guidance; relevance considers authority, jurisdiction, version, dates, applicability — not just similarity. Human-created/reviewed; the retrieval system must not define its own ground truth. Human feedback proposes judgments but never silently modifies the approved dataset.
* **Controlled execution:** each Evaluation Run validates dataset+corpus, resolves configuration (immutable snapshot), executes every query, captures ranked results, compares with judgments, calculates query-level and aggregate metrics, stores a report. Failed queries are recorded — never silently excluded.
* **Metrics:** Precision@K = relevant-in-top-K / K. Recall@K = relevant-retrieved-in-top-K / total known relevant. nDCG@K = DCG@K / IDCG@K (graded, rank-discounted, 0.0–1.0). Interpret jointly; no single metric defines quality. Later candidates: MRR@10, Hit Rate@10, Coverage, latency, index size, processing cost.
* **Baseline comparison:** baseline = the accepted controlled reference (not necessarily best). Comparison reports baseline/candidate values, absolute change, improved/regressed/unchanged queries, latency changes. Aggregate improvement must not hide critical-query regressions. Valid comparison controls dataset version, corpus, active versions, judgments, metric implementation, preprocessing, filters.
* **Reproducibility:** a run is reproducible only when dataset version + corpus/document versions + target index + retrieval configuration + metric implementation + application version are all identified. Without this, the result must not become an accepted baseline.
* Guard against evaluation-data leakage (over-optimizing on one small set); dataset changes always create a new version; regression thresholds are defined only after a representative baseline exists.

---

## 7. Data and Artifact Ownership

Data categories that must never be conflated:

```text
Canonical Source Data
Operational State
Derived Artifacts
Serving Data
Evaluation Data
Observability Data
```

**OpenSearch is a derived serving layer, not the source of truth.** It is authoritative only for "what searchable representation currently exists in a specific index." Indexes are replaceable and rebuildable from canonical artifacts + configuration.

Ownership matrix (Ch. 15.43):

| Data / Artifact | Primary owner | Secondary representation |
| --- | --- | --- |
| Original source file | S3 | Operational source reference |
| Document identity / Version / approved metadata / governance state | Operational state store | OpenSearch reference/filter/serving copies |
| Parsed / normalized artifacts | S3 when retained | Processing-run reference |
| Chunk text / embedding vectors | OpenSearch (serving) | Optional S3 chunk manifest; provenance records |
| Processing Run / Indexing Run | Operational state store | Logs, artifact references, write outcomes |
| Index mapping definition | Version-controlled configuration | Deployed OpenSearch mapping |
| Configuration definition | Repository + environment configuration | Immutable Configuration Snapshot |
| Golden Evaluation Dataset | S3 or versioned dataset repository | Operational registration |
| Evaluation Run summary | Operational state store | Detailed S3 report |
| Logs and runtime metrics | CloudWatch / observability platform | Selected application summaries |
| Audit events | Durable append-oriented store (operational DB initially; S3 archival later) | — |
| Infrastructure definition | CloudFormation | Deployed AWS resources |

Key rules (Ch. 15.1, 15.45):

* Every important data object has one authoritative owner; derived data traceable to canonical input.
* Operational state must survive restarts; **logs are never the only source of lifecycle state**; UI state is never authoritative.
* Every Document Version references a canonical Source Artifact; the source file must not exist only in OpenSearch; every indexed Chunk references a Document Version and Processing Run.
* Historical runs reference immutable Configuration Snapshots; evaluation results reference dataset version + target index.
* Deletion in one store does not imply deletion in others; deleting an index never deletes the canonical source; rebuilding an index must be possible from retained source + configuration.
* S3, the state store, and OpenSearch share no native transaction — consistency is managed through controlled state transitions and reconciliation (orphaned data detectable, cleanup conservative, canonical data never auto-deleted).
* Derived/unconfirmed metadata must not silently overwrite confirmed metadata.
* Retention differs per category (long-term: canonical artifacts, governance history, approved datasets, baselines; configurable: derived artifacts, inactive indexes, reports, query history; short: temp files, debug logs). Full query text is sensitive — its storage/logging/redaction must follow an explicit policy.

Detail: canonical Chapter 15.

---

## 8. Configuration Boundary

Principle: *Configure parameters expected to change within the Compliance project. Implement structural behaviour explicitly in code.* Configuration provides controlled flexibility; it must not bypass validation, lifecycle rules, traceability, or security.

### Configurable (main MVP categories, Ch. 16.39)

Supported file types; max file size; S3 resource references; parser selection among supported implementations; normalization settings; metadata field rules; chunking strategy / chunk size / overlap; embedding model / vector dimensions / batch size / normalization; OpenSearch endpoint, index name, alias, vector field, similarity metric; retrieval mode / top-k / candidate count / filters / fusion parameters (e.g. RRF constant); evaluation dataset, K values, metrics, baseline; logging level; environment endpoints; retry/timeout values within code-enforced safe bounds.

### Remains in code (Ch. 16.30)

Lifecycle invariants, entity relationships, authorization checks, state-transition validation, metric formulas, checksum verification, failure classification, provenance requirements, mandatory security controls, API contract validation, supported strategy implementations. Configuration selects approved behaviour; it never redefines correctness rules.

### Must not be configurable initially (Ch. 16.31)

Arbitrary Python import paths, runtime plugin loading, arbitrary workflow graphs, arbitrary vector DBs or clouds, custom executable scripts, user-defined metric formulas or lifecycle states, bypassing governance filters, disabling provenance, mandatory file validation, or required security controls (including mandatory log redaction).

### Sources and Precedence (Ch. 16.18)

```text
Application Defaults
→ Version-Controlled Configuration File
→ Environment-Specific Configuration
→ Environment Variables
→ Explicit Approved Runtime Override
```

Deterministic, documented; effective configuration validated after resolution. Environment configuration (region, buckets, endpoints — via env vars, ECS task definitions, CloudFormation parameters, Parameter Store, Secrets Manager) stays separate from experiment configuration.

### Validation and Snapshots

Validation detects missing values, unsupported options, invalid ranges, incompatible combinations (especially vector-dimension mismatches), unsafe retry/timeout values. Invalid configuration fails clearly — no silent defaults. Every significant Processing/Indexing/evaluation-relevant Retrieval/Evaluation Run references an **immutable Configuration Snapshot** (effective validated config + checksum + app version). Filenames are labels, not configuration identity. Distinguish Configuration File Version ≠ Configuration Snapshot ≠ Application Version ≠ Index Mapping Version.

### Change Consequences (Ch. 16.24)

* May apply without reindexing: query top-k, candidate count, selected filters, certain fusion parameters, metric selection.
* Usually requires reprocessing or reindexing: parser behaviour, normalization rules, chunk size/overlap, embedding model, vector dimensions, index mapping, analyzers. The operational consequence of a change must be explicit; an index stays associated with the configuration that created it; incompatible combinations (e.g. 768-dim index with 1024-dim query vector) are rejected before execution.

### Secrets Exclusion

Secrets (credentials, API keys, tokens, encryption material) never in repository files, Docker images, committed `.env`, reports, or exposed snapshots. AWS access prefers IAM roles over static credentials; secrets injected at runtime (Secrets Manager / Parameter Store).

Detail: canonical Chapter 16.

---

## 9. Security, Observability, and Auditability

### Security Baseline (Ch. 17.57)

```text
Validated Uploads · Private S3 Storage · Encryption in Transit · Encryption at Rest
IAM Task Roles · No Static AWS Credentials · No Secrets in Source Code
Non-Root Containers · Validated API Contracts · Restricted OpenSearch Access
Safe Logging · Governance Filtering · Configuration Validation
Structured Audit-Relevant Events
```

* **Least privilege** for users, application roles, IAM roles, DB/OpenSearch permissions, pipelines. ECS Task Role limited to required app permissions; Execution Role limited to infrastructure needs (ECR pull, logs, runtime secrets).
* **Access:** MVP may use simplified authentication (restricted network, simple login, API key, authenticated proxy) in a controlled environment; production exposure requires an approved mechanism (mechanism is an open decision). Authorization separates read from write; MVP simplification: Technical Operator vs. Query User. Technical access never implies domain authority.
* **Data protection:** private S3 (block public access) and private/VPC OpenSearch; users never access OpenSearch directly — all traffic through the application layer. Encryption in transit (TLS everywhere in production) and at rest (AWS-managed keys initially; customer-managed KMS only when required).
* **Upload security:** files are untrusted input — extension/media-type/size/empty/readability checks, safe filename handling (user filenames never define unrestricted storage paths), checksum; parser resource limits (size, timeouts, archive-entry/memory limits); no macro or embedded-script execution; unsupported formats rejected.
* **Backend governance enforcement:** normal retrieval excludes `SUPERSEDED / DISABLED / DELETED`; enforced by backend retrieval logic, never only by the UI. Security controls generally must be backend-enforced.
* **Safe logging:** no uncontrolled document content, query text, vectors, credentials, personal/confidential data; redaction implemented in code and not removable through ordinary configuration. Query text storage follows an explicit sensitivity/retention policy.
* Integrity: source checksum verifiable against S3; failed authorization stops the action; state transitions controlled; deletion actions differentiated; future LLM components must treat retrieved document text as untrusted input (prompt-injection boundary). Human responsibility for legal interpretation is preserved (Ch. 17.52).

### Observability (Ch. 18)

**Observability = understanding system behaviour. Auditability = durable evidence of significant actions and state changes.** They are distinct layers with different retention and integrity requirements.

* **Structured logs** with timestamp, level, component, event, request ID, and stable domain identifiers (`document_id`, `document_version_id`, `processing_run_id`, `indexing_run_id`, `retrieval_run_id`, `evaluation_run_id`, `configuration_snapshot_id`) — not filenames or OpenSearch-internal IDs.
* **Correlation identifiers** on every request, connecting UI → API → processing → S3/embedding/OpenSearch operations; the Processing Run ID is the durable business-process reference after the request ends.
* **Health vs. readiness:** liveness = process alive (not dependent on every external service); readiness = able to serve intended traffic (config validity, state store, OpenSearch, required index, S3, embedding readiness). Dependency states: `AVAILABLE / DEGRADED / UNAVAILABLE / UNKNOWN`; partial operation permitted where safe.
* **Processing-stage visibility:** per-stage name, timestamps, duration, attempt number, status, error category; ingestion errors distinguishable (`Upload Failed / Source Storage Failed / Processing Failed / Indexing Failed / Verification Failed`). Partial bulk failures visible — never just HTTP success. Controlled error categories (`VALIDATION_ERROR … DEPENDENCY_ERROR, INTERNAL_ERROR`); warnings never hide conditions that should fail.
* Metrics: ingestion/processing/query/evaluation counters, durations, latency, no-result rate, knowledge-base counts (documents, versions, failed runs, active indexes, inconsistencies).

### Auditability

Audit-relevant state changes (minimum MVP set, Ch. 18.51): document uploaded, Document Version created, processing retried, version activated/superseded/disabled, index activated, evaluation baseline selected, permanent deletion. Audit events record actor (typed: `HUMAN_USER / SYSTEM_COMPONENT / BACKGROUND_JOB / DEPLOYMENT_PIPELINE / ADMINISTRATOR`), timestamp, action, affected entity, previous state, new state, outcome, correlation ID. Governance changes preserve previous/new state and replacement version. Audit records are append-oriented, not modifiable through ordinary workflows, retained independently from debug logs. Logged ≠ auditable; a valid no-result is never recorded as a failure; infrastructure failure stays distinguishable from retrieval-quality failure.

Detail: canonical Chapters 17–18.

---

## 10. Failure, Retry, and Idempotency

Assume failures between any two stages and across every dependency; S3, the state store, OpenSearch, and model services share no transaction.

```text
Failure Detection → Failure Classification → Retry Decision
→ Controlled Recovery → Final State Verification
```

* **Failure categories** (controlled, Ch. 19.3): `VALIDATION / AUTHENTICATION / AUTHORIZATION / CONFIGURATION / STORAGE / PARSING / NORMALIZATION / METADATA / CHUNKING / EMBEDDING / INDEXING / VERIFICATION / RETRIEVAL / EVALUATION / DEPENDENCY / CONSISTENCY / INTERNAL` — each defines retry permission, user-correction need, stop behaviour, cleanup need.
* **Retryability:** `RETRYABLE` (transient: timeouts, temporary unavailability, rate limits), `NON_RETRYABLE` (unsupported file, invalid metadata, corrupted source, dimension mismatch, invalid mapping, unauthorized), `CONDITIONALLY_RETRYABLE` (after correction), `UNKNOWN` (small bounded attempts, then investigation). Severity (`WARNING/RECOVERABLE/BLOCKING/CRITICAL`) is separate from retryability.
* **Bounded retries:** bounded, observable, failure-aware, idempotent, backed off (exponential + jitter); no infinite loops, no retrying deterministic validation failures; narrowest safe retry scope (failed batch, not whole document; failed OpenSearch items, not all items). Manual retry for cases needing operator review; retry eligibility visible in monitoring; retry history never overwrites previous failure evidence; a terminal `FAILED` run never becomes `SUCCEEDED` — a retry is a new attempt/run with a clear relationship.
* **Partial failure:** partial success ≠ complete success. Record expected/successful/failed/unverified counts. Partial embedding: retry only the failed subset under identical configuration. Partial indexing: inspect item-level bulk results; MVP normally requires complete indexing. Verification failure prevents activation.
* **Unknown outcome:** a timeout does not prove failure; verify intended state (idempotency key, expected identifier, checksum, operational record) before repeating side effects.
* **Cross-store consistency:** explicit intermediate states + reconciliation (artifact without registration, registration without artifact, chunks from failed runs, Index Record without physical index…). Compensation (delete failed-run chunks, deactivate incomplete index, restore previous alias) is controlled and may preserve failed artifacts for investigation. Rollback references a previously verified state and never erases history.
* **Idempotency:** repeating the same logical request creates no unintended additional effects. Idempotency keys / logical request identifiers with request fingerprints — a key reused with materially different content is rejected. Upload idempotency distinguishes: same request repeated / same file intentionally re-uploaded / new version / different document with identical content — **Duplicate Detection ≠ Document Versioning**; checksum equality alone never defines business identity. S3 keys stable per Source Artifact; canonical artifacts never silently overwritten with different content.
* **Deterministic identifiers:** Chunk identity derived from Document Version + processing representation + sequence/source span + content checksum (scheme open); never only OpenSearch-generated IDs. Indexing uses stable IDs so retries replace/confirm rather than duplicate; write semantics (create-only / upsert / replacement) explicit.
* **Safe reprocessing / safe index replacement:**

```text
Current Verified Representation → Build Candidate → Verify Candidate
→ Compare or Approve → Activate Candidate → Retain or Retire Previous
```

A failed candidate build must never damage the active verified representation.

* **Concurrency:** uniqueness constraints, optimistic concurrency (expected-current-state checks on governance transitions), conditional writes; workers assume at-least-once delivery and verify run status/ownership before executing; poison documents stop after a bounded limit and go to manual review; dead-letter records (if a queue exists) never replace the authoritative failed run state.
* **Key invariants (Ch. 19.56, selected):** failed required stage prevents completion; duplicate uploads never create uncontrolled versions; repeated indexing never duplicates chunks; timeout ≠ confirmed failure; failed OpenSearch item writes inspected individually; canonical artifacts never deleted as automatic compensation; retrieval failure ≠ valid no-result; evaluation failures never silently alter reported metrics; Retry ≠ Safe Recovery.

Detail: canonical Chapter 19.

---

## 11. AWS Deployment Direction

Accepted/probable service direction:

```text
ECR                      → container images                  (accepted direction)
ECS Fargate API          → FastAPI application               (accepted direction)
Optional ECS Processing Worker                               (likely; introduction point open)
S3                       → canonical + retained artifacts    (accepted direction)
OpenSearch               → lexical/vector/hybrid retrieval   (accepted direction)
CloudWatch               → logs, metrics, alarms             (accepted direction)
CloudFormation           → infrastructure provisioning       (accepted direction)
Likely PostgreSQL (RDS)  → operational state                 (likely required before final MVP; not confirmed)
Likely SQS               → asynchronous ingestion            (likely; introduction point open)
Secrets Manager          → where secrets are required        (preferred for credentials)
```

* **Modular application rather than premature microservices.** API + optional worker; the same repository and container image with different commands is the likely initial approach (separate images only when dependencies/runtime genuinely differ). Multi-stage builds, non-root user, no embedded secrets, health endpoints.
* **Networking direction:** private VPC posture — public entry via **ALB (probable entry point)**, ECS tasks in private subnets, private S3/OpenSearch/database access; VPC endpoints and NAT decided by embedding/integration model. Data services not publicly exposed. IAM: Execution Role vs. Task Role vs. Deployment Role (CI/CD via GitHub Actions + OIDC; no persistent access keys).
* **OpenSearch as shared managed service** — used by API and worker; never embedded per container; never directly accessed by users; rebuildable from canonical artifacts + configuration. Separate physical indexes for baseline/candidate/experiments; alias (e.g. `cvs-review-portal-active`) likely for safe promotion/rollback (strategy open).
* **Application deployment ≠ index activation.** Index promotion (build candidate → verify → evaluate → approve → switch alias → retain previous for rollback) is a data-lifecycle action. Application rollback (previous image/task definition) does not automatically change the active index, governance state, baselines, or sources.
* **Ingestion mode:** earliest vertical slice may be synchronous; production-oriented ingestion likely asynchronous (upload → validate → store → create Processing Run → submit background work → return accepted; user monitors progress). Queue messages carry identifiers, not content, and are never the source of truth for processing state; workers tolerate duplicate delivery.
* **Environment separation:** Local / Development / Production(-like Test) with separate buckets, indexes/domains, databases, IAM roles, secrets; local defaults never connect silently to production. Local development via Docker Compose (local OpenSearch, optional local PostgreSQL, queue emulator or synchronous mode, S3 emulator where selected) preserving the same logical contracts.
* **Minimum first deployment:** ECR + ECS Fargate FastAPI + S3 + OpenSearch + CloudWatch Logs + CloudFormation + IAM. The first slice may postpone SQS, the separate worker, PostgreSQL, and full authentication — but container memory must not remain the final operational-state solution. **Probable final MVP:** adds worker, ALB, RDS PostgreSQL, SQS, Secrets Manager. Redis and LangGraph remain excluded without a concrete requirement.
* **Decision status labels:** PostgreSQL — *likely required, introduction point open*. SQS + worker separation — *likely, introduction point open*. Authentication mechanism — *open* (simplified acceptable only in controlled environments). UI hosting — *open* (FastAPI-served vs. S3+CloudFront vs. ECS container). Embedding execution model, OpenSearch sizing/engine, VPC topology, alias strategy, CloudFront — *open* (Ch. 20.64).
* Deployments traceable (commit SHA, image digest, stack version); deployment success includes application-readiness verification, not just CloudFormation success. DR boundary: reconstructable from IaC + images + canonical artifacts + backups + configuration history; no multi-region requirement.

Detail: canonical Chapter 20.

---

## 12. Open Technical Decisions

Statuses used by the canonical reference: `OPEN / UNDER_INVESTIGATION / PROVISIONAL / ACCEPTED / DEFERRED / REJECTED`. The canonical register (Ch. 21.25) tracks TD-001…TD-010; additional IDs below (CD-*) are compact-reference labels for canonical Ch. 21 items. **Nothing below is resolved here.**

CD-* identifiers are navigation-only labels inside this derived document.
They must not be used as canonical ADR, issue, implementation, or
acceptance-criteria identifiers.

Provisional current direction (Ch. 21.22): modular monolith + optional worker; FastAPI; deterministic pipeline; S3 source storage; PostgreSQL likely; SQS + ECS worker when async ingestion arrives; OpenSearch BM25/vector/hybrid comparison; validated YAML + environment configuration; versioned golden dataset with P@10/R@10/nDCG@10; ECR/ECS/S3/OpenSearch/CloudWatch/CloudFormation deployment; Redis not required; LangGraph deferred.

### Application Architecture

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| CD-A1 | Internal module boundaries of the modular monolith | Open (direction: modular monolith) | Dependency rules, testability, future copyability | First implementation structure |
| CD-A2 | When processing moves from API into a separate worker (sync → background task → worker → SQS+worker) | Open | Timeouts, retries, monitoring, scaling | Async ingestion deliverable |
| CD-A3 | Shared container image vs. separate images | Open (preference: shared image, different commands) | Build/deploy complexity, image size | First deployment |
| CD-A4 | LangGraph usage | Deferred | Not justified by deterministic pipeline | Only if conditional/HITL workflows appear |

### Persistence / Operational State

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| TD-001 | Operational state store (PostgreSQL requirement + introduction point) | Open (PostgreSQL likely required before final MVP) | Durable lifecycle state, monitoring, consistency | Monitoring deliverable |
| CD-P1 | Which entities become persistent relational records | Open | Avoid over-persisting before requirements known | Data-model design |
| CD-P2 | Processing-stage persistence model (records / fields in Run / events / hybrid) | Open | Retries, monitoring, diagnosis | Processing deliverable |
| CD-P3 | Audit-event persistence location | Open (formal tamper-evident storage may be deferred) | Traceability of state changes | Governance/audit deliverable |
| CD-P4 | Idempotency store | Open (preference: PostgreSQL + constraints) | Duplicate-request safety | Async/retry design |

### Ingestion

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| CD-I1 | Upload transport (API vs. pre-signed S3 vs. both) | Open (direct API simpler initially) | File size limits, scaling | Data Ingest deliverable |
| CD-I2 | Required upload metadata | Open | Blocks upload UX and validation | Data Ingest deliverable |
| CD-I3 | Document identity rules (new Document vs. new Version vs. reprocess) | Open | Governance, duplicates, retrieval history | Data Ingest deliverable |
| CD-I4 | Duplicate-detection policy | Open (checksum alone insufficient) | Idempotency vs. versioning boundary | Data Ingest deliverable |
| CD-I5 | S3 object-key convention | Open | Traceability, safe reprocessing, deletion | Data Ingest deliverable |
| CD-I6 | Retained intermediate artifacts | Open | Reproducibility vs. cost | Processing deliverable |

### Parsing / Normalization

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| CD-N1 | TXT encoding detection/fallback | Open | Rejection vs. replacement behaviour | Parser deliverable |
| CD-N2 | Markdown parsing approach (plain / AST / heading-aware) | Open | Structure preservation | Parser deliverable |
| TD-002 | DOCX parser (`python-docx`, Unstructured, other) | Open | Headings, lists, tables, security, weight | Data Ingest deliverable |
| CD-N3 | Table handling in DOCX | Open (ignoring tables risks losing compliance content) | Retrieval completeness | Parser deliverable |
| CD-N4 | Mandatory normalization pipeline (Unicode form, whitespace, headers) | Open (conservative until documents inspected) | Content fidelity | Processing deliverable |

### Metadata

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| CD-M1 | Fixed Compliance metadata schema (candidates: title, document_type, source_authority, source_category, jurisdiction, publication_date, effective_date, version_label, governance_status, section_heading, article_reference, applicable_role) | Open | Provenance, filtering, governance | Metadata deliverable |
| CD-M2 | Metadata-origin recording (`USER_PROVIDED / FILE_DERIVED / RULE_DERIVED / MODEL_DERIVED / REVIEWER_CONFIRMED`) | Open | Trust vs. model complexity | Metadata deliverable |
| CD-M3 | Required vs. optional fields per lifecycle gate (storage/processing/indexing/activation) | Open | Upload friction vs. quality | Metadata deliverable |
| CD-M4 | Automatic metadata extraction | Open (direction: deterministic/manual first) | Accuracy vs. effort | Metadata deliverable |
| CD-M5 | Section/article identification method | Open | Compliance retrieval quality, citations | Metadata/chunking deliverable |

### Chunking

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| TD-003 | Initial chunking strategy (fixed / recursive / heading-aware recursive) | Open (heading-aware recursive a likely start; must be validated) | Retrieval quality baseline | Chunking deliverable |
| CD-C1 | Measurement unit (chars/words/tokens/blocks) | Open | Model limits, reproducibility | Chunking deliverable |
| CD-C2 | Baseline chunk size and overlap | Open (from corpus + evaluation, not defaults) | Retrieval quality | Chunking deliverable |
| CD-C3 | Heading context (in chunk / metadata / hierarchy / prefix) | Open | Retrieval vs. duplication | Chunking deliverable |
| CD-C4 | Small-section handling | Open (discarding risks losing provisions) | Legal completeness | Chunking deliverable |
| CD-C5 | Deterministic Chunk identifier scheme | Open | Idempotency, provenance, retries | Chunking/indexing deliverable |
| CD-C6 | Parent-child retrieval | Deferred | Wait for baseline evaluation | Post-baseline |

### Embeddings

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| TD-004 | Embedding model | Open | Quality, dimensions, licensing, cost, feasibility | Embedding deliverable |
| CD-E1 | Multilingual support | Open (MVP appears English-first; no assumption) | Model choice | Embedding deliverable |
| CD-E2 | Vector dimensions | Open (constraint of model + mapping, not preference) | Index compatibility | Embedding deliverable |
| CD-E3 | Embedding execution model (in-container / external API / dedicated inference / managed AWS) | Open | Security, memory, cost, throughput | Embedding + AWS deliverable |
| CD-E4 | Model revision pinning | Open | Reproducibility | Embedding deliverable |
| CD-E5 | Query/document prefixes | Open | Model-correct usage | Embedding deliverable |
| CD-E6 | Embedding reuse rules | Open (valid only with identical chunk content + config) | Cost vs. validity | Reindexing design |

### OpenSearch / Indexing

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| TD-005 | OpenSearch vector configuration (engine, parameters) | Open | Recall, latency, filtering behaviour | Indexing deliverable |
| CD-O1 | Domain sizing (dev + prod-like) | Open | Cost (likely largest baseline cost) | AWS deliverable |
| CD-O2 | Similarity metric (cosine / inner product / Euclidean) | Open (must align with embedding normalization) | Correctness | Indexing deliverable |
| CD-O3 | Lexical analyzer and field strategy | Open | Exact-term/article retrieval | Indexing deliverable |
| CD-O4 | First explicit index mapping (restrict dynamic mapping) | Open | Contract stability | Indexing deliverable |
| CD-O5 | Index naming convention | Open | Environment/experiment separation | Indexing deliverable |
| CD-O6 | Alias strategy | Open (likely valuable before final MVP) | Safe promotion/rollback | Index-lifecycle design |
| CD-O7 | Index granularity | Open (direction: one shared index per controlled representation/experiment) | Governance, experiments | Indexing deliverable |
| CD-O8 | Bulk batch size + retry behaviour | Open | Partial-failure handling | Indexing deliverable |
| CD-O9 | Verification rules (counts, fields, sample retrieval, mapping) | Open | Activation gate | Indexing deliverable |

### Retrieval

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| TD-006 | Initial retrieval baseline (BM25 / vector / hybrid) | Open (useful sequence: separate BM25 and vector baselines first) | Everything downstream is compared against it | Data Query deliverable |
| CD-R1 | Hybrid fusion method | Open (initial preference may be RRF) | Score comparability | Retrieval deliverable |
| CD-R2 | RRF parameters / candidate counts / default top-k | Open (evaluation K=10 fixed; UI default may differ) | Recall/latency trade-off | Retrieval deliverable |
| CD-R3 | Available metadata filters in first Query UI | Open | Depends on metadata schema | Data Query deliverable |
| CD-R4 | Governance-filter enforcement + PostgreSQL↔OpenSearch synchronization | Open (must not depend on UI-provided values) | Safety-critical | Data Query deliverable |
| CD-R5 | Score display per role | Open (raw scores never labelled confidence) | User trust | UI deliverable |
| CD-R6 | Weak-result detection | Open (no thresholds before score distributions studied) | No-answer behaviour | Data Query deliverable |
| CD-R7 | Query-time deduplication strategy | Open (must not remove distinct evidence) | Result quality | Retrieval deliverable |
| CD-R8 | Reranking | Deferred until baseline evaluated | Complexity control | Post-baseline |

### Evaluation

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| TD-007 | Relevance-judgment granularity (Document/Section/span/Chunk) | Open (section or span more stable across chunking changes) | Dataset reusability | Evaluation deliverable |
| CD-V1 | Binary vs. graded relevance scale | Open (graded supports nDCG more meaningfully) | Metric meaning, annotation cost | Evaluation deliverable |
| CD-V2 | Golden dataset format (JSONL likely) and storage (Git/S3/PostgreSQL) | Open | Versioning, reproducibility | Evaluation deliverable |
| CD-V3 | Dataset size and query coverage | Open (coverage-driven, not arbitrary) | Metric reliability | Evaluation deliverable |
| CD-V4 | Corpus versioning for evaluation runs | Open | Comparison validity | Evaluation deliverable |
| CD-V5 | Metric averaging policy (failed queries, no-answer, <K results) | Open | Metric correctness | Evaluation deliverable |
| CD-V6 | No-answer expected behaviour | Open (depends on weak-result detection) | Dataset design | Evaluation deliverable |
| CD-V7 | Baseline acceptance process | Open (initially explicit Technical Operator selection) | Regression interpretation | Evaluation deliverable |
| CD-V8 | Regression thresholds | Deferred until a representative baseline exists | Avoid invented thresholds | Post-baseline |

### UI

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| TD-008 | UI framework (FastAPI templates / Streamlit / lightweight React / other) | Open | Workflow speed, API separation | UI deliverable |
| CD-U1 | Ingest page metadata fields; Monitoring navigation model; Query page default controls; Evaluation UI placement (page/section/API-CLI only); source-artifact access method (pre-signed URL / streaming / none initially) | Open | Usability of the three MVP pages | UI deliverable |

### AWS

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| CD-W1 | First AWS vertical slice composition | Open (likely: ECR, ECS Fargate API, S3, OpenSearch, CloudWatch, IAM, CloudFormation) | Foundation for everything | First AWS deliverable |
| TD-009 | SQS + worker introduction point; worker concurrency model | Open | Async processing, scaling | Async ingestion deliverable |
| CD-W2 | Embedding compute sufficiency on Fargate CPU | Open | Model feasibility | Embedding deliverable |
| CD-W3 | OpenSearch environment strategy (separate domains vs. shared non-prod vs. local) | Open (production isolation mandatory) | Cost vs. isolation | AWS deliverable |
| CD-W4 | VPC topology, NAT/VPC endpoints; CloudFormation stack boundaries; DB migration execution method | Open | Security, cost, operability | AWS deliverable |
| CD-W5 | UI hosting (FastAPI / S3+CloudFront / ECS) | Open | Deployment shape | UI + AWS deliverable |

### Security

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| TD-010 | MVP authentication mechanism (local / controlled AWS / production) | Open | Must not defer beyond exposure point | AWS exposure deliverable |
| CD-S1 | Role enforcement scope (Technical Operator + Query User vs. one role) | Open (backend boundaries ready for later separation) | Later RBAC path | Security deliverable |
| CD-S2 | Document-level authorization | Open (single-KB MVP appears not to require it) | Architecture must not block later enforcement | Security review |
| CD-S3 | Query-text retention (full/temporary/redacted/hashed/none) | Open | Privacy, audit | Security deliverable |
| CD-S4 | Malware scanning of uploads; data-classification labels; customer-managed KMS keys | Open (KMS: AWS-managed likely sufficient initially) | Exposure-dependent | Security review |

### Testing / Operations

| ID | Decision | Status | Why it matters | Required by |
| --- | --- | --- | --- | --- |
| CD-T1 | Local dependency strategy (local OpenSearch / mocks / LocalStack / testcontainers / real dev AWS — combination likely) | Open | Test fidelity | Testing setup |
| CD-T2 | Integration-test targets (real S3/OpenSearch/PostgreSQL/SQS) and end-to-end test corpus | Open | Confidence at boundaries | Testing deliverable |
| CD-T3 | Quality gates (test categories, coverage expectations, typing, Ruff, build gates) | Open (coverage % never replaces critical-path testing) | Definition of Done | Testing deliverable |
| CD-T4 | Retrieval regression in CI/CD (every PR / selected runs / scheduled / pre-release) | Open | Cost vs. protection | CI/CD deliverable |
| CD-T5 | Logging framework, metrics publication method, tracing, alert thresholds, reconciliation trigger, retention periods | Open (tracing likely unneeded initially; alerts after baseline behaviour measured; on-demand consistency check likely required) | Observability/ops baseline | Observability deliverable |

Decision dependencies (Ch. 21.19): parsing sequence (documents → parser → metadata → normalization → chunking → size/overlap); vector sequence (model → dimensions → normalization → mapping → similarity → query embedding); evaluation sequence (metadata/corpus → granularity → format → metric policy → baseline → thresholds); async sequence (duration/state → PostgreSQL → SQS → worker contract → idempotency → scaling); production-access sequence (exposure → authn → authz → network → query retention → audit).

Detail: canonical Chapter 21.

---

## 13. Project-Level Success Criteria

Success is demonstrated through working behaviour, persisted state, inspectable evidence, automated tests, evaluation results, and deployment reproducibility — never merely "containers start" or "example queries look reasonable."

MVP-complete conditions (Ch. 22):

* **End-to-end lifecycle:** a supported document completes Upload → … → Evaluation with no undocumented manual changes to S3, OpenSearch, records, or configuration; TXT, Markdown, and DOCX all supported; unsupported formats explicitly rejected.
* **Canonical source preservation:** every Document Version references an S3 Source Artifact with checksum; independent of OpenSearch; index deletion/rebuild never removes the source.
* **Version and run traceability:** Document / Document Version / Processing Run / Indexing Run / Search Index demonstrably distinct; forward (`Document → … → Index`) and reverse (`Search Result → Chunk → Processing Run → Document Version → Source Artifact`) traceability; no inference from filenames.
* **Monitoring:** explicit processing state (stage running/completed/failed, chunk counts, configuration, target index) via application interfaces — no direct DB/S3/OpenSearch inspection required; failed/partial runs never appear successful; index registry with active/candidate indexes, configurations, counts, verification status.
* **Governance-aware retrieval:** `ACTIVE/SUPERSEDED/DISABLED/DELETED` (or approved equivalent) enforced by backend; disabled/superseded excluded from normal retrieval; not bypassable by omitting a UI filter; indexing success ≠ governance approval.
* **Inspectable results:** ranked results with rank, identifiers, title, section, content, governance status, source reference, scores; stable application contracts; clear distinction of invalid query / execution failure / no-result / weak result / success.
* **Golden evaluation dataset:** versioned, traceable identity, realistic and metadata-sensitive queries incl. no-answer cases, not local-machine-only.
* **Metric correctness:** Precision@10, Recall@10, nDCG@10 correct and covered by automated tests with known expected examples; failed queries visible in reports.
* **Reproducibility:** every Evaluation Run identifies dataset version + corpus/index build + target index + retrieval configuration + metric implementation (+ app version where required); runs reference immutable Configuration Snapshots; baseline comparison shows query-level improvements and regressions.
* **Failure handling:** representative failures (unsupported file, invalid metadata, parser failure, empty chunks, embedding failure, dimension mismatch, partial bulk failure, unavailable index) handled with visible category, safe stop, protected prior content, clear retry path; repeated/retried operations create no uncontrolled side effects.
* **Security baseline:** all Ch. 17.57 controls demonstrated; production-facing environments use approved authentication; no uncontrolled sensitive-content duplication in logs/temp files/snapshots/reports.
* **Deployment reproducibility:** CloudFormation-provisioned; images in ECR traceable to source versions; no undocumented manual AWS steps; containers stateless (task replacement loses nothing durable); health ≠ readiness distinguished.
* **Automated testing:** critical-path coverage (configuration, validation, parsers, chunking, identifiers, duplicates, lifecycle transitions, dimension validation, indexing, partial writes, result contracts, governance filtering, metrics, failure/retry) prioritized over coverage percentage; Poetry/Ruff/type-checking quality gates maintained.
* **Scope control:** MVP remains Data Ingest + Data Monitoring + Data Query + Retrieval Evaluation; no deferred capability becomes an undocumented dependency.

Anti-success conditions (Ch. 22.40) include: sources existing only in OpenSearch, indistinguishable versions, failures shown as success, retry-created duplicates, unknown active-index configuration, provenance-free chunks, inactive content in normal retrieval, manually-only evaluated quality, irreproducible results, hardcoded configuration, committed secrets, manual deployment steps, durable state inside containers, untested critical workflows.

Detail: canonical Chapter 22.

---

## 14. Critical Invariants

Mandatory implementation constraints. Consolidated from canonical Chapters 12–22.

**Identity and lifecycle**

1. `Document ≠ Document Version` — a Document is logical identity; versions are specific source editions.
2. `Document Version ≠ Processing Run` — reprocessing with new technical configuration never creates a new source version.
3. `Processing Run ≠ Indexing Run` — processing success is distinct from search-index publication.
4. `Processing Succeeded ≠ Indexing Succeeded ≠ Verification Succeeded ≠ Governance Activation` — each gate is separate; a Document Version becomes retrievable only after verification succeeds **and** governance permits.
5. `Indexed ≠ Approved for Retrieval` — presence in OpenSearch never implies availability; retrieval availability = technical readiness + governance status.
6. A Chunk cannot exist without a Processing Run and Document Version; every retrieved chunk remains traceable to its source version (result provenance is mandatory — no isolated text fragments).
7. `Duplicate Detection ≠ Document Versioning` — checksum equality never defines business identity.

**Data ownership**

8. `OpenSearch Data ≠ Canonical Source Data` — OpenSearch is a derived, replaceable serving layer; the source file must never exist only there; deleting an index never deletes the canonical source; indexes must be rebuildable from retained source + configuration.
9. `Logs ≠ Durable Operational State` — lifecycle state lives in controlled operational records, never reconstructed only from logs; UI state is never authoritative.
10. `Current Configuration ≠ Historical Configuration Snapshot` — every significant run references an immutable snapshot; historical runs are never reinterpreted with current configuration; snapshots exclude secrets.
11. Derived/unconfirmed metadata never silently overwrites confirmed metadata.

**Retrieval and governance**

12. Governance enforcement is backend logic: normal retrieval excludes `SUPERSEDED / DISABLED / DELETED`; not bypassable through UI behaviour or omitted filters.
13. Query and document embeddings must be compatible (model, dimensions, normalization); vector/index compatibility validated before indexing and querying; no silent model fallback.
14. `No Results ≠ Retrieval Failure` — a valid empty result and an execution failure are distinct outcomes, in APIs, logs, and metrics.
15. Retrieval scores are never presented as calibrated confidence; `Relevant ≠ Complete` and `Relevant ≠ Legally Applicable`; rank 1 means highest-ranked by configuration, not legally correct.
16. `Technical User ≠ Domain Authority` — processing capability never grants authority to classify content as active/official/authoritative.

**Failure and idempotency**

17. `Retry ≠ Safe Recovery` — retries are bounded, backoff-controlled, category-aware; non-retryable failures never loop; unknown outcomes verified before side effects repeat; timeout ≠ confirmed failure.
18. Partial success is never reported as complete success; failed OpenSearch bulk items inspected individually; a terminal `FAILED` run never becomes `SUCCEEDED` — retries create new attempts with preserved history.
19. Writes are idempotent through stable deterministic identifiers (chunks, runs, artifacts); repeated requests never create duplicate versions, chunks, or indexed content; idempotency keys reused with different content are rejected.
20. Safe reindexing: build candidate → verify → compare/approve → activate → retain previous; a failed candidate never damages the active verified representation; rollback references a verified state and preserves history; canonical artifacts are never deleted as automatic compensation.
21. Cross-store operations (S3 / state store / OpenSearch) assume no shared transaction; inconsistencies remain visible and reconcilable.

**Boundaries**

22. `Application Deployment ≠ Index Activation` — separate operations with separate rollback paths.
23. `Infrastructure Monitoring ≠ Knowledge-Lifecycle (Application) Monitoring` — CloudWatch owns infrastructure telemetry; CVS Review Portal owns document/run/index/evaluation visibility; neither replaces the other.
24. Retrieval relevance never implies legal correctness or compliance approval; the system supports human analysis and never issues legal judgment.

---

## 15. Canonical Reference Navigation

| Compact Topic | Canonical Chapter |
| --- | --- |
| Product purpose, problem, goals, non-goals, users, MVP scope | Chapters 1–6 |
| Functional areas and core use cases | Chapters 7–8 |
| System context and logical components | Chapters 9–10 |
| Domain entities | Chapter 11 |
| Document lifecycle | Chapter 12 |
| Query lifecycle | Chapter 13 |
| Evaluation model | Chapter 14 |
| Data and artifact ownership | Chapter 15 |
| Configuration boundary | Chapter 16 |
| Security and compliance requirements | Chapter 17 |
| Observability and auditability | Chapter 18 |
| Failure, retry, and idempotency | Chapter 19 |
| AWS deployment direction | Chapter 20 |
| Open technical decisions | Chapter 21 |
| Project-level success criteria | Chapter 22 |

Detailed functional-area references: `01_data_ingest_reference.md`, `02_data_monitoring_reference.md`, `03_data_query_reference.md`.
