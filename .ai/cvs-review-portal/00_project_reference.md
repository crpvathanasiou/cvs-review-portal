# CVS Review Portal — Semi-Technical Project Reference

> **LEGACY DOCUMENT.** This file describes a compliance document-ingestion / OpenSearch / AWS system inherited from a template. It is **not** the current product specification for the CVS Review Portal (dataset/run review of Engine exports). Canonical current specification: [`08_portal_specification.md`](08_portal_specification.md). Retain for history only; do not implement from this file.

# 1. Executive Summary

**CVS Review Portal** is a compliance-first system for ingesting, monitoring, searching, and evaluating regulatory and related documents.

The initial objective is to create a controlled and measurable knowledge base through which an AI/Search Engineer or Compliance User can:

* ingest compliance documents,
* monitor their processing status, versions, and indexes,
* execute retrieval queries,
* inspect retrieved evidence and its provenance,
* and objectively evaluate retrieval quality.

The system does not treat Retrieval-Augmented Generation as a simple flow:

```text
Document → Embedding → Vector Search → LLM Answer
```

Instead, it separates the problem into three primary functional areas:

```text
Data Ingest
→ Data Monitoring
→ Data Query and Evaluation
```

## 1.1 Data Ingest

Data Ingest covers the process through which a source document becomes searchable content.

The initial workflow includes:

```text
Upload
→ Validation
→ Storage
→ Parsing
→ Normalization
→ Metadata Extraction
→ Chunking
→ Embedding
→ OpenSearch Indexing
```

The first version will support:

* TXT,
* Markdown,
* DOCX.

Original documents and required processing artifacts will be stored in AWS S3.

Searchable chunks, embeddings, and retrieval metadata will be stored in OpenSearch.

## 1.2 Data Monitoring

Data Monitoring provides visibility into the state of the knowledge base.

The user must be able to determine:

* which documents have been ingested,
* which document versions exist,
* which version is active,
* which ingestion or indexing run produced the current data,
* which configuration was used,
* which OpenSearch index contains each document version,
* which processing stages succeeded or failed,
* and which content is active, superseded, disabled, or deleted.

This monitoring scope concerns the application and knowledge lifecycle.

It does not replace infrastructure monitoring for ECS, OpenSearch, S3, or other AWS resources. Infrastructure-level monitoring may remain in AWS CloudWatch and the corresponding AWS service consoles.

## 1.3 Data Query and Evaluation

Data Query allows users to execute retrieval queries against indexed compliance documents.

Users will be able to inspect top-ranked results together with:

* source document,
* document version,
* section or heading,
* chunk content,
* retrieval rank,
* available retrieval scores,
* and associated metadata.

The first version focuses on retrieval quality and inspection.

Generating a final LLM answer is not a mandatory requirement for the initial MVP.

The system will also support retrieval evaluation using a golden evaluation dataset and established information-retrieval metrics, initially:

* Precision@10,
* Recall@10,
* nDCG@10.

The objective is to ensure that every significant change to chunking, embeddings, indexing, or retrieval configuration can be compared with a previous baseline through reproducible evaluation runs.

## 1.4 Technical Direction

The initial technical direction includes:

* Python for the application and processing components,
* FastAPI for application APIs,
* Poetry for dependency and package management,
* Docker for containerized execution,
* AWS S3 for source documents and processing artifacts,
* OpenSearch for lexical, vector, and potentially hybrid retrieval,
* Amazon ECR for container images,
* Amazon ECS Fargate for deployment,
* CloudFormation for infrastructure provisioning.

Additional components such as PostgreSQL, Redis, a background queue, or LangGraph are not assumed to be mandatory.

They will be introduced only when a clear functional or operational requirement justifies them.

## 1.5 Configuration Philosophy

The project will be configurable in areas where retrieval experimentation or environment-specific configuration is genuinely required.

Examples include:

* embedding model,
* vector dimensions,
* chunking strategy,
* chunk size,
* chunk overlap,
* retrieval mode,
* top-k,
* OpenSearch index name,
* evaluation metrics and K values.

The project will not initially attempt to become a fully generic RAG platform or plugin-based framework.

The implementation will remain focused on the Compliance domain, with a clean modular structure and a limited number of extension points.

This should make it possible to copy and adapt both the Python codebase and the AWS infrastructure for a future use case without prematurely generalizing the entire architecture.

## 1.6 Initial Product Boundary

The first meaningful release of CVS Review Portal must demonstrate end-to-end that:

```text
A compliance document
can be ingested,
stored,
processed,
converted into indexed chunks,
monitored,
queried,
and evaluated.
```

At this stage, the project is not:

* an autonomous compliance decision system,
* a legal advice engine,
* a multi-agent application,
* a generic document management platform,
* a multi-domain SaaS product,
* or a complete production conversational assistant.

The primary value of the first release is the creation of a reliable, traceable, and measurable retrieval foundation.

Future capabilities may include:

* LLM answer generation,
* citations,
* query rewriting,
* reranking,
* compliance-specific reasoning,
* answer validation,
* human review,
* and agentic workflows.

---

# 2. Problem Statement

Organizations operating in regulated environments rely on a large number of documents, including:

* regulations,
* legislation,
* standards,
* regulatory guidelines,
* internal policies,
* compliance procedures,
* technical documentation,
* audit evidence,
* and interpretative guidance.

These documents are often extensive, interconnected, and available in multiple versions.

They may also contain:

* amendments,
* repealed provisions,
* different publication and effective dates,
* jurisdiction-specific requirements,
* and different levels of authority depending on the source.

The primary problem is not simply storing these documents.

The problem is reliably transforming them into a searchable, traceable, version-aware, and measurable knowledge base.

## 2.1 Difficulty Locating the Correct Evidence

Traditional keyword search is often insufficient when a user:

* uses terminology different from the source document,
* describes an obligation indirectly,
* does not know the correct regulation or article,
* needs information distributed across multiple sections,
* or must distinguish general guidance from a binding requirement.

A result containing similar words is not necessarily the correct compliance evidence.

A semantic search result can also be conceptually related but still unsuitable because it:

* comes from the wrong jurisdiction,
* applies to a different organization or role,
* originates from a secondary rather than official source,
* has been superseded by a newer version,
* or lacks the required regulatory detail.

## 2.2 Document Version and Validity Risk

In the Compliance domain, the correctness of a retrieved result depends not only on its content but also on whether the document remains valid and applicable.

The system must be capable of distinguishing:

* different versions of the same document,
* active and superseded versions,
* publication and effective dates,
* amendments,
* withdrawn or disabled documents,
* official and secondary sources.

Without version awareness, retrieval may return accurate text from an obsolete or inapplicable source.

This is particularly dangerous because the result may appear convincing while no longer being valid.

## 2.3 Lack of End-to-End Traceability

In many basic RAG implementations, source documents are converted into chunks and embeddings without preserving a complete relationship across the processing lifecycle:

```text
Original Document
→ Document Version
→ Processing Run
→ Parsing Output
→ Chunk
→ Embedding
→ OpenSearch Index
→ Retrieved Result
```

This makes it difficult to answer essential questions:

* Which source document produced the result?
* Which version was used?
* Which section or heading contained the text?
* Which chunking configuration produced the chunk?
* Which embedding model was used?
* Which index contains it?
* When and why was the document reprocessed?

For a Compliance system, displaying an isolated text snippet is not sufficient.

Each result must preserve clear provenance and must be traceable to the canonical source artifact.

## 2.4 Uncontrolled Document Processing

The ingestion process contains multiple stages:

```text
Upload
→ Validation
→ Storage
→ Parsing
→ Normalization
→ Metadata Extraction
→ Chunking
→ Embedding
→ Indexing
```

Each stage may fail or produce low-quality output.

Potential problems include:

* corrupted or unsupported files,
* incorrect character encoding,
* loss of headings or lists,
* incorrect chunk boundaries,
* excessively small or large chunks,
* duplicated content,
* incomplete indexing,
* vector-dimension and index-mapping mismatches,
* partial processing without an explicit failure state.

Without an explicit processing lifecycle, a document may appear available even though it has only been partially processed.

## 2.5 Limited Visibility Into the Knowledge Base

The user or AI/Search Engineer must be able to understand the actual state of the knowledge base.

This includes:

* which documents exist,
* which versions are indexed,
* which content is active,
* which ingestion runs failed,
* how many chunks were created,
* which indexes are available,
* which configuration was used,
* and whether stored source documents match the indexed content.

Without this visibility, retrieval quality cannot be diagnosed reliably.

An incorrect result may be caused by:

* incorrect query processing,
* poor chunking,
* a missing document,
* failed indexing,
* an obsolete document version,
* an incorrect metadata filter,
* or an unsuitable embedding model.

The system must help identify the actual cause.

## 2.6 Retrieval Quality Is Often Evaluated Subjectively

Many RAG projects assume that retrieval works because a small number of example queries return apparently relevant results.

This is not sufficient.

Retrieval quality should be assessed using:

* predefined queries,
* known relevant documents, sections, or chunks,
* relevance judgments,
* repeatable evaluation runs,
* comparable metrics.

Without a golden evaluation dataset, it is impossible to determine objectively whether a change to:

* chunk size,
* chunk overlap,
* embedding model,
* vector dimensions,
* metadata filters,
* hybrid fusion,
* or ranking strategy

improved or degraded the system.

## 2.7 Configuration Changes Are Difficult to Compare

The retrieval system will require controlled experimentation.

Examples include:

```text
Embedding Model A vs Embedding Model B
Small Chunks vs Large Chunks
Dense Retrieval vs Hybrid Retrieval
Different Top-K Values
Different Metadata Filters
Different OpenSearch Mappings
```

If parameters are hardcoded or not associated with specific processing and evaluation runs, results are not reproducible.

The system therefore requires controlled configuration management so that each indexed dataset and evaluation result is connected to the parameters that produced it.

## 2.8 Risk of Treating the Search Index as the Source of Truth

OpenSearch must not be treated as the sole source of truth.

Indexed chunks and embeddings are derived serving artifacts.

They may be:

* regenerated,
* deleted,
* reindexed,
* or replaced after a configuration change.

The original source document and its version must remain available independently of the retrieval index.

Without this separation, the system cannot reliably support:

* reproducibility,
* reprocessing,
* auditability,
* or safe index migration.

## 2.9 Premature Dependence on Final LLM Answers

The quality of a final LLM answer depends directly on the quality of the retrieved context.

An LLM can produce a convincing but incorrect answer when:

* the correct evidence is missing,
* obsolete content is retrieved,
* a relevant section has been incorrectly divided,
* or the retrieved chunks do not fully cover the question.

For this reason, the initial project scope must allow the retrieval layer to be inspected and evaluated independently before system success depends on answer generation.

## 2.10 Core Problem to Be Solved

The core problem addressed by CVS Review Portal is:

> How can compliance documents be ingested, versioned, transformed into searchable content, monitored throughout their lifecycle, and retrieved with quality that can be measured and verified?

The system must ensure that:

* source content is preserved,
* processing status is visible,
* document versions are distinguishable,
* every indexed chunk is traceable,
* obsolete documents can be excluded,
* query results can be inspected,
* and retrieval changes can be evaluated objectively.

The first version does not attempt to solve the entire problem of automated compliance reasoning.

It focuses on creating the reliable ingestion, monitoring, retrieval, and evaluation foundation required for future capabilities.

---

# 3. Project Goals

The main goal of CVS Review Portal is to establish a reliable, traceable, and measurable foundation for ingesting, monitoring, searching, and evaluating compliance documents.

These goals describe the required direction of the first meaningful version.

They are not yet the detailed Definition of Done for individual implementation deliverables.

## 3.1 Establish an End-to-End Document Lifecycle

The system must support a complete and controlled lifecycle for each document:

```text
Upload
→ Validation
→ Source Storage
→ Parsing
→ Normalization
→ Metadata Extraction
→ Chunking
→ Embedding
→ Indexing
→ Monitoring
→ Querying
→ Evaluation
```

The user must be able to follow a document from its original upload through processing and into retrieval queries.

The lifecycle must be explicit, observable, and resilient to partial failures.

## 3.2 Preserve Canonical Source Documents

Original uploaded documents must be preserved independently of the search index.

AWS S3 will act as the canonical storage layer for:

* original source files,
* normalized or parsed artifacts where required,
* processing outputs required for reproducibility,
* evaluation datasets,
* exported reports or evidence bundles.

OpenSearch must be treated as a serving and retrieval layer rather than the sole source of truth.

## 3.3 Support Controlled Document Ingestion

The first version must support:

* TXT,
* Markdown,
* DOCX.

The ingestion process must include:

* file validation,
* supported-file-type validation,
* file-size limits,
* document identity,
* duplicate handling,
* source-storage confirmation,
* processing status,
* controlled failure states.

The objective is not merely to upload a file.

The system must determine whether every required processing stage completed successfully.

## 3.4 Maintain Document and Version Traceability

The system must clearly distinguish between:

```text
Document
Document Version
Processing Run
Indexing Run
Chunk
Index
```

Every indexed chunk must be connected to:

* the original source document,
* the specific document version,
* the processing run,
* the chunking configuration,
* the embedding configuration,
* and the OpenSearch index in which it was stored.

A document version must not be treated as equivalent to a processing run.

The same document version may be reprocessed using a different configuration without automatically becoming a new source version.

## 3.5 Provide Document and Index Monitoring

The system must provide application-level visibility into:

* documents,
* document versions,
* ingestion runs,
* processing stages,
* indexing runs,
* OpenSearch indexes,
* active configurations,
* failure states.

Users must be able to determine:

* which documents are available,
* which versions were processed,
* which version is active,
* which content is superseded or disabled,
* which documents failed,
* and which index contains each version.

Data Monitoring does not replace AWS infrastructure monitoring.

Infrastructure resources such as ECS, S3, and OpenSearch may continue to be monitored through CloudWatch and the relevant AWS services.

## 3.6 Support Document Version Governance

The system must support governance states for document versions.

Indicative states include:

```text
ACTIVE
SUPERSEDED
DISABLED
DELETED
```

The retrieval mechanism must be able to exclude content that is not active or appropriate for use.

The objective is to reduce the risk of retrieving:

* obsolete requirements,
* superseded document versions,
* withdrawn guidance,
* disabled content.

## 3.7 Create Searchable and Inspectable Content

Compliance documents must be converted into searchable chunks that preserve sufficient context and provenance.

Each chunk must include or be connected to metadata such as:

* document identifier,
* document version,
* title,
* section or heading,
* source location,
* jurisdiction where applicable,
* publication or effective date where available,
* source authority,
* governance status.

Retrieval results must not appear as isolated text fragments without source context.

## 3.8 Support Configurable Retrieval Experiments

The project must allow controlled changes to important ingestion and retrieval parameters.

The initial configurable areas include:

* embedding model,
* vector dimensions,
* embedding batch size,
* chunking strategy,
* chunk size,
* chunk overlap,
* retrieval mode,
* top-k,
* index name,
* fusion parameters where applicable,
* evaluation metrics and K values.

Configuration must support genuine experimentation without turning the project into a fully generic plugin framework.

Available options may remain limited and explicitly supported by the codebase.

## 3.9 Provide Query Testing Capabilities

The system must provide a Data Query interface through which an AI/Search Engineer or Compliance User can:

* submit a query,
* select or inspect the retrieval configuration,
* apply supported metadata filters,
* receive ranked results,
* inspect retrieved chunks,
* view rank, scores, and provenance,
* identify no-result or low-confidence cases.

The initial Query interface should operate primarily as a retrieval testing workbench rather than a final conversational assistant.

## 3.10 Support Lexical and Vector Retrieval

OpenSearch will be the primary retrieval engine.

The project must be designed to support:

* lexical retrieval using BM25,
* vector retrieval,
* metadata filtering,
* potentially hybrid retrieval.

The final retrieval strategy does not need to be treated as permanently fixed from the beginning.

The project must support objective comparison between retrieval configurations before a production baseline is selected.

## 3.11 Measure Retrieval Quality Objectively

The system must support an evaluation dataset containing:

* predefined queries,
* relevant documents, sections, or chunks,
* binary or graded relevance judgments,
* edge cases,
* no-answer queries where applicable.

The initial metrics are:

* Precision@10,
* Recall@10,
* nDCG@10.

Possible later metrics include:

* MRR@10,
* Hit Rate@10,
* Coverage,
* retrieval latency,
* index size,
* processing time.

Every significant change to the retrieval pipeline must be measurable through a repeatable evaluation process.

## 3.12 Ensure Experiment Reproducibility

Every ingestion, indexing, and evaluation run must be associated with a specific configuration snapshot.

The system must be able to identify:

* embedding model,
* vector dimensions,
* chunking strategy,
* chunk size,
* chunk overlap,
* index mapping,
* retrieval mode,
* top-k,
* evaluation dataset,
* execution timestamp.

Experiment results must not depend on undocumented local settings.

## 3.13 Support Safe Reprocessing and Reindexing

The system must support controlled reprocessing when any of the following changes:

* parser,
* normalization logic,
* metadata extraction,
* chunking strategy,
* embedding model,
* OpenSearch index configuration.

Reprocessing must not destroy the original source document or create uncontrolled duplicates.

The relationship between previous and new configurations must remain clear:

```text
Previous Processing Configuration
→ Previous Index

New Processing Configuration
→ New Index or Controlled Replacement
```

The exact index migration and alias strategy will be defined during later technical design.

## 3.14 Establish Clear Failure and Retry Behaviour

The project must manage failures explicitly.

Examples include:

* parsing failure,
* metadata-extraction failure,
* embedding-generation failure,
* indexing failure,
* partial batch processing,
* OpenSearch unavailability,
* invalid configuration,
* unsupported document format.

A failed or partially processed document must not appear as successfully available for retrieval.

Retries must be idempotent or controlled through stable identifiers and processing runs.

## 3.15 Provide Operational Observability

The system must produce structured logs and basic operational metrics for:

* ingestion requests,
* processing duration,
* processing-stage failures,
* number of generated chunks,
* embedding duration,
* indexing duration,
* retrieval latency,
* result count,
* evaluation duration,
* evaluation metrics.

Observability must help distinguish between:

* data-quality problems,
* processing problems,
* retrieval-configuration problems,
* infrastructure problems.

## 3.16 Apply Security-by-Default Principles

The first version must follow baseline security practices:

* no secrets in source code,
* environment-based configuration,
* IAM roles instead of static AWS credentials,
* least-privilege access,
* private S3 access by default,
* encryption in transit,
* encryption at rest,
* upload-size limits,
* file-type validation,
* controlled logging of document content,
* non-root Docker runtime,
* dependency and code-quality checks.

The first version does not require complete enterprise IAM or multi-tenant authorization, but the design should not create unnecessary barriers to adding them later.

## 3.17 Maintain a Focused Compliance-First Scope

The project must remain focused on the Compliance use case.

Modularity and configuration should support:

* retrieval experimentation,
* maintainability,
* testing,
* potential future project duplication.

It is not an initial goal to support every domain, parser, vector database, cloud provider, or workflow through generic abstractions.

The guiding principle is:

> Build for Compliance while keeping the implementation structured enough to be copied, adapted, and selectively generalized later.

## 3.18 Create a Foundation for Future AI Capabilities

The first release should provide the technical foundation for future capabilities such as:

* LLM answer generation,
* source citations,
* query rewriting,
* query decomposition,
* reranking,
* parent-child retrieval,
* compliance-specific metadata extraction,
* answer validation,
* confidence and coverage checks,
* human review,
* agentic workflows,
* compliance reporting.

These future capabilities must not delay the completion of the initial ingestion, monitoring, query, and evaluation foundation.

## 3.19 Project Goal Summary

The project is moving in the correct direction when it enables:

```text
Compliance Documents
→ to be ingested in a controlled manner
→ preserved as canonical source artifacts
→ transformed into traceable indexed content
→ monitored by document, version, run, and index
→ searched through inspectable retrieval results
→ evaluated through reproducible metrics
```

Success will not be judged only by whether the system produces a convincing AI answer.

It will primarily be judged by whether the underlying knowledge and retrieval system is:

* reliable,
* traceable,
* reproducible,
* measurable,
* maintainable,
* suitable for future extension.

---

# 4. Non-Goals

CVS Review Portal intentionally has a constrained initial scope.

The first version focuses on establishing a reliable foundation for:

```text
Data Ingest
→ Data Monitoring
→ Data Query
→ Retrieval Evaluation
```

The following capabilities are explicitly outside the initial project scope.

## 4.1 Not a Generic Multi-Domain RAG Platform

The project is not initially intended to operate as a fully generalized platform for every domain.

The implementation will remain focused on Compliance and may include:

* compliance-specific metadata,
* compliance-oriented filters,
* document-version governance,
* source-authority information,
* jurisdiction,
* publication and effective dates.

The first version is not required to support every domain through configuration alone.

For a future use case, the Python application and AWS infrastructure may be copied and adapted.

Shared frameworks or libraries should be extracted only after multiple real implementations demonstrate which components are genuinely common.

## 4.2 Not a Fully Configurable Plugin Framework

The project will not initially support:

* dynamic loading of arbitrary Python classes,
* automatic plugin discovery,
* arbitrary parser plugins,
* arbitrary embedding providers,
* arbitrary vector databases,
* arbitrary workflow definitions through YAML,
* runtime installation of new components.

Configuration files will cover a limited and controlled set of parameters.

Supported options will be implemented explicitly by the codebase.

## 4.3 Not an Autonomous Compliance Decision System

CVS Review Portal will not autonomously determine:

* whether an organization is compliant,
* whether a practice violates a regulation,
* whether an AI system definitively belongs to a specific risk category,
* which legal action must be taken,
* whether a compliance requirement has been implemented sufficiently.

The retrieval system may locate and present relevant evidence.

Final compliance or legal judgment remains the responsibility of an appropriately qualified human expert.

## 4.4 Not a Legal Advice Engine

The project is not intended to provide binding legal advice.

Retrieval results or future AI-generated answers must not be presented as:

* formal legal opinions,
* replacements for qualified legal counsel,
* final interpretations of legislation,
* guarantees of regulatory compliance.

The system functions as an evidence-discovery and human-analysis support tool.

## 4.5 Not a Complete Conversational AI Assistant

The first version does not require:

* multi-turn conversation memory,
* conversation history,
* personalized responses,
* follow-up question management,
* complex dialogue orchestration,
* long-running user sessions.

The initial Data Query interface will function mainly as a retrieval testing workbench.

## 4.6 Not a Multi-Agent System

The project does not initially require:

* planner agents,
* retrieval agents,
* compliance agents,
* validator agents,
* supervisor agents,
* multi-agent orchestration,
* autonomous tool selection.

The ingestion and retrieval flows are primarily deterministic and should be implemented as explicit pipeline stages.

LangGraph or another agent orchestration technology will be introduced only when there is a demonstrated requirement for conditional reasoning, human review, adaptive retrieval, or controlled tool execution.

## 4.7 Not a Full Document Management System

CVS Review Portal does not aim to replace an enterprise Document Management System.

The first version does not require:

* collaborative document editing,
* approval workflows,
* electronic signatures,
* document authoring,
* document check-in/check-out,
* enterprise folder structures,
* organization-wide sharing portals,
* advanced retention policies,
* legal-hold management.

Documents are managed only to the extent required for ingestion, version traceability, indexing, retrieval, and evaluation.

## 4.8 Not a General-Purpose Search Engine

The project will not attempt to support every type of search workload.

The scope is limited to curated compliance and regulatory documents.

It does not initially include:

* web-scale crawling,
* public internet search,
* e-commerce search,
* image search,
* multimedia search,
* social-media indexing,
* behaviour-based ranking,
* recommendation systems.

## 4.9 No PDF or OCR Support in the Initial Version

The first version supports:

* TXT,
* Markdown,
* DOCX.

PDF and OCR support are excluded from the initial scope.

These capabilities introduce additional complexity such as:

* page-layout analysis,
* reading-order reconstruction,
* headers and footers,
* tables,
* scanned pages,
* image extraction,
* OCR quality control,
* page-level citations.

They may be introduced later as separate deliverables.

## 4.10 No Automatic Web Crawling or Regulatory Updates

The system will not automatically search for or download new regulations or regulatory publications from the internet.

The initial version does not include:

* web crawlers,
* scheduled regulatory monitoring,
* automatic external version detection,
* automatic amendment ingestion,
* automatic superseding of previous documents.

Documents will be introduced through a controlled upload or ingestion mechanism.

## 4.11 No Automatic Trust or Authority Determination

The system will not automatically determine whether a source is:

* official,
* legally binding,
* authoritative,
* secondary guidance,
* unreliable.

Source authority may be stored as metadata, but it must be supplied or confirmed through the controlled ingestion process.

## 4.12 No Fully Automated Metadata Extraction Requirement

The first version does not require all compliance metadata to be extracted automatically using an LLM or machine-learning model.

Metadata may initially be:

* supplied during upload,
* derived from filenames or document properties,
* extracted using deterministic rules,
* completed manually.

## 4.13 No Mandatory Answer Generation

Generating a final LLM answer is not a core requirement of the first release.

The initial priority is:

```text
Query
→ Retrieve
→ Rank
→ Inspect
→ Evaluate
```

rather than:

```text
Query
→ Retrieve
→ Generate a Polished Answer
```

## 4.14 No Automatic Citation Validation

The initial system must preserve provenance for each retrieved chunk.

It does not initially need to validate automatically that:

* every generated claim is supported by a citation,
* each citation precisely supports the corresponding statement,
* the answer does not contradict its sources,
* citations are complete.

This belongs to a future answer-validation layer.

## 4.15 No Model Fine-Tuning

The first version does not include:

* embedding-model fine-tuning,
* LLM fine-tuning,
* domain-specific pretraining,
* reranker training,
* reinforcement learning,
* preference optimization.

Existing models will be evaluated first.

Fine-tuning should be considered only when evaluation demonstrates that baseline approaches are insufficient.

## 4.16 No Mandatory Advanced Retrieval From the Beginning

The first version does not require:

* query decomposition,
* multi-query retrieval,
* HyDE,
* parent-child retrieval,
* graph retrieval,
* knowledge graphs,
* cross-encoder reranking,
* adaptive retrieval,
* self-corrective RAG,
* agentic retrieval loops.

The initial baseline should remain simple enough to understand, measure, and compare.

## 4.17 No Multi-Cloud or Cloud-Agnostic Infrastructure

The first version will use AWS.

The architecture does not need to support AWS, Azure, Google Cloud, and on-premises deployment simultaneously.

Cloud portability should be treated as a future adaptation rather than an initial requirement.

## 4.18 No Arbitrary Vector Database Support

OpenSearch is the selected retrieval engine for the first version.

The project does not require an abstraction layer supporting immediate switching between:

* OpenSearch,
* Pinecone,
* Weaviate,
* Milvus,
* Qdrant,
* pgvector,
* other vector databases.

Internal interfaces may still be used where they improve testing and maintainability.

## 4.19 No Production-Scale Multi-Tenancy

The first version does not require:

* multiple organizations,
* tenant isolation,
* tenant-specific indexes,
* tenant-specific encryption keys,
* tenant billing,
* quotas,
* organization-level administration,
* tenant-specific data-residency policies.

The initial deployment may operate as a single-environment, single-knowledge-base system.

## 4.20 No Complete Enterprise Identity and Access Management

The first version does not require:

* SSO,
* SAML,
* enterprise OAuth federation,
* Active Directory integration,
* fine-grained role-based permissions,
* attribute-based access control,
* document-level access policies.

A simpler access mechanism may be used for controlled development and testing.

## 4.21 No Replacement of AWS Operational Monitoring

Data Monitoring will not attempt to reproduce every AWS infrastructure metric.

It will not become a complete dashboard for:

* ECS CPU and memory,
* container networking,
* S3 infrastructure metrics,
* OpenSearch node metrics,
* VPC traffic,
* IAM events,
* CloudFormation internals.

Application monitoring will focus on:

* documents,
* versions,
* processing runs,
* indexing runs,
* indexes,
* failures,
* configuration traceability.

## 4.22 No Premature Microservice Decomposition

The functional areas:

* Data Ingest,
* Data Monitoring,
* Data Query

do not imply three independent microservices.

The initial implementation may use a modular monolith with:

* a shared FastAPI application,
* clear internal modules,
* explicit contracts,
* an optional processing worker where required.

Microservice decomposition should occur only if justified by independent scaling, security isolation, resource isolation, deployment cadence, or team ownership.

## 4.23 No Premature Use of PostgreSQL, Redis, or LangGraph

PostgreSQL, Redis, and LangGraph are not mandatory simply because they are available.

Each component must be justified by a concrete requirement.

Possible examples include:

* PostgreSQL for durable operational state and relational traceability,
* Redis for caching, coordination, or temporary task state,
* LangGraph for stateful, conditional, or human-in-the-loop workflows.

## 4.24 No Optimization for Unproven Scale

The first release will not be optimized for speculative workloads such as:

* millions of documents,
* thousands of concurrent users,
* continuous high-volume ingestion,
* global active-active deployment,
* petabyte-scale storage,
* unrealistic latency requirements.

The system should be production-disciplined and capable of scaling, but infrastructure sizing and optimization must be based on actual measurements and requirements.

## 4.25 No Claim of Compliance Certification

The existence or use of CVS Review Portal does not mean that:

* the tool itself is certified as compliant,
* its users automatically become compliant,
* its results constitute compliance approval,
* it replaces a formal audit or certification process.

The project supports evidence discovery, traceability, and retrieval evaluation.

It does not provide compliance certification.

## 4.26 Scope-Control Principle

A capability should not be introduced merely because it may be useful in the future.

It should be introduced only when:

* it is necessary for the current Compliance use case,
* it is required by the next agreed deliverable,
* its implementation and operational cost are justified,
* and it cannot be deferred without weakening the end-to-end objective.

---

# 5. Target Users and Roles

CVS Review Portal initially serves a limited set of users involved in creating, maintaining, testing, and using the compliance knowledge base.

The roles described in this chapter represent functional responsibilities and access needs.

They do not yet constitute a final authorization model and do not require full Role-Based Access Control in the first version.

The primary roles are:

```text
AI / Search Engineer
Compliance User
System Administrator
```

Additional roles such as Compliance Administrator, Reviewer, Domain Expert, or Auditor may be introduced later.

## 5.1 AI / Search Engineer

The AI / Search Engineer is the primary technical user of the first version.

This role is responsible for developing, testing, and improving the ingestion and retrieval pipeline.

### Primary Responsibilities

The AI / Search Engineer may:

* upload compliance documents,
* monitor ingestion,
* inspect parsing and indexing failures,
* inspect generated chunks,
* review document and chunk metadata,
* execute retrieval queries,
* apply metadata filters,
* compare lexical, vector, and hybrid retrieval,
* execute evaluation datasets,
* inspect Precision@K, Recall@K, and nDCG@K,
* compare retrieval configurations,
* start controlled reprocessing or reindexing,
* investigate retrieval-quality problems.

### Questions This Role Must Be Able to Answer

* Which documents were ingested successfully?
* Which processing stage failed?
* How many chunks were produced?
* Which chunking configuration was used?
* Which embedding model was used?
* Which OpenSearch index contains the chunks?
* Why does a relevant document not appear in the top results?
* Did the new configuration improve Recall@10?
* Did it degrade nDCG@10 or retrieval latency?
* Are duplicate or obsolete chunks present in the active index?

### Expected Technical Knowledge

This role may understand:

* chunking,
* embeddings,
* vector dimensions,
* BM25,
* hybrid retrieval,
* metadata filtering,
* top-k,
* relevance judgments,
* Precision,
* Recall,
* nDCG,
* indexing,
* reindexing.

The UI for this role may expose more technical information than the interface intended for business users.

## 5.2 Compliance User

The Compliance User is the primary domain user.

This user accesses the indexed knowledge base to locate regulatory, policy, procedural, or technical evidence relevant to a compliance question or task.

### Primary Responsibilities

The Compliance User may:

* submit natural-language questions,
* apply simple domain filters,
* inspect top-ranked results,
* view the source document,
* view the relevant section or heading,
* inspect the document version,
* review publication or effective dates,
* distinguish official from secondary sources,
* access the relevant source artifact where permitted,
* use retrieved results as evidence for further human analysis.

### Questions This Role Must Be Able to Answer

* Which provision relates to this requirement?
* Which regulation or policy contains it?
* Is this document version active?
* When was it published or made effective?
* Is the source official?
* Which exact section supports the result?
* Are there additional relevant sources?
* Does the result apply to the correct jurisdiction or organizational role?

### Expected Technical Knowledge

The Compliance User is not expected to understand:

* embedding models,
* vector dimensions,
* index mappings,
* RRF,
* OpenSearch configuration,
* metric formulas.

The interface should expose technical details only when they improve understanding or trust.

For example, the user may see result rank and source metadata without having to interpret raw vector scores.

### Role Limitation

A retrieved result must not be treated as:

* a final legal interpretation,
* compliance approval,
* formal legal advice,
* proof that an organization is compliant.

The system supports evidence discovery and human analysis.

## 5.3 System Administrator

The System Administrator is responsible for operational management of the application and the knowledge base.

In the first version, this role may be combined with the AI / Search Engineer.

### Primary Responsibilities

The System Administrator may:

* monitor application state,
* manage document-lifecycle actions,
* activate or disable document versions,
* inspect failed ingestion and indexing runs,
* initiate controlled retries,
* manage available OpenSearch indexes,
* inspect application-level index health,
* review configuration snapshots,
* manage environment-specific settings,
* control access to storage and application resources,
* coordinate deployment, rollback, and infrastructure updates.

### Questions This Role Must Be Able to Answer

* Which document versions are active?
* Which documents are superseded or disabled?
* Which ingestion runs failed?
* Is there a mismatch between stored documents and indexed content?
* Which index is used by the active query configuration?
* When was the index created?
* Which configuration snapshot created it?
* Is it safe to retry or reindex?
* Which versions may be removed from the serving layer?
* Is the problem caused by configuration or deployment?

### Application Monitoring Boundary

The System Administrator may use CVS Review Portal for application-level monitoring, including:

* document status,
* processing status,
* indexing status,
* configuration traceability,
* document-to-index mappings.

Infrastructure-level monitoring will remain primarily in AWS CloudWatch and the relevant AWS services.

## 5.4 Compliance Administrator

The Compliance Administrator is a possible future role combining domain ownership and document governance.

It does not need to exist as a separate technical authorization role in the first MVP.

### Potential Responsibilities

The Compliance Administrator may:

* approve newly ingested documents,
* confirm source authority,
* select the active document version,
* mark a version as superseded,
* correct compliance metadata,
* confirm jurisdiction and effective dates,
* disable inappropriate or outdated sources,
* approve a document for inclusion in the active retrieval index.

This role becomes important when document governance should not be controlled solely by technical users.

## 5.5 Reviewer or Domain Expert

The Reviewer is a possible future role responsible for assessing retrieval quality and relevance judgments.

### Potential Responsibilities

The Reviewer may:

* inspect retrieved results,
* classify results as relevant or non-relevant,
* assign graded relevance scores,
* approve golden queries,
* correct relevance judgments,
* identify missing evidence,
* review ambiguous or no-answer queries,
* support evaluation-dataset creation.

This role may be fulfilled by:

* a Compliance expert,
* a legal professional,
* a policy specialist,
* another authorized domain reviewer.

Domain-expert participation is important because semantic similarity alone does not establish regulatory relevance.

## 5.6 Auditor or Read-Only Reviewer

The Auditor is a possible future read-only role.

### Potential Responsibilities

The Auditor may inspect:

* document provenance,
* version history,
* ingestion history,
* configuration snapshots,
* index history,
* evaluation reports,
* governance-status changes,
* available audit records.

The Auditor does not need permission to:

* upload documents,
* modify configurations,
* trigger indexing,
* activate or disable versions,
* change relevance judgments.

This role is not required for the initial development MVP, but its needs should inform traceability design.

## 5.7 Initial MVP Role Simplification

To avoid premature complexity, the first version may use two practical access levels.

### Technical Operator

The Technical Operator temporarily combines:

* AI / Search Engineer,
* System Administrator,
* selected Compliance Administrator capabilities required for testing.

The Technical Operator may:

* ingest documents,
* monitor processing,
* manage versions,
* start reprocessing,
* test queries,
* execute evaluations.

### Query User

The Query User primarily corresponds to the Compliance User.

The Query User may:

* submit queries,
* apply permitted filters,
* inspect retrieved evidence and provenance.

This simplification allows the project to prove the main workflows without implementing full RBAC.

## 5.8 High-Level Capability Matrix

| Capability                      | AI / Search Engineer | Compliance User | System Administrator | Future Reviewer |
| ------------------------------- | -------------------: | --------------: | -------------------: | --------------: |
| Upload documents                |                  Yes |        Optional |                  Yes |              No |
| View document status            |                  Yes |         Limited |                  Yes |       Read-only |
| View document versions          |                  Yes |             Yes |                  Yes |       Read-only |
| Change active version           |             Optional |              No |                  Yes |              No |
| Inspect chunks                  |                  Yes |         Limited |                  Yes |             Yes |
| Execute retrieval queries       |                  Yes |             Yes |             Optional |             Yes |
| View technical retrieval scores |                  Yes |        Optional |             Optional |             Yes |
| Run evaluation datasets         |                  Yes |              No |             Optional |        Optional |
| Add relevance judgments         |                  Yes |              No |                   No |             Yes |
| Start reprocessing              |                  Yes |              No |                  Yes |              No |
| Manage indexes                  |              Limited |              No |                  Yes |              No |
| View audit history              |                  Yes |         Limited |                  Yes |             Yes |

This matrix is a functional direction rather than a final authorization specification.

## 5.9 Role and Permission Design Principles

### Least Privilege

Each user should receive only the permissions required by their role.

### Separation of Technical and Domain Authority

The technical ability to ingest or index a document does not necessarily grant authority to classify it as active, official, or authoritative.

### Read and Write Separation

Actions that modify:

* document status,
* active version,
* index state,
* configuration,
* relevance judgments

must be distinguished from read-only actions.

### Traceable Administrative Actions

Important changes should eventually be associated with:

* actor,
* timestamp,
* action,
* affected entity,
* previous state,
* new state.

### Progressive Security Implementation

The first version may use a simplified access model for controlled development and testing.

Complete authentication and authorization should be introduced when the actual users, organizational responsibilities, security requirements, and document-level policies are known.

## 5.10 Primary User Priority for the First Release

The first release will primarily be designed for the:

```text
AI / Search Engineer acting as the Technical Operator
```

This user must be able to complete the full workflow:

```text
Upload Document
→ Monitor Processing
→ Inspect Document and Index State
→ Execute Retrieval Query
→ Inspect Evidence
→ Run Evaluation
→ Compare Results
```

The Compliance User is also an important target user, but the first UI may remain more testing-oriented than business-facing.

This allows the project to validate:

* ingestion quality,
* traceability,
* indexing correctness,
* retrieval usefulness,
* evaluation reliability,

before significant effort is invested in final user experience and enterprise access management.


# 6. MVP Scope

The Minimum Viable Product of CVS Review Portal must demonstrate a complete and measurable workflow across the three primary functional areas:

```text
Data Ingest
→ Data Monitoring
→ Data Query and Evaluation
```

The MVP is not defined only by the presence of individual technical components.

It must demonstrate that a compliance document can move through the complete lifecycle from controlled upload to indexed retrieval and objective evaluation.

## 6.1 MVP Objective

The objective of the MVP is to prove that CVS Review Portal can create and operate a reliable compliance knowledge base.

The MVP must demonstrate that:

```text
A compliance document
can be uploaded,
validated,
stored,
processed,
versioned,
indexed,
monitored,
queried,
and evaluated.
```

The first release should prioritize:

* correctness,
* traceability,
* reproducibility,
* observability,
* retrieval quality,
* controlled scope.

The MVP does not need to provide every future user experience, retrieval technique, document format, or enterprise capability.

## 6.2 Primary MVP User

The primary user of the MVP is the:

```text
AI / Search Engineer acting as Technical Operator
```

This user must be able to complete the full end-to-end workflow:

```text
Upload a document
→ Monitor processing
→ Inspect the document version
→ Inspect the target index
→ Execute retrieval queries
→ Inspect retrieved evidence
→ Run evaluation
→ Review retrieval metrics
```

The MVP may also support a simplified Query User experience for Compliance Users.

However, the first interface may remain technical and evaluation-oriented rather than optimized as a final business-facing application.

## 6.3 Supported Document Formats

The MVP will support the following source-document formats:

* TXT,
* Markdown,
* DOCX.

Each supported format must be processed through a clearly defined parser.

The MVP does not include:

* PDF,
* scanned documents,
* OCR,
* HTML,
* spreadsheets,
* images,
* audio,
* video.

Unsupported formats must be rejected explicitly rather than accepted and processed partially.

## 6.4 Data Ingest Scope

The Data Ingest MVP must support the controlled transformation of source documents into searchable OpenSearch content.

The required workflow is:

```text
Upload
→ Validation
→ Source Storage
→ Parsing
→ Normalization
→ Metadata Handling
→ Chunking
→ Embedding
→ Indexing
→ Processing Verification
```

### 6.4.1 Upload

The system must provide an interface through which an authorized Technical Operator can upload a supported document.

The upload process must capture or generate the information required to identify the document and initiate processing.

The first upload interface may be:

* a simple web page,
* a FastAPI endpoint,
* or both.

The final UI technology is not part of the MVP architectural commitment.

### 6.4.2 File Validation

The system must validate at least:

* file extension,
* supported media type where available,
* maximum file size,
* empty-file conditions,
* basic file readability,
* required upload metadata.

A rejected upload must return a clear failure reason.

A rejected file must not continue into the processing pipeline.

### 6.4.3 Source Storage

The original uploaded file must be stored in AWS S3 before it is treated as successfully received for processing.

The stored source artifact must be associated with:

* document identifier,
* document-version identifier,
* original filename,
* upload timestamp,
* storage location,
* content checksum or equivalent identity signal.

The OpenSearch index must not become the only location from which the original document can be reconstructed or identified.

### 6.4.4 Document Identity

The MVP must distinguish between:

```text
Document
Document Version
Processing Run
```

A Document represents the logical compliance source.

A Document Version represents a specific source version or edition of that document.

A Processing Run represents one execution of the processing pipeline against a document version.

The same document version may be reprocessed without automatically creating a new source version.

### 6.4.5 Duplicate Handling

The MVP must provide controlled duplicate handling.

At minimum, it must be possible to identify whether:

* the same file has already been uploaded,
* the same document version already exists,
* the same processing request has already completed,
* a retry would create duplicate indexed content.

The exact duplicate-resolution policy may remain configurable or subject to later refinement.

However, retries must not create uncontrolled duplicate chunks.

### 6.4.6 Parsing

The system must extract usable text and structural information from TXT, Markdown, and DOCX files.

Where available, parsing should preserve:

* headings,
* paragraphs,
* lists,
* section order,
* basic document structure.

The parser does not need to preserve the complete visual formatting of the original file.

### 6.4.7 Normalization

The system must apply a controlled normalization process before chunking.

Normalization may include:

* whitespace normalization,
* line-ending normalization,
* removal of unsupported control characters,
* preservation of meaningful paragraph boundaries,
* preservation of headings,
* consistent text encoding.

Normalization must not silently remove legally or semantically meaningful content.

### 6.4.8 Metadata Handling

The MVP must support a minimum metadata set required for traceability and retrieval.

Indicative metadata includes:

* document identifier,
* document-version identifier,
* title,
* source filename,
* source type,
* source authority where supplied,
* jurisdiction where supplied,
* publication date where supplied,
* effective date where supplied,
* version label where supplied,
* governance status,
* section or heading,
* processing-run identifier.

Metadata may initially be:

* provided during upload,
* derived from the source file,
* extracted through deterministic rules,
* completed manually.

Fully automated metadata extraction is not required.

### 6.4.9 Chunking

The MVP must support at least one approved chunking strategy.

The chunking process must produce chunks that:

* preserve document traceability,
* retain useful local context,
* avoid uncontrolled duplication,
* preserve section or heading information where possible,
* comply with configured size limits.

The MVP may support a limited number of explicitly implemented strategies, such as:

* fixed-size chunking,
* recursive text chunking,
* heading-aware recursive chunking.

A plugin-based chunking framework is not required.

### 6.4.10 Embedding Generation

The system must generate embeddings for indexed chunks using one selected embedding model.

The embedding configuration must record at least:

* model identifier,
* vector dimensions,
* normalization setting where applicable,
* batch size,
* execution timestamp,
* configuration version or snapshot.

Support for multiple embedding providers is not required in the first implementation.

However, the model and dimensions should be configurable to support controlled experiments.

### 6.4.11 OpenSearch Indexing

The MVP must index searchable content in OpenSearch.

Each indexed chunk must include or reference:

* chunk text,
* embedding vector,
* document identifier,
* document-version identifier,
* processing-run identifier,
* section or heading,
* governance status,
* retrieval metadata,
* relevant compliance metadata.

The indexing process must verify that:

* the target index exists,
* the vector dimensions match the index mapping,
* the expected number of chunks was indexed,
* failed writes are detected,
* the document is not marked as available before indexing succeeds.

## 6.5 Data Monitoring Scope

The Data Monitoring MVP must provide visibility into the application-level state of documents, versions, processing runs, and indexes.

It does not replace AWS infrastructure monitoring.

### 6.5.1 Document Monitoring

The user must be able to view a list of ingested documents.

For each document, the system should expose at least:

* document identifier,
* title,
* source type,
* current active version,
* governance status,
* latest processing status,
* last update timestamp.

### 6.5.2 Document-Version Monitoring

The user must be able to inspect the versions associated with a document.

For each version, the system should expose:

* document-version identifier,
* version label where available,
* source filename,
* publication date where available,
* effective date where available,
* governance status,
* S3 source location or controlled source reference,
* latest successful processing run,
* associated index.

### 6.5.3 Processing-Run Monitoring

The user must be able to inspect the processing history of a document version.

A processing run must expose at least:

* run identifier,
* start time,
* completion time,
* current or final status,
* current or failed stage,
* configuration snapshot,
* generated chunk count,
* error summary where applicable,
* target index.

Indicative processing statuses include:

```text
RECEIVED
VALIDATING
STORED
PARSING
NORMALIZING
CHUNKING
EMBEDDING
INDEXING
INDEXED
FAILED
```

The final status model will be refined during technical design.

### 6.5.4 Governance Monitoring

The user must be able to identify whether a document version is:

```text
ACTIVE
SUPERSEDED
DISABLED
DELETED
```

The MVP must ensure that inactive content can be excluded from the normal retrieval path.

The exact approval workflow for changing governance status is not required in the first version.

### 6.5.5 Index Monitoring

The user must be able to inspect the OpenSearch indexes used by the application.

At minimum, the system should expose:

* logical index name,
* physical index name where different,
* creation timestamp,
* embedding model,
* vector dimensions,
* chunking configuration,
* document count,
* chunk count,
* active or inactive status,
* application-level readiness state.

Detailed OpenSearch cluster metrics may remain in AWS monitoring tools.

### 6.5.6 Document-to-Index Traceability

The system must allow the user to determine:

```text
Document
→ Document Version
→ Processing Run
→ Indexing Run
→ OpenSearch Index
```

This relationship must be visible without requiring direct inspection of raw OpenSearch records.

## 6.6 Data Query Scope

The Data Query MVP must provide a controlled interface for retrieval testing and evidence inspection.

### 6.6.1 Query Input

The user must be able to submit a natural-language query.

The query interface may also support a limited set of metadata filters, such as:

* jurisdiction,
* source authority,
* document title,
* governance status,
* publication or effective date,
* document version.

The final list of filters will depend on the approved metadata model.

### 6.6.2 Query Validation

The system must validate:

* empty queries,
* maximum query length,
* unsupported filter values,
* invalid retrieval configuration,
* unavailable target index.

Invalid queries must return a clear error rather than producing misleading empty results.

### 6.6.3 Retrieval Modes

The MVP must support at least one retrieval mode selected as the initial baseline.

The architecture should permit controlled support for:

* BM25 lexical retrieval,
* vector retrieval,
* hybrid retrieval.

Not all three modes need to be fully optimized before the first vertical slice is usable.

However, the project should be able to compare at least two retrieval configurations during the evaluation phase.

### 6.6.4 Ranked Search Results

The query response must return ranked results.

Each result must include at least:

* rank,
* chunk identifier,
* document identifier,
* document-version identifier,
* document title,
* section or heading where available,
* chunk content,
* source metadata,
* governance status,
* available retrieval scores,
* source reference.

The result contract must remain inspectable and suitable for evaluation.

### 6.6.5 Provenance

Every result must be traceable to the original source artifact.

The user must be able to identify:

* which document produced the result,
* which version was used,
* which section contained the content,
* which chunk was retrieved,
* which processing run created the chunk,
* which index served the result.

### 6.6.6 No-Result Behaviour

The system must handle cases where no suitable result is found.

It must distinguish between:

* no indexed content,
* no result after filters,
* query execution failure,
* valid query with no relevant result,
* low-score or low-confidence result set where supported.

The system must not present an empty or weak result as confirmed evidence.

## 6.7 Retrieval Evaluation Scope

The MVP must support repeatable retrieval evaluation.

### 6.7.1 Golden Evaluation Dataset

The system must support an evaluation dataset containing:

* query identifier,
* query text,
* relevant document, section, or chunk identifiers,
* binary or graded relevance judgments,
* optional category or difficulty label,
* optional no-answer designation.

The exact judgment granularity will be finalized during evaluation design.

### 6.7.2 Initial Metrics

The initial required metrics are:

* Precision@10,
* Recall@10,
* nDCG@10.

The evaluation implementation should permit later addition of:

* MRR@10,
* Hit Rate@10,
* Coverage,
* retrieval latency,
* processing time,
* index size.

### 6.7.3 Evaluation Runs

Each evaluation run must record:

* evaluation-run identifier,
* evaluation dataset version,
* target index,
* retrieval configuration,
* top-k,
* applied filters,
* execution timestamp,
* calculated metrics,
* query-level results where practical.

### 6.7.4 Baseline Comparison

The MVP must allow a new evaluation run to be compared with an existing baseline.

The comparison should help determine whether a change:

* improved retrieval quality,
* reduced recall,
* changed result ordering,
* increased latency,
* introduced missing or duplicate results.

A complete experiment-management platform is not required.

A structured report or comparison view is sufficient.

## 6.8 Configuration Scope

The MVP must support controlled configuration for parameters that are expected to change during development and retrieval experimentation.

Initial configurable parameters include:

### Ingestion

* supported file types,
* maximum file size,
* S3 bucket and prefixes,
* parser selection from supported implementations,
* normalization settings.

### Chunking

* chunking strategy,
* chunk size,
* chunk overlap,
* minimum chunk size where applicable,
* heading preservation.

### Embeddings

* model identifier,
* vector dimensions,
* batch size,
* normalization setting,
* execution device where applicable.

### OpenSearch

* endpoint,
* index name,
* index alias where used,
* vector field name,
* similarity metric,
* shard and replica settings where required.

### Retrieval

* retrieval mode,
* top-k,
* candidate count,
* metadata filters,
* lexical and vector weights where applicable,
* fusion parameters where applicable.

### Evaluation

* evaluation dataset,
* K values,
* enabled metrics,
* baseline run or baseline configuration.

Configuration must remain explicit and validated.

The MVP does not require dynamic plugin discovery or arbitrary runtime component loading.

## 6.9 AWS Deployment Scope

The MVP deployment direction includes:

```text
Amazon ECR
→ Container Images

Amazon ECS Fargate
→ FastAPI Application
→ Optional Processing Worker

Amazon S3
→ Source and Processing Artifacts

Amazon OpenSearch Service
→ Searchable Chunks and Embeddings

AWS CloudFormation
→ Infrastructure Provisioning
```

Additional AWS components may be introduced only when justified.

Examples include:

* queue service for background ingestion,
* PostgreSQL-compatible database for operational state,
* Redis for temporary coordination or caching,
* CloudWatch for logs and infrastructure metrics,
* Application Load Balancer for API access.

The MVP does not require all optional components from the beginning.

## 6.10 User Interface Scope

The MVP requires functional interfaces for:

### Data Ingest Page

The user must be able to:

* select a supported file,
* enter required metadata,
* submit the ingestion request,
* view immediate validation errors,
* receive the created document and processing identifiers.

### Data Monitoring Page

The user must be able to:

* view documents,
* inspect versions,
* inspect processing status,
* inspect failures,
* view associated indexes,
* identify active, superseded, or disabled content.

### Data Query Page

The user must be able to:

* submit a query,
* apply supported filters,
* view ranked results,
* inspect source metadata,
* view available retrieval scores,
* initiate or inspect an evaluation run where permitted.

The UI may initially prioritize functionality over final visual design.

The final front-end framework is not part of the MVP reference decision.

## 6.11 Operational Scope

The MVP must include baseline operational discipline.

This includes:

* structured application logs,
* processing-stage logs,
* clear error classification,
* health and readiness endpoints,
* configuration validation,
* dependency checks,
* non-root containers,
* automated tests,
* code-quality checks,
* infrastructure provisioning through CloudFormation.

The MVP is not required to provide global-scale availability or advanced disaster recovery.

## 6.12 Testing Scope

The MVP must include automated testing for critical behaviour.

Testing should cover:

* configuration validation,
* file validation,
* parser behaviour,
* chunk creation,
* stable identifiers,
* duplicate handling,
* metadata preservation,
* embedding-dimension validation,
* OpenSearch indexing contracts,
* retrieval-result contracts,
* evaluation-metric calculations,
* failure-state transitions.

Integration tests should cover the most important end-to-end boundaries.

The exact test suite and coverage thresholds will be defined in the intermediate deliverables and Definition of Done.

## 6.13 Explicitly Deferred From the MVP

The following remain outside the initial MVP:

* PDF and OCR ingestion,
* automated web crawling,
* automatic regulatory updates,
* full legal reasoning,
* final LLM answer generation,
* automatic citation validation,
* multi-agent workflows,
* advanced query decomposition,
* reranking,
* knowledge graphs,
* parent-child retrieval,
* enterprise SSO,
* full RBAC,
* production multi-tenancy,
* arbitrary vector-database support,
* multi-cloud deployment,
* model fine-tuning,
* large-scale optimization.

These capabilities may be introduced only after the core retrieval foundation is stable and measurable.

## 6.14 MVP End-to-End Scenario

A successful MVP should support the following scenario:

```text
1. A Technical Operator uploads a DOCX compliance document.

2. The system validates the file and stores the original artifact in S3.

3. A Document and Document Version are created.

4. The system parses and normalizes the document.

5. Required metadata is attached or confirmed.

6. The document is divided into traceable chunks.

7. Embeddings are generated using the selected configuration.

8. Chunks, vectors, and metadata are indexed in OpenSearch.

9. The Data Monitoring page shows the document as successfully indexed.

10. The operator can inspect the processing run, chunk count, configuration, and target index.

11. The operator submits a compliance query through the Data Query page.

12. The system returns ranked chunks with source, version, section, metadata, and scores.

13. The operator runs the golden evaluation dataset.

14. The system calculates Precision@10, Recall@10, and nDCG@10.

15. The evaluation result is stored with the exact configuration that produced it.
```

## 6.15 MVP Completion Boundary

The MVP is complete at project level when all of the following are demonstrably true:

* at least one supported document format completes the full vertical slice,
* TXT, Markdown, and DOCX are supported before final MVP completion,
* source artifacts are preserved in S3,
* documents and versions are distinguishable,
* processing states are visible,
* indexed chunks preserve provenance,
* OpenSearch retrieval returns inspectable ranked results,
* inactive content can be excluded,
* evaluation datasets can be executed,
* Precision@10, Recall@10, and nDCG@10 are calculated correctly,
* processing and evaluation runs are connected to configuration snapshots,
* the application can be deployed through Docker and CloudFormation,
* critical workflows are covered by automated tests.

Detailed acceptance criteria will be defined later for each intermediate deliverable.

## 6.16 MVP Scope Principle

The MVP should remain the smallest implementation that proves the full controlled lifecycle:

```text
Source Document
→ Searchable Knowledge
→ Observable State
→ Inspectable Retrieval
→ Measurable Quality
```

A feature belongs in the MVP only when it is necessary to prove or protect this lifecycle.

Features that improve sophistication without being required for the end-to-end objective should be deferred.


# 7. Functional Areas

CVS Review Portal is organized around three primary functional areas:

```text
Data Ingest
→ Data Monitoring
→ Data Query and Evaluation
```

These areas represent separate user workflows and responsibility boundaries.

They do not necessarily imply separate microservices or independent deployments.

The initial implementation may remain a modular monolith with clearly separated modules and interfaces.

## 7.1 Data Ingest

Data Ingest is responsible for transforming source documents into searchable content.

Its responsibilities include:

* upload and validation,
* source storage,
* document and version identification,
* parsing and normalization,
* metadata handling,
* chunking,
* embedding generation,
* OpenSearch indexing,
* processing verification.

Detailed requirements are defined in:

```text
01_data_ingest_reference.md
```

## 7.2 Data Monitoring

Data Monitoring provides visibility into the state and history of the compliance knowledge base.

Its responsibilities include monitoring:

* documents,
* document versions,
* processing runs,
* processing failures,
* indexing runs,
* OpenSearch indexes,
* configuration snapshots,
* governance states such as active, superseded, or disabled.

It focuses on application and knowledge lifecycle monitoring rather than infrastructure monitoring.

Detailed requirements are defined in:

```text
02_data_monitoring_reference.md
```

## 7.3 Data Query and Evaluation

Data Query and Evaluation is responsible for retrieving, inspecting, and measuring indexed compliance content.

Its responsibilities include:

* query submission,
* query validation,
* metadata filtering,
* lexical, vector, or hybrid retrieval,
* ranked-result inspection,
* provenance display,
* golden-dataset execution,
* Precision@K, Recall@K, and nDCG@K calculation,
* baseline comparison.

Detailed requirements are defined in:

```text
03_data_query_reference.md
```

## 7.4 Shared Responsibilities

Some capabilities are shared across all three functional areas:

* configuration validation,
* identifiers and data contracts,
* structured logging,
* security,
* error handling,
* auditability,
* configuration traceability,
* testing.

These shared capabilities should be implemented consistently without merging the functional responsibilities of the three areas.

## 7.5 Functional Boundary Principle

Each functional area should have clear inputs, outputs, responsibilities, and failure states.

A component should belong to the area that owns its primary business responsibility.

Cross-area dependencies should use explicit contracts rather than direct access to internal implementation details.


# 8. Core Use Cases

The following use cases define the main user-visible capabilities of the initial CVS Review Portal system.

They describe functional outcomes rather than detailed implementation steps.

## 8.1 UC-01 — Upload a Compliance Document

**Primary Actor:** Technical Operator

The user uploads a supported TXT, Markdown, or DOCX document together with the required metadata.

The system:

* validates the file,
* creates document and version identifiers,
* stores the original artifact,
* and starts a processing run.

**Expected Outcome:**
The source document is safely stored and registered for processing.

## 8.2 UC-02 — Process and Index a Document

**Primary Actor:** System

The system processes a stored document version through:

```text
Parsing
→ Normalization
→ Metadata Handling
→ Chunking
→ Embedding
→ Indexing
```

**Expected Outcome:**
The document becomes searchable only after all required processing and indexing stages complete successfully.

## 8.3 UC-03 — Inspect Document Status

**Primary Actor:** Technical Operator

The user views the current state of an uploaded document.

The system displays information such as:

* document status,
* active version,
* latest processing run,
* failed processing stage,
* generated chunk count,
* associated index.

**Expected Outcome:**
The user can determine whether the document is available, processing, or failed.

## 8.4 UC-04 — Inspect Document Versions

**Primary Actor:** Technical Operator or Compliance User

The user views all registered versions of a logical document.

The system displays:

* version identifier,
* version label,
* publication and effective dates where available,
* governance status,
* processing history,
* associated indexes.

**Expected Outcome:**
The user can distinguish current, previous, superseded, and disabled versions.

## 8.5 UC-05 — Manage Document Governance Status

**Primary Actor:** Technical Operator or Future Compliance Administrator

The user changes the governance state of a document version.

Possible states include:

```text
ACTIVE
SUPERSEDED
DISABLED
DELETED
```

**Expected Outcome:**
Only appropriate document versions remain available through the normal retrieval path.

The exact approval and permission workflow is deferred.

## 8.6 UC-06 — Inspect Processing and Indexing Runs

**Primary Actor:** Technical Operator

The user inspects the history of processing and indexing executions for a document version.

The system displays:

* run identifier,
* processing configuration,
* timestamps,
* completed stages,
* failure details,
* generated chunk count,
* target index.

**Expected Outcome:**
The user can trace how the indexed representation was produced.

## 8.7 UC-07 — Retry or Reprocess a Document Version

**Primary Actor:** Technical Operator

The user retries a failed run or starts a new processing run using the same or updated configuration.

**Expected Outcome:**
The document version is reprocessed without losing the original source artifact or creating uncontrolled duplicate indexed content.

## 8.8 UC-08 — Inspect Available Indexes

**Primary Actor:** Technical Operator or System Administrator

The user views the indexes registered with the application.

The system displays:

* index name,
* active status,
* creation time,
* embedding configuration,
* vector dimensions,
* chunking configuration,
* document count,
* chunk count.

**Expected Outcome:**
The user understands which index is active and what configuration produced it.

## 8.9 UC-09 — Execute a Retrieval Query

**Primary Actor:** AI / Search Engineer or Compliance User

The user submits a natural-language query and may apply supported metadata filters.

The system executes the selected retrieval strategy and returns ranked chunks.

**Expected Outcome:**
The user receives inspectable evidence from active and permitted document versions.

## 8.10 UC-10 — Inspect Retrieval Evidence

**Primary Actor:** AI / Search Engineer or Compliance User

The user examines an individual retrieval result.

The system provides:

* chunk content,
* result rank,
* available retrieval scores,
* source document,
* document version,
* section or heading,
* source authority,
* jurisdiction and dates where available,
* source reference.

**Expected Outcome:**
The user can understand where the result came from and whether it is applicable.

## 8.11 UC-11 — Handle No-Result or Weak-Result Queries

**Primary Actor:** Query User

The system detects when:

* no indexed content is available,
* filters remove all candidates,
* no results are returned,
* retrieval execution fails,
* or available results appear weak according to supported criteria.

**Expected Outcome:**
The system clearly communicates the condition without presenting unsupported evidence as a confident result.

## 8.12 UC-12 — Run a Retrieval Evaluation

**Primary Actor:** AI / Search Engineer

The user selects:

* an evaluation dataset,
* a target index,
* a retrieval configuration,
* and the required metrics.

The system executes all evaluation queries and compares retrieved results with the relevance judgments.

**Expected Outcome:**
The system calculates at least:

* Precision@10,
* Recall@10,
* nDCG@10.

## 8.13 UC-13 — Inspect Evaluation Results

**Primary Actor:** AI / Search Engineer

The user reviews:

* aggregate metrics,
* query-level results,
* missing relevant content,
* ranking differences,
* failed queries,
* execution latency where recorded.

**Expected Outcome:**
The user can identify strengths, weaknesses, and retrieval-quality regressions.

## 8.14 UC-14 — Compare With a Baseline

**Primary Actor:** AI / Search Engineer

The user compares a new evaluation run with an earlier baseline.

The comparison may include:

* metric changes,
* query-level rank changes,
* recall regressions,
* newly retrieved relevant content,
* latency changes.

**Expected Outcome:**
The user can determine whether a configuration change improved or degraded retrieval quality.

## 8.15 UC-15 — Trace a Result to Its Source

**Primary Actor:** Any Authorized User

The user follows a retrieved result back through:

```text
Retrieved Chunk
→ Processing Run
→ Document Version
→ Original Source Artifact
```

**Expected Outcome:**
Every result can be traced to the source content and processing configuration that produced it.

## 8.16 Core Use-Case Boundary

The initial use cases focus on:

```text
Controlled Ingestion
→ Observable Knowledge State
→ Inspectable Retrieval
→ Measurable Quality
```

Use cases involving final LLM-generated answers, autonomous compliance reasoning, complex review workflows, or multi-agent orchestration remain outside the initial MVP.


# 9. System Context

CVS Review Portal operates as a controlled application layer between users, source documents, AWS storage, and the retrieval infrastructure.

Its primary responsibility is to transform compliance documents into traceable searchable content and expose that content through monitoring, query, and evaluation workflows.

## 9.1 High-Level Context

```text
Users
  │
  ▼
CVS Review Portal Application
  │
  ├── Data Ingest
  ├── Data Monitoring
  └── Data Query and Evaluation
  │
  ├── AWS S3
  ├── OpenSearch
  └── Optional Operational State Store
```

The application coordinates document processing and retrieval but does not replace the underlying AWS services.

## 9.2 Primary Actors

The primary actors interacting with the system are:

* AI / Search Engineer,
* Compliance User,
* System Administrator,
* future Compliance Reviewer or Auditor.

Each actor accesses only the workflows relevant to their responsibilities.

## 9.3 CVS Review Portal Application Boundary

Inside the CVS Review Portal application boundary are:

* upload and validation workflows,
* document identity and version management,
* parsing and normalization,
* metadata handling,
* chunking,
* embedding generation,
* OpenSearch indexing,
* document and processing monitoring,
* retrieval execution,
* result inspection,
* evaluation execution,
* configuration traceability.

The exact internal module and deployment structure will be defined during technical design.

## 9.4 AWS S3

AWS S3 stores canonical source artifacts and selected derived artifacts.

It may contain:

* original uploaded documents,
* normalized or parsed outputs,
* evaluation datasets,
* generated reports,
* reproducibility artifacts.

S3 is the durable artifact-storage layer.

It is not the primary query or retrieval interface.

## 9.5 OpenSearch

OpenSearch acts as the serving and retrieval layer.

It stores:

* searchable chunk text,
* embedding vectors,
* retrieval metadata,
* document and version references,
* governance-status fields,
* filtering fields.

OpenSearch may support:

* BM25 lexical retrieval,
* vector retrieval,
* metadata filtering,
* hybrid retrieval.

The OpenSearch index is a derived representation and may be rebuilt from canonical source artifacts and configuration records.

## 9.6 Operational State Store

The system may require a durable operational state store for entities such as:

* documents,
* document versions,
* processing runs,
* processing stages,
* indexing runs,
* registered indexes,
* configuration snapshots,
* evaluation runs.

PostgreSQL is a likely option, but it is not considered mandatory until the detailed data model confirms the requirement.

Operational state must not be stored only in application memory.

## 9.7 Embedding Model

The embedding model converts document chunks and user queries into vector representations.

The model may initially be:

* hosted inside the application or worker container,
* accessed through an external model service,
* or deployed as a separate inference component.

The final execution model will depend on:

* selected embedding model,
* memory and compute requirements,
* throughput,
* cost,
* deployment simplicity.

The embedding model does not own document state or retrieval decisions.

## 9.8 User Interface

The initial system will include three functional pages:

```text
Data Ingest
Data Monitoring
Data Query
```

The interface may be implemented using a lightweight web application suitable for technical testing.

The final front-end framework remains an open decision.

The UI communicates with the application through explicit API contracts.

## 9.9 Infrastructure Monitoring Boundary

Application-level monitoring belongs within CVS Review Portal and includes:

* document status,
* document-version status,
* processing runs,
* indexing runs,
* configuration traceability,
* retrieval and evaluation results.

Infrastructure-level monitoring remains primarily within AWS services such as CloudWatch and the OpenSearch, ECS, and S3 consoles.

Examples include:

* ECS task health,
* CPU and memory utilization,
* container restarts,
* OpenSearch cluster health,
* AWS service availability,
* infrastructure-level alerts.

## 9.10 Initial Deployment Context

The initial AWS deployment direction is:

```text
User
  │
  ▼
Application Endpoint
  │
  ▼
ECS Fargate
  ├── FastAPI Application
  └── Optional Processing Worker
        │
        ├── S3
        ├── OpenSearch
        └── Optional Operational Store
```

Container images will be stored in Amazon ECR.

Infrastructure resources will be provisioned through CloudFormation.

A background queue, PostgreSQL, Redis, or separate worker service will be added only when required by the final processing and state-management design.

## 9.11 External Systems

The initial MVP does not require integration with:

* external regulatory websites,
* enterprise document-management systems,
* identity providers,
* ticketing systems,
* external compliance platforms,
* web crawlers,
* third-party legal databases.

Such integrations may be introduced later through controlled ingestion or API adapters.

## 9.12 Trust Boundaries

The main trust boundaries are:

```text
User Input
→ Application Validation

Application
→ AWS Services

Source Artifact
→ Derived Processing Output

Operational Metadata
→ Search Index

Retrieved Result
→ Human Interpretation
```

Each boundary requires validation, authorization, logging, and traceability appropriate to its risk.

Retrieved content must remain evidence for human analysis and must not automatically be treated as a final compliance judgment.

## 9.13 Context Boundary Principle

CVS Review Portal owns the application and knowledge lifecycle.

It does not own:

* the legal authority of the original source,
* the correctness of user-supplied metadata without review,
* the availability of external regulatory sources,
* final legal or compliance decisions,
* the full infrastructure-monitoring lifecycle.

The system must make these boundaries visible so that technical retrieval quality is not confused with legal authority or compliance correctness.


# 10. Logical Components

CVS Review Portal is composed of logical components with clear responsibilities across:

```text
Data Ingest
→ Data Monitoring
→ Data Query and Evaluation
```

These components describe functional boundaries.

They do not necessarily represent separate services, containers, repositories, or deployment units.

The initial implementation may use a modular monolith with an optional background worker.

## 10.1 User Interface

The User Interface provides access to the three primary application areas:

```text
Data Ingest Page
Data Monitoring Page
Data Query Page
```

Its responsibilities include:

* collecting user input,
* displaying validation errors,
* showing processing and index state,
* displaying ranked retrieval results,
* presenting evaluation metrics.

The UI must communicate with the backend through explicit API contracts and must not directly access S3, OpenSearch, or the operational state store.

## 10.2 Application API

The Application API is the primary entry point for UI and external client requests.

It is responsible for:

* request validation,
* authorization where applicable,
* routing requests to the appropriate application component,
* returning stable response contracts,
* translating domain errors into appropriate API responses.

FastAPI will provide the initial API layer.

## 10.3 Upload and Validation Component

This component receives uploaded source documents and validates them before processing.

Its responsibilities include:

* validating supported file types,
* checking file-size limits,
* rejecting empty or unreadable files,
* validating required metadata,
* generating or accepting stable request identifiers,
* preventing invalid files from entering the processing pipeline.

It does not parse, chunk, embed, or index document content.

## 10.4 Document Registry

The Document Registry manages the logical identity and lifecycle of documents and document versions.

It is responsible for recording relationships between:

```text
Document
→ Document Version
→ Source Artifact
→ Processing Run
→ Indexing Run
```

Its responsibilities may include:

* document identifiers,
* document-version identifiers,
* version labels,
* publication and effective dates,
* governance status,
* source references,
* active-version relationships.

The registry represents application state rather than searchable document content.

## 10.5 Artifact Storage Component

The Artifact Storage Component manages access to canonical and derived artifacts stored in S3.

Its responsibilities include:

* storing original uploaded files,
* generating controlled object keys,
* retrieving source artifacts for reprocessing,
* storing selected parsed or normalized outputs,
* storing evaluation datasets and reports,
* verifying successful storage operations.

The component should hide direct S3 implementation details from higher-level application modules.

## 10.6 Processing Orchestrator

The Processing Orchestrator coordinates the document-processing lifecycle.

It manages the ordered execution of stages such as:

```text
Validation
→ Parsing
→ Normalization
→ Metadata Handling
→ Chunking
→ Embedding
→ Indexing
→ Verification
```

Its responsibilities include:

* creating processing runs,
* tracking stage transitions,
* passing validated contracts between stages,
* stopping processing after unrecoverable failures,
* coordinating retries,
* preventing partial processing from being marked successful.

The initial orchestrator should remain deterministic.

LangGraph is not required unless later workflows introduce genuine conditional, stateful, or human-in-the-loop behaviour.

## 10.7 Parser Components

Parser Components convert supported source files into a common parsed-document representation.

Initial parser implementations will support:

* TXT,
* Markdown,
* DOCX.

Each parser is responsible for extracting:

* document text,
* paragraphs,
* headings where available,
* lists where available,
* basic structural information,
* source-format metadata.

Parsers should produce a consistent internal contract regardless of the source format.

## 10.8 Text Normalization Component

The Text Normalization Component prepares parsed text for metadata extraction and chunking.

Its responsibilities may include:

* normalizing encoding,
* normalizing whitespace and line endings,
* removing unsupported control characters,
* preserving meaningful paragraph boundaries,
* preserving headings and section order,
* identifying empty or unusable content.

Normalization rules must be controlled and testable.

They must not silently remove legally or semantically important content.

## 10.9 Metadata Component

The Metadata Component validates, derives, enriches, and normalizes document metadata.

Metadata may originate from:

* user-provided upload fields,
* document properties,
* deterministic extraction rules,
* filenames,
* manually reviewed values.

Indicative metadata includes:

* title,
* source authority,
* jurisdiction,
* publication date,
* effective date,
* version label,
* document type,
* section or heading,
* governance status.

The component must distinguish between confirmed metadata and automatically derived metadata where this distinction is operationally important.

## 10.10 Chunking Component

The Chunking Component converts normalized document content into traceable retrieval units.

Its responsibilities include:

* applying the selected chunking strategy,
* respecting configured size and overlap,
* preserving section context,
* generating stable or reproducible chunk identifiers,
* associating chunks with document and processing metadata,
* avoiding empty or uncontrolled duplicate chunks.

The MVP may support a small number of explicit chunking strategies.

A dynamic plugin framework is not required.

## 10.11 Embedding Component

The Embedding Component converts document chunks and queries into vector representations.

Its responsibilities include:

* loading or accessing the selected embedding model,
* validating model configuration,
* processing embeddings in controlled batches,
* validating vector dimensions,
* recording model and execution metadata,
* handling model or inference failures.

Document and query embeddings must use compatible model and normalization settings.

## 10.12 OpenSearch Index Management Component

The Index Management Component manages application-level OpenSearch index definitions and lifecycle information.

Its responsibilities may include:

* creating indexes from approved mappings,
* validating mappings,
* validating vector dimensions,
* registering index metadata,
* identifying active and inactive indexes,
* supporting controlled reindexing,
* supporting aliases if selected later,
* reporting application-level index readiness.

It does not replace OpenSearch infrastructure administration or AWS monitoring.

## 10.13 Indexing Component

The Indexing Component writes processed chunks and metadata into OpenSearch.

Its responsibilities include:

* preparing index documents,
* performing batch writes,
* detecting partial failures,
* verifying indexed counts,
* preventing incompatible vectors from being written,
* recording indexing-run results,
* associating indexed content with its source and configuration.

A document version must not be marked retrievable until required indexing verification succeeds.

## 10.14 Monitoring and Registry Query Component

This component provides application-level views over:

* documents,
* versions,
* processing runs,
* processing stages,
* indexing runs,
* indexes,
* governance states,
* configuration snapshots.

It supports the Data Monitoring page and associated APIs.

It should retrieve operational state through application contracts rather than requiring users to inspect raw database or OpenSearch records.

## 10.15 Governance Component

The Governance Component manages the usability state of document versions.

Indicative states include:

```text
ACTIVE
SUPERSEDED
DISABLED
DELETED
```

Its responsibilities may include:

* validating permitted state transitions,
* recording status changes,
* selecting the active version,
* excluding inactive content from normal retrieval,
* preserving governance history where required.

The first version may implement simplified governance actions without a complete approval workflow.

## 10.16 Query Processing Component

The Query Processing Component prepares user queries for retrieval.

Its responsibilities include:

* validating query input,
* normalizing query text,
* validating metadata filters,
* selecting an approved retrieval configuration,
* generating query embeddings where required,
* forwarding retrieval requests to the retrieval component.

Advanced query rewriting, decomposition, and agentic planning are deferred.

## 10.17 Retrieval Component

The Retrieval Component executes searches against OpenSearch.

Depending on the selected configuration, it may support:

* BM25 lexical retrieval,
* vector retrieval,
* hybrid retrieval,
* metadata filtering,
* candidate fusion,
* top-k selection.

Its responsibilities include:

* applying the correct index and retrieval configuration,
* excluding inactive content,
* returning ranked results,
* preserving available scoring information,
* distinguishing execution failures from valid empty results.

## 10.18 Result Assembly Component

The Result Assembly Component converts raw OpenSearch responses into stable application-level result contracts.

Each result should contain or reference:

* rank,
* chunk identifier,
* document identifier,
* document-version identifier,
* document title,
* section or heading,
* chunk content,
* relevant metadata,
* available scores,
* source reference,
* processing and index provenance where required.

This component prevents OpenSearch-specific response structures from leaking directly into the UI or external API.

## 10.19 Evaluation Dataset Component

The Evaluation Dataset Component manages golden queries and relevance judgments.

Its responsibilities include:

* loading evaluation datasets,
* validating dataset structure,
* versioning datasets,
* representing relevant documents, sections, or chunks,
* supporting binary or graded relevance,
* supporting no-answer cases where applicable.

Evaluation datasets may initially be stored as controlled JSONL or similar artifacts.

## 10.20 Evaluation Engine

The Evaluation Engine executes retrieval queries against a selected configuration and calculates metrics.

The initial metrics include:

* Precision@10,
* Recall@10,
* nDCG@10.

Its responsibilities include:

* running the complete evaluation dataset,
* recording query-level retrieval results,
* comparing results with relevance judgments,
* calculating aggregate metrics,
* recording execution metadata,
* preserving the configuration snapshot.

The metric implementations must be independently testable.

## 10.21 Baseline Comparison Component

The Baseline Comparison Component compares evaluation runs.

It may report:

* aggregate metric changes,
* query-level improvements,
* query-level regressions,
* newly retrieved relevant results,
* lost relevant results,
* ranking changes,
* latency differences where available.

The MVP does not require a complete experiment-management platform.

A structured comparison report is sufficient.

## 10.22 Configuration Component

The Configuration Component loads and validates application, ingestion, retrieval, and evaluation settings.

Its responsibilities include:

* reading configuration files,
* reading environment-specific values,
* validating supported options,
* rejecting incompatible combinations,
* creating immutable configuration snapshots,
* associating snapshots with processing and evaluation runs.

Secrets must not be stored in project configuration files.

AWS credentials and sensitive values must be supplied through appropriate environment and IAM mechanisms.

## 10.23 Operational State Component

The Operational State Component persists application state that must survive process or container restarts.

This may include:

* document records,
* document versions,
* processing runs,
* stage status,
* indexing runs,
* index registry records,
* governance changes,
* evaluation runs,
* configuration snapshots.

The final persistence technology will be selected after the entity and consistency requirements are defined.

PostgreSQL remains a likely option.

## 10.24 Observability Component

The Observability Component provides structured technical and business-process visibility.

It should support:

* structured logs,
* correlation identifiers,
* document and processing identifiers,
* stage duration,
* failure classification,
* chunk counts,
* indexing counts,
* retrieval latency,
* evaluation duration,
* health and readiness information.

Application logs should avoid uncontrolled exposure of document content, credentials, or other sensitive values.

## 10.25 Shared Contracts

Components must exchange data through explicit contracts.

Indicative shared contracts include:

```text
DocumentRecord
DocumentVersion
SourceArtifact
ParsedDocument
NormalizedDocument
Chunk
ProcessingRun
IndexingRun
IndexRecord
QueryRequest
SearchResult
EvaluationDataset
EvaluationRun
ConfigurationSnapshot
```

The final models will be defined during detailed design.

Contracts should distinguish domain entities from S3, OpenSearch, FastAPI, and database-specific representations.

## 10.26 Initial Deployment Mapping

A possible initial deployment mapping is:

```text
FastAPI Application
├── Application API
├── Upload and Validation
├── Document Registry Access
├── Data Monitoring APIs
├── Query Processing
├── Retrieval
└── Evaluation APIs

Processing Worker
├── Processing Orchestrator
├── Parsers
├── Normalization
├── Metadata Handling
├── Chunking
├── Embeddings
└── Indexing
```

Both processes may use:

* the same Python codebase,
* the same container image,
* different startup commands.

This mapping is a likely implementation direction rather than a final architectural commitment.

## 10.27 Logical Component Principle

Each component should have:

* one clear primary responsibility,
* explicit inputs and outputs,
* defined failure behaviour,
* testable contracts,
* minimal knowledge of infrastructure-specific details outside its responsibility.

Logical separation should improve maintainability and testability without creating premature service boundaries or unnecessary abstractions.


# 11. Core Domain Entities

CVS Review Portal uses a limited set of domain entities to represent the lifecycle of documents, processing, indexing, retrieval, and evaluation.

These entities define conceptual boundaries.

They do not yet represent final database tables, Pydantic models, OpenSearch mappings, or API schemas.

## 11.1 Entity Relationship Overview

```text
Document
  └── Document Version
        ├── Source Artifact
        └── Processing Run
              ├── Processing Stages
              ├── Produced Artifacts
              ├── Chunks
              └── Indexing Run
                    └── Search Index

Query
  └── Retrieval Run
        └── Search Results
              └── Retrieved Chunks

Evaluation Dataset
  ├── Evaluation Queries
  └── Relevance Judgments

Evaluation Run
  ├── Retrieval Runs
  ├── Metric Results
  └── Configuration Snapshot
```

## 11.2 Document

A Document represents a logical compliance source independently of any specific uploaded file or version.

Examples include:

* the EU AI Act,
* an internal AI governance policy,
* an ISO standard,
* a regulatory guideline,
* a compliance procedure.

Indicative attributes include:

* document identifier,
* canonical title,
* document type,
* source authority,
* jurisdiction,
* description,
* creation timestamp,
* current active-version reference.

A Document may have multiple Document Versions.

The Document itself does not represent searchable content.

## 11.3 Document Version

A Document Version represents a specific edition, release, amendment state, or uploaded source version of a Document.

Indicative attributes include:

* document-version identifier,
* document identifier,
* version label,
* publication date,
* effective date,
* expiration or withdrawal date where applicable,
* source authority,
* jurisdiction,
* governance status,
* source-artifact reference,
* creation timestamp.

Possible governance states include:

```text
ACTIVE
SUPERSEDED
DISABLED
DELETED
```

A new Processing Run does not automatically create a new Document Version.

The same Document Version may be processed multiple times using different technical configurations.

## 11.4 Source Artifact

A Source Artifact represents the original file stored in S3.

Indicative attributes include:

* source-artifact identifier,
* document-version identifier,
* original filename,
* media type,
* file extension,
* file size,
* content checksum,
* S3 bucket and object key,
* upload timestamp,
* uploader or actor identifier where available.

The Source Artifact is canonical input data.

It must remain independent from OpenSearch indexes and derived processing outputs.

## 11.5 Derived Artifact

A Derived Artifact represents an output produced during document processing and stored outside the search index.

Examples may include:

* parsed document representation,
* normalized text,
* extracted metadata,
* chunk export,
* processing manifest,
* evaluation report.

Indicative attributes include:

* artifact identifier,
* artifact type,
* document-version identifier,
* processing-run identifier,
* storage reference,
* checksum,
* creation timestamp.

Not every intermediate representation must be stored permanently.

The required retained artifacts will be decided according to reproducibility, debugging, cost, and auditability needs.

## 11.6 Processing Run

A Processing Run represents one execution of the ingestion-processing pipeline for a specific Document Version.

A Processing Run may use a different:

* parser version,
* normalization configuration,
* chunking configuration,
* embedding model,
* metadata logic,
* target index.

Indicative attributes include:

* processing-run identifier,
* document-version identifier,
* configuration-snapshot identifier,
* status,
* current stage,
* start and completion timestamps,
* generated chunk count,
* failure summary,
* retry or parent-run reference.

Possible high-level statuses include:

```text
PENDING
RUNNING
SUCCEEDED
FAILED
CANCELLED
```

A successful Processing Run does not by itself guarantee that indexed content is active for retrieval.

## 11.7 Processing Stage Execution

A Processing Stage Execution represents the execution state of an individual stage within a Processing Run.

Indicative stages include:

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

Indicative attributes include:

* stage-execution identifier,
* processing-run identifier,
* stage name,
* status,
* attempt number,
* start and completion timestamps,
* input-artifact reference,
* output-artifact reference,
* error category,
* error summary.

This entity enables stage-level monitoring, controlled retries, and failure diagnosis.

A simplified implementation may initially store stage information within the Processing Run rather than as a separate persistence entity.

## 11.8 Chunk

A Chunk represents a traceable retrieval unit derived from a specific Document Version and Processing Run.

Indicative attributes include:

* chunk identifier,
* document identifier,
* document-version identifier,
* processing-run identifier,
* sequence number,
* chunk text,
* section or heading,
* parent-section reference,
* source-position information,
* token or character count,
* chunking-configuration reference,
* content checksum,
* governance metadata.

A Chunk must preserve sufficient provenance to trace it back to the original source.

Chunk identity must distinguish between:

* the logical source content,
* and the specific processed representation.

Changing the chunking strategy may produce new Chunk identifiers without creating a new Document Version.

## 11.9 Embedding Record

An Embedding Record represents the vector representation generated for a Chunk or Query.

Indicative attributes include:

* embedding-record identifier,
* source entity type,
* source entity identifier,
* model identifier,
* vector dimensions,
* normalization setting,
* embedding-configuration reference,
* creation timestamp.

The vector itself may be stored directly within OpenSearch rather than in the operational state store.

The operational model only needs to preserve enough information to verify compatibility and reproducibility.

## 11.10 Index Record

An Index Record represents an OpenSearch index known to CVS Review Portal.

It describes the application-level purpose and configuration of the index rather than OpenSearch infrastructure internals.

Indicative attributes include:

* index-record identifier,
* logical index name,
* physical index name,
* alias where applicable,
* lifecycle status,
* creation timestamp,
* chunking-configuration reference,
* embedding-configuration reference,
* vector dimensions,
* similarity metric,
* mapping version,
* document count,
* chunk count,
* readiness status.

Possible lifecycle states include:

```text
BUILDING
READY
ACTIVE
INACTIVE
FAILED
DEPRECATED
```

An index may contain content from multiple Documents and Document Versions.

## 11.11 Indexing Run

An Indexing Run represents one controlled attempt to write processed chunks into an OpenSearch index.

Indicative attributes include:

* indexing-run identifier,
* processing-run identifier,
* target index-record identifier,
* expected chunk count,
* successful write count,
* failed write count,
* verification status,
* start and completion timestamps,
* error summary.

The Indexing Run distinguishes successful document processing from successful search-index publication.

A Document Version must not be considered retrievable until the required indexing verification succeeds.

## 11.12 Configuration Snapshot

A Configuration Snapshot represents the immutable configuration used by a processing, retrieval, or evaluation run.

It may include:

* parser settings,
* normalization settings,
* chunking strategy,
* chunk size,
* chunk overlap,
* embedding model,
* vector dimensions,
* index mapping version,
* retrieval mode,
* top-k,
* fusion parameters,
* enabled filters,
* evaluation metric settings.

Indicative attributes include:

* configuration-snapshot identifier,
* configuration type,
* configuration content or reference,
* checksum,
* creation timestamp,
* application or code version.

Configuration Snapshots allow results to be reproduced and compared without depending on the current configuration file.

## 11.13 Query Request

A Query Request represents the validated user input submitted to the retrieval system.

Indicative attributes include:

* query identifier,
* query text,
* metadata filters,
* requested top-k,
* requested retrieval mode,
* target index or active-index reference,
* actor identifier where available,
* submission timestamp.

The raw user request and the normalized retrieval representation may be stored separately when necessary.

## 11.14 Retrieval Run

A Retrieval Run represents one execution of a Query Request against a specific index and retrieval configuration.

Indicative attributes include:

* retrieval-run identifier,
* query identifier,
* target index-record identifier,
* configuration-snapshot identifier,
* execution status,
* result count,
* retrieval latency,
* execution timestamp,
* error information where applicable.

A repeated Query Request may produce multiple Retrieval Runs when executed against different indexes or configurations.

## 11.15 Search Result

A Search Result represents one ranked Chunk returned by a Retrieval Run.

Indicative attributes include:

* retrieval-run identifier,
* chunk identifier,
* rank,
* lexical score where available,
* vector score where available,
* fused score where available,
* document identifier,
* document-version identifier,
* section or heading,
* source reference,
* result metadata.

Search Results are derived results rather than canonical records.

They may be stored for evaluation, comparison, debugging, or audit purposes where justified.

## 11.16 Evaluation Dataset

An Evaluation Dataset represents a versioned collection of queries and relevance judgments used to measure retrieval quality.

Indicative attributes include:

* evaluation-dataset identifier,
* name,
* version,
* description,
* domain scope,
* creation timestamp,
* reviewer or owner where available,
* storage reference,
* status.

Possible statuses include:

```text
DRAFT
REVIEWED
APPROVED
ARCHIVED
```

Evaluation Dataset versioning is important because metric results are only comparable when the judgment set is known.

## 11.17 Evaluation Query

An Evaluation Query represents one predefined information need within an Evaluation Dataset.

Indicative attributes include:

* evaluation-query identifier,
* evaluation-dataset identifier,
* query text,
* category,
* difficulty level,
* expected filters where applicable,
* no-answer designation,
* notes or rationale.

An Evaluation Query should represent a realistic user information need rather than merely repeating the wording of a source document.

## 11.18 Relevance Judgment

A Relevance Judgment records whether a specific document, section, or chunk is relevant to an Evaluation Query.

Indicative attributes include:

* relevance-judgment identifier,
* evaluation-query identifier,
* target entity type,
* target entity identifier,
* relevance grade,
* reviewer identifier where available,
* judgment timestamp,
* justification or notes.

The target entity may be:

```text
DOCUMENT
DOCUMENT_VERSION
SECTION
CHUNK
```

The selected judgment granularity must remain consistent within an evaluation design.

Graded judgments may use a controlled scale such as:

```text
0 = Not Relevant
1 = Partially Relevant
2 = Relevant
3 = Highly Relevant
```

The final scale will be defined in the evaluation strategy.

## 11.19 Evaluation Run

An Evaluation Run represents one execution of an Evaluation Dataset against a selected index and retrieval configuration.

Indicative attributes include:

* evaluation-run identifier,
* evaluation-dataset identifier and version,
* target index-record identifier,
* configuration-snapshot identifier,
* status,
* start and completion timestamps,
* query count,
* failed-query count,
* aggregate metric results,
* execution duration.

An Evaluation Run must remain connected to both:

* the exact evaluation dataset,
* and the exact retrieval configuration.

## 11.20 Metric Result

A Metric Result represents a calculated evaluation value.

Indicative attributes include:

* metric-result identifier,
* evaluation-run identifier,
* metric name,
* K value,
* aggregate value,
* optional query-level value,
* calculation version.

Initial metric names include:

```text
PRECISION
RECALL
NDCG
```

Metric implementations must be versioned or otherwise controlled when calculation behaviour changes.

## 11.21 Governance Event

A Governance Event records a meaningful change to the usability or authority status of a Document Version.

Examples include:

* version activated,
* version superseded,
* version disabled,
* metadata corrected,
* source authority confirmed.

Indicative attributes include:

* governance-event identifier,
* document-version identifier,
* event type,
* previous state,
* new state,
* actor identifier,
* timestamp,
* reason or notes.

A complete Governance Event model may be deferred from the earliest MVP, but important state changes should remain traceable.

## 11.22 Audit Event

An Audit Event represents a significant user or system action that may require historical traceability.

Examples include:

* document uploaded,
* processing retried,
* index activated,
* configuration changed,
* evaluation executed,
* governance status changed.

Indicative attributes include:

* audit-event identifier,
* actor type and identifier,
* action,
* affected entity type,
* affected entity identifier,
* timestamp,
* correlation identifier,
* outcome,
* relevant state changes.

Audit logging must remain distinct from general application debugging logs.

## 11.23 Entity Identity Principles

Core entities must use stable identifiers that do not depend solely on:

* filenames,
* display titles,
* database row numbers,
* OpenSearch internal identifiers,
* S3 object paths.

Identifiers should support:

* traceability,
* idempotency,
* reprocessing,
* retries,
* index migration,
* API references.

Content checksums may support duplicate detection but should not automatically replace explicit entity identifiers.

## 11.24 Entity Versioning Principles

The system must distinguish between different forms of versioning:

```text
Document Version
→ change in the source document or its authoritative edition

Processing Configuration Version
→ change in how the source is transformed

Index Version
→ change in the searchable representation or mapping

Evaluation Dataset Version
→ change in queries or relevance judgments

Application Version
→ change in the implementation
```

These versions must not be merged into a single generic version field.

## 11.25 Canonical and Derived Entity Boundary

Canonical entities and artifacts include:

* Document,
* Document Version,
* Source Artifact,
* confirmed governance metadata.

Derived entities and artifacts include:

* Parsed Document,
* Normalized Document,
* Chunk,
* Embedding,
* Search Index content,
* Search Result,
* Metric Result.

Derived content may be regenerated.

Canonical source identity and governance history must remain available independently.

## 11.26 Initial MVP Entity Set

The first implementation does not need to persist every entity described in this chapter independently.

The minimum likely persistent set is:

```text
Document
Document Version
Source Artifact
Processing Run
Chunk or Chunk Manifest
Index Record
Indexing Run
Configuration Snapshot
Evaluation Dataset
Evaluation Run
```

Entities such as Processing Stage Execution, Governance Event, Audit Event, and individual Metric Result records may initially use simplified representations.

The final persistence model will be defined after workflow, consistency, monitoring, and query requirements are refined.

## 11.27 Domain Entity Principle

Each entity must represent one clear business or processing concept.

The model must preserve the distinctions between:

```text
Source Identity
Source Version
Processing Execution
Search Representation
Retrieval Execution
Evaluation Execution
```

These distinctions are necessary for reliable monitoring, reproducibility, controlled reprocessing, and compliance-oriented traceability.



# 12. Document Lifecycle

The Document Lifecycle defines how a compliance source enters CVS Review Portal, becomes searchable, remains governed, and is eventually superseded, disabled, or removed from the serving layer.

The lifecycle must distinguish between:

```text
Source Lifecycle
Processing Lifecycle
Indexing Lifecycle
Governance Lifecycle
```

These lifecycles are related but must not be treated as the same state model.

## 12.1 Lifecycle Overview

A typical document lifecycle is:

```text
Upload
→ Validate
→ Store Source Artifact
→ Register Document and Version
→ Process
→ Index
→ Verify
→ Activate for Retrieval
→ Monitor
→ Reprocess or Supersede
→ Disable or Delete
```

A document must not become available for normal retrieval until all required stages have completed successfully.

## 12.2 Document Creation

A Document is created when a new logical compliance source is introduced into the system.

Examples include:

* a regulation,
* a standard,
* an internal policy,
* a regulatory guideline,
* a compliance procedure.

Document creation establishes the logical identity of the source independently of any specific file version.

A Document may later contain multiple Document Versions.

## 12.3 Document Version Creation

A Document Version is created when a specific edition, amendment state, publication, or source revision is uploaded.

A new Document Version should be created when the source content or authoritative edition changes.

Examples include:

* a new regulatory publication,
* an amended policy,
* an updated standard,
* a revised internal procedure,
* a corrected official release.

Reprocessing the same source version with a different chunking or embedding configuration does not automatically create a new Document Version.

## 12.4 Upload and Validation

The lifecycle begins when an authorized user submits:

* a supported source file,
* required document metadata,
* optional version and governance metadata.

The upload must be validated before processing continues.

Validation may include:

* supported file type,
* maximum file size,
* non-empty content,
* basic readability,
* required metadata,
* checksum generation,
* duplicate detection.

A failed validation must stop the lifecycle before the file is registered as successfully ingested.

## 12.5 Source Artifact Storage

After validation, the original source file is stored in S3.

Successful source storage must be confirmed before downstream processing begins.

The stored artifact must remain associated with:

* Document,
* Document Version,
* original filename,
* content checksum,
* S3 location,
* upload timestamp.

The original artifact is the canonical processing input.

Derived chunks or indexed content must never replace it as the source of truth.

## 12.6 Initial Source State

After successful registration and storage, the Document Version may enter an initial source state such as:

```text
REGISTERED
```

or:

```text
STORED
```

The final naming will be defined during detailed design.

This state means that:

* the source artifact exists,
* the version has been registered,
* processing may begin.

It does not mean that the document is searchable.

## 12.7 Processing Run Creation

Each execution of the processing pipeline creates a new Processing Run.

The Processing Run must be associated with:

* Document Version,
* source artifact,
* configuration snapshot,
* application version where required,
* target index or index-building intent.

The same Document Version may have multiple Processing Runs.

Examples include:

```text
Run 1
→ Chunk size 500
→ Embedding Model A

Run 2
→ Chunk size 800
→ Embedding Model A

Run 3
→ Chunk size 800
→ Embedding Model B
```

These are different technical representations of the same source version.

## 12.8 Processing Lifecycle

The initial processing stages are:

```text
VALIDATION
→ PARSING
→ NORMALIZATION
→ METADATA_HANDLING
→ CHUNKING
→ EMBEDDING
→ INDEXING
→ VERIFICATION
```

The processing lifecycle must make the current stage and outcome visible.

Indicative Processing Run statuses include:

```text
PENDING
RUNNING
SUCCEEDED
FAILED
CANCELLED
```

The detailed stage status may use:

```text
NOT_STARTED
RUNNING
SUCCEEDED
FAILED
SKIPPED
```

## 12.9 Parsing

During parsing, the system converts the source format into a common internal document representation.

The parsing stage should preserve, where available:

* headings,
* paragraphs,
* lists,
* section order,
* basic document structure.

If parsing fails, the Processing Run must be marked as failed.

The document must not proceed with incomplete or unreadable parsed content.

## 12.10 Normalization

Normalization prepares parsed content for chunking and retrieval.

It may include:

* whitespace normalization,
* encoding normalization,
* line-ending normalization,
* removal of unsupported control characters,
* preservation of meaningful structural boundaries.

The normalized output must remain traceable to the original source.

Normalization must not silently remove legally or semantically significant content.

## 12.11 Metadata Handling

Document and section metadata may be:

* supplied by the user,
* derived from file properties,
* extracted through deterministic logic,
* manually completed,
* enriched later.

The system must validate required metadata before making content active for retrieval.

Metadata confidence or origin should be preserved where relevant.

For example:

```text
USER_CONFIRMED
SOURCE_DERIVED
SYSTEM_DERIVED
```

The final metadata-origin model may be simplified in the MVP.

## 12.12 Chunking

The Chunking stage creates traceable retrieval units.

Each Chunk must remain associated with:

* Document,
* Document Version,
* Processing Run,
* sequence or source position,
* section or heading,
* chunking configuration.

Chunk generation must detect conditions such as:

* empty output,
* unexpectedly low chunk count,
* uncontrolled duplication,
* chunks exceeding configured limits.

A new chunking configuration creates a new processed representation, not a new source version.

## 12.13 Embedding

The Embedding stage creates vector representations for the generated chunks.

The system must verify:

* model configuration,
* expected vector dimensions,
* successful batch completion,
* compatibility with the target index mapping.

A partial embedding batch must not be treated as complete processing unless the missing items are explicitly identified and recovered.

## 12.14 Indexing

The Indexing stage writes searchable chunks, embeddings, and metadata into OpenSearch.

The system must record:

* target index,
* expected chunk count,
* successfully indexed count,
* failed count,
* indexing timestamps,
* indexing errors.

The source Document Version must not be marked as retrievable merely because some chunks were successfully written.

## 12.15 Index Verification

After indexing, the system must verify that the expected searchable representation exists.

Verification may include:

* expected and actual chunk counts,
* required metadata fields,
* vector-dimension compatibility,
* absence of failed bulk writes,
* retrievability of test records,
* index readiness.

Only after verification succeeds may the Processing Run be marked as successfully completed.

## 12.16 Retrieval Availability

A successfully processed Document Version is not automatically active for retrieval.

Retrieval availability depends on both:

```text
Technical Readiness
+
Governance Status
```

A Document Version may be technically indexed but still:

* awaiting activation,
* superseded,
* disabled,
* restricted from the active retrieval path.

The normal query flow should include only content that is both technically ready and permitted by governance rules.

## 12.17 Governance Lifecycle

The governance lifecycle controls whether a Document Version may participate in normal retrieval.

Indicative states include:

```text
DRAFT
ACTIVE
SUPERSEDED
DISABLED
DELETED
```

`DRAFT` may be omitted from the first implementation if activation is automatic after successful processing.

### ACTIVE

The Document Version is approved for normal retrieval.

### SUPERSEDED

A newer or more applicable version has replaced it.

The content may remain stored for history and audit but should normally be excluded from active retrieval.

### DISABLED

The version is intentionally excluded without necessarily being replaced.

Possible reasons include:

* incorrect metadata,
* questionable authority,
* processing-quality issue,
* temporary review,
* inappropriate content.

### DELETED

The version has been removed according to an approved deletion process.

Logical deletion may be used before permanent artifact removal.

## 12.18 Active Version Selection

A Document may have one or more stored versions, but the application must identify which version is active for normal retrieval.

The initial model should normally allow one active version per logical document and applicable context.

More complex cases may later require multiple active versions because of:

* different jurisdictions,
* different effective periods,
* parallel authoritative publications,
* different organizational applicability.

The MVP should avoid implementing these complex rules unless the initial Compliance dataset requires them.

## 12.19 Superseding a Version

When a newer version becomes active, the previous version may be marked as superseded.

A superseding action should preserve:

* previous version,
* replacement version,
* effective timestamp,
* actor,
* reason where required.

Superseding a version does not require immediate deletion from S3 or OpenSearch.

The content may remain available for historical inspection while being excluded from the normal retrieval path.

## 12.20 Reprocessing

Reprocessing creates a new Processing Run for an existing Document Version.

Reprocessing may be required when changing:

* parser implementation,
* normalization logic,
* metadata rules,
* chunking configuration,
* embedding model,
* index mapping,
* defect correction.

The lifecycle should be:

```text
Existing Document Version
→ New Processing Run
→ New Derived Artifacts
→ New or Updated Index Representation
→ Verification
→ Controlled Activation
```

The existing successful representation should remain available until the replacement is verified, unless there is a security or correctness reason to disable it immediately.

## 12.21 Reindexing

Reindexing changes the searchable representation without changing the canonical source artifact.

A safe reindexing approach may use:

```text
Current Active Index
→ Build New Index
→ Verify New Index
→ Compare Retrieval Quality
→ Switch Alias or Active Reference
→ Retain or Retire Previous Index
```

The exact alias and migration strategy will be defined during technical design.

Direct destructive replacement should be avoided when it prevents rollback or comparison.

## 12.22 Retry Behaviour

Retries may occur at:

* full Processing Run level,
* individual stage level,
* failed embedding batch level,
* failed indexing batch level.

The retry strategy must ensure that:

* successful source storage is not repeated unnecessarily,
* duplicate chunks are not created,
* indexing retries remain idempotent,
* attempt history remains visible,
* final state reflects the actual outcome.

A retry must not overwrite previous failure evidence without preserving the attempt history required for diagnosis.

## 12.23 Failure States

A failure may occur during any processing stage.

Examples include:

* invalid source artifact,
* parser failure,
* unusable normalized output,
* metadata-validation failure,
* empty chunk output,
* embedding-service failure,
* dimension mismatch,
* OpenSearch unavailability,
* partial indexing failure,
* verification mismatch.

When a failure occurs:

1. the failed stage must be recorded,
2. subsequent dependent stages must stop,
3. the Processing Run must not be marked successful,
4. the Document Version must not become newly retrievable,
5. sufficient error information must be available for investigation.

## 12.24 Partial Failure

Partial success must not be represented as complete success.

Examples include:

* 95 of 100 chunks embedded,
* 98 of 100 chunks indexed,
* metadata extracted only for part of the document,
* one batch failed while others succeeded.

The system may support controlled recovery from partial failure.

However, the processing state must remain incomplete until the required consistency conditions are satisfied.

## 12.25 Cancellation

A Processing Run may be cancelled before completion.

Cancellation should:

* stop new processing work where practical,
* preserve completed-stage information,
* mark remaining stages as not executed or cancelled,
* prevent activation of incomplete output.

Cancellation support may be deferred if the initial processing jobs are short and controlled.

## 12.26 Disablement

A Document Version may be disabled after successful indexing.

Disablement should immediately prevent normal retrieval without requiring deletion of the canonical artifact.

Possible reasons include:

* discovered source problem,
* incorrect applicability,
* obsolete content,
* legal or operational review,
* data-quality issue.

Disablement must be reversible if the version is later approved again.

## 12.27 Deletion

Deletion must distinguish between:

```text
Removal From Retrieval
Removal From OpenSearch
Removal Of Derived Artifacts
Removal Of Canonical Source Artifact
Removal Of Operational Metadata
```

These actions should not automatically occur together.

The MVP may initially implement logical deletion or disablement.

Permanent deletion should require a controlled process because it affects:

* auditability,
* reproducibility,
* historical evaluation,
* processing traceability.

## 12.28 Lifecycle Monitoring

The Data Monitoring area must allow users to inspect:

* current document state,
* current active version,
* governance status,
* latest Processing Run,
* processing-stage history,
* associated index,
* chunk count,
* failure state,
* previous successful representation.

The monitoring view should distinguish clearly between:

```text
Uploaded
Processed
Indexed
Verified
Active
```

These terms must not be used interchangeably.

## 12.29 Lifecycle Auditability

Important lifecycle events should be traceable.

Examples include:

* document created,
* version uploaded,
* source artifact stored,
* processing started,
* processing failed,
* processing retried,
* indexing verified,
* version activated,
* version superseded,
* version disabled,
* version deleted.

Where available, each event should record:

* actor,
* timestamp,
* affected entity,
* previous state,
* new state,
* reason,
* correlation identifier.

## 12.30 Lifecycle Invariants

The following rules should always remain true:

1. A Document Version cannot exist without a Document.
2. A Processing Run cannot exist without a Document Version.
3. A Chunk cannot exist without a Processing Run and Document Version.
4. An Indexing Run cannot be successful if required chunks failed to index.
5. A Document Version cannot become retrievable before verification succeeds.
6. A superseded or disabled version must be excluded from normal retrieval.
7. Reprocessing must not modify the canonical source artifact.
8. Technical configuration changes must not create false source versions.
9. Deleting an index must not delete the canonical source document.
10. Every retrieved chunk must remain traceable to its source version.

## 12.31 Initial MVP Lifecycle

The minimum lifecycle required for the MVP is:

```text
UPLOADED
→ VALIDATED
→ STORED
→ PROCESSING
→ INDEXED
→ VERIFIED
→ ACTIVE
```

Failure path:

```text
Any Processing Stage
→ FAILED
→ RETRY OR REPROCESS
```

Governance path:

```text
ACTIVE
→ SUPERSEDED
or
ACTIVE
→ DISABLED
```

The final implementation may represent processing and governance states in separate fields rather than as one combined status.

## 12.32 Lifecycle Design Principle

The lifecycle must make it impossible to confuse:

```text
Source Exists
with
Processing Succeeded

Processing Succeeded
with
Indexing Succeeded

Indexing Succeeded
with
Content Is Active

Content Is Active
with
Content Is Legally Correct or Applicable
```

CVS Review Portal controls the technical and governance lifecycle of the knowledge base.

It does not independently establish the legal validity or applicability of the source content.

# 13. Query Lifecycle

The Query Lifecycle defines how a user request moves from initial submission to validated, filtered, ranked, and inspectable retrieval results.

The lifecycle must distinguish between:

```text
Query Input
→ Query Processing
→ Retrieval Execution
→ Result Assembly
→ Evaluation or Human Interpretation
```

The initial Query Lifecycle focuses on retrieval quality and evidence inspection.

It does not require final LLM answer generation.

## 13.1 Lifecycle Overview

A typical query follows this lifecycle:

```text
Submit Query
→ Validate Input
→ Resolve Retrieval Configuration
→ Normalize Query
→ Validate Metadata Filters
→ Select Target Index
→ Generate Query Representation
→ Retrieve Candidates
→ Rank or Fuse Results
→ Apply Result Rules
→ Assemble Provenance
→ Return Inspectable Results
```

The system must distinguish between:

* an invalid query,
* a failed retrieval execution,
* a valid query with no results,
* a valid query with weak results,
* and a successful retrieval with relevant evidence.

## 13.2 Query Submission

A Query Request is created when an authorized user submits:

* natural-language query text,
* optional metadata filters,
* optional top-k value,
* optional retrieval mode,
* optional target index or approved configuration.

The system should generate a stable query or request identifier for traceability.

The user interface may expose only a simplified subset of these options depending on the user role.

## 13.3 Query Validation

The system must validate the Query Request before retrieval begins.

Validation may include:

* non-empty query text,
* maximum query length,
* supported retrieval mode,
* valid top-k range,
* supported metadata filters,
* valid filter values,
* available target index,
* compatible embedding configuration,
* permitted governance scope.

An invalid request must return a clear validation error.

It must not be converted into a misleading empty result set.

## 13.4 Query Normalization

The Query Processing Component may normalize the query before retrieval.

Normalization may include:

* whitespace normalization,
* line-ending normalization,
* removal of unsupported control characters,
* consistent Unicode handling,
* preservation of legally meaningful terms,
* optional normalization of common abbreviations.

The original user query and normalized query should remain distinguishable where traceability requires it.

The MVP does not require advanced rewriting or automatic reformulation.

## 13.5 Retrieval Configuration Resolution

Each Retrieval Run must use an explicit and validated retrieval configuration.

The configuration may define:

* retrieval mode,
* target index,
* top-k,
* candidate count,
* embedding model,
* similarity settings,
* lexical and vector weights,
* fusion parameters,
* permitted filters,
* minimum-score rules where applicable.

The resolved configuration must be captured as, or linked to, an immutable Configuration Snapshot.

The system must not rely on undocumented runtime defaults.

## 13.6 Target Index Selection

The system must determine which OpenSearch index will serve the query.

The target may be selected through:

* the application’s active index reference,
* a configured index alias,
* an explicit technical-operator selection,
* an evaluation-run configuration.

The Query Lifecycle must verify that the selected index is:

* registered,
* ready,
* compatible with the retrieval configuration,
* permitted for the requesting workflow.

A user-facing Compliance Query should normally use the active approved index.

An AI / Search Engineer may be allowed to query an experimental index.

## 13.7 Metadata Filter Validation

Optional metadata filters must be validated before execution.

Possible filters may include:

* jurisdiction,
* source authority,
* document type,
* document title,
* governance status,
* publication date,
* effective date,
* document version.

The system must distinguish between:

* an unsupported filter,
* an invalid filter value,
* a valid filter that produces no candidates.

Normal retrieval must exclude content that is:

* disabled,
* deleted,
* superseded where current-only retrieval is required,
* otherwise outside the permitted governance scope.

## 13.8 Query Representation

The retrieval strategy determines which query representation is required.

### Lexical Retrieval

For BM25 retrieval, the normalized query text is used to search indexed text fields.

### Vector Retrieval

For vector retrieval, the query is converted into an embedding using a model compatible with the indexed document embeddings.

### Hybrid Retrieval

For hybrid retrieval, the system may create both:

* a lexical query representation,
* a vector query representation.

The Query Lifecycle must verify compatibility between:

* query embedding model,
* vector dimensions,
* index mapping,
* normalization settings.

## 13.9 Query Embedding

When vector retrieval is enabled, the Embedding Component generates the query vector.

The system must record or make available:

* embedding model identifier,
* vector dimensions,
* normalization setting,
* embedding latency,
* execution outcome.

A failed query embedding must be represented as a retrieval failure.

The system must not silently fall back to another embedding model unless an explicit fallback policy has been approved.

## 13.10 Candidate Retrieval

The Retrieval Component retrieves candidate chunks from OpenSearch.

Depending on the selected mode, this may include:

```text
BM25 Candidate Retrieval
Vector Candidate Retrieval
or
Both
```

The candidate count may be larger than the final top-k when fusion, deduplication, or reranking is applied.

The system must preserve enough execution information to diagnose:

* missing candidates,
* filter-related exclusions,
* scoring behaviour,
* empty result sets.

## 13.11 Lexical Retrieval

Lexical retrieval uses indexed text and BM25 or another approved OpenSearch lexical-ranking mechanism.

It is particularly useful for:

* exact regulatory terms,
* article numbers,
* defined terms,
* named standards,
* specific legal phrases,
* identifiers and codes.

The system may expose the lexical score for technical inspection.

Raw lexical scores should not automatically be interpreted as probabilities or confidence values.

## 13.12 Vector Retrieval

Vector retrieval uses query and chunk embeddings to identify semantically related content.

It is particularly useful when:

* the query uses different wording from the source,
* the obligation is described indirectly,
* terminology varies,
* conceptually related evidence must be found.

The system may expose the vector score for technical inspection.

Vector similarity alone does not establish legal relevance or applicability.

## 13.13 Hybrid Retrieval

Hybrid retrieval combines lexical and vector candidates.

The fusion method may use:

* Reciprocal Rank Fusion,
* weighted score combination,
* another explicitly approved method.

The selected method and parameters must be recorded in the Retrieval Run configuration.

Hybrid retrieval must not be assumed superior without evaluation.

It must be compared objectively against lexical and vector baselines.

## 13.14 Candidate Deduplication

Candidate results may contain duplicate or near-duplicate chunks caused by:

* overlap,
* repeated document sections,
* multiple indexed versions,
* multiple retrieval methods,
* duplicated source content.

The system may apply controlled deduplication before returning final results.

Deduplication must not remove distinct evidence merely because two chunks are semantically similar.

Any deduplication strategy must remain deterministic and testable.

## 13.15 Governance Filtering

The Query Lifecycle must enforce governance rules.

Normal retrieval should include only content that is:

* technically indexed,
* verified,
* active,
* within the permitted query scope.

Experimental or administrative query modes may allow access to inactive or superseded content for comparison and investigation.

Such access must be explicit and distinguishable from normal Compliance User retrieval.

## 13.16 Ranking and Top-K Selection

After candidate retrieval and optional fusion, the system selects the final ranked results.

The ranking stage may consider:

* lexical rank,
* vector rank,
* fused rank,
* metadata constraints,
* duplicate handling,
* governance rules,
* optional minimum-score conditions.

The final result set must preserve stable rank ordering.

The system should not claim that rank 1 is necessarily legally correct.

It indicates that the result was ranked highest by the selected retrieval configuration.

## 13.17 Result Assembly

Raw OpenSearch responses must be converted into stable application-level Search Result contracts.

Each result should contain at least:

* rank,
* chunk identifier,
* document identifier,
* document-version identifier,
* document title,
* section or heading,
* chunk content,
* source authority where available,
* jurisdiction where available,
* publication or effective date where available,
* governance status,
* available retrieval scores,
* source reference.

OpenSearch-specific response structures should not be exposed directly to the UI.

## 13.18 Provenance Assembly

Every returned result must remain traceable through:

```text
Search Result
→ Chunk
→ Processing Run
→ Document Version
→ Source Artifact
```

Where required, the result should also identify:

* target index,
* index configuration,
* chunking configuration,
* embedding configuration.

The Query User may see a simplified provenance view.

The AI / Search Engineer may access the full technical trace.

## 13.19 Retrieval Run Recording

A Retrieval Run should record enough information to support:

* debugging,
* evaluation,
* comparison,
* auditability,
* reproducibility.

Indicative fields include:

* retrieval-run identifier,
* original query,
* normalized query,
* target index,
* retrieval configuration,
* applied filters,
* execution timestamp,
* result count,
* retrieval latency,
* execution status,
* error details where applicable.

Not every interactive query must be retained indefinitely.

The retention policy will be defined later.

## 13.20 Successful Retrieval

A Retrieval Run may be considered technically successful when:

* the query was valid,
* the target index was available,
* retrieval executed without error,
* the response contract was assembled correctly.

Technical success does not guarantee relevance.

A successful query may still return:

* irrelevant results,
* incomplete evidence,
* weak results,
* no results.

Retrieval quality must be evaluated separately.

## 13.21 No-Result Outcome

A valid query may return no results.

Possible causes include:

* no relevant indexed content,
* restrictive filters,
* missing document versions,
* inactive content exclusion,
* index incompleteness,
* unsuitable query representation.

The system should return an explicit no-result outcome.

It must not fabricate evidence or automatically present unrelated content as relevant.

## 13.22 Weak-Result Outcome

The system may identify a weak result set when supported by an approved rule.

Possible signals include:

* scores below a configured threshold,
* low separation between results,
* no results from one retrieval channel,
* incomplete coverage of expected metadata,
* only superseded or inactive matches in diagnostic mode.

Weak-result detection must be treated as an operational heuristic.

Raw retrieval scores must not automatically be presented as calibrated confidence probabilities.

## 13.23 Retrieval Failure

A Retrieval Run may fail because of:

* invalid configuration,
* unavailable index,
* query-embedding failure,
* dimension mismatch,
* OpenSearch timeout,
* OpenSearch execution error,
* result-contract failure,
* authorization failure.

A failed Retrieval Run must remain distinguishable from a valid no-result outcome.

The user should receive a clear but safe error message.

Technical error details should be available through structured logs and monitoring.

## 13.24 Retry Behaviour

Retries may be appropriate for transient failures such as:

* temporary OpenSearch unavailability,
* network timeout,
* temporary model-service failure.

Retry policies must be:

* bounded,
* observable,
* safe,
* appropriate to the failure category.

Invalid queries, incompatible configurations, and deterministic mapping errors should not be retried automatically without correction.

## 13.25 Query History

The system may maintain Query and Retrieval Run history for:

* technical debugging,
* evaluation,
* result comparison,
* usage analysis,
* audit purposes.

The MVP may implement limited retention.

Stored query data must be handled carefully because queries may contain:

* internal policy information,
* sensitive organizational context,
* personal data,
* confidential business information.

Logging full query text should be controlled rather than assumed.

## 13.26 Human Interpretation

Retrieved results are evidence candidates for human review.

The user remains responsible for evaluating:

* legal authority,
* jurisdiction,
* effective date,
* applicability,
* completeness,
* relationship to other provisions.

A high retrieval rank does not replace domain judgment.

The system must avoid presenting retrieval output as final compliance approval or legal advice.

## 13.27 Evaluation Query Lifecycle

When a query originates from a Golden Evaluation Dataset, the lifecycle is similar to an interactive query:

```text
Load Evaluation Query
→ Apply Evaluation Configuration
→ Execute Retrieval
→ Capture Ranked Results
→ Compare With Relevance Judgments
→ Calculate Query-Level Metrics
```

Evaluation queries must use the exact approved:

* dataset version,
* target index,
* retrieval configuration,
* top-k,
* filter rules.

## 13.28 Comparison Lifecycle

A retrieval configuration comparison may follow:

```text
Same Evaluation Dataset
→ Run Against Baseline Configuration
→ Run Against Candidate Configuration
→ Compare Metrics
→ Inspect Query-Level Changes
```

A valid comparison should control for changes in:

* evaluation-dataset version,
* document corpus,
* active document versions,
* target index content.

Otherwise, metric changes may not be attributable only to retrieval configuration.

## 13.29 Future Answer-Generation Extension

A future answer-generation lifecycle may extend the retrieval flow:

```text
Query
→ Retrieval
→ Evidence Selection
→ LLM Answer Generation
→ Citation Assembly
→ Answer Validation
→ Human Review
```

This future extension must consume the established Search Result contracts.

It must not bypass retrieval provenance or governance filtering.

Answer generation remains outside the initial mandatory Query Lifecycle.

## 13.30 Query Lifecycle Invariants

The following rules should remain true:

1. An invalid Query Request must not execute retrieval.
2. Every Retrieval Run must use an explicit target index.
3. Every Retrieval Run must use a traceable configuration.
4. Query and document embeddings must be compatible.
5. Normal retrieval must exclude disallowed governance states.
6. A failed retrieval must not be represented as a valid empty result.
7. Every Search Result must reference an indexed Chunk.
8. Every returned Chunk must remain traceable to a Document Version.
9. Retrieval scores must not be presented as calibrated legal confidence.
10. No-result behaviour must not generate unsupported evidence.
11. Technical retrieval success must not be confused with relevance.
12. Relevance must not be confused with legal applicability.

## 13.31 Initial MVP Query Lifecycle

The minimum Query Lifecycle required for the MVP is:

```text
QUERY_RECEIVED
→ VALIDATED
→ CONFIGURATION_RESOLVED
→ RETRIEVAL_EXECUTED
→ RESULTS_ASSEMBLED
→ COMPLETED
```

Alternative outcomes include:

```text
QUERY_RECEIVED
→ VALIDATION_FAILED
```

```text
VALIDATED
→ RETRIEVAL_FAILED
```

```text
RETRIEVAL_EXECUTED
→ NO_RESULTS
```

The final implementation may represent technical status and result outcome separately.

## 13.32 Query Lifecycle Design Principle

The lifecycle must make it impossible to confuse:

```text
Query Is Valid
with
Retrieval Succeeded

Retrieval Succeeded
with
Results Are Relevant

Results Are Relevant
with
Evidence Is Complete

Evidence Is Complete
with
Legal Interpretation Is Correct
```

CVS Review Portal is responsible for controlled and traceable retrieval.

It does not independently establish final legal or compliance conclusions.


# 14. Evaluation Model

The Evaluation Model defines how CVS Review Portal measures retrieval quality in a controlled, reproducible, and explainable manner.

Evaluation must determine whether the retrieval system returns the correct evidence, at an appropriate rank, for realistic compliance queries.

The initial evaluation scope focuses on retrieval rather than final LLM-generated answers.

## 14.1 Evaluation Objective

The primary objective is to answer:

> Does the retrieval system consistently return the most relevant compliance evidence for a defined set of user information needs?

The Evaluation Model must support:

* repeatable testing,
* baseline comparison,
* query-level diagnosis,
* configuration comparison,
* regression detection,
* evidence-based retrieval decisions.

Evaluation must not rely only on a small number of manually selected demonstration queries.

## 14.2 Evaluation Boundary

The initial Evaluation Model measures:

```text
Query
→ Retrieved Documents, Sections, or Chunks
→ Ranking Quality
```

It does not initially measure:

* final answer correctness,
* citation correctness,
* legal interpretation quality,
* answer completeness,
* hallucination rate,
* user satisfaction,
* autonomous compliance decisions.

These may be added later as separate evaluation layers.

## 14.3 Evaluation Dataset

A Golden Evaluation Dataset is a controlled and versioned collection of:

* realistic queries,
* relevant evidence,
* relevance judgments,
* optional categories,
* optional difficulty levels,
* optional no-answer cases.

Each dataset must have a stable identifier and version.

Indicative dataset information includes:

* dataset name,
* dataset version,
* domain scope,
* creation date,
* reviewer or owner,
* approval status,
* source corpus version,
* judgment granularity.

Evaluation results are meaningful only when the exact dataset version is known.

## 14.4 Evaluation Query

An Evaluation Query represents a realistic user information need.

A good evaluation query should:

* reflect how an actual Compliance User may ask the question,
* avoid copying source wording unnecessarily,
* have a clear information need,
* be answerable from the approved document corpus,
* support reliable relevance judgment.

Queries may include:

* exact regulatory terms,
* indirect descriptions of obligations,
* article or standard references,
* cross-document questions,
* metadata-sensitive questions,
* ambiguous queries,
* no-answer queries.

## 14.5 Query Categories

Evaluation queries may be grouped into categories such as:

* exact-term lookup,
* semantic paraphrase,
* article or section lookup,
* obligation identification,
* jurisdiction-sensitive query,
* date-sensitive query,
* version-sensitive query,
* source-authority-sensitive query,
* multi-evidence query,
* no-answer query.

Categories help identify which retrieval behaviours are strong or weak.

Aggregate metrics alone may hide important category-level failures.

## 14.6 Difficulty Levels

Evaluation queries may optionally be classified as:

```text
EASY
MEDIUM
HARD
```

Indicative interpretation:

### EASY

The query contains terminology closely matching the relevant source.

### MEDIUM

The query uses paraphrased or indirect language but refers to one clear source section.

### HARD

The query may require:

* multiple pieces of evidence,
* metadata filtering,
* version awareness,
* distinction between related obligations,
* recognition of domain-specific applicability.

Difficulty classification is useful for diagnosis but does not replace relevance judgments.

## 14.7 Judgment Granularity

Relevance may be judged at different levels:

```text
Document
Section
Chunk
```

### Document-Level Judgment

A document is marked relevant to the query.

This is easier to maintain but may be too coarse for chunk-level retrieval evaluation.

### Section-Level Judgment

A document section or heading is marked relevant.

This offers better semantic precision while remaining relatively stable across moderate chunking changes.

### Chunk-Level Judgment

A specific indexed chunk is marked relevant.

This provides direct retrieval evaluation but may become unstable when chunking configuration changes.

The selected granularity must match the evaluation objective.

For chunking experiments, section-level or source-span judgments may be more reusable than fixed chunk identifiers.

## 14.8 Relevance Judgments

A Relevance Judgment records the usefulness of a result for a specific Evaluation Query.

The initial system may support binary relevance:

```text
0 = Not Relevant
1 = Relevant
```

For nDCG and more detailed ranking analysis, graded relevance is preferred.

An indicative scale is:

```text
0 = Not Relevant
1 = Partially Relevant
2 = Relevant
3 = Highly Relevant
```

The final judgment scale must include written guidance so that reviewers apply it consistently.

## 14.9 Relevance Criteria

A result should not be marked relevant only because it is semantically similar.

Relevance may depend on:

* whether it addresses the actual information need,
* source authority,
* jurisdiction,
* document version,
* effective date,
* organizational role,
* regulatory applicability,
* evidence completeness.

A result may contain related terminology but still be non-relevant because it applies to the wrong context.

## 14.10 Golden Judgment Creation

Golden judgments may initially be created manually by:

* AI / Search Engineer,
* Compliance specialist,
* legal or regulatory reviewer,
* another authorized domain expert.

A practical initial process may be:

```text
Create Query
→ Retrieve Broad Candidate Set
→ Review Candidate Evidence
→ Add Missing Relevant Evidence
→ Assign Relevance Grades
→ Review and Approve
```

The retrieval system may assist candidate discovery, but it must not define its own ground truth without human review.

## 14.11 Judgment Review

Important or ambiguous judgments should be reviewed by a domain-qualified person.

Where practical, the system may record:

* reviewer identity,
* review date,
* judgment rationale,
* disagreement notes,
* approval status.

Multiple-reviewer agreement may be introduced later for high-value evaluation datasets.

## 14.12 No-Answer Queries

The evaluation dataset should include queries for which no relevant evidence exists in the approved corpus.

No-answer queries test whether the retrieval system:

* returns unrelated content,
* over-relies on semantic similarity,
* ignores metadata restrictions,
* presents weak evidence as relevant.

For retrieval-only evaluation, a no-answer query may be expected to produce:

* no results after an approved threshold,
* an explicit weak-result outcome,
* or no judged-relevant result within top-k.

The exact no-answer policy depends on whether score thresholds are used.

## 14.13 Evaluation Corpus

Every Evaluation Run must identify the evaluated corpus.

The corpus definition may include:

* active Documents,
* active Document Versions,
* target OpenSearch index,
* index build identifier,
* governance-state rules,
* relevant metadata scope.

Two runs should not be treated as a pure retrieval-configuration comparison if their underlying corpora differ.

## 14.14 Evaluation Configuration

Each Evaluation Run must use an explicit configuration containing at least:

* evaluation dataset and version,
* target index,
* retrieval mode,
* top-k,
* candidate count,
* metadata filters,
* embedding configuration,
* hybrid-fusion parameters where applicable,
* score thresholds where applicable,
* metric definitions.

The configuration must be stored as an immutable snapshot.

## 14.15 Evaluation Execution

A standard Evaluation Run follows:

```text
Load Evaluation Dataset
→ Validate Dataset and Corpus
→ Resolve Retrieval Configuration
→ Execute Every Evaluation Query
→ Capture Ranked Results
→ Compare With Relevance Judgments
→ Calculate Query-Level Metrics
→ Calculate Aggregate Metrics
→ Store Evaluation Report
```

A failed query must be recorded.

It must not be silently excluded from aggregate results without an explicit calculation policy.

## 14.16 Precision@K

Precision@K measures how many of the top K retrieved results are relevant.

```text
Precision@K
=
Relevant Results in Top K
/
K
```

For example, if 6 of the top 10 results are relevant:

```text
Precision@10 = 0.60
```

Precision is useful when irrelevant results impose review cost on the user.

A high Precision@10 indicates that the result list contains relatively little noise.

## 14.17 Recall@K

Recall@K measures how many of all known relevant results were retrieved within the top K.

```text
Recall@K
=
Relevant Results Retrieved in Top K
/
Total Known Relevant Results
```

For example, if 4 relevant sections exist and 3 are retrieved within the top 10:

```text
Recall@10 = 0.75
```

Recall is important when missing relevant compliance evidence may lead to incomplete analysis.

Recall depends strongly on the completeness of the relevance judgments.

## 14.18 nDCG@K

Normalized Discounted Cumulative Gain measures ranking quality using graded relevance.

It rewards:

* highly relevant results,
* results appearing near the top of the ranking.

A highly relevant result at rank 1 contributes more than the same result at rank 10.

The metric compares the actual ranking with the best possible ranking for the same relevance judgments.

```text
nDCG@K
=
DCG@K
/
IDCG@K
```

The result usually ranges from:

```text
0.0 to 1.0
```

A higher value indicates that the most relevant evidence appears closer to the top.

## 14.19 Metric Interpretation

Metrics must be interpreted together.

For example:

* high Precision but low Recall may mean that results are accurate but incomplete,
* high Recall but low Precision may mean that relevant evidence is found together with significant noise,
* acceptable Precision and Recall but low nDCG may mean that relevant results are ranked too low.

No single metric should define retrieval quality alone.

## 14.20 Additional Metrics

Possible later metrics include:

### MRR@K

Measures how early the first relevant result appears.

Useful when the user mainly needs one correct answer source.

### Hit Rate@K

Measures whether at least one relevant result appears within top K.

### Coverage

Measures how many evaluation queries return at least one relevant result.

### Retrieval Latency

Measures query execution time.

### Index Size

Measures storage impact of a processing configuration.

### Processing Cost and Duration

Measures the operational impact of chunking and embedding choices.

These metrics may be introduced when they support a specific design decision.

## 14.21 Query-Level Results

Every Evaluation Run should preserve query-level information where practical.

For each query, this may include:

* retrieved identifiers,
* result ranks,
* relevance grades,
* Precision@K,
* Recall@K,
* nDCG@K,
* retrieval latency,
* applied filters,
* execution failure,
* no-result status.

Query-level analysis is required to understand why aggregate metrics changed.

## 14.22 Aggregate Results

Aggregate metrics may be reported as:

* mean across all queries,
* median where useful,
* category-level mean,
* difficulty-level mean,
* percentage of queries improved,
* percentage of queries regressed.

The aggregation method must remain consistent between comparable runs.

## 14.23 Failed Query Handling

Evaluation execution may fail for individual queries because of:

* invalid query data,
* embedding failure,
* OpenSearch timeout,
* retrieval error,
* incompatible configuration.

The Evaluation Run must record:

* number of failed queries,
* affected query identifiers,
* failure reasons.

A run with failures should not automatically be treated as directly comparable to a complete baseline.

## 14.24 Baseline Evaluation

A Baseline Evaluation Run represents the accepted reference configuration.

The baseline should identify:

* source corpus,
* target index,
* chunking configuration,
* embedding model,
* retrieval mode,
* evaluation dataset,
* metric implementation version.

A baseline is not necessarily the best possible system.

It is the controlled reference against which candidate changes are compared.

## 14.25 Candidate Evaluation

A Candidate Evaluation Run tests a proposed change.

Examples include:

* different chunk size,
* different overlap,
* different embedding model,
* BM25 versus vector retrieval,
* dense versus hybrid retrieval,
* different RRF parameter,
* new metadata filter,
* new index mapping.

A candidate should ideally change one major factor at a time when the goal is causal diagnosis.

## 14.26 Baseline Comparison

A comparison should report:

* baseline metric values,
* candidate metric values,
* absolute change,
* relative change where useful,
* improved queries,
* regressed queries,
* unchanged queries,
* latency or cost changes.

Example:

```text
Recall@10
Baseline: 0.72
Candidate: 0.79
Absolute Change: +0.07
```

Aggregate improvement must not hide severe regressions on important queries.

## 14.27 Regression Rules

The project may later define regression thresholds.

Examples include:

* Recall@10 must not decrease by more than an approved value,
* no critical query may lose all relevant results,
* nDCG@10 must remain above the baseline threshold,
* P95 retrieval latency must remain within an acceptable range.

These thresholds should be established after an initial baseline exists.

They should not be invented before representative data is available.

## 14.28 Critical Queries

Some compliance queries may be classified as critical.

Examples may include:

* high-risk obligations,
* mandatory documentation requirements,
* prohibited practices,
* reporting deadlines,
* governance responsibilities.

A candidate configuration may be rejected even if aggregate metrics improve when it causes unacceptable regression on critical queries.

## 14.29 Experiment Comparison Controls

For a valid controlled comparison, the following should remain unchanged unless intentionally tested:

* evaluation-dataset version,
* document corpus,
* active document versions,
* relevance judgments,
* metric implementation,
* query preprocessing,
* applicable filters.

When multiple factors change, the comparison must state that the result cannot be attributed to one component alone.

## 14.30 Chunking Evaluation Considerations

Chunking changes may alter chunk identifiers and boundaries.

This creates a challenge for chunk-level judgments.

Possible strategies include:

* evaluate at document level,
* evaluate at section level,
* use source-span identifiers,
* remap judgments to new chunks,
* maintain separate datasets for specific chunking experiments.

The selected strategy must avoid falsely penalizing a configuration only because identifiers changed.

## 14.31 Evaluation Data Leakage

The system must reduce the risk of over-optimizing against the same small evaluation set.

Possible safeguards include:

* separate development and validation query sets,
* hidden holdout queries,
* periodic addition of new realistic queries,
* avoiding manual tuning for individual test queries,
* tracking repeated experiment use.

The MVP may begin with one controlled dataset, but the limitation must be recognized.

## 14.32 Evaluation Dataset Evolution

The Golden Evaluation Dataset will evolve as the project discovers:

* missing query types,
* ambiguous judgments,
* weak coverage,
* new document versions,
* real user failures,
* important no-answer cases.

A dataset change must create a new version.

Previous Evaluation Runs must continue to reference the dataset version used at execution time.

## 14.33 Human Feedback

Future versions may allow users or reviewers to mark results as:

* relevant,
* partially relevant,
* irrelevant,
* outdated,
* wrong jurisdiction,
* incomplete.

Human feedback may be used to propose new relevance judgments.

It should not automatically modify the approved Golden Evaluation Dataset without review.

## 14.34 Evaluation Report

An Evaluation Report should include:

* evaluation-run identifier,
* dataset version,
* corpus and target index,
* retrieval configuration,
* aggregate metrics,
* query-level results,
* failures,
* category-level analysis,
* comparison with baseline where applicable,
* execution timestamp,
* code or application version.

The report may initially be stored as JSON, CSV, HTML, or another controlled artifact.

## 14.35 Evaluation Reproducibility

An Evaluation Run is reproducible only when the system can identify:

```text
Evaluation Dataset Version
+
Corpus and Document Versions
+
Target Index
+
Retrieval Configuration
+
Metric Implementation
+
Application Version
```

If any required element is unknown, the result should not be treated as fully reproducible.

## 14.36 Evaluation Storage

Evaluation artifacts may be stored across:

### Operational State Store

For:

* Evaluation Run metadata,
* status,
* configuration references,
* aggregate metrics.

### S3

For:

* evaluation datasets,
* detailed query-level reports,
* exported comparison reports,
* larger reproducibility artifacts.

### OpenSearch

OpenSearch should not be the canonical store for approved evaluation datasets or final evaluation history unless a specific requirement justifies it.

## 14.37 Evaluation Observability

The system should record:

* run duration,
* query count,
* successful query count,
* failed query count,
* average retrieval latency,
* evaluation calculation duration,
* dataset and configuration identifiers.

Evaluation failures must be distinguishable from poor retrieval quality.

## 14.38 Evaluation and Legal Correctness

Retrieval metrics measure whether judged-relevant evidence is returned and ranked appropriately.

They do not prove:

* that the source is legally authoritative,
* that the judgment set is complete,
* that the evidence is legally applicable,
* that a future generated answer is correct,
* that the organization is compliant.

The Evaluation Model supports technical and domain-informed retrieval validation.

It does not replace legal or compliance review.

## 14.39 Initial MVP Evaluation Model

The minimum evaluation capability required for the MVP is:

```text
Versioned Golden Evaluation Dataset
→ Evaluation Queries
→ Relevance Judgments
→ Retrieval Execution
→ Precision@10
→ Recall@10
→ nDCG@10
→ Stored Evaluation Report
→ Baseline Comparison
```

The first implementation may use:

* JSONL or another simple dataset format,
* command-line or API-triggered execution,
* structured JSON or CSV reports,
* a basic UI summary.

A complete experiment-tracking platform is not required.

## 14.40 Evaluation Invariants

The following rules should remain true:

1. Every Evaluation Run must reference a dataset version.
2. Every Evaluation Run must reference a target index and corpus.
3. Every Evaluation Run must use a traceable retrieval configuration.
4. Metric calculations must use approved relevance judgments.
5. Failed queries must not disappear silently from reports.
6. Runs with different datasets must not be treated as directly comparable without qualification.
7. Retrieval relevance must not be confused with legal correctness.
8. Aggregate improvements must not hide critical-query regressions.
9. Dataset changes must create a new version.
10. Metric implementation changes must be traceable.
11. Chunking changes must account for judgment-granularity effects.
12. An evaluation result without reproducibility information must not become an accepted baseline.

## 14.41 Evaluation Design Principle

The Evaluation Model must make it impossible to confuse:

```text
A Few Queries Look Good
with
Retrieval Is Reliably Good

Aggregate Metrics Improved
with
Every Important Query Improved

Relevant Evidence Was Retrieved
with
All Necessary Evidence Was Retrieved

Retrieval Quality Is High
with
The Final Legal Interpretation Is Correct
```

CVS Review Portal should use evaluation to guide retrieval decisions through measurable evidence rather than intuition alone.


# 15. Data and Artifact Ownership

Data and Artifact Ownership defines which component or storage layer is authoritative for each type of information produced or consumed by CVS Review Portal.

The objective is to prevent ambiguity between:

```text
Canonical Source Data
Operational State
Derived Processing Artifacts
Searchable Representations
Configuration
Evaluation Data
Observability Data
```

Each data category must have a clearly defined owner, source of truth, lifecycle, and regeneration policy.

## 15.1 Ownership Principles

The system should follow these principles:

1. Every important data object must have one authoritative owner.
2. Derived data must remain traceable to its canonical input.
3. OpenSearch must not become the sole source of truth for documents.
4. Operational state must survive application and container restarts.
5. Configuration used by a run must remain reproducible.
6. Derived artifacts may be regenerated when their source and configuration remain available.
7. Deletion from one storage layer must not automatically imply deletion from all others.
8. Storage technology must reflect the access and consistency requirements of the data.

## 15.2 Data Ownership Overview

The initial ownership model is:

```text
AWS S3
→ Canonical source files and retained processing artifacts

Operational State Store
→ Documents, versions, runs, statuses, relationships, and governance state

OpenSearch
→ Searchable chunks, vectors, and retrieval metadata

Configuration Files and Snapshots
→ Processing, indexing, retrieval, and evaluation settings

Evaluation Dataset Store
→ Golden queries and relevance judgments

Observability Systems
→ Logs, metrics, traces, and infrastructure events
```

The exact persistence technology for operational state remains an implementation decision.

PostgreSQL is the likely option if relational consistency and lifecycle querying require it.

## 15.3 Canonical Source Ownership

The original uploaded document is the canonical source artifact.

AWS S3 owns the durable binary or text representation of that source.

Examples include:

* TXT files,
* Markdown files,
* DOCX files.

The canonical source artifact must preserve:

* original content,
* original filename,
* media type,
* file size,
* content checksum,
* upload timestamp,
* storage location,
* relationship to the Document Version.

The canonical source must remain available independently of:

* parsed output,
* chunks,
* embeddings,
* OpenSearch indexes,
* evaluation results.

## 15.4 Document Identity Ownership

The operational state layer owns the logical identity of:

* Documents,
* Document Versions,
* Source Artifacts,
* Processing Runs,
* Indexing Runs,
* registered indexes.

S3 object paths and OpenSearch document identifiers must not independently define the application’s canonical Document identity.

For example:

```text
Document ID
→ owned by the application domain model

S3 Object Key
→ storage location associated with the Document Version

OpenSearch Chunk ID
→ derived search identifier associated with a Processing Run
```

This separation allows files and indexes to move without changing the logical identity of the source.

## 15.5 Document Metadata Ownership

Document metadata may have several origins:

* supplied by a user,
* derived from file properties,
* extracted through deterministic rules,
* enriched by a model,
* confirmed by a Compliance reviewer.

The operational state layer should own the approved document-level metadata.

Examples include:

* canonical title,
* version label,
* jurisdiction,
* source authority,
* publication date,
* effective date,
* document type,
* governance status.

Derived or unconfirmed metadata should remain distinguishable from reviewed or authoritative metadata where required.

OpenSearch may contain a copy of selected metadata for filtering and result display.

That copy is a serving representation rather than the authoritative metadata record.

## 15.6 Governance State Ownership

The operational state layer owns governance state.

Examples include:

```text
DRAFT
ACTIVE
SUPERSEDED
DISABLED
DELETED
```

OpenSearch may store governance fields to support filtering.

However, the application registry remains authoritative for:

* which version is active,
* which version was superseded,
* why a version was disabled,
* when a status changed,
* who performed the change.

Changes to governance state must be propagated to the serving layer in a controlled manner.

## 15.7 Processing Run Ownership

The operational state layer owns the status and history of each Processing Run.

This includes:

* run identifier,
* source Document Version,
* configuration snapshot,
* execution status,
* current or failed stage,
* timestamps,
* retry relationships,
* error summaries,
* produced-artifact references,
* generated chunk counts.

Application logs may contain technical details about a run, but logs must not be treated as the primary source of processing state.

The Data Monitoring interface should read lifecycle state from controlled operational records rather than reconstructing it from logs.

## 15.8 Processing Stage Ownership

Processing-stage status may be stored:

* as independent stage records,
* or as structured state within the Processing Run.

The operational state layer remains authoritative for whether a stage:

```text
NOT_STARTED
RUNNING
SUCCEEDED
FAILED
SKIPPED
CANCELLED
```

Logs provide diagnostic evidence but do not replace explicit stage state.

The implementation may begin with a simplified stage model and evolve when retry and monitoring requirements become clearer.

## 15.9 Parsed Artifact Ownership

A Parsed Artifact is a derived representation created from the source file.

Examples include:

* structured paragraphs,
* extracted headings,
* list structures,
* normalized document tree,
* parser metadata.

S3 may own the retained parsed artifact when it is required for:

* debugging,
* reproducibility,
* reprocessing,
* parser comparison,
* auditability.

The operational state layer should store only:

* artifact identifier,
* artifact type,
* checksum,
* storage reference,
* producing Processing Run.

Parsed artifacts that can be regenerated cheaply may not need permanent retention.

The retention decision will depend on cost and operational value.

## 15.10 Normalized Artifact Ownership

Normalized text is also a derived artifact.

If retained, it should be stored in S3 or another durable artifact store.

It should remain associated with:

* source Document Version,
* Processing Run,
* normalization configuration,
* checksum,
* storage reference.

OpenSearch should not be the only location containing the normalized text because indexed chunk text may not preserve the full normalized document.

## 15.11 Chunk Ownership

A Chunk is a derived retrieval unit.

Its logical identity and provenance are owned by the application processing model.

The actual chunk representation may exist in:

### OpenSearch

For:

* searchable text,
* vectors,
* filterable metadata,
* serving-time result retrieval.

### S3 Chunk Manifest or Export

Optionally, for:

* reproducibility,
* index rebuilding,
* debugging,
* comparison between chunking strategies.

### Operational State Store

For:

* chunk manifest references,
* counts,
* checksums,
* processing relationships,
* selected chunk metadata where necessary.

The MVP does not require every full chunk body to be duplicated in a relational database.

## 15.12 Embedding Ownership

Embeddings are derived technical artifacts.

OpenSearch is the likely serving store for document-chunk vectors.

The system must retain sufficient configuration information to regenerate them, including:

* embedding model,
* model version or identifier,
* vector dimensions,
* normalization setting,
* input chunk identifier,
* Processing Run,
* configuration snapshot.

The operational state store does not need to store full embedding vectors unless a specific requirement justifies it.

Embedding vectors should not be treated as canonical business data.

## 15.13 OpenSearch Ownership

OpenSearch owns the active searchable representation used during retrieval.

This includes:

* chunk text,
* embedding vectors,
* lexical fields,
* filterable metadata,
* document and version identifiers,
* governance fields,
* index-specific scoring structures.

OpenSearch is authoritative only for:

> What searchable representation currently exists in a specific index.

It is not authoritative for:

* the original source document,
* approved document metadata,
* document-version history,
* processing history,
* governance history,
* approved evaluation data.

An index should be considered replaceable and rebuildable.

## 15.14 Index Registry Ownership

The operational state layer owns the application-level Index Registry.

The registry records:

* logical index identity,
* physical index name,
* alias where applicable,
* lifecycle status,
* mapping version,
* embedding configuration,
* chunking configuration,
* source corpus,
* creation timestamp,
* readiness state,
* active or inactive status.

OpenSearch owns the physical index.

CVS Review Portal owns the interpretation and lifecycle of that index within the application.

## 15.15 Index Mapping Ownership

Index mappings should be defined through version-controlled application or infrastructure configuration.

The mapping definition may include:

* text fields,
* keyword fields,
* date fields,
* vector field,
* vector dimensions,
* similarity metric,
* analyzers,
* filterable metadata fields.

The version-controlled definition is the design source of truth.

The deployed OpenSearch mapping is the runtime representation.

The system should be able to compare the expected mapping with the actual deployed mapping.

## 15.16 Configuration File Ownership

Version-controlled configuration files own the editable configuration definitions used by the application.

Examples include:

* parser settings,
* normalization settings,
* chunking settings,
* embedding settings,
* OpenSearch settings,
* retrieval settings,
* evaluation settings.

Configuration files should contain:

* supported non-secret values,
* explicit defaults,
* validated options.

They must not contain:

* AWS credentials,
* private keys,
* access tokens,
* production secrets.

Secrets and sensitive environment values must be supplied through approved AWS and runtime mechanisms.

## 15.17 Configuration Snapshot Ownership

The operational state layer or retained artifact store owns immutable Configuration Snapshots associated with executed runs.

A snapshot must preserve the effective configuration after:

* configuration-file loading,
* environment-specific resolution,
* default application,
* validation.

The snapshot should include or reference:

* processing configuration,
* index configuration,
* retrieval configuration,
* evaluation configuration,
* application version.

The current configuration file must not be assumed to represent the settings used by a historical run.

## 15.18 Environment Configuration Ownership

Environment-specific infrastructure values may be owned by:

* CloudFormation parameters,
* ECS task-definition environment variables,
* AWS Systems Manager Parameter Store,
* AWS Secrets Manager,
* deployment pipelines.

Examples include:

* S3 bucket names,
* OpenSearch endpoint,
* database endpoint,
* AWS region,
* secret references,
* log level,
* runtime environment name.

Environment configuration should remain separate from domain and experiment configuration.

## 15.19 Evaluation Dataset Ownership

Approved Golden Evaluation Datasets are controlled evaluation artifacts.

S3 or a version-controlled dataset repository may own the dataset files.

The operational state layer may own:

* dataset registration,
* dataset version,
* approval status,
* owner or reviewer,
* storage reference,
* checksum.

The evaluation dataset must not be owned solely by an individual developer’s local filesystem.

## 15.20 Relevance Judgment Ownership

Relevance Judgments are domain-informed evaluation records.

Their authoritative representation should be stored in a versioned evaluation dataset or controlled evaluation store.

The system should preserve:

* evaluation-query identity,
* relevant target identity,
* relevance grade,
* reviewer where available,
* judgment version,
* notes or rationale where required.

Evaluation results must not overwrite the approved relevance judgments.

Human feedback may propose new judgments but should not silently modify the golden dataset.

## 15.21 Evaluation Run Ownership

The operational state layer owns the lifecycle and summary metadata of Evaluation Runs.

This includes:

* evaluation-run identifier,
* dataset version,
* target index,
* retrieval configuration,
* status,
* timestamps,
* aggregate metrics,
* failed-query count.

S3 may own detailed evaluation artifacts such as:

* query-level results,
* CSV exports,
* JSON reports,
* comparison reports,
* diagnostic result sets.

## 15.22 Metric Result Ownership

Metric results are derived evaluation outputs.

The operational state layer may store aggregate values needed for:

* monitoring,
* comparison,
* baseline selection,
* UI display.

Detailed query-level metric outputs may be retained in S3.

The approved metric calculation implementation is owned by the application codebase and its tests.

A metric result is meaningful only together with:

* dataset version,
* corpus,
* index,
* retrieval configuration,
* metric implementation version.

## 15.23 Query Data Ownership

Interactive query data may be owned temporarily or durably by the operational state layer, depending on the retention policy.

Possible retained information includes:

* query identifier,
* normalized query,
* applied filters,
* target index,
* retrieval configuration,
* result count,
* latency,
* outcome.

Full query text may contain sensitive information.

Therefore, ownership and retention must define whether query text is:

* stored in full,
* redacted,
* hashed,
* stored temporarily,
* excluded from logs,
* retained only for approved evaluation workflows.

## 15.24 Retrieval Result Ownership

Retrieval results are transient derived outputs.

OpenSearch produces the raw search response.

The application owns the normalized Search Result contract returned to the UI.

Search Results may be retained for:

* evaluation,
* debugging,
* comparison,
* auditability.

They do not need to become permanent operational records for every interactive query.

Retention should be proportional to the actual requirement.

## 15.25 User Interface State Ownership

The UI may own temporary presentation state, such as:

* currently selected document,
* unsaved filter selections,
* pagination state,
* current query text,
* expanded result panels.

The UI must not own authoritative:

* document status,
* governance state,
* processing state,
* index state,
* evaluation results.

Authoritative state must be retrieved from backend APIs.

## 15.26 Audit Data Ownership

Audit Events should be stored in a durable append-oriented location when formal auditability is required.

Audit data may include:

* actor,
* action,
* affected entity,
* previous state,
* new state,
* timestamp,
* outcome,
* correlation identifier.

The operational state database may initially store audit events.

Longer-term archival may use S3 or a dedicated audit/logging solution.

Audit data must remain distinct from ordinary debug logs.

## 15.27 Application Log Ownership

Application logs are owned by the observability platform, likely CloudWatch Logs in AWS.

Logs may contain:

* request identifiers,
* correlation identifiers,
* run identifiers,
* stage names,
* durations,
* error categories,
* safe technical context.

Logs must avoid uncontrolled storage of:

* full document content,
* full query content,
* credentials,
* secrets,
* personal or confidential information.

Logs support diagnosis.

They do not replace domain or operational records.

## 15.28 Metrics Ownership

Operational metrics may be owned by CloudWatch or another approved monitoring platform.

Examples include:

* ingestion duration,
* processing failures,
* chunk count,
* embedding duration,
* indexing duration,
* retrieval latency,
* evaluation duration,
* request volume.

Metric systems provide aggregated operational visibility.

They do not own the authoritative state of individual Documents or Processing Runs.

## 15.29 Infrastructure State Ownership

AWS services own the runtime infrastructure state.

Examples include:

* ECS task status,
* ECR image availability,
* S3 bucket state,
* OpenSearch cluster health,
* CloudFormation stack state,
* load-balancer health.

CVS Review Portal may display selected application-relevant readiness signals.

It should not duplicate the complete AWS infrastructure control plane.

## 15.30 CloudFormation Ownership

CloudFormation templates own the declared infrastructure definition for the AWS environment.

They may define:

* ECS services and task definitions,
* ECR repositories,
* S3 buckets,
* IAM roles,
* networking,
* OpenSearch resources,
* monitoring resources,
* optional database resources.

CloudFormation does not own:

* application domain data,
* document metadata,
* processing history,
* evaluation results.

Infrastructure definitions and application data lifecycles must remain separate.

## 15.31 Code Ownership

The Python codebase owns:

* domain rules,
* validation logic,
* state-transition rules,
* parser implementations,
* chunking implementations,
* retrieval logic,
* metric implementations,
* API contracts.

Configuration selects among supported behaviours.

Configuration must not redefine core domain invariants or bypass required validation.

## 15.32 Canonical Versus Derived Data

The system should classify data as either canonical or derived.

### Canonical or Authoritative

* original Source Artifact,
* Document identity,
* Document Version identity,
* approved metadata,
* governance state,
* approved Evaluation Dataset,
* approved Relevance Judgments,
* run and configuration history.

### Derived

* parsed output,
* normalized output,
* chunks,
* embeddings,
* OpenSearch indexes,
* retrieval results,
* metric reports.

Derived data may be regenerated when canonical data, configuration, and implementation version remain available.

## 15.33 Regeneration Policy

A derived artifact may be considered safely regenerable when the system retains:

```text
Canonical Source
+
Configuration Snapshot
+
Relevant Application or Model Version
+
Required Metadata
```

Examples include:

* regenerating chunks from normalized text,
* regenerating embeddings from chunks,
* rebuilding an OpenSearch index,
* rerunning an evaluation report.

Regeneration may not produce identical output when external model implementations or dependencies have changed.

Where exact reproducibility is required, model and dependency versions must be preserved.

## 15.34 Data Consistency Across Stores

CVS Review Portal may store related information across S3, the operational state store, and OpenSearch.

The system must therefore manage consistency explicitly.

Examples include:

* a Source Artifact record must correspond to an existing S3 object,
* an indexed Chunk must reference a valid Document Version,
* an active Document Version must have a verified searchable representation,
* an Index Record must correspond to an available OpenSearch index,
* an Evaluation Run must reference an existing dataset and index.

Consistency checks may run:

* during processing,
* during activation,
* during monitoring,
* through scheduled reconciliation where later required.

## 15.35 Cross-Store Transaction Boundary

S3, the operational database, and OpenSearch do not share one native transaction.

The application must therefore use controlled state transitions.

For example:

```text
1. Register processing intent
2. Store source artifact
3. Confirm storage
4. Update operational state
5. Process and index
6. Verify OpenSearch writes
7. Mark processing successful
8. Activate only after verification
```

The system must never assume that a write to one store guarantees successful writes to the others.

## 15.36 Orphaned Data

Partial failures may create orphaned data such as:

* S3 artifact without completed registration,
* operational record without source artifact,
* OpenSearch chunks from a failed Indexing Run,
* derived artifact without an active Processing Run.

The system should support:

* detection,
* safe cleanup,
* reconciliation,
* retention for debugging where appropriate.

Cleanup must not remove valid canonical data automatically.

## 15.37 Data Retention

Retention periods may differ by data category.

Indicative direction:

### Long-Term Retention

* canonical source artifacts,
* Document and Document Version records,
* governance history,
* approved evaluation datasets,
* accepted baseline reports.

### Configurable Retention

* derived parsed and normalized artifacts,
* inactive indexes,
* detailed evaluation reports,
* interactive query history,
* technical audit events.

### Shorter Retention

* temporary upload files,
* transient processing files,
* debug logs,
* failed intermediate batches where not required.

Final retention periods will depend on:

* legal obligations,
* organizational policy,
* storage cost,
* debugging requirements,
* audit needs.

## 15.38 Data Deletion Ownership

Deletion authority must be explicit.

Possible deletion actions include:

* disabling a Document Version,
* removing chunks from active retrieval,
* deleting an inactive OpenSearch index,
* deleting derived artifacts,
* deleting the canonical source artifact,
* deleting operational metadata.

These actions have different risk and should not be represented as one generic delete operation.

Permanent deletion of canonical data should require a controlled decision and must respect applicable retention requirements.

## 15.39 Backup and Recovery Ownership

AWS service configurations may provide backup and recovery mechanisms.

Indicative responsibilities include:

### S3

* versioning where enabled,
* lifecycle policies,
* replication where required.

### Operational State Store

* database backups,
* point-in-time recovery,
* schema migration control.

### OpenSearch

* snapshots or index rebuilding from canonical artifacts.

The preferred recovery approach for OpenSearch may be regeneration rather than treating the index as irreplaceable.

## 15.40 Data Access Ownership

Backend components should access data only through approved application interfaces.

Examples include:

* Artifact Storage Component for S3,
* repository or persistence interfaces for operational state,
* Retrieval and Indexing Components for OpenSearch.

The UI must not directly access storage systems.

Direct manual access may exist for administrators but should not become part of the normal application workflow.

## 15.41 Security Ownership

Each storage layer has specific security responsibilities.

### S3

* private access,
* encryption,
* controlled bucket policies,
* lifecycle rules.

### Operational State Store

* private networking,
* credentials through approved secret mechanisms,
* least-privilege database access,
* backup protection.

### OpenSearch

* private or controlled network access,
* encryption,
* restricted index operations,
* role separation where implemented.

### Application

* authorization,
* validation,
* safe logging,
* prevention of unauthorized cross-component access.

## 15.42 Data Classification

The system may later classify data according to sensitivity.

Possible categories include:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

Classification may affect:

* access control,
* logging,
* retention,
* encryption,
* query-history storage,
* export permissions.

A complete classification framework is not required in the first MVP, but the architecture should not assume that all documents and queries are public.

## 15.43 Initial MVP Ownership Matrix

| Data or Artifact           | Primary Owner                            | Secondary Representation            |
| -------------------------- | ---------------------------------------- | ----------------------------------- |
| Original source file       | S3                                       | Operational source reference        |
| Document identity          | Operational state store                  | OpenSearch reference fields         |
| Document Version           | Operational state store                  | OpenSearch metadata copy            |
| Approved document metadata | Operational state store                  | OpenSearch filter fields            |
| Governance state           | Operational state store                  | OpenSearch serving copy             |
| Parsed artifact            | S3 when retained                         | Processing-run reference            |
| Normalized artifact        | S3 when retained                         | Processing-run reference            |
| Chunk text                 | OpenSearch for serving                   | Optional S3 chunk manifest          |
| Embedding vector           | OpenSearch                               | Configuration and provenance record |
| Processing Run             | Operational state store                  | Logs and artifact references        |
| Indexing Run               | Operational state store                  | OpenSearch write outcome            |
| Index mapping definition   | Version-controlled configuration         | Deployed OpenSearch mapping         |
| Configuration definition   | Repository and environment configuration | Immutable Configuration Snapshot    |
| Golden Evaluation Dataset  | S3 or versioned dataset repository       | Operational registration            |
| Evaluation Run summary     | Operational state store                  | Detailed S3 report                  |
| Logs and runtime metrics   | CloudWatch or observability platform     | Selected application summaries      |
| Infrastructure definition  | CloudFormation                           | Deployed AWS resources              |

## 15.44 Initial MVP Simplification

The MVP does not need to persist every derived artifact.

A minimal ownership model may use:

```text
S3
→ Original source files
→ Evaluation datasets
→ Selected reports

Operational State Store
→ Documents
→ Versions
→ Processing Runs
→ Index Records
→ Configuration Snapshots
→ Evaluation Run summaries

OpenSearch
→ Chunks
→ Embeddings
→ Retrieval metadata
```

Parsed, normalized, and chunk-manifest artifacts may be retained selectively when required for debugging or reproducibility.

## 15.45 Ownership Invariants

The following rules should remain true:

1. Every Document Version must reference a canonical Source Artifact.
2. The original source file must not exist only in OpenSearch.
3. Every indexed Chunk must reference a Document Version and Processing Run.
4. OpenSearch governance fields must reflect the authoritative governance state.
5. Historical runs must reference immutable Configuration Snapshots.
6. Evaluation results must reference a specific dataset version and target index.
7. Logs must not become the only source of lifecycle state.
8. UI state must not become authoritative application state.
9. Deleting an index must not delete the canonical source artifact.
10. Rebuilding an index must be possible from retained source and configuration data.
11. Derived metadata must not silently overwrite confirmed metadata.
12. Cross-store failures must remain visible and reconcilable.

## 15.46 Data Ownership Design Principle

The ownership model must make it impossible to confuse:

```text
Stored in S3
with
Registered Successfully

Registered Successfully
with
Processed Successfully

Present in OpenSearch
with
Approved for Retrieval

Copied Into an Index
with
Authoritative Metadata

Available in Logs
with
Durable Operational State

Technically Recoverable
with
Legally Permitted to Retain
```

CVS Review Portal must maintain a clear distinction between canonical information, operational state, derived representations, and serving-time data.


# 16. Configuration Boundary

The Configuration Boundary defines which system behaviours may be changed through configuration and which behaviours must remain controlled by application code, domain rules, or infrastructure design.

The objective is to support practical experimentation and environment-specific deployment without turning CVS Review Portal into a fully dynamic framework.

Configuration should provide controlled flexibility.

It must not allow users to bypass required validation, lifecycle rules, traceability, or security controls.

## 16.1 Configuration Objectives

Configuration should allow the project to:

* change environment-specific values,
* compare retrieval configurations,
* test chunking and embedding alternatives,
* control supported runtime behaviour,
* reproduce processing and evaluation runs,
* avoid unnecessary code changes for approved parameter adjustments.

Configuration should not attempt to make every component interchangeable.

The initial principle is:

> Configure parameters that are expected to change within the Compliance project. Implement structural behaviour explicitly in code.

## 16.2 Configuration Categories

The initial configuration model may include:

```text
Application Configuration
Environment Configuration
Ingestion Configuration
Parsing and Normalization Configuration
Metadata Configuration
Chunking Configuration
Embedding Configuration
OpenSearch and Index Configuration
Retrieval Configuration
Evaluation Configuration
Observability Configuration
Security Configuration
```

These categories may initially exist in one or several validated files.

The exact file structure will be defined during technical design.

## 16.3 Application Configuration

Application Configuration controls general application behaviour.

Indicative settings include:

* application name,
* environment name,
* API version,
* log level,
* enabled functional areas,
* default pagination size,
* request-size limits,
* health-check behaviour.

Application Configuration must not contain secrets.

## 16.4 Environment Configuration

Environment Configuration contains values that differ between:

```text
Local
Development
Testing
Staging
Production
```

Indicative values include:

* AWS region,
* S3 bucket name,
* OpenSearch endpoint,
* operational database endpoint,
* ECS-specific settings,
* active index alias,
* external service endpoints.

Environment values may be supplied through:

* environment variables,
* ECS task definitions,
* CloudFormation parameters,
* AWS Systems Manager Parameter Store,
* AWS Secrets Manager.

Environment-specific values should remain separate from retrieval-experiment configuration.

## 16.5 Secret Configuration

Secrets must not be stored in:

* repository configuration files,
* Docker images,
* committed `.env` files,
* evaluation reports,
* configuration snapshots intended for general inspection.

Secrets may include:

* database passwords,
* API keys,
* private tokens,
* external model credentials,
* encryption keys.

AWS access should prefer IAM roles rather than static credentials.

Configuration Snapshots must exclude secret values or replace them with safe references.

## 16.6 Ingestion Configuration

Ingestion Configuration controls approved upload and processing limits.

Indicative settings include:

* supported file extensions,
* supported media types,
* maximum file size,
* upload timeout,
* duplicate-detection mode,
* checksum algorithm,
* S3 object prefixes,
* retained artifact types,
* retry limits.

The codebase must define which options are supported.

Configuration must not enable arbitrary file execution or unsafe parser behaviour.

## 16.7 Parser Configuration

Parser Configuration selects among explicitly supported parsers and parser options.

Indicative settings include:

* parser implementation for each file type,
* heading extraction,
* list preservation,
* document-property extraction,
* empty-section handling,
* encoding fallback policy.

An approved mapping may resemble:

```yaml
parsing:
  txt:
    parser: plain_text
  markdown:
    parser: markdown_structured
  docx:
    parser: python_docx
```

The MVP does not require arbitrary Python module names or runtime parser-plugin loading.

## 16.8 Normalization Configuration

Normalization Configuration controls deterministic text-cleaning behaviour.

Indicative settings include:

* whitespace normalization,
* line-ending normalization,
* Unicode normalization,
* control-character handling,
* repeated-empty-line limits,
* heading preservation,
* paragraph-boundary preservation.

Normalization settings must not permit silent removal of important content without explicit implementation and tests.

Some normalization rules may remain mandatory and non-configurable when required for safety or consistency.

## 16.9 Metadata Configuration

Metadata Configuration defines the approved metadata fields and related validation rules.

Indicative settings include:

* required upload fields,
* optional fields,
* allowed document types,
* allowed jurisdictions,
* allowed source-authority types,
* date formats,
* default governance state,
* fields available for filtering,
* fields copied into OpenSearch.

The MVP may use a fixed Compliance metadata model with a limited number of configurable requirements.

It does not need a fully dynamic schema-definition engine.

## 16.10 Chunking Configuration

Chunking Configuration is a primary experimentation area.

Indicative settings include:

* chunking strategy,
* chunk size,
* chunk overlap,
* minimum chunk size,
* maximum chunk size,
* heading preservation,
* section-boundary behaviour,
* inclusion of heading text,
* tokenizer or measurement unit.

Supported strategies may initially include:

```text
FIXED_SIZE
RECURSIVE
HEADING_AWARE_RECURSIVE
```

Only explicitly implemented strategies may be selected.

Changing chunking configuration creates a new processed representation and should be associated with a new Processing Run and Configuration Snapshot.

## 16.11 Embedding Configuration

Embedding Configuration defines how vectors are generated.

Indicative settings include:

* model identifier,
* model revision where available,
* vector dimensions,
* normalization setting,
* batch size,
* maximum input length,
* query prefix,
* document prefix,
* execution device,
* inference endpoint where applicable.

The system must validate compatibility between:

* selected model,
* configured dimensions,
* generated vector dimensions,
* OpenSearch index mapping.

The MVP may initially support one embedding provider and a limited set of approved models.

## 16.12 OpenSearch Connection Configuration

OpenSearch connection settings may include:

* endpoint,
* AWS region,
* authentication mode,
* connection timeout,
* read timeout,
* retry count,
* bulk-indexing batch size.

Credentials must be resolved through approved runtime mechanisms.

Connection configuration must remain separate from index-design configuration where practical.

## 16.13 Index Configuration

Index Configuration defines the searchable representation.

Indicative settings include:

* logical index name,
* physical index naming convention,
* alias,
* shard count,
* replica count,
* refresh interval,
* vector field name,
* vector dimensions,
* similarity metric,
* vector engine,
* lexical analyzers,
* keyword fields,
* date fields,
* filterable metadata,
* mapping version.

An index configuration must be treated as a controlled, versioned definition.

Changes that are incompatible with the existing mapping should normally create a new physical index.

## 16.14 Retrieval Configuration

Retrieval Configuration controls how queries are executed.

Indicative settings include:

* retrieval mode,
* target index or alias,
* top-k,
* candidate count,
* enabled metadata filters,
* default governance filters,
* lexical field boosts,
* vector search parameters,
* fusion method,
* RRF constant,
* lexical and vector weights,
* minimum-score rules,
* deduplication behaviour.

Indicative retrieval modes include:

```text
LEXICAL
VECTOR
HYBRID
```

Only approved combinations should be permitted.

Configuration validation must reject incompatible or incomplete retrieval settings.

## 16.15 Evaluation Configuration

Evaluation Configuration defines how retrieval experiments are executed.

Indicative settings include:

* evaluation dataset identifier and version,
* target index,
* retrieval configuration reference,
* K values,
* enabled metrics,
* baseline run,
* failed-query policy,
* query categories included,
* latency collection,
* report format.

The initial required metrics are:

```text
Precision@10
Recall@10
nDCG@10
```

Metric formulas and domain invariants remain implemented in code.

Configuration may select metrics but must not redefine their mathematical meaning.

## 16.16 Observability Configuration

Observability Configuration may include:

* log level,
* structured-log format,
* correlation-ID behaviour,
* stage-duration metrics,
* query-latency metrics,
* sensitive-field redaction,
* tracing enablement,
* health-check dependencies.

Mandatory security redaction rules should not be fully removable through ordinary runtime configuration.

## 16.17 Retry and Timeout Configuration

Operational parameters may be configurable within safe limits.

Examples include:

* processing retry count,
* OpenSearch retry count,
* embedding timeout,
* indexing timeout,
* request timeout,
* backoff settings,
* batch size.

The codebase should enforce minimum and maximum allowed values.

Configuration must not permit unlimited retries or unbounded resource use.

## 16.18 Configuration Sources and Precedence

The system may resolve configuration from several sources.

An indicative precedence order is:

```text
Application Defaults
→ Version-Controlled Configuration File
→ Environment-Specific Configuration
→ Environment Variables
→ Explicit Approved Runtime Override
```

The final precedence model must be documented and deterministic.

Runtime overrides should be limited to approved Technical Operator or evaluation workflows.

The effective configuration must be validated after all sources are resolved.

## 16.19 Configuration Validation

Configuration must be validated before the affected workflow begins.

Validation should detect:

* missing required values,
* unsupported options,
* invalid numeric ranges,
* incompatible combinations,
* vector-dimension mismatches,
* invalid index names,
* unknown retrieval modes,
* unsupported file types,
* invalid metric settings,
* unsafe timeout or retry values.

Invalid configuration must fail clearly.

The system must not silently replace invalid values with undocumented defaults.

## 16.20 Configuration Snapshot

Every significant Processing Run, Indexing Run, Retrieval Run used for evaluation, and Evaluation Run must reference an immutable Configuration Snapshot.

The snapshot should represent the effective validated configuration used during execution.

It may include:

* configuration content,
* configuration checksum,
* configuration type,
* application version,
* creation timestamp,
* parent configuration reference where applicable.

Historical runs must not depend on the current mutable configuration files.

## 16.21 Configuration Identity

Each Configuration Snapshot should have a stable identifier.

A checksum may help determine whether two effective configurations are identical.

However, the application should not rely only on filenames such as:

```text
config.yaml
production.yaml
experiment-1.yaml
```

Filenames are descriptive labels, not reliable configuration identities.

## 16.22 Configuration Versioning

Configuration changes should be version-controlled through Git for development and infrastructure review.

Executed configurations should also be stored as immutable snapshots.

The system must distinguish between:

```text
Configuration File Version
Configuration Snapshot
Application Version
Index Mapping Version
```

These concepts should not be merged into one generic version field.

## 16.23 Experiment Configuration

An experiment configuration should normally change only the parameters required for the experiment.

For example:

```text
Baseline
→ chunk size: 500
→ overlap: 50
→ embedding model: A
→ hybrid retrieval

Candidate
→ chunk size: 800
→ overlap: 100
→ embedding model: A
→ hybrid retrieval
```

Changing multiple major parameters at once is allowed, but the resulting comparison cannot isolate the effect of one change.

The configuration system should make the differences between baseline and candidate visible.

## 16.24 Runtime Configuration Changes

Not every configuration change should apply immediately to running workloads.

Examples:

### May Apply Without Reindexing

* query top-k,
* candidate count,
* selected metadata filters,
* certain fusion parameters,
* evaluation metric selection.

### Usually Requires Reprocessing or Reindexing

* parser behaviour,
* normalization rules,
* chunk size,
* chunk overlap,
* embedding model,
* vector dimensions,
* index mapping,
* analyzer changes.

The system must make the operational consequence of a configuration change explicit.

## 16.25 Active Configuration

The system may maintain an active configuration reference for:

* ingestion,
* retrieval,
* evaluation baseline,
* active index.

The active configuration must be identifiable through the Data Monitoring area.

Activating a configuration should not rewrite historical run records.

## 16.26 Configuration Promotion

A configuration may move through a controlled lifecycle such as:

```text
DRAFT
→ TESTED
→ APPROVED
→ ACTIVE
→ RETIRED
```

A complete configuration-approval workflow is not required for the MVP.

However, the project should distinguish between:

* experimental configuration,
* accepted baseline,
* active production configuration.

## 16.27 Configuration and Index Compatibility

An index must remain associated with the configuration that created it.

The system must prevent incompatible combinations such as:

* querying a 768-dimensional index with a 1024-dimensional query vector,
* using incorrect field names,
* applying filters against fields absent from the mapping,
* using a lexical analyzer inconsistent with the expected index design.

Compatibility checks should happen before query or indexing execution where possible.

## 16.28 Configuration and Document Compatibility

Some configuration changes may affect whether historical processing results remain usable.

For example:

* changing required metadata fields,
* changing governance defaults,
* changing parser rules,
* changing chunk identifiers.

The system must not assume that old processed representations satisfy new configuration rules.

Revalidation or reprocessing may be required.

## 16.29 Configuration and Code Compatibility

Configuration selects behaviours supported by the installed application version.

A configuration must not reference an option unsupported by that code version.

Configuration Snapshots should therefore record the application or code version used.

Backward compatibility may be introduced where useful, but it is not guaranteed for every configuration revision.

## 16.30 What Must Remain in Code

The following should normally remain controlled by application code:

* lifecycle invariants,
* entity relationships,
* authorization checks,
* state-transition validation,
* metric formulas,
* checksum verification,
* failure classification,
* source-provenance requirements,
* mandatory security controls,
* API contract validation,
* supported strategy implementations.

Configuration may select approved behaviour.

It must not redefine core correctness rules.

## 16.31 What Must Not Be Configurable Initially

The MVP does not require configuration for:

* arbitrary Python import paths,
* runtime installation of plugins,
* arbitrary workflow graphs,
* arbitrary vector databases,
* arbitrary cloud providers,
* custom executable scripts,
* user-defined metric formulas,
* user-defined lifecycle states,
* bypassing governance filters,
* disabling required provenance,
* disabling mandatory file validation,
* disabling required security controls.

These capabilities would increase complexity and operational risk without supporting the initial Compliance objective.

## 16.32 Configuration File Structure

A possible initial structure is:

```text
config/
├── application.yaml
├── ingestion.yaml
├── retrieval.yaml
├── evaluation.yaml
└── environments/
    ├── local.yaml
    ├── test.yaml
    └── production.yaml
```

Alternatively, the MVP may begin with one validated configuration file.

The number of files should reflect actual maintainability needs rather than architectural preference.

## 16.33 Example Configuration Shape

An indicative configuration may resemble:

```yaml
application:
  environment: development
  log_level: INFO

ingestion:
  supported_extensions:
    - txt
    - md
    - docx
  max_file_size_mb: 20

chunking:
  strategy: heading_aware_recursive
  chunk_size: 700
  chunk_overlap: 100

embedding:
  model: BAAI/bge-base-en-v1.5
  dimensions: 768
  normalize: true
  batch_size: 32

opensearch:
  index_name: cvs-review-portal-v1
  similarity_metric: cosine

retrieval:
  mode: hybrid
  top_k: 10
  candidate_count: 50
  fusion:
    method: rrf
    rrf_k: 60

evaluation:
  dataset: compliance-golden-v1
  k_values:
    - 10
  metrics:
    - precision
    - recall
    - ndcg
```

This example is illustrative.

It does not represent final technical decisions.

## 16.34 Configuration Testing

Configuration behaviour must be covered by automated tests.

Tests should include:

* valid configuration loading,
* missing required values,
* unsupported strategy values,
* invalid ranges,
* incompatible dimensions,
* invalid retrieval combinations,
* environment override behaviour,
* snapshot stability,
* secret exclusion.

A configuration should not be considered supported until its validation and execution paths are tested.

## 16.35 Configuration Observability

The Data Monitoring area should expose sufficient configuration information to answer:

* Which configuration processed this document version?
* Which embedding model produced this index?
* Which chunk size and overlap were used?
* Which retrieval configuration served this query?
* Which configuration produced this evaluation result?
* Which configuration is currently active?

Sensitive values must not be exposed.

## 16.36 Configuration Drift

Configuration drift occurs when deployed behaviour differs from the expected configuration.

Possible causes include:

* manual environment changes,
* stale ECS task definitions,
* untracked environment variables,
* modified OpenSearch mappings,
* local configuration overrides,
* inconsistent container versions.

The system should preserve enough information to compare:

```text
Expected Configuration
with
Resolved Runtime Configuration
with
Historical Configuration Snapshot
```

Automated drift detection may be introduced later.

## 16.37 Local Development Configuration

Local development should use safe and explicit defaults.

Local configuration may point to:

* local or test dependencies,
* LocalStack or mocked AWS services where selected,
* local OpenSearch,
* test S3 buckets,
* reduced batch sizes.

Local defaults must not silently connect to production resources.

## 16.38 Production Configuration

Production configuration should be deployed through controlled infrastructure and release processes.

Production changes should be:

* reviewable,
* versioned,
* validated,
* traceable,
* reversible where practical.

Manual modification of production settings should be minimized.

## 16.39 Initial MVP Configuration Boundary

The minimum configurable areas for the MVP are:

```text
Supported File Types
Maximum File Size
S3 Resource References
Chunking Strategy
Chunk Size
Chunk Overlap
Embedding Model
Vector Dimensions
Embedding Batch Size
OpenSearch Index Name
Retrieval Mode
Top-K
Hybrid Fusion Parameters Where Used
Evaluation Dataset
Evaluation Metrics and K Values
Logging Level
Environment-Specific Endpoints
```

The MVP does not require a UI for editing all configuration values.

Configuration may initially be managed through validated files and deployment settings.

## 16.40 Configuration Invariants

The following rules should remain true:

1. Every executed configuration must be validated.
2. Historical runs must reference immutable Configuration Snapshots.
3. Secrets must not appear in version-controlled configuration or exposed snapshots.
4. Configuration must not override domain invariants.
5. Unsupported options must fail explicitly.
6. Vector dimensions must match the embedding model and index mapping.
7. Configuration changes requiring reindexing must not be applied as simple query-time changes.
8. Runtime defaults must be explicit and documented.
9. Evaluation comparisons must identify configuration differences.
10. Environment configuration must remain separate from experiment intent.
11. Configuration must select only behaviours implemented by the installed application version.
12. Production configuration changes must be traceable.

## 16.41 Configuration Boundary Principle

The Configuration Boundary must make it impossible to confuse:

```text
Configurable
with
Arbitrary

Flexible
with
Uncontrolled

Environment Setting
with
Retrieval Experiment

Current Configuration
with
Historical Run Configuration

Changing a Parameter
with
Safely Applying the Change

Configuration Validation
with
Business Correctness
```

CVS Review Portal should use configuration to support controlled experimentation and deployment.

It should not transfer core architecture, domain invariants, or security responsibility from tested code into unrestricted configuration.


# 17. Security and Compliance Requirements

Security and compliance requirements define how CVS Review Portal protects source documents, operational state, retrieval data, infrastructure access, and user actions.

The initial objective is not to implement a complete enterprise security programme.

It is to establish secure defaults and prevent architectural decisions that would make later hardening difficult.

The system must distinguish between:

```text
Application Security
Data Security
Infrastructure Security
Access Control
Auditability
Compliance-Specific Safeguards
```

## 17.1 Security Objectives

CVS Review Portal should protect:

* source documents,
* document metadata,
* document versions,
* processing artifacts,
* operational records,
* queries,
* retrieval results,
* evaluation datasets,
* configuration,
* credentials,
* infrastructure resources.

The primary security objectives are:

```text
Confidentiality
Integrity
Availability
Traceability
Least Privilege
Controlled Data Lifecycle
```

## 17.2 Security Boundary

The initial security boundary includes:

* the user interface,
* FastAPI endpoints,
* document uploads,
* processing components,
* S3 access,
* OpenSearch access,
* operational-state persistence,
* ECS tasks,
* deployment configuration,
* logs and metrics.

External source websites, legal authority, and organizational compliance decisions remain outside the application security boundary.

## 17.3 Authentication

The MVP may use a simplified authentication mechanism suitable for a controlled development environment.

Possible initial approaches include:

* restricted network access,
* a simple application login,
* an API key for technical testing,
* access through an authenticated reverse proxy.

The MVP does not require full enterprise SSO.

However, production-facing endpoints must not remain anonymously accessible unless explicitly justified.

Authentication design should support later integration with:

* OpenID Connect,
* OAuth 2.0,
* AWS Cognito,
* enterprise identity providers,
* SAML-based SSO.

## 17.4 Authorization

Authorization must distinguish between read and write capabilities.

Indicative capability groups include:

```text
Document Ingestion
Document Monitoring
Governance Management
Index Management
Query Execution
Evaluation Execution
Configuration Management
Audit Inspection
```

The initial MVP may simplify authorization into:

```text
Technical Operator
Query User
```

The Technical Operator may perform ingestion, monitoring, testing, and controlled administrative actions.

The Query User may submit queries and inspect permitted results.

## 17.5 Least-Privilege Principle

Users and system components must receive only the permissions required to perform their responsibilities.

Examples include:

* the UI must not access S3 directly,
* the Query component should not delete source artifacts,
* the Processing Worker should not manage unrelated AWS resources,
* the application should not use administrator-level AWS credentials,
* a Query User should not activate or delete document versions.

Least privilege applies to:

* application roles,
* AWS IAM roles,
* database permissions,
* OpenSearch permissions,
* deployment pipelines,
* human administrators.

## 17.6 Separation of Technical and Domain Authority

The ability to process a document does not automatically grant authority to classify it as:

* official,
* legally binding,
* active,
* authoritative,
* applicable.

Technical users may operate the system.

Domain authority should remain with an approved Compliance Administrator, reviewer, or other authorized role where required.

The MVP may combine these responsibilities operationally, but the domain model should preserve the distinction.

## 17.7 AWS Identity and Access Management

AWS workloads should use IAM roles rather than static access keys.

Indicative roles may include:

* ECS Task Role,
* ECS Execution Role,
* deployment role,
* CI/CD role,
* administrative support role.

The ECS Task Role should grant only required application permissions, such as:

* read and write access to approved S3 prefixes,
* approved OpenSearch operations,
* access to specific secrets or parameters,
* log publishing.

The ECS Execution Role should remain limited to infrastructure execution needs such as:

* pulling images from ECR,
* sending logs,
* retrieving approved runtime secrets.

## 17.8 Secret Management

Secrets must not be stored in:

* source code,
* committed configuration files,
* Docker images,
* logs,
* evaluation reports,
* public documentation,
* configuration snapshots.

Secrets may include:

* database credentials,
* external API keys,
* service tokens,
* private certificates,
* encryption material.

Approved storage may include:

* AWS Secrets Manager,
* AWS Systems Manager Parameter Store,
* protected CI/CD secret storage.

Secret values should be injected at runtime.

## 17.9 Network Security

Production AWS resources should use private networking where practical.

Indicative direction:

```text
Public Entry Point
→ Load Balancer or Controlled Application Endpoint
→ Private ECS Tasks
→ Private S3 Access
→ Private OpenSearch Access
→ Private Operational Database
```

OpenSearch and the operational database should not be publicly accessible without a justified requirement.

Security groups should restrict traffic to known application components and required ports.

## 17.10 Transport Encryption

Data must be encrypted in transit.

This includes communication between:

* users and the application,
* application and S3,
* application and OpenSearch,
* application and operational state store,
* application and external model services.

HTTPS or TLS must be used for production communication.

Certificate validation must not be disabled in production.

## 17.11 Encryption at Rest

Sensitive stored data should be encrypted at rest.

This includes:

* S3 objects,
* OpenSearch data,
* operational database storage,
* logs,
* backups,
* evaluation artifacts.

AWS-managed encryption keys may be sufficient initially.

Customer-managed KMS keys may be introduced when required by organizational policy, separation of duties, auditability, or data-classification requirements.

## 17.12 S3 Security

S3 buckets used by CVS Review Portal should:

* block public access,
* use encryption at rest,
* restrict access through IAM,
* use controlled object prefixes,
* enable versioning where justified,
* use lifecycle policies where appropriate,
* record access events where required.

Pre-signed URLs may be used for controlled temporary access.

They should:

* have limited validity,
* grant only required access,
* avoid exposing unrestricted bucket paths.

## 17.13 OpenSearch Security

OpenSearch access must be restricted to approved application and administrative identities.

Security controls may include:

* VPC-only access,
* IAM-based access,
* fine-grained access control where required,
* encryption in transit,
* encryption at rest,
* index-level permissions.

Normal Query Users should access OpenSearch only through the CVS Review Portal API.

They should not receive direct OpenSearch credentials.

## 17.14 Operational State Store Security

If PostgreSQL or another operational database is introduced, it should use:

* private network access,
* encrypted connections,
* encrypted storage,
* restricted database roles,
* managed secrets,
* backup protection,
* controlled migration permissions.

Application runtime access should be separated from administrative schema-management access where practical.

## 17.15 Upload Security

Uploaded files must be treated as untrusted input.

Validation must include:

* allowed extension,
* expected media type where available,
* maximum file size,
* empty-file detection,
* basic parser readability,
* safe filename handling,
* checksum generation.

The application must not rely solely on the filename extension.

The original filename must not be used directly as an unrestricted S3 object path or local filesystem path.

## 17.16 Malicious or Unsafe Files

Even supported formats may contain malicious or malformed content.

Potential risks include:

* decompression bombs,
* malformed DOCX archives,
* extremely large internal structures,
* parser denial of service,
* embedded external relationships,
* unexpected macros or attachments,
* path traversal through archive entries.

The system should use safe parser libraries and enforce:

* size limits,
* parsing timeouts where practical,
* archive-entry limits,
* memory limits,
* controlled temporary storage.

The system does not need to execute macros, embedded scripts, or external document relationships.

## 17.17 File-Type Scope

The MVP supports:

```text
TXT
Markdown
DOCX
```

Unsupported formats must be rejected.

The system must not attempt best-effort parsing of arbitrary binary files.

PDF, OCR, HTML, images, and spreadsheets require separate security and parsing reviews before support is introduced.

## 17.18 Temporary File Handling

Temporary processing files should:

* use controlled directories,
* use generated names,
* avoid user-controlled paths,
* have restricted permissions,
* be removed after processing,
* not persist across runs unless explicitly retained.

Container-local storage must not be treated as durable source storage.

## 17.19 Input Validation

All external inputs must be validated through explicit schemas.

This includes:

* upload metadata,
* query requests,
* filters,
* pagination,
* governance-state changes,
* evaluation requests,
* configuration overrides.

Validation must reject:

* unexpected fields where appropriate,
* invalid identifiers,
* unsupported enum values,
* invalid date formats,
* excessive string lengths,
* invalid numeric ranges.

Pydantic models should be used for application-level validation.

## 17.20 API Security

FastAPI endpoints should apply:

* authentication,
* authorization,
* request validation,
* request-size limits,
* secure error responses,
* rate limiting where justified,
* correlation identifiers,
* safe CORS configuration.

Production CORS settings must not allow unrestricted origins unless explicitly required.

Interactive API documentation may be restricted or disabled in production when appropriate.

## 17.21 Rate Limiting and Resource Protection

The system should protect expensive or sensitive operations from abuse.

Potentially controlled operations include:

* file uploads,
* document processing,
* embedding generation,
* retrieval queries,
* evaluation runs,
* reprocessing,
* index creation.

The initial MVP may implement simple limits.

More advanced rate limiting may be introduced when user volume and abuse scenarios are known.

## 17.22 Denial-of-Service Protection

The system should enforce bounded resource use.

Examples include:

* maximum upload size,
* maximum document length,
* maximum query length,
* bounded top-k,
* bounded candidate count,
* bounded batch size,
* bounded retry count,
* processing timeouts,
* concurrency limits.

Configuration must not allow unbounded values.

## 17.23 Query Security

Queries may contain confidential information.

The system should define whether query text is:

* stored,
* logged,
* redacted,
* retained temporarily,
* excluded from long-term history.

Full query text should not be included automatically in general-purpose logs.

Sensitive query handling should be appropriate to the document classification and deployment context.

## 17.24 Retrieval Authorization

Retrieval must apply authorization and governance filters before results are returned.

The system must prevent unauthorized access to:

* disabled documents,
* restricted documents,
* documents outside the user’s permitted scope,
* experimental indexes where access is limited,
* previous versions where historical access is restricted.

The initial single-knowledge-base MVP may not require document-level authorization.

However, the retrieval interface should not bypass the application layer in a way that makes future enforcement impossible.

## 17.25 Governance Enforcement

Document governance states must be enforced in retrieval.

Normal Query User access should exclude content marked:

```text
SUPERSEDED
DISABLED
DELETED
```

unless the approved use case permits historical retrieval.

Governance filtering must not rely only on UI behaviour.

It must be enforced by backend retrieval logic.

## 17.26 Data Integrity

The system must protect against accidental or unauthorized modification.

Integrity mechanisms may include:

* content checksums,
* immutable source references,
* version identifiers,
* configuration checksums,
* controlled state transitions,
* indexing verification,
* database constraints,
* audit events.

A source artifact change should not occur silently under the same Document Version identity.

## 17.27 Source Artifact Integrity

The content checksum recorded during upload should be verifiable against the stored S3 object.

If the stored content differs from the registered checksum, the artifact should not be treated as valid without investigation.

S3 versioning may be enabled where preservation of historical object states is required.

## 17.28 Processing Integrity

Each Processing Run must use an identified:

* Source Artifact,
* Document Version,
* Configuration Snapshot,
* application version where required.

The system must not combine chunks or embeddings from unrelated processing configurations within one controlled representation without explicit design.

Partial processing must not be marked as complete.

## 17.29 Index Integrity

Indexing verification should detect:

* failed bulk writes,
* missing chunks,
* vector-dimension mismatches,
* missing required metadata,
* incorrect target index,
* duplicate identifiers where uniqueness is expected.

A Document Version must not become retrievable until required verification succeeds.

## 17.30 Configuration Integrity

Configuration must be:

* validated,
* version-controlled where applicable,
* associated with immutable execution snapshots,
* protected from unauthorized production modification.

Configuration changes affecting indexing or retrieval must be traceable.

Historical runs must not be relabeled with newer configuration values.

## 17.31 Logging Security

Logs should include safe operational information such as:

* request identifier,
* correlation identifier,
* Document identifier,
* Processing Run identifier,
* stage,
* duration,
* error category,
* outcome.

Logs should not include uncontrolled:

* full document content,
* full query content,
* embedding vectors,
* credentials,
* access tokens,
* personal data,
* confidential metadata.

Redaction rules should be implemented in code and not be removable through ordinary user configuration.

## 17.32 Error Handling

User-facing errors must provide useful information without exposing:

* stack traces,
* internal network details,
* credentials,
* SQL statements,
* OpenSearch internals,
* sensitive document content,
* infrastructure identifiers not intended for users.

Technical diagnostic information should be available through structured logs and monitoring.

## 17.33 Auditability

Important actions should be traceable.

Examples include:

* document uploaded,
* document version created,
* processing started,
* processing retried,
* index created,
* index activated,
* document activated,
* document superseded,
* document disabled,
* evaluation executed,
* configuration promoted.

An audit record should eventually include:

* actor,
* timestamp,
* action,
* affected entity,
* previous state,
* new state,
* outcome,
* correlation identifier.

The earliest MVP may implement a simplified audit model.

## 17.34 Audit Log Protection

Audit data should be protected from unauthorized modification and deletion.

Audit records must remain separate from ordinary application logs when formal auditability is required.

Access to audit history should be read-only for most users.

## 17.35 Data Retention

Retention must be defined separately for:

* canonical source artifacts,
* document metadata,
* processing history,
* inactive indexes,
* derived artifacts,
* query history,
* evaluation datasets,
* evaluation reports,
* application logs,
* audit events.

Retention should reflect:

* legal requirements,
* organizational policy,
* debugging needs,
* reproducibility,
* storage cost,
* data sensitivity.

The MVP may begin with explicit development defaults.

It should not implement indefinite retention accidentally.

## 17.36 Data Deletion

Deletion must distinguish between:

```text
Disable From Retrieval
Remove From Active Index
Delete Derived Artifacts
Delete Canonical Source
Delete Operational Metadata
Delete Audit History
```

These actions must not be collapsed into one uncontrolled delete command.

Permanent source deletion should require deliberate authorization.

Deletion behaviour must respect any applicable retention, investigation, or legal-hold requirements.

## 17.37 Backup and Recovery

Security includes the ability to recover from failure or accidental deletion.

Indicative requirements include:

* S3 durability and optional versioning,
* operational database backups,
* controlled database migrations,
* OpenSearch snapshots or rebuild capability,
* version-controlled CloudFormation,
* recoverable configuration.

OpenSearch should remain rebuildable from retained source artifacts and processing configuration where practical.

## 17.38 Availability

The MVP should provide basic availability protections, including:

* health endpoint,
* readiness endpoint,
* dependency checks,
* controlled retries,
* ECS task restart behaviour,
* timeout handling,
* clear degraded-state reporting.

The initial release does not require multi-region active-active architecture.

Availability targets should be defined only when real operational requirements exist.

## 17.39 Dependency Security

The project should manage software dependencies through Poetry and controlled lockfiles.

Security practices should include:

* pinned or locked dependencies,
* dependency vulnerability scanning,
* timely security updates,
* removal of unused dependencies,
* trusted package sources,
* reviewed base images.

Container and dependency scanning may be integrated into CI/CD.

## 17.40 Container Security

Containers should:

* run as a non-root user,
* use minimal runtime images,
* avoid unnecessary tools,
* avoid embedded secrets,
* use read-only filesystems where practical,
* limit writable directories,
* define health checks,
* use pinned base-image versions or controlled update policies.

Build and runtime stages should remain separated.

## 17.41 CI/CD Security

The deployment pipeline should use short-lived credentials.

GitHub Actions or another CI/CD platform should authenticate to AWS through OIDC where possible.

The pipeline should avoid persistent AWS access keys.

Deployment permissions should be limited to required:

* ECR operations,
* CloudFormation operations,
* ECS updates,
* approved infrastructure resources.

Code-quality, tests, and security checks should run before deployment.

## 17.42 Infrastructure as Code Security

CloudFormation templates should define security-sensitive infrastructure explicitly.

This may include:

* IAM roles,
* security groups,
* encryption settings,
* bucket policies,
* private networking,
* logging,
* backup settings.

Manual production changes should be minimized.

Infrastructure drift should be detectable through AWS and deployment controls.

## 17.43 Environment Separation

Development, testing, staging, and production environments should use separate resources where practical.

Examples include:

* S3 buckets,
* OpenSearch indexes or domains,
* operational databases,
* IAM roles,
* secrets,
* ECS services.

Local and test environments must not connect silently to production resources.

## 17.44 Production Data in Development

Production documents, queries, and metadata should not be copied into development environments without explicit approval and appropriate protection.

Test environments should prefer:

* synthetic data,
* public regulatory documents,
* sanitized datasets,
* controlled test metadata.

## 17.45 Data Classification

The system may later classify documents and related data as:

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

Classification may influence:

* user access,
* query logging,
* export permissions,
* retention,
* encryption-key requirements,
* environment use.

A complete classification framework is not required in the MVP.

However, the design must not assume that all compliance documents are public.

## 17.46 Personal Data

Although the initial corpus may focus on regulations and policies, uploaded documents or queries may contain personal data.

The system should support:

* data minimization,
* controlled access,
* limited logging,
* justified retention,
* deletion procedures,
* restricted non-production use.

Personal-data handling requirements must be refined when the actual corpus and users are known.

## 17.47 Prompt Injection and Document-Based Attacks

Future LLM capabilities may treat retrieved document text as model context.

Documents must therefore be considered untrusted instructions.

Possible future risks include:

* prompt injection inside documents,
* requests to ignore system rules,
* malicious tool instructions,
* fabricated authority statements,
* data-exfiltration attempts.

The retrieval-only MVP does not execute document instructions.

Future LLM or agentic components must clearly separate:

```text
Retrieved Evidence
from
Trusted System Instructions
```

## 17.48 Model and Embedding Service Security

If an external model service is used, the project must evaluate:

* what document or query content is transmitted,
* provider data-retention policy,
* geographic processing location,
* encryption,
* contractual controls,
* whether submitted content is used for model training,
* availability and rate limits.

Sensitive documents must not be sent to an external provider without an approved data-handling decision.

## 17.49 Compliance-Specific Source Provenance

Every retrieved result must identify sufficient provenance for human verification.

This should include:

* source Document,
* Document Version,
* source authority where available,
* section or heading,
* publication or effective date where available,
* governance status,
* source-artifact reference.

A result without provenance must not be treated as reliable compliance evidence.

## 17.50 Official and Secondary Sources

The system should preserve whether a source is:

* official,
* secondary guidance,
* internal policy,
* interpretative material,
* other approved category.

The system must not automatically infer legal authority solely from semantic content.

Authority classification should be supplied or confirmed through controlled metadata and governance processes.

## 17.51 Version and Applicability Safeguards

Normal retrieval must reduce the risk of returning outdated evidence.

Safeguards include:

* active-version filtering,
* governance-state enforcement,
* effective-date metadata,
* document-version visibility,
* superseded-version exclusion,
* source-authority display.

The system cannot guarantee legal applicability automatically.

It must provide the information needed for human assessment.

## 17.52 Human Responsibility

CVS Review Portal supports:

* evidence discovery,
* retrieval testing,
* traceability,
* document governance,
* evaluation.

It does not replace:

* qualified legal advice,
* compliance review,
* regulatory interpretation,
* formal audit,
* certification,
* organizational accountability.

Security controls must not create the impression that technically protected output is legally correct.

## 17.53 Compliance With Applicable Requirements

The project should be designed to support applicable organizational and legal requirements.

Depending on the final deployment and data, these may include:

* GDPR obligations,
* security policies,
* record-retention policies,
* access-control requirements,
* audit requirements,
* vendor-risk management,
* incident-response requirements.

The exact compliance obligations cannot be finalized until the deployment context, users, document corpus, and data classifications are known.

## 17.54 Incident Detection and Response

The MVP should provide enough observability to investigate incidents such as:

* unauthorized access attempt,
* unexpected document modification,
* repeated failed uploads,
* abnormal query volume,
* processing abuse,
* invalid governance changes,
* compromised credential use.

A complete Security Operations Center integration is outside the MVP.

However, security-relevant events should be loggable and traceable.

## 17.55 Security Testing

Automated and manual testing should cover critical security behaviour.

Examples include:

* unauthorized endpoint access,
* invalid file types,
* oversized files,
* unsafe filenames,
* invalid metadata,
* excessive query length,
* restricted governance-state access,
* secret leakage in logs,
* permission-boundary tests,
* configuration validation,
* malicious DOCX structures where practical.

Security tests should become part of the deliverable Definition of Done.

## 17.56 Threat Modelling

A lightweight threat model should be created before production deployment.

It should consider:

* malicious uploaders,
* unauthorized Query Users,
* compromised application credentials,
* accidental administrative actions,
* untrusted document content,
* data leakage through logs,
* insecure index access,
* configuration tampering,
* dependency vulnerabilities,
* cross-environment access.

Threat modelling should focus on realistic risks rather than speculative complexity.

## 17.57 Initial MVP Security Requirements

The minimum required security baseline includes:

```text
Validated Uploads
Private S3 Storage
Encryption in Transit
Encryption at Rest
IAM Task Roles
No Static AWS Credentials
No Secrets in Source Code
Non-Root Containers
Validated API Contracts
Restricted OpenSearch Access
Safe Logging
Governance Filtering
Configuration Validation
Structured Audit-Relevant Events
```

The MVP may use simplified authentication in a controlled environment.

Production exposure requires an approved authentication and authorization mechanism.

## 17.58 Security Invariants

The following rules should remain true:

1. Source documents must not be publicly accessible by default.
2. AWS runtime access must use approved IAM roles.
3. Secrets must not be committed to the repository.
4. Uploaded files must be validated before processing.
5. User-controlled filenames must not define unrestricted storage paths.
6. Unsupported files must not enter the processing pipeline.
7. Normal retrieval must enforce governance restrictions.
8. The UI must not access storage systems directly.
9. Logs must not expose uncontrolled source or query content.
10. Historical configuration records must not contain secrets.
11. A failed authorization check must stop the requested action.
12. Document provenance must remain visible in retrieval results.
13. Security controls must be enforced by the backend, not only by the UI.
14. Technical users must not automatically receive domain authority.
15. OpenSearch must not become a public or unrestricted query endpoint.
16. Production resources must not be used silently from local development.
17. Permanent deletion must remain separate from retrieval disablement.
18. Future LLM components must treat document content as untrusted input.

## 17.59 Security and Compliance Design Principle

The security model must make it impossible to confuse:

```text
Authenticated
with
Authorized

Technically Accessible
with
Permitted to Use

Indexed
with
Approved for Retrieval

Encrypted
with
Legally Compliant

Logged
with
Auditable

Relevant
with
Authoritative

Securely Delivered
with
Legally Correct
```

CVS Review Portal must protect the technical and knowledge lifecycle while preserving clear human responsibility for source authority, legal interpretation, and compliance decisions.



# 18. Observability and Auditability

Observability and Auditability define how CVS Review Portal exposes operational behaviour, document-processing state, retrieval activity, configuration usage, and important user or system actions.

The objective is to make the system understandable and diagnosable without relying on direct inspection of containers, raw database records, or OpenSearch internals.

The system must distinguish between:

```text
Observability
→ Understanding current and historical system behaviour

Auditability
→ Preserving traceable evidence of significant actions and state changes
```

Observability supports engineering and operations.

Auditability supports accountability, governance, investigation, and historical reconstruction.

## 18.1 Objectives

The observability and audit model should allow authorized users to answer:

* What happened?
* When did it happen?
* Which component performed the action?
* Which document, version, run, index, query, or evaluation was affected?
* Which configuration was used?
* Did the operation succeed, fail, or partially complete?
* Which processing stage failed?
* Who initiated or approved an important state change?
* Can the resulting data and behaviour be reconstructed?

## 18.2 Observability Scope

Application observability includes:

* API requests,
* document ingestion,
* processing stages,
* artifact storage,
* chunk generation,
* embedding generation,
* indexing,
* document governance,
* query execution,
* retrieval latency,
* evaluation execution,
* configuration resolution,
* dependency health.

Infrastructure observability remains primarily within AWS services and may include:

* ECS task health,
* CPU and memory utilization,
* container restarts,
* load-balancer health,
* OpenSearch cluster health,
* database health,
* S3 and networking events,
* CloudFormation stack state.

CVS Review Portal may expose selected infrastructure-readiness signals but should not duplicate the complete AWS monitoring layer.

## 18.3 Auditability Scope

Auditability focuses on significant actions and state transitions, including:

* document uploaded,
* Document Version created,
* processing started,
* processing retried,
* processing failed,
* index created,
* index activated,
* document version activated,
* document version superseded,
* document version disabled,
* reprocessing initiated,
* evaluation executed,
* baseline changed,
* configuration promoted,
* important metadata corrected,
* deletion requested or completed.

Not every debug log entry is an audit event.

Audit events should represent meaningful actions that may require later explanation.

## 18.4 Observability Layers

The system should use several complementary observability layers.

### Application Logs

Detailed structured records of technical events.

### Operational State

Durable current and historical state for Documents, runs, indexes, and evaluations.

### Metrics

Aggregated numerical signals used to identify behaviour and trends.

### Traces or Correlation Flows

Relationships between requests and downstream operations.

### Audit Events

Durable records of important actions and state changes.

These layers must not be treated as interchangeable.

## 18.5 Structured Logging

Application logs should use a structured format suitable for machine search and aggregation.

Indicative fields include:

* timestamp,
* log level,
* environment,
* service or component,
* event name,
* request identifier,
* correlation identifier,
* actor identifier where permitted,
* Document identifier,
* Document Version identifier,
* Processing Run identifier,
* Indexing Run identifier,
* Retrieval Run identifier,
* Evaluation Run identifier,
* stage,
* outcome,
* duration,
* error category.

Free-form text may be included for human readability, but important diagnostic fields should remain structured.

## 18.6 Correlation Identifiers

Every user request should receive a correlation identifier.

This identifier should connect related events across:

```text
UI Request
→ FastAPI Request
→ Processing Run
→ S3 Operation
→ Embedding Operation
→ OpenSearch Operation
→ Final Response
```

Long-running background processing may use both:

* request correlation identifier,
* durable Processing Run identifier.

The Processing Run identifier should remain the primary business-process reference after the initiating API request has completed.

## 18.7 Domain Identifiers in Logs

Logs should include stable domain identifiers when relevant.

Examples include:

* `document_id`,
* `document_version_id`,
* `processing_run_id`,
* `indexing_run_id`,
* `index_id`,
* `retrieval_run_id`,
* `evaluation_run_id`,
* `configuration_snapshot_id`.

Logs should not rely only on:

* filenames,
* user-facing titles,
* S3 object keys,
* OpenSearch internal identifiers.

Stable identifiers make cross-system investigation more reliable.

## 18.8 Sensitive Data in Logs

Logs must avoid uncontrolled inclusion of:

* complete document content,
* complete query text,
* chunk text,
* embedding vectors,
* credentials,
* access tokens,
* database connection strings,
* personal data,
* confidential metadata.

Where diagnostic context is required, the system may log:

* content length,
* checksum,
* safe identifier,
* redacted excerpt,
* metadata field names,
* error category.

Redaction rules should be enforced in code.

They should not depend only on developer discipline.

## 18.9 API Observability

For API requests, the system should record:

* endpoint,
* HTTP method,
* status code,
* request duration,
* request size where useful,
* response size where useful,
* authenticated actor reference where available,
* correlation identifier,
* error category.

Health-check traffic may use reduced logging to avoid unnecessary volume.

Request bodies must not be logged automatically.

## 18.10 Ingestion Observability

The ingestion workflow should record:

* upload accepted or rejected,
* file type,
* file size,
* checksum result,
* generated identifiers,
* source-storage outcome,
* duplicate-detection outcome,
* processing start,
* processing completion,
* processing failure.

The system should make it possible to distinguish:

```text
Upload Failed
Source Storage Failed
Processing Failed
Indexing Failed
Verification Failed
```

These conditions must not appear as one generic ingestion error.

## 18.11 Processing-Stage Observability

Each processing stage should expose:

* stage name,
* start timestamp,
* completion timestamp,
* duration,
* attempt number,
* input reference,
* output reference where retained,
* status,
* error category,
* safe error summary.

Indicative stages include:

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

This information may be represented through durable stage state, structured logs, or both.

## 18.12 Parsing Observability

Parsing observability may include:

* parser implementation,
* parser version,
* input file type,
* input size,
* extracted paragraph count,
* extracted heading count,
* output text length,
* warning count,
* parsing duration,
* failure category.

The system should detect suspicious outcomes such as:

* zero extracted text,
* unexpectedly small output,
* malformed source structure,
* unsupported document features.

Warnings should remain distinguishable from failures.

## 18.13 Normalization Observability

Normalization observability may include:

* normalization configuration,
* input length,
* output length,
* removed control-character count,
* preserved heading count,
* normalization duration,
* validation warnings.

Large unexpected differences between input and normalized output should be visible for investigation.

## 18.14 Chunking Observability

Chunking observability should include:

* chunking strategy,
* chunk size,
* overlap,
* generated chunk count,
* minimum chunk size,
* maximum chunk size,
* average chunk size,
* empty chunks rejected,
* duplicate chunks detected,
* processing duration.

These signals help diagnose retrieval problems caused by chunking rather than search configuration.

## 18.15 Embedding Observability

Embedding observability should include:

* model identifier,
* model revision where available,
* vector dimensions,
* batch size,
* chunk count,
* successful vector count,
* failed vector count,
* total duration,
* average batch duration,
* retry count,
* execution environment or endpoint.

Full vectors must not be logged.

The system should detect:

* unexpected dimensions,
* incomplete batches,
* model loading failures,
* external provider failures,
* rate-limit errors.

## 18.16 Indexing Observability

Indexing observability should include:

* target index,
* expected document count,
* successful write count,
* failed write count,
* bulk-request count,
* retry count,
* indexing duration,
* verification outcome,
* mapping-compatibility result.

Partial bulk failures must remain visible.

The system must not report only the HTTP success of a bulk request when individual item writes failed.

## 18.17 Index Observability

The application-level index view should expose:

* logical index name,
* physical index name,
* alias where applicable,
* lifecycle status,
* readiness status,
* mapping version,
* embedding model,
* vector dimensions,
* source corpus,
* document count,
* chunk count,
* creation timestamp,
* last verified timestamp.

Detailed node, shard, storage, and cluster metrics may remain in OpenSearch and CloudWatch tooling.

## 18.18 Query Observability

Query execution should record:

* Retrieval Run identifier,
* target index,
* retrieval mode,
* top-k,
* candidate count,
* applied filters,
* result count,
* query-embedding duration where applicable,
* OpenSearch execution duration,
* total retrieval latency,
* execution outcome.

Full query text should be stored or logged only according to an approved retention and sensitivity policy.

A safe query hash or evaluation-query identifier may be used where full text retention is unnecessary.

## 18.19 Retrieval Result Observability

The system may record result-level technical information for debugging or evaluation, including:

* chunk identifier,
* rank,
* retrieval channel,
* lexical score,
* vector score,
* fused score,
* governance-filter outcome.

Interactive result details do not need permanent retention by default.

Evaluation runs should preserve sufficient result information for reproducibility and comparison.

## 18.20 Evaluation Observability

Evaluation observability should include:

* Evaluation Run identifier,
* dataset identifier and version,
* target index,
* configuration snapshot,
* query count,
* successful query count,
* failed query count,
* execution duration,
* aggregate metrics,
* baseline comparison outcome.

Query-level evaluation results should identify:

* retrieved ranks,
* relevance judgments,
* metric values,
* execution failures,
* no-result outcomes.

## 18.21 Configuration Observability

Authorized users should be able to determine:

* which configuration is currently active,
* which configuration processed a Document Version,
* which configuration created an index,
* which configuration served a Retrieval Run,
* which configuration produced an Evaluation Run.

Configuration observability should expose safe, non-secret values.

Configuration Snapshots must not reveal credentials or sensitive runtime secrets.

## 18.22 Application Metrics

Indicative application metrics include:

### Ingestion Metrics

* uploads accepted,
* uploads rejected,
* ingestion success rate,
* ingestion failure rate,
* processing duration,
* documents awaiting processing.

### Processing Metrics

* parser failures,
* metadata-validation failures,
* average chunk count,
* embedding failures,
* indexing failures,
* verification failures.

### Query Metrics

* query volume,
* successful retrieval rate,
* no-result rate,
* failure rate,
* average latency,
* P95 latency where useful.

### Evaluation Metrics

* evaluation duration,
* failed evaluation queries,
* latest Precision@10,
* latest Recall@10,
* latest nDCG@10,
* baseline regression count.

Metrics should support diagnosis without exposing sensitive content.

## 18.23 Business and Knowledge-Lifecycle Metrics

The Data Monitoring area may expose application-level counts such as:

* total Documents,
* total Document Versions,
* active versions,
* superseded versions,
* disabled versions,
* failed Processing Runs,
* active indexes,
* inactive indexes,
* documents without verified indexes,
* orphaned or inconsistent records.

These metrics describe the health of the knowledge base rather than infrastructure utilization.

## 18.24 Health Checks

The application should provide a lightweight health endpoint indicating whether the process is running.

A liveness check should avoid dependence on every external service.

Example purpose:

```text
Is the application process alive?
```

A failing external dependency should not necessarily cause the container to be treated as dead if the application can still recover.

## 18.25 Readiness Checks

The readiness endpoint should indicate whether the application is capable of serving its intended traffic.

Depending on the component, readiness may check:

* configuration validity,
* operational state-store connectivity,
* OpenSearch connectivity,
* required index availability,
* S3 access,
* embedding component readiness.

Readiness checks should be bounded and should not create excessive load.

## 18.26 Dependency Health

Dependency-health information should distinguish between:

```text
AVAILABLE
DEGRADED
UNAVAILABLE
UNKNOWN
```

The application may remain partially usable when one dependency is degraded.

For example:

* Data Monitoring may remain available during an embedding-service outage.
* Query may remain available while new ingestion is paused.
* Source uploads may be accepted only if durable storage remains available.

The exact degraded-mode behaviour will be defined during technical design.

## 18.27 Error Classification

Errors should use controlled categories rather than unstructured exception text alone.

Indicative categories include:

```text
VALIDATION_ERROR
AUTHENTICATION_ERROR
AUTHORIZATION_ERROR
STORAGE_ERROR
PARSER_ERROR
NORMALIZATION_ERROR
METADATA_ERROR
CHUNKING_ERROR
EMBEDDING_ERROR
INDEXING_ERROR
RETRIEVAL_ERROR
EVALUATION_ERROR
CONFIGURATION_ERROR
DEPENDENCY_ERROR
INTERNAL_ERROR
```

Error classification supports:

* user messaging,
* retry decisions,
* metrics,
* alerting,
* root-cause analysis.

## 18.28 Warning Classification

Warnings should represent suspicious but non-fatal conditions.

Examples include:

* unusually low extracted text,
* missing optional metadata,
* very small chunks,
* high duplicate rate,
* weak retrieval results,
* inactive source referenced in diagnostic mode,
* unexpected index-count difference within an approved tolerance.

Warnings must not be used to hide conditions that should cause failure.

## 18.29 Alerting

Alerts should focus on conditions requiring timely action.

Possible examples include:

* repeated ingestion failures,
* sustained OpenSearch unavailability,
* high indexing-failure rate,
* processing backlog growth,
* evaluation regression against baseline,
* unauthorized access attempts,
* repeated configuration failures,
* missing active index,
* source and index consistency mismatch.

Alert thresholds should be based on actual operational requirements.

The MVP does not require a complex alerting platform before representative usage exists.

## 18.30 Dashboards

Operational dashboards may be divided into:

### Application Operations Dashboard

* request volume,
* error rates,
* processing duration,
* queue or backlog where applicable,
* dependency state.

### Knowledge Base Dashboard

* Documents,
* versions,
* processing states,
* governance states,
* indexes,
* data inconsistencies.

### Retrieval Quality Dashboard

* query latency,
* no-result rate,
* evaluation metrics,
* baseline comparison,
* critical-query regressions.

The first MVP may expose this information through simple Data Monitoring and Evaluation pages rather than a dedicated dashboard platform.

## 18.31 Audit Event Model

An Audit Event should include, where applicable:

* audit-event identifier,
* timestamp,
* actor type,
* actor identifier,
* action,
* affected entity type,
* affected entity identifier,
* previous state,
* new state,
* outcome,
* reason or comment,
* correlation identifier,
* source component.

Audit records should be structured and durable.

## 18.32 Actor Identification

Audit events should distinguish between:

```text
HUMAN_USER
SYSTEM_COMPONENT
BACKGROUND_JOB
DEPLOYMENT_PIPELINE
ADMINISTRATOR
```

Where authentication is simplified, actor information may initially be limited.

The design should allow stronger identity attribution when enterprise authentication is introduced.

## 18.33 Auditable Actions

At minimum, the following actions should be considered for audit recording:

* source document upload,
* Document Version creation,
* document metadata change,
* governance-state change,
* processing retry,
* reprocessing request,
* index creation,
* index activation,
* active-index change,
* evaluation execution,
* baseline selection,
* configuration promotion,
* document disablement,
* deletion action.

Read-only query execution does not necessarily require a formal audit event for every request.

Its logging and retention depend on sensitivity, usage, and organizational policy.

## 18.34 Governance Audit Trail

Changes to a Document Version’s governance status should preserve:

* previous state,
* new state,
* actor,
* timestamp,
* reason,
* replacement version where applicable.

For example:

```text
ACTIVE
→ SUPERSEDED
→ replaced_by: document_version_002
```

A current governance status without historical context may be insufficient for compliance investigation.

## 18.35 Configuration Audit Trail

Significant configuration actions should be traceable.

Examples include:

* configuration created,
* configuration approved,
* configuration activated,
* configuration retired,
* active retrieval configuration changed,
* baseline configuration changed.

Historical runs must retain their original Configuration Snapshot regardless of later configuration changes.

## 18.36 Index Audit Trail

Index lifecycle actions should preserve:

* index created,
* build completed,
* verification completed,
* index activated,
* alias switched,
* index deactivated,
* index deleted.

The audit trail should identify:

* source corpus,
* processing configuration,
* actor or system process,
* timestamps,
* outcome.

## 18.37 Evaluation Audit Trail

Evaluation history should identify:

* who or what initiated the run,
* dataset version,
* target index,
* retrieval configuration,
* metric implementation,
* execution outcome,
* resulting metrics,
* baseline relationship.

Changing the accepted baseline should be auditable because it changes how future regressions are interpreted.

## 18.38 Audit Log Integrity

Audit records should be protected against unauthorized modification.

Possible controls include:

* append-oriented storage,
* restricted write permissions,
* read-only access for reviewers,
* retention policies,
* archival to S3,
* checksums or immutable storage controls where required.

A complete tamper-evident audit platform is not mandatory for the initial MVP.

However, audit records should not be editable through ordinary application workflows.

## 18.39 Observability Versus Auditability

The following distinction must remain clear:

### Observability Example

```text
Embedding batch failed after 12.4 seconds because the model endpoint timed out.
```

### Auditability Example

```text
Technical Operator initiated reprocessing of Document Version X using Configuration Y.
```

Observability explains system behaviour.

Auditability records accountable actions and meaningful state changes.

Some events may serve both purposes, but they should still follow the appropriate retention and integrity requirements.

## 18.40 Retention

Retention should be defined separately for:

* application logs,
* infrastructure logs,
* metrics,
* traces,
* audit events,
* query history,
* detailed evaluation results.

Indicative direction:

### Shorter Retention

* debug logs,
* high-volume request logs,
* temporary traces.

### Medium Retention

* operational metrics,
* processing diagnostics,
* retrieval performance history.

### Longer Retention

* governance events,
* configuration changes,
* index lifecycle events,
* accepted evaluation baselines,
* deletion records.

Final periods depend on organizational, legal, cost, and investigation requirements.

## 18.41 Query and Document Privacy

Observability must account for the sensitivity of:

* source-document content,
* user queries,
* retrieved evidence,
* metadata,
* evaluation queries.

The project should support:

* content redaction,
* query-text suppression,
* identifier-based logging,
* limited-access log groups,
* controlled retention,
* safe exports.

Observability should not create a secondary uncontrolled copy of sensitive knowledge.

## 18.42 Environment Separation

Logs, metrics, dashboards, and audit records should identify the environment.

Development, testing, staging, and production data should not be mixed unintentionally.

Production alerts should not be triggered by test environments.

Production query or document content should not flow into development observability systems without approval.

## 18.43 Local Development Observability

Local development should provide enough visibility to diagnose workflows without requiring the full AWS observability stack.

This may include:

* structured console logs,
* local correlation identifiers,
* test metrics,
* processing status endpoints,
* local dependency health.

Local logs should follow the same sensitive-data rules as production logs.

## 18.44 Production Observability

Production deployment may use:

* CloudWatch Logs,
* CloudWatch Metrics,
* CloudWatch Alarms,
* ECS service events,
* OpenSearch monitoring,
* database monitoring,
* optional distributed tracing.

The exact AWS monitoring configuration will be defined during infrastructure design.

## 18.45 Monitoring Access

Access to observability and audit data should follow least privilege.

Indicative access patterns include:

* developers may access development logs,
* operators may access production operational metrics,
* security personnel may access security events,
* auditors may receive read-only audit access,
* Query Users should not access technical logs.

Observability data may contain sensitive infrastructure and usage information.

## 18.46 Reconciliation

Because state exists across S3, an operational store, and OpenSearch, the system may require reconciliation checks.

Examples include:

* registered Source Artifact missing from S3,
* S3 artifact without operational registration,
* successful Processing Run without expected chunks,
* active Document Version missing from active index,
* Index Record pointing to a missing OpenSearch index,
* indexed chunks referencing unknown Document Versions.

Reconciliation may initially be manual or on demand.

Scheduled reconciliation can be introduced when operational need is demonstrated.

## 18.47 Operational Reports

The system may generate reports such as:

* failed-processing report,
* document-to-index consistency report,
* active-version report,
* inactive-index report,
* evaluation regression report,
* governance-change report.

Reports should reference stable identifiers and timestamps.

A complete reporting platform is not required for the MVP.

## 18.48 Definition of Successful Observability

The system is sufficiently observable when an authorized Technical Operator can determine:

* whether a request reached the application,
* which run was created,
* which stage is currently executing,
* where a failure occurred,
* which dependency was involved,
* which configuration was used,
* whether the resulting index is valid,
* whether retrieval is functioning,
* whether evaluation quality changed.

This should be possible without attaching a debugger to a production container.

## 18.49 Definition of Sufficient Auditability

The system is sufficiently auditable when an authorized reviewer can determine:

* who initiated an important action,
* when it occurred,
* which entity was affected,
* what changed,
* whether the action succeeded,
* which configuration or version was involved,
* whether the previous state can be identified.

The MVP may implement a limited set of audit events first.

The model should allow additional audited actions later.

## 18.50 Initial MVP Observability Requirements

The minimum MVP baseline includes:

```text
Structured Application Logs
Correlation Identifiers
Document and Run Identifiers
Processing-Stage Status
Stage Durations
Safe Error Classification
Chunk and Indexing Counts
Retrieval Latency
Evaluation Run Metrics
Health and Readiness Endpoints
Configuration Traceability
Basic Audit Events for Important State Changes
```

A complete distributed tracing, SIEM, or enterprise audit platform is not required.

## 18.51 Initial MVP Audit Events

The initial audit set should cover at least:

* Document uploaded,
* Document Version created,
* processing retried,
* Document Version activated,
* Document Version superseded,
* Document Version disabled,
* index activated,
* evaluation baseline selected,
* permanent deletion initiated or completed where supported.

Additional technical events may remain ordinary structured logs.

## 18.52 Observability and Auditability Invariants

The following rules should remain true:

1. Logs must not be the only source of durable lifecycle state.
2. Important requests and runs must have correlation identifiers.
3. Processing failures must identify the failed stage.
4. Partial indexing failures must remain visible.
5. Historical runs must remain linked to Configuration Snapshots.
6. Audit events must identify the affected entity.
7. Governance changes must preserve previous and new state.
8. Audit records must not be modifiable through ordinary user workflows.
9. Sensitive document and query content must not be logged by default.
10. A valid no-result query must not be recorded as a retrieval failure.
11. Infrastructure failure must remain distinguishable from retrieval-quality failure.
12. Evaluation failure must remain distinguishable from poor evaluation metrics.
13. Current operational state must not erase relevant historical actions.
14. The UI must not reconstruct authoritative state only from logs.
15. Every active index must have traceable build and verification information.
16. Monitoring access must remain restricted according to role.
17. Observability configuration must not disable mandatory security redaction.
18. Audit retention must be independent from short-lived debug-log retention.

## 18.53 Observability and Auditability Design Principle

The design must make it impossible to confuse:

```text
Logged
with
Persisted as Authoritative State

Technically Visible
with
Auditable

Request Succeeded
with
Business Workflow Completed

Processing Completed
with
Index Verification Succeeded

Query Returned Results
with
Results Were Relevant

No Results
with
System Failure

Current State
with
Complete Historical Explanation
```

CVS Review Portal should provide enough operational visibility to diagnose its behaviour and enough historical traceability to explain important actions and state changes.



# 19. Failure, Retry and Idempotency Principles

Failure, Retry and Idempotency principles define how CVS Review Portal handles unsuccessful operations without losing traceability, corrupting state, or creating uncontrolled duplicate data.

The system must assume that failures may occur between any two processing stages and across any external dependency.

The design must distinguish between:

```text
Failure Detection
→ Failure Classification
→ Retry Decision
→ Controlled Recovery
→ Final State Verification
```

Retries must not be treated as a universal response to every failure.

They must be applied only when the operation is safe to repeat and the underlying failure is potentially recoverable.

## 19.1 Objectives

The failure-management model should ensure that:

* failures are explicit and observable,
* partial success is not reported as complete success,
* retryable and non-retryable failures are distinguished,
* repeated requests do not create uncontrolled duplicates,
* canonical source artifacts remain protected,
* previous successful representations remain available during replacement attempts,
* failed attempts remain traceable,
* recovery can occur without manual data repair wherever practical.

## 19.2 Failure Boundary

Failures may occur across:

```text
API Request
→ Upload Validation
→ S3 Storage
→ Operational State Update
→ Parsing
→ Normalization
→ Metadata Handling
→ Chunking
→ Embedding
→ OpenSearch Indexing
→ Verification
→ Governance Activation
→ Query Execution
→ Evaluation Execution
```

The system must not assume that an earlier successful step guarantees the success of later steps.

S3, the operational state store, OpenSearch, and external model services do not participate in one shared transaction.

## 19.3 Failure Categories

Failures should be classified into controlled categories.

Indicative categories include:

```text
VALIDATION_FAILURE
AUTHENTICATION_FAILURE
AUTHORIZATION_FAILURE
CONFIGURATION_FAILURE
STORAGE_FAILURE
PARSING_FAILURE
NORMALIZATION_FAILURE
METADATA_FAILURE
CHUNKING_FAILURE
EMBEDDING_FAILURE
INDEXING_FAILURE
VERIFICATION_FAILURE
RETRIEVAL_FAILURE
EVALUATION_FAILURE
DEPENDENCY_FAILURE
CONSISTENCY_FAILURE
INTERNAL_FAILURE
```

Each category should define:

* whether retry is permitted,
* whether user correction is required,
* whether the current run must stop,
* whether cleanup or reconciliation is required.

## 19.4 Retryability Classification

Failures should be classified as:

```text
RETRYABLE
NON_RETRYABLE
CONDITIONALLY_RETRYABLE
UNKNOWN
```

### Retryable

A transient problem may succeed without changing the request.

Examples include:

* temporary network timeout,
* temporary OpenSearch unavailability,
* external embedding-service rate limit,
* temporary S3 service error,
* short-lived dependency interruption.

### Non-Retryable

The operation will continue to fail until the input, configuration, or implementation changes.

Examples include:

* unsupported file type,
* invalid metadata,
* corrupted source document,
* vector-dimension mismatch,
* invalid index mapping,
* unauthorized action,
* unsupported retrieval mode.

### Conditionally Retryable

Retry may be appropriate only after a controlled action.

Examples include:

* corrected metadata,
* repaired configuration,
* recreated target index,
* increased service quota,
* operator-approved parser fallback.

### Unknown

The failure has not yet been classified safely.

Unknown failures should not receive unlimited automated retries.

They should stop after a small bounded attempt count and require investigation.

## 19.5 Failure Severity

Failures may also be assigned a severity such as:

```text
WARNING
RECOVERABLE
BLOCKING
CRITICAL
```

### Warning

The operation may continue, but a suspicious condition requires visibility.

### Recoverable

The current attempt failed, but controlled retry may succeed.

### Blocking

The current workflow cannot continue without correction.

### Critical

The failure may affect integrity, security, multiple documents, or active retrieval.

Severity and retryability are related but separate concepts.

## 19.6 Failure Recording

Every failed operation should record, where applicable:

* failure identifier,
* failure category,
* affected entity,
* processing or retrieval stage,
* attempt number,
* timestamp,
* retryability classification,
* safe error summary,
* underlying dependency,
* correlation identifier,
* whether cleanup is required.

Full stack traces may be stored in restricted technical logs.

They should not be exposed through user-facing responses.

## 19.7 User-Facing Failure Behaviour

User-facing errors should explain:

* what operation failed,
* whether the request was accepted,
* whether processing may be retried,
* whether user correction is required,
* which stable identifier can be used for monitoring.

The user should not receive:

* raw stack traces,
* internal credentials,
* database statements,
* unrestricted S3 paths,
* sensitive infrastructure details,
* uncontrolled source-document excerpts.

## 19.8 Processing Run Failure State

A Processing Run must enter a failure state when a required processing stage cannot complete.

Indicative outcome:

```text
RUNNING
→ FAILED
```

The run should preserve:

* the last successfully completed stage,
* the failed stage,
* attempt history,
* produced artifacts,
* failure category,
* retry guidance.

A failed run must not be changed retrospectively into a successful run after a new retry.

A retry should create a new attempt or new Processing Run with a clear relationship to the failed execution.

## 19.9 Stage Failure Behaviour

When a required stage fails:

1. the current stage must be marked failed,
2. dependent later stages must not begin,
3. the Processing Run must not be marked successful,
4. incomplete output must not become active,
5. partial artifacts must be recorded or safely removed,
6. the failure must remain visible through Data Monitoring.

Independent cleanup actions may continue after the main workflow stops.

## 19.10 Partial Failure

Partial failure occurs when only part of a batch or stage succeeds.

Examples include:

* some chunks fail to embed,
* some OpenSearch bulk items fail,
* only part of the document is parsed,
* metadata is missing for several sections,
* verification detects fewer chunks than expected.

Partial success must not be represented as complete success.

The system should record:

```text
Expected Count
Successful Count
Failed Count
Unverified Count
```

Required consistency rules must be satisfied before the workflow may continue.

## 19.11 Partial Embedding Failure

When embeddings are generated in batches, the system must identify:

* which Chunk identifiers succeeded,
* which Chunk identifiers failed,
* which batch attempt failed,
* whether retry is safe.

The stage may retry only the failed subset when:

* chunk inputs are stable,
* the same embedding configuration is used,
* successful vectors are preserved safely,
* duplicate outputs cannot be created.

The embedding stage is complete only when every required Chunk has one valid compatible vector.

## 19.12 Partial Indexing Failure

OpenSearch bulk operations may return an overall successful HTTP response while individual writes fail.

The Indexing Component must inspect item-level results.

It must record:

* expected write count,
* successful write count,
* failed item identifiers,
* failure reasons,
* retry count.

The Indexing Run must not be marked successful until:

* all required chunks have been indexed,
* or an explicitly approved tolerance policy has been satisfied.

The initial MVP should normally require complete indexing.

## 19.13 Verification Failure

Verification may fail even when earlier indexing requests appeared successful.

Examples include:

* missing chunks,
* duplicate chunk identifiers,
* incorrect vector dimensions,
* missing required metadata,
* unexpected document count,
* inability to retrieve a known indexed record.

A verification failure must prevent activation.

The system should preserve the failed representation for investigation or remove it through controlled cleanup.

## 19.14 Query Failure

A Query Request may fail during:

* validation,
* configuration resolution,
* query embedding,
* OpenSearch execution,
* result assembly,
* authorization.

A retrieval failure must remain distinct from:

```text
Valid Query With No Results
```

A failed query may be retried only when the failure is transient and the request remains valid.

## 19.15 Evaluation Failure

An Evaluation Run may fail:

* before execution,
* for an individual query,
* during metric calculation,
* during report storage.

The run must record:

* completed-query count,
* failed-query count,
* affected identifiers,
* whether aggregate metrics are valid,
* whether the run is comparable with the baseline.

Failed queries must not disappear silently from the aggregate calculation.

## 19.16 Dependency Failure

Dependencies may include:

* S3,
* OpenSearch,
* operational state store,
* embedding service,
* authentication provider,
* queue or coordination system.

Dependency failures should record:

* dependency name,
* operation,
* timeout or error category,
* attempt count,
* degradation impact.

The application may support partial operation where safe.

For example:

* monitoring may remain available while ingestion is unavailable,
* query may remain available while new embeddings cannot be generated,
* uploaded artifacts must not be accepted as durable if S3 is unavailable.

## 19.17 Retry Principles

Retries must be:

```text
Bounded
Observable
Failure-Aware
Idempotent
Backed Off
```

The system must avoid:

* infinite retries,
* immediate tight retry loops,
* retrying deterministic validation failures,
* retrying unauthorized requests,
* hiding persistent failures behind repeated attempts.

## 19.18 Retry Limits

Retry limits should be configurable within safe bounds.

A retry policy may define:

* maximum attempts,
* initial delay,
* backoff multiplier,
* maximum delay,
* retryable error categories,
* total timeout.

Example conceptual policy:

```text
Attempt 1
→ short delay
Attempt 2
→ longer delay
Attempt 3
→ final automatic attempt
→ failure requiring investigation
```

The exact values will depend on the dependency and operation.

## 19.19 Exponential Backoff

Transient dependency failures should generally use exponential backoff.

Jitter may be added to reduce synchronized retry bursts.

The retry mechanism must respect:

* API timeouts,
* user-request duration,
* background-job limits,
* external provider rate limits.

Long-running retries should occur in background processing rather than blocking an interactive API request.

## 19.20 Retry Scope

Retries may occur at different levels:

```text
API Request Retry
Processing Stage Retry
Batch Retry
Full Processing Run Retry
Index Build Retry
Evaluation Query Retry
Full Evaluation Run Retry
```

The narrowest safe retry scope should be preferred.

For example:

* retry a failed embedding batch rather than re-parse the whole document,
* retry failed OpenSearch items rather than rewriting every successful item,
* retry one failed evaluation query rather than restarting the entire dataset.

## 19.21 Automatic Versus Manual Retry

### Automatic Retry

Suitable for predictable transient failures.

Examples include:

* network timeout,
* temporary service unavailability,
* rate-limit response.

### Manual Retry

Suitable when operator review or correction is required.

Examples include:

* parser failure on an unusual document,
* incorrect metadata,
* invalid mapping,
* repeated verification mismatch,
* unknown internal failure.

The Data Monitoring area should indicate whether a run is eligible for automatic or manual retry.

## 19.22 Retry History

Each retry should preserve:

* previous attempt reference,
* new attempt identifier,
* initiator,
* retry reason,
* configuration used,
* timestamps,
* final outcome.

Retry history must not overwrite previous failure evidence.

## 19.23 Idempotency Definition

An operation is idempotent when repeating the same logical request does not create additional unintended effects beyond the first successful execution.

Examples include:

* repeated upload submission does not create uncontrolled duplicate versions,
* repeated S3 storage confirmation does not create unrelated artifacts,
* repeated indexing of the same Chunk identifier does not create duplicate records,
* repeated governance-state request does not create conflicting state,
* repeated evaluation request can be recognized or executed as a distinct explicit run.

Idempotency does not always mean returning the identical response.

It means preserving the intended system state.

## 19.24 Idempotency Key

Operations with duplicate-request risk should support a stable idempotency key or equivalent logical request identifier.

Possible sources include:

* client-provided request identifier,
* server-generated upload session identifier,
* Processing Run identifier,
* Indexing Run identifier,
* deterministic Chunk identifier,
* explicit operation identifier.

An idempotency record may store:

* key,
* operation type,
* request fingerprint,
* status,
* result reference,
* creation time,
* expiration where applicable.

## 19.25 Request Fingerprint

An idempotency key should be associated with the logical request content.

A request fingerprint may include:

* operation type,
* actor or tenant scope where applicable,
* Document Version identifier,
* configuration identifier,
* content checksum,
* target index.

If the same idempotency key is reused with materially different input, the system should reject the request rather than treat it as equivalent.

## 19.26 Upload Idempotency

Repeated upload requests may occur because of:

* browser retry,
* network timeout,
* user resubmission,
* client uncertainty about the response.

The system should distinguish between:

```text
Same Request Repeated
Same File Uploaded Intentionally Again
New Version of the Same Document
Different Document With Identical Content
```

The system may use:

* idempotency key,
* content checksum,
* Document identity,
* version metadata.

Checksum equality alone should not automatically define the business meaning of the upload.

## 19.27 Source Storage Idempotency

S3 object keys should be controlled and stable for a Source Artifact.

Repeated storage of the same successful upload should not generate multiple unrelated canonical artifacts.

The system may:

* detect an existing object with the expected checksum,
* confirm it as already stored,
* reject checksum mismatch,
* use S3 versioning where intentional replacement is permitted.

The system must not silently overwrite a canonical source artifact with different content.

## 19.28 Processing Idempotency

A Processing Run represents an explicit technical execution.

Starting the same processing request twice should not unintentionally create concurrent duplicate runs.

The system should determine whether to:

* return the existing active run,
* reject the duplicate request,
* create a new explicitly requested experiment run.

The decision may depend on:

* Document Version,
* configuration snapshot,
* requested operation,
* current run status.

## 19.29 Chunk Identity

Chunk identifiers should support deterministic or controlled repeated indexing.

An indicative Chunk identity may derive from:

```text
Document Version
+
Processing Run or Processing Representation
+
Chunk Sequence or Source Span
+
Content Checksum
```

The exact identifier scheme will be defined later.

Chunk identifiers must not rely only on OpenSearch-generated IDs.

## 19.30 Indexing Idempotency

Indexing should use stable identifiers so that retrying the same write replaces or confirms the intended index document rather than creating another copy.

Indexing operations should define clearly whether they use:

* create-only semantics,
* upsert semantics,
* replacement semantics.

The selected behaviour must be consistent with the Indexing Run and index-build strategy.

For controlled full index builds, deterministic writes followed by verification are preferred.

## 19.31 Governance Action Idempotency

Repeatedly requesting the same valid governance state should not produce conflicting outcomes.

For example:

```text
ACTIVE → ACTIVE
```

may return the current state without creating another substantive transition.

However, separate user actions may still create audit events where organizational requirements justify them.

Conflicting transitions must be rejected.

## 19.32 Evaluation Run Idempotency

Evaluation Runs are usually explicit historical executions.

Repeating the same evaluation configuration may intentionally create a new run to measure:

* time variation,
* deployment changes,
* performance variation.

Therefore, evaluation execution is not automatically deduplicated by configuration equality.

An accidental duplicate request may still be controlled through a request idempotency key.

Each accepted run must receive its own Evaluation Run identifier.

## 19.33 Idempotency Record Retention

Idempotency records should be retained long enough to cover realistic duplicate-request windows.

Retention may differ by operation.

Examples include:

* interactive API requests: limited time window,
* upload operations: longer window,
* processing commands: until the related run reaches a terminal state,
* governance actions: durable state and audit history.

The final policy will depend on the persistence model and operational behaviour.

## 19.34 Concurrency Control

Idempotency must be supported by concurrency controls.

Potential conflicts include:

* two uploads creating the same version,
* two workers processing the same run,
* concurrent retries indexing the same chunks,
* simultaneous active-version changes,
* concurrent index activation.

Possible controls include:

* database uniqueness constraints,
* optimistic concurrency,
* row-level locking,
* conditional writes,
* distributed locks where justified,
* single-consumer ownership for a job.

The simplest reliable mechanism should be preferred.

## 19.35 Optimistic Concurrency

State-changing operations may require an expected current version or state.

For example:

```text
Change Governance State
only if
Current State = ACTIVE
```

If another operation changed the state first, the request should fail with a conflict rather than overwrite the newer state.

## 19.36 Duplicate Worker Execution

A background job may be delivered or started more than once.

The processing design should assume at-least-once execution where a queue is introduced.

Before executing work, the worker should verify:

* Processing Run status,
* ownership or lease,
* attempt state,
* whether the output already exists,
* whether the operation is safe to repeat.

Message receipt alone must not define whether work should be performed.

## 19.37 Processing Lease

Long-running work may use a lease or heartbeat model.

A Processing Run may record:

* worker identifier,
* lease expiration,
* heartbeat timestamp,
* attempt number.

If a worker disappears, another worker may resume or retry only after the lease expires.

A full lease model may be deferred until background concurrency requires it.

## 19.38 Poison Documents

A poison document is a source that repeatedly causes deterministic or resource-intensive failure.

Examples include:

* malformed DOCX structure,
* parser crash,
* excessive archive expansion,
* extreme processing time,
* unsupported internal feature.

The system should:

* stop automatic retries after a bounded limit,
* mark the run for manual review,
* preserve the source artifact safely,
* prevent repeated uncontrolled resource consumption.

## 19.39 Dead-Letter Handling

If a queue is introduced, repeatedly failed messages may be moved to a dead-letter queue or equivalent failure store.

Dead-letter records should include:

* message or operation identifier,
* Processing Run identifier,
* attempt count,
* last failure category,
* timestamp,
* recovery guidance.

A dead-letter queue is an operational mechanism.

It does not replace the authoritative failed Processing Run state.

## 19.40 Timeout Handling

All external calls and long-running operations should have bounded timeouts.

Timeouts may apply to:

* upload requests,
* S3 operations,
* parser execution,
* embedding inference,
* OpenSearch indexing,
* retrieval,
* evaluation queries.

A timeout must be classified according to whether the underlying operation may still have completed.

For example, a client timeout after an S3 write does not prove that the write failed.

The system may need verification before retry.

## 19.41 Unknown Outcome

An unknown outcome occurs when the caller cannot determine whether an operation completed.

Examples include:

* network connection lost after sending the request,
* timeout after OpenSearch may have accepted writes,
* response lost after S3 storage succeeded.

The recovery process should first inspect the intended state using:

* idempotency key,
* expected identifier,
* checksum,
* target index,
* operational record.

The system should not immediately repeat side effects without checking.

## 19.42 Cross-Store Failure

A workflow may succeed in one store and fail in another.

Examples include:

```text
S3 Write Succeeded
Operational Registration Failed
```

```text
Operational Run Created
OpenSearch Indexing Failed
```

```text
OpenSearch Writes Succeeded
Verification-State Update Failed
```

The application must use explicit intermediate states and reconciliation.

It must not assume distributed atomicity.

## 19.43 Controlled Cross-Store Sequence

An indicative safe sequence is:

```text
1. Create operation intent
2. Assign stable identifiers
3. Perform external write
4. Verify external outcome
5. Persist confirmed state
6. Continue to next stage
7. Mark complete only after final verification
```

Where state-store creation cannot precede the external write, the operation must preserve enough identity to reconcile the result.

## 19.44 Compensation

Compensation is a controlled action that reverses or isolates an earlier side effect.

Examples include:

* deleting chunks written by a failed Indexing Run,
* marking an incomplete index inactive,
* removing an unregistered temporary S3 artifact,
* restoring the previous active-index alias.

Compensation is not always equivalent to rollback.

The system may preserve failed artifacts for investigation while preventing their use.

## 19.45 Safe Replacement

Reprocessing and reindexing should use a safe replacement pattern:

```text
Current Verified Representation
→ Build Candidate Representation
→ Verify Candidate
→ Compare or Approve
→ Activate Candidate
→ Retain or Retire Previous Representation
```

The current successful representation should normally remain active while the candidate is being built.

A failed candidate build must not damage the existing active representation.

## 19.46 Rollback

Rollback should be possible for significant serving changes such as:

* active index switch,
* retrieval configuration promotion,
* governance activation.

Rollback should reference a previously verified state.

Rollback must not erase the history of the failed or rejected change.

## 19.47 Reconciliation

Reconciliation checks identify inconsistencies after partial failure.

Examples include:

* Source Artifact registered but missing from S3,
* S3 object present without completed registration,
* successful Processing Run with missing derived content,
* Index Record without physical OpenSearch index,
* indexed chunks from a failed run,
* active version with no verified representation.

Reconciliation may be:

* initiated manually,
* executed during monitoring,
* scheduled later.

## 19.48 Orphan Cleanup

Orphaned derived data may include:

* temporary files,
* failed chunk exports,
* embeddings without completed indexing,
* chunks from failed runs,
* inactive test indexes.

Cleanup must:

* identify ownership,
* verify that the data is not active,
* preserve required audit or debugging evidence,
* avoid deleting canonical source artifacts.

Automatic cleanup should be conservative.

## 19.49 State Transition Validation

All workflow state changes must be validated.

Examples of invalid transitions include:

```text
FAILED → SUCCEEDED
without a new attempt
```

```text
INDEXING → ACTIVE
without verification
```

```text
DISABLED → SUPERSEDED
without approved governance logic
```

```text
DELETED → ACTIVE
without restoration process
```

The allowed transition model should be implemented and tested in code.

## 19.50 Terminal States

Indicative terminal Processing Run states include:

```text
SUCCEEDED
FAILED
CANCELLED
```

A terminal run should not resume silently.

Further processing should create:

* a new attempt,
* a child run,
* or an explicit retry execution.

Historical terminal state must remain unchanged.

## 19.51 Monitoring Requirements

The Data Monitoring area should show:

* current status,
* failed stage,
* failure category,
* attempt count,
* retry eligibility,
* latest retry,
* previous successful representation,
* cleanup or reconciliation requirement.

The user should be able to distinguish:

```text
FAILED — RETRYABLE
FAILED — USER ACTION REQUIRED
FAILED — CONFIGURATION CHANGE REQUIRED
FAILED — MANUAL INVESTIGATION REQUIRED
```

## 19.52 Audit Requirements

The following actions should be auditable where applicable:

* manual retry initiated,
* reprocessing initiated,
* failed run cancelled,
* candidate index activated,
* rollback performed,
* orphan cleanup performed,
* permanent data deletion performed,
* retry policy overridden.

The audit event should preserve:

* actor,
* reason,
* previous state,
* new state,
* affected identifiers,
* outcome.

## 19.53 Testing Requirements

Automated tests should cover:

* retryable failure classification,
* non-retryable failure classification,
* maximum-attempt enforcement,
* backoff-policy configuration,
* duplicate request handling,
* idempotency-key reuse,
* conflicting request fingerprint,
* partial embedding failure,
* partial indexing failure,
* verification failure,
* repeated worker execution,
* concurrent state transition,
* failed cross-store operation,
* safe reprocessing,
* active-index rollback.

Failure paths must receive the same design attention as successful paths.

## 19.54 Initial MVP Failure Model

The initial MVP should support:

```text
Explicit Processing Run Status
Explicit Failed Stage
Controlled Error Categories
Bounded Retry Count
Manual Retry
Stable Request and Run Identifiers
Upload Duplicate Detection
Deterministic Chunk Identifiers
Idempotent OpenSearch Writes
Indexing Count Verification
Safe Reprocessing
Structured Failure Logs
```

A full distributed workflow engine, dead-letter queue, lease system, or automated reconciliation scheduler is not mandatory initially.

These should be introduced only when asynchronous processing and concurrency justify them.

## 19.55 Initial MVP Retry Direction

A practical initial retry model may be:

### Validation and Configuration Failures

```text
No automatic retry
→ correct input or configuration
```

### S3 and OpenSearch Transient Failures

```text
Bounded automatic retry
→ exponential backoff
→ failed state after limit
```

### Parsing and Chunking Failures

```text
No repeated automatic retry for deterministic failure
→ manual investigation or corrected implementation
```

### Embedding-Service Failures

```text
Retry failed batch
→ bounded attempts
→ preserve successful batch results safely
```

### Verification Failures

```text
Stop activation
→ inspect or rebuild candidate representation
```

## 19.56 Failure Invariants

The following rules should remain true:

1. A failed required stage must prevent workflow completion.
2. Partial success must not be represented as complete success.
3. A retry must not erase the previous attempt history.
4. Automatic retries must be bounded.
5. Non-retryable failures must not enter repeated automatic retry loops.
6. Retries must use stable operation and entity identifiers.
7. Duplicate upload requests must not create uncontrolled Document Versions.
8. Repeated indexing must not create duplicate Chunks.
9. A timeout must not automatically be interpreted as confirmed failure.
10. Unknown outcomes must be verified before repeating side effects.
11. A failed candidate index must not replace the active verified index.
12. Failed OpenSearch item writes must be inspected individually.
13. A Processing Run must not become successful after entering a terminal failed state.
14. Cross-store inconsistencies must remain visible and reconcilable.
15. Logs must not be the only evidence of a failed operation.
16. Idempotency keys reused with different request content must be rejected.
17. Governance operations must validate the expected current state.
18. Canonical source artifacts must not be deleted as automatic compensation for derived-processing failure.
19. Retrieval failure must remain distinguishable from a valid no-result outcome.
20. Evaluation failures must not silently improve or reduce reported metrics.

## 19.57 Failure, Retry and Idempotency Design Principle

The design must make it impossible to confuse:

```text
Retrying
with
Recovering Safely

Request Repeated
with
New Business Operation

Partial Success
with
Completed Workflow

Timeout
with
Confirmed Failure

Write Accepted
with
Write Verified

Duplicate Detection
with
Document Versioning

Failed Candidate Build
with
Active System Failure

Idempotent
with
Stateless
```

CVS Review Portal must treat failures as normal operational conditions and preserve enough state, identity, and history to recover without corrupting the knowledge base or losing trust in its processing results.




# 20. AWS Deployment Direction

The AWS Deployment Direction defines the initial cloud architecture for running CVS Review Portal in a secure, reproducible, and operationally manageable manner.

The objective is to support the current Compliance-focused MVP without introducing unnecessary infrastructure complexity.

The deployment direction should remain compatible with:

```text
Data Ingest
→ Data Monitoring
→ Data Query and Evaluation
```

The initial architecture should favour managed AWS services, containerized application components, private service communication, and infrastructure provisioning through CloudFormation.

## 20.1 Deployment Objectives

The AWS deployment should provide:

* reproducible infrastructure,
* containerized application execution,
* durable source-artifact storage,
* managed search and vector retrieval,
* secure service-to-service access,
* application and infrastructure observability,
* controlled configuration and secret management,
* safe deployment and rollback,
* a clear path from local development to production.

The first deployment does not need to support speculative enterprise scale, multi-region availability, or full multi-tenancy.

## 20.2 Initial AWS Service Direction

The initial technical direction includes:

```text
Amazon ECR
→ Container image storage

Amazon ECS Fargate
→ Application and processing execution

Amazon S3
→ Canonical source and retained artifacts

Amazon OpenSearch Service
→ Lexical, vector, and hybrid retrieval

AWS CloudFormation
→ Infrastructure provisioning

Amazon CloudWatch
→ Logs, metrics, alarms, and operational visibility
```

Additional services may be introduced only when justified by concrete requirements.

Likely optional services include:

* Application Load Balancer,
* Amazon RDS for PostgreSQL,
* Amazon SQS,
* AWS Secrets Manager,
* AWS Systems Manager Parameter Store,
* AWS KMS,
* Amazon Cognito,
* AWS WAF.

## 20.3 High-Level Deployment Context

An indicative deployment is:

```text
User
  │
  ▼
Application Entry Point
  │
  ▼
Application Load Balancer
  │
  ▼
ECS Fargate Service
  ├── FastAPI Application
  ├── Data Ingest APIs
  ├── Data Monitoring APIs
  ├── Data Query APIs
  └── Evaluation APIs
        │
        ├── Amazon S3
        ├── Amazon OpenSearch Service
        ├── Optional Operational Database
        └── Optional Background Queue
```

A separate ECS Fargate worker may be introduced for document processing.

The API and worker may use:

* the same repository,
* the same Docker image,
* different container commands,
* different ECS task definitions.

## 20.4 Initial Deployment Model

The preferred initial deployment model is:

```text
Modular Application
+
Optional Background Worker
+
Managed AWS Dependencies
```

The logical functional areas do not require separate microservices.

The first implementation may run:

### Application Service

Responsible for:

* API requests,
* upload coordination,
* Data Monitoring endpoints,
* Data Query,
* evaluation requests,
* user-facing application responses.

### Processing Worker

Responsible for:

* parsing,
* normalization,
* metadata processing,
* chunking,
* embedding,
* OpenSearch indexing,
* verification.

The worker should be introduced when processing duration or resource use makes synchronous API execution inappropriate.

## 20.5 Amazon ECR

Amazon ECR will store container images for the application.

The deployment pipeline should:

```text
Build Image
→ Run Tests and Quality Checks
→ Tag Image
→ Push to ECR
→ Update ECS Task Definition
→ Deploy ECS Service
```

Image tags may include:

* Git commit SHA,
* release version,
* environment label where required.

Production deployments should avoid relying only on mutable tags such as:

```text
latest
```

Each deployed ECS task should reference a traceable image version.

## 20.6 Container Image Direction

The existing Docker and Poetry template provides the baseline container structure.

The runtime image should:

* use a multi-stage build,
* install only required runtime dependencies,
* run as a non-root user,
* avoid embedded secrets,
* expose health endpoints,
* use a deterministic startup command,
* include application-version information.

The same image may support multiple execution modes.

For example:

```text
API Command
→ start FastAPI application

Worker Command
→ start document-processing worker

Evaluation Command
→ execute controlled evaluation process
```

Separate images should be created only when dependencies or runtime requirements differ significantly.

## 20.7 Amazon ECS Fargate

ECS Fargate is the preferred initial compute platform because it provides:

* managed container execution,
* no EC2 server management,
* task-level IAM roles,
* independent service scaling,
* integration with ECR,
* integration with CloudWatch,
* support for private networking.

The initial ECS deployment may include:

```text
ECS Service 1
→ FastAPI Application

ECS Service 2
→ Processing Worker, when required
```

An Evaluation Worker may initially share the processing-worker deployment or run as an on-demand ECS task.

## 20.8 FastAPI Application Service

The FastAPI ECS service should provide:

* health endpoint,
* readiness endpoint,
* upload API,
* Data Monitoring API,
* Data Query API,
* evaluation-control API,
* stable response contracts.

The service should remain stateless with respect to container-local storage.

Durable state must be stored in:

* S3,
* OpenSearch,
* or the approved operational state store.

The application should remain replaceable during deployment without losing workflow state.

## 20.9 Processing Worker

The Processing Worker should handle resource-intensive or long-running ingestion stages.

Indicative responsibilities include:

```text
Retrieve Source Artifact
→ Parse
→ Normalize
→ Handle Metadata
→ Chunk
→ Generate Embeddings
→ Index
→ Verify
→ Update Processing State
```

The worker should use stable Processing Run identifiers and explicit state transitions.

Worker execution must assume that a task may be retried or delivered more than once.

Processing must therefore remain idempotent or controlled through durable run state.

## 20.10 Synchronous Versus Asynchronous Ingestion

A small local or early development version may execute processing synchronously.

However, production-oriented ingestion should likely use asynchronous execution because:

* DOCX processing may take time,
* embedding generation may be slow,
* indexing may require multiple batches,
* HTTP requests should not remain open for the full processing duration,
* retries and monitoring are easier with durable background work.

An indicative interaction is:

```text
Upload Request
→ Validate
→ Store Source Artifact
→ Create Processing Run
→ Submit Background Work
→ Return Accepted Response
```

The user then monitors progress through the Data Monitoring page.

## 20.11 Background Queue Direction

Amazon SQS is the likely queue option if asynchronous ingestion is introduced.

A possible flow is:

```text
FastAPI Application
→ Create Durable Processing Run
→ Send Processing Message to SQS
→ Processing Worker Receives Message
→ Execute Pipeline
→ Update Durable State
```

SQS provides:

* durable message delivery,
* decoupling between API and worker,
* retry support,
* visibility timeout,
* dead-letter queue support,
* horizontal worker scaling.

SQS is not mandatory for the earliest local vertical slice.

It should be introduced when asynchronous processing becomes an agreed deliverable.

## 20.12 Queue Message Boundary

A queue message should contain identifiers rather than full document content.

Indicative message fields include:

* processing-run identifier,
* document-version identifier,
* source-artifact identifier,
* configuration-snapshot identifier,
* correlation identifier.

The worker should load authoritative state and artifacts from durable stores.

The queue message must not become the source of truth for document or processing state.

## 20.13 Amazon S3

S3 will store canonical and selected derived artifacts.

Indicative structure:

```text
s3://cvs-review-portal-<environment>/
├── source/
│   └── documents/
├── parsed/
├── normalized/
├── manifests/
├── evaluation-datasets/
├── evaluation-reports/
└── exports/
```

The final prefix structure should be based on stable identifiers rather than only filenames.

Example:

```text
source/documents/{document_id}/{document_version_id}/{source_artifact_id}/original.docx
```

S3 object keys must not expose unrestricted user-controlled paths.

## 20.14 S3 Environment Separation

Each environment should use separate storage boundaries.

Possible approaches include:

```text
Separate Bucket per Environment
```

or:

```text
Strictly Controlled Prefix per Environment
```

Separate buckets are usually clearer for:

* IAM permissions,
* lifecycle rules,
* accidental cross-environment access,
* deletion control,
* production isolation.

Local and test environments must not silently write to production buckets.

## 20.15 S3 Versioning and Lifecycle

S3 versioning may be enabled for canonical source buckets when historical object protection is required.

Lifecycle rules may manage:

* temporary upload artifacts,
* old derived artifacts,
* evaluation reports,
* inactive exports,
* incomplete multipart uploads.

Canonical source deletion rules should remain conservative.

Derived artifacts may use shorter retention where they can be regenerated safely.

## 20.16 Amazon OpenSearch Service

Amazon OpenSearch Service will provide:

* BM25 lexical retrieval,
* vector search,
* metadata filtering,
* potentially hybrid retrieval,
* ranked result serving.

The OpenSearch domain should be treated as a shared managed service used by the application and processing worker.

It must not be embedded inside each application container.

## 20.17 OpenSearch Network Direction

The preferred production direction is:

```text
OpenSearch Domain
→ Deployed within or accessible through private VPC networking
→ Accessible only by approved ECS task roles and administrators
```

Normal users should never access OpenSearch directly.

All query traffic should pass through the CVS Review Portal application layer.

This allows the application to enforce:

* authentication,
* authorization,
* governance filtering,
* result contracts,
* logging,
* query limits.

## 20.18 OpenSearch Index Direction

The application may use separate physical indexes for:

* active baseline,
* candidate experiments,
* reindexing,
* rollback.

An indicative naming scheme may be:

```text
cvs-review-portal-documents-v001
cvs-review-portal-documents-v002
cvs-review-portal-experiment-<id>
```

An alias may later identify the currently active index:

```text
cvs-review-portal-active
```

The exact naming and alias strategy will be defined during index-lifecycle design.

## 20.19 Safe Index Promotion

A safe index-promotion flow is:

```text
Create Candidate Index
→ Populate Candidate Index
→ Verify Counts and Mapping
→ Run Evaluation
→ Approve Candidate
→ Switch Active Alias
→ Retain Previous Index for Rollback
```

The deployment must not require destructive replacement of the currently active index.

Index promotion is an application and data-lifecycle action, not necessarily an infrastructure deployment.

## 20.20 Operational State Store Direction

The system will likely require durable operational state for:

* Documents,
* Document Versions,
* Processing Runs,
* Processing Stage status,
* Indexing Runs,
* Index Registry,
* Configuration Snapshots,
* Evaluation Runs,
* governance state,
* audit events.

Amazon RDS for PostgreSQL is the likely AWS option.

It provides:

* relational consistency,
* transactions,
* constraints,
* queryable relationships,
* backups,
* point-in-time recovery,
* managed operation.

PostgreSQL should be introduced when the detailed workflow confirms that S3 and OpenSearch alone cannot represent the required state safely.

Given the defined domain entities and lifecycle requirements, PostgreSQL is likely to become part of the MVP architecture.

## 20.21 PostgreSQL Deployment Direction

If introduced, PostgreSQL should be:

* deployed in private subnets,
* inaccessible directly from the public internet,
* encrypted at rest,
* accessed using encrypted connections,
* protected through security groups,
* backed up automatically,
* configured with controlled credentials.

Application runtime credentials should be stored in Secrets Manager or another approved secret mechanism.

Database schema migrations should run through a controlled deployment step.

## 20.22 Redis Direction

Redis is not currently a required architectural dependency.

It may later be justified for:

* short-lived caching,
* distributed coordination,
* rate limiting,
* temporary session state,
* processing leases,
* idempotency windows.

Redis should not be used as the only store for durable:

* Document state,
* Processing Runs,
* governance state,
* configuration history,
* audit history.

The Redis service included in the initial starter template should not be treated as required until a concrete use case is approved.

## 20.23 Embedding Execution Direction

The selected embedding model may run through one of several deployment models.

### In-Container Model

The worker loads the embedding model directly.

Benefits:

* simple data boundary,
* no external inference dependency,
* easier local reproduction.

Costs:

* larger image,
* longer startup,
* higher memory requirements,
* model duplicated across worker tasks.

### External Managed or Hosted Endpoint

The worker calls an external model endpoint.

Benefits:

* centralized model serving,
* independent model scaling,
* smaller application containers.

Costs:

* network dependency,
* additional security review,
* provider cost,
* content-transfer considerations.

### Dedicated ECS Inference Service

A separate ECS service hosts the model.

This may be useful when:

* multiple workers share the same model,
* model loading is expensive,
* independent inference scaling is needed.

The initial selection should favour the simplest model compatible with cost, performance, and data-security requirements.

## 20.24 CPU and Memory Direction

Fargate task sizing should be based on measured workloads.

Different components may require different profiles:

### FastAPI Application

Likely:

* lower memory,
* moderate CPU,
* latency-sensitive.

### Processing Worker

Likely:

* higher memory,
* more CPU,
* longer-running tasks,
* possible embedding-model memory requirements.

The API and worker should not be forced into the same task size merely because they share a codebase.

## 20.25 Scaling Direction

The application and processing worker should scale independently where practical.

### API Scaling

Potential signals:

* request count,
* CPU utilization,
* memory utilization,
* response latency.

### Worker Scaling

Potential signals:

* SQS queue depth,
* age of oldest message,
* running Processing Runs,
* CPU or memory utilization.

### OpenSearch Scaling

Should be based on:

* corpus size,
* vector count,
* query volume,
* index-storage requirements,
* latency,
* shard behaviour.

The MVP does not need advanced autoscaling before representative usage exists.

## 20.26 Application Load Balancer

An Application Load Balancer is the likely production entry point for the FastAPI service.

It may provide:

* HTTPS termination,
* target health checks,
* path-based routing where later required,
* controlled public entry,
* integration with WAF,
* ECS service discovery.

The FastAPI ECS tasks should normally remain in private subnets behind the ALB.

For early controlled development, a simpler endpoint may be used.

## 20.27 User Interface Hosting

The final UI technology remains open.

Possible AWS hosting approaches include:

### UI Served by FastAPI

Suitable for:

* simple server-rendered pages,
* limited testing UI,
* one deployable application.

### Static UI in S3 and CloudFront

Suitable for:

* separate frontend application,
* static asset delivery,
* independent frontend deployment.

### UI Container in ECS

Suitable when:

* the frontend requires server-side rendering,
* frontend and API scale independently.

The MVP should select the simplest approach that supports the three required pages.

## 20.28 Authentication Deployment Direction

The earliest controlled environment may use simplified authentication.

A later production deployment may use:

* Amazon Cognito,
* external OpenID Connect provider,
* authenticated reverse proxy,
* enterprise identity integration.

Authentication should be enforced before the application API.

Authorization rules must still be applied within the application.

## 20.29 AWS Secrets Manager

AWS Secrets Manager is the preferred option for credentials such as:

* database password,
* external model-service API key,
* authentication client secret.

Secrets should be injected into ECS tasks at runtime.

They must not be copied into:

* Docker images,
* repository files,
* CloudFormation outputs,
* application logs.

## 20.30 AWS Systems Manager Parameter Store

Parameter Store may be used for non-secret or lower-sensitivity environment values such as:

* feature flags,
* approved endpoint references,
* environment-specific configuration,
* resource identifiers.

The final division between environment variables, Parameter Store, and Secrets Manager should remain simple and documented.

## 20.31 AWS KMS

AWS KMS may provide encryption keys for:

* S3,
* OpenSearch,
* RDS,
* Secrets Manager,
* selected log groups.

AWS-managed keys may be sufficient for the initial MVP.

Customer-managed keys may be introduced when required for:

* explicit key policies,
* separation of duties,
* customer requirements,
* audit controls,
* controlled key rotation.

## 20.32 CloudWatch Logs

ECS application and worker logs should be sent to CloudWatch Logs.

Log groups should be separated by:

* environment,
* service or execution type,
* possibly application component where operationally useful.

Retention must be configured explicitly.

Production log groups should not use accidental indefinite retention.

## 20.33 CloudWatch Metrics and Alarms

CloudWatch may monitor:

* ECS task health,
* API error rates,
* processing failures,
* queue depth,
* OpenSearch availability,
* database health,
* application custom metrics.

Initial alarms may cover:

* application service unavailable,
* sustained API failures,
* worker failures,
* processing backlog,
* missing active index,
* repeated indexing failures,
* dependency unavailability.

Thresholds should be refined after baseline usage is observed.

## 20.34 CloudWatch and Application Monitoring Boundary

CloudWatch owns infrastructure and technical telemetry.

CVS Review Portal owns application-lifecycle visibility.

For example:

```text
CloudWatch
→ ECS task restarted

CVS Review Portal Monitoring
→ Processing Run failed during embedding
```

Both may be needed to determine root cause.

Neither should attempt to replace the other.

## 20.35 Networking Direction

The production VPC may include:

```text
Public Subnets
→ Application Load Balancer

Private Application Subnets
→ ECS Fargate Tasks

Private Data Subnets
→ RDS where used

Private Service Access
→ OpenSearch
→ S3 through VPC endpoint where justified
→ Secrets Manager and other AWS services
```

The final topology should remain proportionate to the project scale.

The main requirement is that data services should not be publicly exposed unnecessarily.

## 20.36 VPC Endpoints

VPC endpoints may be introduced for services such as:

* S3,
* ECR,
* CloudWatch Logs,
* Secrets Manager,
* Systems Manager.

Benefits may include:

* reduced public-network dependency,
* improved private traffic control,
* reduced NAT usage.

The MVP does not need every possible endpoint from the beginning.

The selected endpoints should reflect security and cost requirements.

## 20.37 NAT Gateway Direction

Private ECS tasks may require outbound access for:

* package-independent runtime calls,
* external embedding services,
* external authentication,
* approved third-party APIs.

A NAT Gateway may be required if tasks need general internet egress.

If all required services are reachable through VPC endpoints and private AWS services, NAT usage may be reduced.

The decision depends on the embedding and external-integration model.

## 20.38 IAM Role Separation

The initial IAM design should distinguish:

### ECS Execution Role

Used for:

* pulling images from ECR,
* sending logs,
* retrieving runtime secrets where configured by ECS.

### Application Task Role

Used for:

* application access to S3,
* OpenSearch,
* operational database authentication where applicable,
* SQS,
* Parameter Store,
* Secrets Manager.

### Deployment Role

Used by CI/CD for:

* ECR push,
* CloudFormation deployment,
* ECS update,
* approved infrastructure changes.

Permissions must remain scoped to the correct environment and resources.

## 20.39 CloudFormation Direction

CloudFormation will define AWS infrastructure.

Possible stack boundaries include:

```text
Foundation Stack
→ VPC
→ subnets
→ security groups
→ shared IAM foundations

Data Stack
→ S3
→ OpenSearch
→ optional RDS

Application Stack
→ ECS cluster
→ ECS services
→ task definitions
→ ALB
→ log groups
→ alarms
```

For the initial project, fewer stacks may be preferable.

The stack structure should support maintainability without creating unnecessary cross-stack dependencies.

## 20.40 CloudFormation Parameters

Environment-dependent CloudFormation parameters may include:

* environment name,
* AWS region,
* container image tag,
* ECS task CPU and memory,
* desired task count,
* S3 bucket naming,
* OpenSearch sizing,
* database sizing,
* log retention,
* domain names,
* certificate references.

Secrets should not be exposed as ordinary CloudFormation parameters when safer secret references are available.

## 20.41 Infrastructure Outputs

CloudFormation outputs may expose non-sensitive resource references such as:

* ALB DNS name,
* ECS cluster name,
* S3 bucket name,
* OpenSearch domain identifier,
* secret ARN,
* database endpoint where access is controlled.

Sensitive values must not be printed as stack outputs.

## 20.42 Environment Separation

Each environment should use separate AWS resources or clearly isolated resource boundaries.

Indicative environments include:

```text
Local
Development
Test
Staging
Production
```

The project may initially require only:

```text
Local
Development
Production-like Test
```

Production resources should not be shared casually with development workloads.

## 20.43 Local Development Direction

Local development should remain possible through Docker Compose or equivalent local tooling.

Local dependencies may include:

* application container,
* local OpenSearch,
* optional local PostgreSQL,
* optional queue emulator or synchronous processing,
* local filesystem or S3 emulator where selected.

The local architecture should preserve the same logical contracts as AWS, even when implementations differ.

Local defaults must not connect to production AWS resources.

## 20.44 Development AWS Environment

A development AWS environment should allow testing of:

* real S3 behaviour,
* ECS deployment,
* IAM roles,
* OpenSearch mappings,
* CloudFormation,
* background processing,
* observability.

It may use smaller resource sizes and limited data.

Development data should use public, synthetic, or otherwise approved documents.

## 20.45 CI/CD Direction

The deployment workflow should use GitHub Actions with AWS OIDC where possible.

An indicative pipeline is:

```text
Code Commit
→ Install Dependencies
→ Run Unit Tests
→ Run Integration Tests Where Available
→ Run Ruff
→ Run Type Checking
→ Build Docker Image
→ Scan Image and Dependencies
→ Push to ECR
→ Deploy CloudFormation Changes
→ Update ECS Service
→ Run Health Verification
```

Production deployment controls may later include:

* protected branches,
* manual approval,
* environment approval,
* deployment rollback.

## 20.46 Deployment Identity

Each deployment should record:

* Git commit SHA,
* application version,
* Docker image digest,
* CloudFormation stack version or event,
* deployment timestamp,
* environment.

Processing and Evaluation Runs may reference the application version when reproducibility requires it.

## 20.47 Deployment Strategy

The initial ECS deployment may use the default rolling update strategy.

A later production deployment may use:

* rolling replacement,
* blue-green deployment,
* canary deployment.

The deployment strategy should prevent unavailable or unhealthy tasks from replacing all healthy tasks.

Infrastructure simplicity should be balanced with rollback requirements.

## 20.48 Deployment Health Verification

After deployment, the pipeline or operator should verify:

* ECS service stability,
* application liveness,
* application readiness,
* configuration validity,
* required dependency connectivity,
* active-index availability,
* basic query execution where appropriate.

A successful CloudFormation update alone does not prove that the application is functionally ready.

## 20.49 Application Rollback

Application rollback should use a previously known container image and ECS task definition.

Rollback should not automatically change:

* active OpenSearch index,
* Document governance state,
* evaluation baselines,
* source artifacts.

Application rollback and data/index rollback are related but separate operations.

## 20.50 Index Rollback

Index rollback may use:

```text
Active Alias
→ Previous Verified Index
```

The previous index should remain available for a controlled retention period after promotion.

Index rollback must preserve:

* index history,
* promotion event,
* rollback reason,
* affected configuration.

## 20.51 Database Migration Direction

If PostgreSQL is introduced, schema migrations should:

* be version-controlled,
* run through a controlled process,
* support backward-compatible deployment where practical,
* avoid manual undocumented production changes,
* include rollback or recovery planning for destructive changes.

Application deployment and schema migration order must be explicit.

## 20.52 Backup and Recovery Direction

### S3

Recovery may rely on:

* native durability,
* optional versioning,
* lifecycle management,
* replication where later required.

### PostgreSQL

Recovery may use:

* automated backups,
* point-in-time recovery,
* tested restore procedures.

### OpenSearch

Recovery may use:

* snapshots,
* or complete index regeneration from canonical source artifacts and retained configuration.

### Infrastructure

Recovery should use:

* CloudFormation,
* version-controlled configuration,
* container images in ECR,
* documented environment parameters.

## 20.53 Disaster Recovery Boundary

The initial MVP does not require:

* multi-region active-active deployment,
* automated regional failover,
* cross-region database replication,
* zero-data-loss guarantees.

The initial requirement is that the environment can be reconstructed from:

```text
Version-Controlled Infrastructure
+
Container Images
+
Canonical Source Artifacts
+
Operational Backups
+
Configuration History
```

Formal Recovery Time Objective and Recovery Point Objective values should be defined only when business requirements exist.

## 20.54 Cost Direction

The main expected AWS cost drivers are:

* OpenSearch domain,
* ECS Fargate tasks,
* RDS where introduced,
* NAT Gateway,
* embedding-model execution,
* S3 storage,
* CloudWatch logs.

The architecture should avoid unnecessary always-on components.

Examples include:

* no separate service when a module is sufficient,
* on-demand evaluation tasks where practical,
* appropriately sized development OpenSearch,
* explicit log retention,
* controlled inactive-index retention.

Cost optimization should follow measurement rather than speculative complexity.

## 20.55 OpenSearch Cost Consideration

OpenSearch may become the largest baseline cost because it generally requires continuously available managed capacity.

Before production sizing, the project should estimate:

* document count,
* chunk count,
* vector dimensions,
* expected index size,
* query volume,
* replica requirements,
* development and production separation.

The first deployment should use conservative but usable sizing.

It should not assume large-scale capacity before the corpus exists.

## 20.56 Processing Cost Consideration

Processing cost depends on:

* document size,
* chunk count,
* embedding model,
* embedding execution mode,
* reprocessing frequency,
* number of experiments.

Configuration experiments should avoid unnecessary repeated parsing and embedding when compatible derived artifacts can be reused safely.

Reuse must not compromise experiment validity or traceability.

## 20.57 Tagging

AWS resources should use consistent tags.

Indicative tags include:

* `Project`,
* `Environment`,
* `Owner`,
* `ManagedBy`,
* `CostCenter`,
* `DataClassification`.

Example:

```text
Project = cvs-review-portal
Environment = development
ManagedBy = cloudformation
```

Tagging supports cost analysis, ownership, governance, and cleanup.

## 20.58 Resource Naming

Resource names should use a consistent pattern.

Example:

```text
cvs-review-portal-<environment>-<resource>
```

Examples:

```text
cvs-review-portal-dev-api
cvs-review-portal-dev-documents
cvs-review-portal-prod-worker
```

Names should remain stable and should avoid embedding mutable application versions unless the resource is intentionally versioned.

## 20.59 Production Access

Human production access should be limited.

Normal development should occur through:

* CI/CD,
* application APIs,
* controlled monitoring tools.

Direct access to:

* OpenSearch,
* S3 objects,
* databases,
* ECS tasks

should be restricted to approved administrative and support workflows.

Manual changes must not become the normal deployment process.

## 20.60 AWS Audit Direction

AWS CloudTrail may record infrastructure and control-plane actions such as:

* resource changes,
* IAM activity,
* S3 administrative access,
* OpenSearch configuration changes,
* CloudFormation actions.

Application-level audit events remain the responsibility of CVS Review Portal.

CloudTrail does not replace:

* Document governance events,
* Processing Run history,
* evaluation history,
* application-user actions.

## 20.61 Initial AWS MVP Architecture

The likely MVP AWS architecture is:

```text
Internet or Controlled User Network
              │
              ▼
    Application Load Balancer
              │
              ▼
       ECS Fargate API
              │
      ┌───────┼─────────┐
      │       │         │
      ▼       ▼         ▼
     S3   OpenSearch  PostgreSQL
      │
      ▼
Processing Request
      │
      ▼
     SQS
      │
      ▼
ECS Fargate Worker
      │
      ├── S3
      ├── OpenSearch
      └── PostgreSQL
```

This represents the probable target architecture.

The first vertical slice may initially omit:

* SQS,
* separate worker,
* PostgreSQL,
* full authentication.

Those components should be added in the deliverables where their necessity becomes concrete.

## 20.62 Minimum First Deployment

The smallest useful AWS deployment may include:

```text
ECR
ECS Fargate FastAPI Service
S3
OpenSearch
CloudWatch Logs
CloudFormation
IAM Roles
```

This deployment can prove:

* container deployment,
* source upload,
* S3 storage,
* document processing,
* indexing,
* query retrieval.

Operational state may temporarily use a simplified implementation only for the earliest vertical slice.

It must not remain container-memory state in the final MVP.

## 20.63 Probable Final MVP Deployment

The probable final MVP will include:

```text
ECR
ECS Fargate API Service
ECS Fargate Processing Worker
Application Load Balancer
S3
OpenSearch
RDS PostgreSQL
SQS
CloudWatch
Secrets Manager
CloudFormation
IAM Roles
```

Redis and LangGraph remain excluded unless later requirements justify them.

## 20.64 Deployment Decisions Still Open

The following remain open technical decisions:

1. Exact UI hosting model.
2. Exact authentication mechanism.
3. Whether PostgreSQL enters the first vertical slice or a later deliverable.
4. Exact point at which SQS and a separate worker are introduced.
5. Embedding execution model.
6. OpenSearch domain sizing.
7. OpenSearch engine and index parameters.
8. Index alias and promotion strategy.
9. VPC and subnet topology.
10. NAT Gateway and VPC endpoint requirements.
11. S3 artifact-retention policy.
12. RDS sizing and availability model.
13. Whether evaluation runs execute in the worker or as on-demand ECS tasks.
14. Required CloudWatch alarms.
15. Whether CloudFront is required for the UI.

These decisions will be refined through intermediate deliverables rather than resolved speculatively.

## 20.65 Initial Deployment Sequence

A practical deployment sequence is:

```text
1. Deploy shared IAM and logging resources.

2. Deploy S3 source-artifact storage.

3. Deploy OpenSearch.

4. Build and push the application image to ECR.

5. Deploy the FastAPI ECS service.

6. Verify health and dependency access.

7. Implement and verify the first synchronous vertical slice.

8. Add durable operational state.

9. Add SQS and the Processing Worker.

10. Add the functional UI pages.

11. Add evaluation execution and reporting.

12. Add production authentication and hardening.
```

This sequence may be adjusted when the intermediate deliverables are defined.

## 20.66 Deployment Invariants

The following rules should remain true:

1. Canonical source artifacts must remain outside ECS container storage.
2. Application containers must be replaceable without losing durable state.
3. OpenSearch must not run as an embedded database inside each application container.
4. Normal users must not access OpenSearch directly.
5. ECS tasks must use IAM Task Roles rather than static AWS credentials.
6. Production data services should not be publicly exposed unnecessarily.
7. Container images must be traceable to source-code versions.
8. Infrastructure must be provisioned through CloudFormation.
9. Secrets must not appear in CloudFormation outputs or container images.
10. Local development must not connect silently to production resources.
11. Application deployment must remain separate from index activation.
12. Failed candidate indexes must not replace the active verified index.
13. Logs must be sent to durable observability storage.
14. Operational state must survive ECS task replacement.
15. SQS messages, if used, must not become the source of truth for processing state.
16. Worker execution must tolerate duplicate task delivery.
17. Environment resources and permissions must remain isolated.
18. Deployment success must include application-readiness verification.
19. OpenSearch must remain rebuildable from retained source artifacts and configuration.
20. Optional services must be introduced only when justified by a defined requirement.

## 20.67 AWS Deployment Design Principle

The AWS deployment must make it impossible to confuse:

```text
Container Running
with
Application Ready

CloudFormation Succeeded
with
Workflow Works End to End

Document Stored in S3
with
Document Indexed

Index Built
with
Index Active

Application Deployment
with
Data Migration

Queue Message Delivered
with
Processing Completed

Managed Service
with
No Operational Responsibility

Scalable
with
Correctly Sized

Private Network
with
Authorized Access
```

CVS Review Portal should use AWS to provide durable, secure, and reproducible execution while keeping the architecture proportionate to the current Compliance-focused objective.




# 21. Open Technical Decisions

This chapter records technical decisions that remain intentionally unresolved.

These items should not be finalized only through preference or architectural convention.

Each decision should be resolved when:

* the required workflow is understood,
* representative documents and queries are available,
* realistic constraints can be measured,
* and the decision is required by an agreed intermediate deliverable.

The purpose of this chapter is to prevent implicit assumptions from becoming accidental architecture.

## 21.1 Decision Categories

Open decisions are grouped into:

```text
Application Architecture
Data Ingest
Operational State
Document Processing
OpenSearch and Indexing
Retrieval
Evaluation
User Interface
AWS Deployment
Security and Operations
```

Some decisions affect several categories and must be resolved together.

## 21.2 Decision-Making Principle

Each important decision should record:

```text
Decision
Context
Available Options
Selected Option
Rationale
Consequences
Validation Method
Revisit Conditions
```

A decision should not be considered final until its consequences and validation method are understood.

Where uncertainty remains, the project should prefer a reversible baseline over a complex permanent commitment.

## 21.3 Decision Status

Open decisions may use the following status:

```text
OPEN
UNDER_INVESTIGATION
PROVISIONAL
ACCEPTED
DEFERRED
REJECTED
```

### OPEN

The decision has not yet been investigated sufficiently.

### UNDER_INVESTIGATION

Options are being evaluated through research, prototyping, or measurement.

### PROVISIONAL

A temporary direction has been selected to support current implementation.

The decision may still change before the final MVP.

### ACCEPTED

The decision has sufficient evidence and has become the project baseline.

### DEFERRED

The decision is not required for the current deliverable.

### REJECTED

An option has been explicitly excluded with documented reasoning.

## 21.4 Application Architecture

### 21.4.1 Modular Monolith Structure

**Decision:** Define the internal module boundaries of the initial application.

Likely modules include:

* ingest,
* documents,
* monitoring,
* indexing,
* query,
* evaluation,
* configuration,
* observability.

The current direction is a modular monolith.

The exact package structure and dependency rules remain open.

### 21.4.2 API and Worker Boundary

**Decision:** Determine when document processing moves from the FastAPI process into a separate worker.

Options include:

* synchronous processing inside the API,
* background task inside the API service,
* separate worker without a queue,
* separate worker using SQS.

The earliest vertical slice may remain synchronous.

The final MVP will likely require a durable asynchronous worker model.

### 21.4.3 Shared Container Image

**Decision:** Determine whether API, processing worker, and evaluation execution use:

* one shared image with different commands,
* or separate images.

A shared image is the initial preference unless dependency size, security, or runtime-resource requirements justify separation.

### 21.4.4 LangGraph Usage

**Decision:** Determine whether any workflow requires LangGraph.

The deterministic ingestion and retrieval lifecycle does not currently justify it.

LangGraph should remain deferred unless later requirements introduce:

* complex conditional processing,
* stateful human review,
* agentic query planning,
* controlled reasoning loops,
* long-running interruptible workflows.

## 21.5 Operational State

### 21.5.1 PostgreSQL Requirement

**Decision:** Confirm whether PostgreSQL is required and at which deliverable it should be introduced.

Likely requirements include:

* Document and Document Version relationships,
* Processing Run state,
* Index Registry,
* configuration snapshots,
* governance state,
* evaluation history,
* audit events.

Given the current lifecycle and monitoring model, PostgreSQL is likely required before final MVP completion.

The exact introduction point remains open.

### 21.5.2 Operational Data Model

**Decision:** Define which domain entities become persistent relational records.

Potential minimum set:

```text
Document
Document Version
Source Artifact
Processing Run
Index Record
Indexing Run
Configuration Snapshot
Evaluation Dataset Registration
Evaluation Run
```

The project must avoid persisting every conceptual entity independently before its query and consistency requirements are known.

### 21.5.3 Processing Stage Persistence

**Decision:** Determine whether processing stages are stored as:

* separate stage-execution records,
* structured fields inside Processing Run,
* append-only events,
* or a hybrid model.

The MVP should select the simplest model that supports monitoring, retries, and failure diagnosis.

### 21.5.4 Audit Event Persistence

**Decision:** Determine whether audit events are stored:

* in PostgreSQL,
* in an append-oriented S3 artifact,
* in a dedicated logging or audit service,
* or in more than one location.

Formal tamper-evident audit storage may be deferred.

Important state changes must still remain traceable.

### 21.5.5 Idempotency Store

**Decision:** Determine where idempotency records are stored.

Options include:

* PostgreSQL,
* Redis,
* DynamoDB,
* operation-specific uniqueness constraints.

The initial preference is to use PostgreSQL and database constraints unless actual throughput or expiry requirements justify another service.

## 21.6 Data Ingest

### 21.6.1 Upload Transport

**Decision:** Determine whether uploads pass:

* through the FastAPI application,
* directly to S3 through pre-signed URLs,
* or through both methods depending on file size and environment.

Direct API uploads are simpler for the initial MVP.

Pre-signed S3 uploads may become preferable for larger files or production scaling.

### 21.6.2 Required Upload Metadata

**Decision:** Define the minimum metadata required when uploading a document.

Candidate required fields include:

* title,
* document type,
* version label,
* source authority,
* jurisdiction,
* publication date,
* effective date.

The system should not require fields that cannot be reliably known for all document types.

### 21.6.3 Document Identity Rules

**Decision:** Define how the system determines whether an upload belongs to:

* a new Document,
* a new Document Version,
* or an existing Document Version being reprocessed.

This decision affects UI, duplicate detection, governance, and retrieval history.

### 21.6.4 Duplicate Detection

**Decision:** Define how duplicates are detected and handled.

Possible signals include:

* content checksum,
* logical Document identifier,
* version metadata,
* filename,
* source authority,
* publication date.

Checksum equality alone cannot determine business identity.

The final policy must distinguish accidental duplicate requests from intentional reuse of identical content.

### 21.6.5 Source Artifact Key Structure

**Decision:** Define the final S3 object-key convention.

The convention should use stable identifiers and support:

* environment separation,
* Document and Version traceability,
* safe reprocessing,
* controlled deletion,
* artifact-type separation.

### 21.6.6 Retained Intermediate Artifacts

**Decision:** Determine which processing artifacts are retained permanently or temporarily.

Candidates include:

* parsed document,
* normalized text,
* metadata export,
* chunk manifest,
* embedding manifest,
* indexing report.

The decision should balance:

* reproducibility,
* debugging value,
* storage cost,
* regeneration cost,
* auditability.

## 21.7 Parsing and Normalization

### 21.7.1 TXT Parser

**Decision:** Define encoding detection and fallback behaviour for TXT files.

Questions include:

* UTF-8 only or broader encoding support,
* whether malformed content is rejected,
* whether automatic replacement characters are permitted.

### 21.7.2 Markdown Parser

**Decision:** Select the Markdown parsing approach.

Options include:

* plain text handling,
* Markdown AST parsing,
* heading-aware structural extraction.

The selected parser should preserve headings and meaningful structure without unnecessary complexity.

### 21.7.3 DOCX Parser

**Decision:** Select the DOCX parsing implementation.

Potential options include:

* `python-docx`,
* Unstructured,
* another controlled parser.

The decision should evaluate:

* heading preservation,
* lists,
* tables,
* document properties,
* performance,
* security behaviour,
* dependency weight.

### 21.7.4 Table Handling

**Decision:** Determine how tables in DOCX documents are represented.

Options include:

* ignore tables,
* flatten to text,
* preserve row-based structure,
* create separate chunks.

Ignoring tables may lose important compliance information.

A simple deterministic representation may be sufficient initially.

### 21.7.5 Normalization Rules

**Decision:** Define the mandatory normalization pipeline.

Questions include:

* Unicode normalization form,
* whitespace rules,
* heading preservation,
* list-marker treatment,
* repeated-header removal,
* handling of page or section markers.

Normalization should remain conservative until representative documents are inspected.

## 21.8 Metadata

### 21.8.1 Compliance Metadata Schema

**Decision:** Define the initial fixed Compliance metadata model.

Candidate fields include:

```text
title
document_type
source_authority
source_category
jurisdiction
publication_date
effective_date
version_label
governance_status
section_heading
article_reference
applicable_role
```

The MVP should not include every possible Compliance field.

Only fields required for provenance, filtering, governance, and initial use cases should be included.

### 21.8.2 Metadata Origin

**Decision:** Determine whether metadata origin is recorded.

Possible values include:

```text
USER_PROVIDED
FILE_DERIVED
RULE_DERIVED
MODEL_DERIVED
REVIEWER_CONFIRMED
```

This may improve trust and reviewability but adds model complexity.

### 21.8.3 Required Versus Optional Metadata

**Decision:** Determine which fields are required:

* before source storage,
* before processing,
* before indexing,
* before activation.

Not every field needs to block initial upload.

### 21.8.4 Automatic Metadata Extraction

**Decision:** Determine whether the MVP includes automatic metadata extraction.

Options include:

* no automatic extraction,
* deterministic rules only,
* optional LLM-assisted extraction,
* LLM extraction with human confirmation.

The current direction is deterministic or manual metadata first.

### 21.8.5 Section and Article Identification

**Decision:** Determine whether article numbers and section references are:

* extracted by parser structure,
* identified through regular expressions,
* supplied manually,
* or inferred through a model.

This decision may strongly affect Compliance retrieval quality and citations.

## 21.9 Chunking

### 21.9.1 Initial Chunking Strategy

**Decision:** Select the first baseline strategy.

Candidates include:

* fixed-size,
* recursive text splitting,
* heading-aware recursive splitting.

Heading-aware recursive chunking is a likely starting point, but it must be validated against representative documents.

### 21.9.2 Measurement Unit

**Decision:** Determine whether chunk size is measured using:

* characters,
* words,
* tokens,
* parser blocks.

Token-based sizing aligns with model limits but requires tokenizer-specific behaviour.

### 21.9.3 Initial Chunk Size and Overlap

**Decision:** Select the baseline chunk size and overlap.

These values should be determined through:

* corpus inspection,
* chunk-distribution analysis,
* retrieval evaluation,
* embedding-model limits.

They should not be selected only from common RAG defaults.

### 21.9.4 Heading Context

**Decision:** Determine whether heading text is:

* included directly in every chunk,
* stored only as metadata,
* represented through a hierarchy,
* or combined using a controlled prefix.

Repeated headings may improve retrieval but increase duplicated indexed text.

### 21.9.5 Small Section Handling

**Decision:** Determine whether small sections are:

* kept independently,
* merged with adjacent sections,
* merged with their parent section,
* or discarded under a minimum threshold.

Discarding small sections may remove legally important provisions.

### 21.9.6 Chunk Identity

**Decision:** Define the deterministic Chunk identifier scheme.

It must support:

* reprocessing,
* indexing retries,
* experiment separation,
* provenance,
* chunking changes.

### 21.9.7 Parent-Child Retrieval

**Decision:** Determine whether parent-child representation belongs in the MVP.

The current direction is to defer it until the initial chunking baseline is evaluated.

## 21.10 Embeddings

### 21.10.1 Embedding Model

**Decision:** Select the initial embedding model.

Selection criteria include:

* English compliance-text performance,
* possible multilingual requirements,
* vector dimensions,
* local execution feasibility,
* commercial licensing,
* inference latency,
* memory requirements,
* OpenSearch compatibility.

### 21.10.2 Multilingual Support

**Decision:** Determine whether the initial corpus and queries require multilingual embeddings.

The MVP currently appears English-first.

Support for Greek or other languages should not be assumed without actual requirements.

### 21.10.3 Vector Dimensions

**Decision:** Confirm vector dimensions based on the selected model.

Dimensions must be treated as a model and index compatibility constraint rather than an independent preference.

### 21.10.4 Embedding Execution Model

**Decision:** Select between:

* model inside the worker container,
* external model API,
* dedicated inference service,
* managed AWS model service.

The decision should evaluate:

* security,
* startup time,
* memory,
* cost,
* throughput,
* operational simplicity.

### 21.10.5 Model Revision Pinning

**Decision:** Determine how embedding model versions or revisions are pinned.

A model identifier without a revision may be insufficient for reproducibility.

### 21.10.6 Query and Document Prefixes

**Decision:** Determine whether the selected model requires distinct query and document prefixes.

This must be configured consistently and tested.

### 21.10.7 Embedding Reuse

**Decision:** Determine when existing embeddings may be reused across:

* reindexing,
* retrieval experiments,
* mapping changes,
* index migrations.

Reuse is valid only when chunk content and embedding configuration remain identical.

## 21.11 OpenSearch and Indexing

### 21.11.1 OpenSearch Deployment Size

**Decision:** Select initial development and production-like domain sizing.

The decision requires estimates for:

* document count,
* chunk count,
* vector dimensions,
* index size,
* query volume,
* replica requirements.

### 21.11.2 Vector Engine

**Decision:** Select the OpenSearch vector engine and related parameters.

The choice should be based on the deployed OpenSearch version, scale, recall, latency, and supported filtering behaviour.

### 21.11.3 Similarity Metric

**Decision:** Select:

* cosine similarity,
* inner product,
* Euclidean distance,
* or the model-recommended alternative.

This must align with embedding normalization.

### 21.11.4 Lexical Analyzer

**Decision:** Select the initial lexical analyzer and field strategy.

Questions include:

* standard English analyzer,
* keyword subfields,
* stemming,
* stopword behaviour,
* exact-match fields,
* article-reference fields.

### 21.11.5 Index Mapping

**Decision:** Define the first explicit index mapping.

The mapping must include:

* chunk text,
* vector field,
* stable identifiers,
* keyword filters,
* date fields,
* governance fields,
* provenance fields.

Dynamic mapping should be restricted where it risks inconsistent field types.

### 21.11.6 Index Naming

**Decision:** Define the physical and logical index naming convention.

The naming scheme must distinguish:

* environment,
* baseline index,
* candidate experiment,
* mapping version,
* corpus or build identity where required.

### 21.11.7 Alias Strategy

**Decision:** Determine whether the MVP uses an active alias.

An alias supports:

* safe promotion,
* rollback,
* stable query configuration.

It adds lifecycle and permission requirements but is likely valuable before final MVP completion.

### 21.11.8 Index Granularity

**Decision:** Determine whether the system uses:

* one shared Compliance index,
* separate indexes by document type,
* separate indexes by experiment,
* separate indexes by environment only.

The current direction is one shared index per controlled representation or experiment.

### 21.11.9 Indexing Batch Size

**Decision:** Select bulk-indexing batch size and retry behaviour.

The value should be measured against:

* payload size,
* memory,
* OpenSearch throughput,
* partial failure handling.

### 21.11.10 Verification Rules

**Decision:** Define the exact conditions required for index verification.

Possible conditions include:

* expected chunk count,
* zero failed writes,
* required field presence,
* successful sample retrieval,
* mapping compatibility,
* source-version coverage.

## 21.12 Retrieval

### 21.12.1 Initial Retrieval Baseline

**Decision:** Select the first retrieval mode used for the initial vertical slice.

Possible baselines include:

* BM25 only,
* vector only,
* hybrid.

A useful evaluation sequence may begin with separate BM25 and vector baselines before selecting hybrid retrieval.

### 21.12.2 Hybrid Fusion Method

**Decision:** Select the hybrid fusion approach.

Candidates include:

* Reciprocal Rank Fusion,
* weighted normalized scores,
* OpenSearch-native hybrid pipelines.

The initial preference may be RRF because it avoids directly comparing incomparable raw scores.

### 21.12.3 RRF Parameters

**Decision:** Select the initial RRF constant and candidate limits.

Values should be evaluated rather than assumed permanently.

### 21.12.4 Candidate Count

**Decision:** Determine how many lexical and vector candidates are retrieved before final top-k selection.

Candidate count affects:

* Recall,
* latency,
* memory,
* fusion quality.

### 21.12.5 Top-K

**Decision:** Determine the default top-k for:

* technical query inspection,
* Compliance User display,
* evaluation.

Evaluation initially requires K=10, but UI display may use another default.

### 21.12.6 Metadata Filters

**Decision:** Define the filters available in the first Query interface.

Likely candidates include:

* governance status,
* jurisdiction,
* source authority,
* document type,
* date range,
* Document or Version.

### 21.12.7 Governance Filter Enforcement

**Decision:** Define how governance filtering is enforced and synchronized between PostgreSQL and OpenSearch.

The retrieval layer must not depend only on UI-provided filter values.

### 21.12.8 Score Display

**Decision:** Determine which scores are displayed to users.

Technical users may inspect:

* BM25 score,
* vector score,
* fused rank.

Compliance Users may require only rank and source information.

Raw scores must not be labelled as confidence.

### 21.12.9 Weak-Result Detection

**Decision:** Determine whether the MVP identifies weak result sets.

Possible approaches include:

* no threshold,
* retrieval-mode-specific thresholds,
* heuristic result separation,
* manually evaluated no-answer behaviour.

Score thresholds should not be introduced before score distributions are studied.

### 21.12.10 Deduplication

**Decision:** Determine whether query-time deduplication is required.

Possible strategies include:

* exact Chunk identifier deduplication,
* same source-span deduplication,
* overlap-aware deduplication,
* one result per section or Document.

The baseline should avoid removing distinct regulatory evidence.

### 21.12.11 Reranking

**Decision:** Determine whether cross-encoder or LLM reranking enters the MVP.

The current direction is to defer reranking until baseline retrieval has been evaluated.

## 21.13 Evaluation

### 21.13.1 Judgment Granularity

**Decision:** Select the initial relevance-judgment level:

* Document,
* Section,
* source span,
* Chunk.

Section or source-span judgment may provide better stability across chunking experiments.

### 21.13.2 Relevance Scale

**Decision:** Select binary or graded relevance.

Graded relevance supports nDCG more meaningfully.

The final scale must be simple enough for consistent human annotation.

### 21.13.3 Golden Dataset Format

**Decision:** Select the initial dataset representation.

Options include:

* JSONL,
* CSV,
* YAML,
* PostgreSQL-managed records.

JSONL is a likely initial choice because it is versionable and supports structured judgments.

### 21.13.4 Dataset Storage

**Decision:** Determine whether the approved dataset is stored in:

* Git,
* S3,
* PostgreSQL,
* or a combination.

The chosen approach must support:

* versioning,
* approval status,
* checksum,
* reproducibility,
* controlled updates.

### 21.13.5 Evaluation Dataset Size

**Decision:** Determine the initial number of evaluation queries.

The dataset must be large enough to include:

* exact-term cases,
* semantic paraphrases,
* metadata-sensitive cases,
* version-sensitive cases,
* difficult queries,
* no-answer queries.

The number should be based on meaningful coverage rather than an arbitrary target.

### 21.13.6 Corpus Versioning

**Decision:** Define how an Evaluation Run identifies the exact corpus.

Possible identifiers include:

* active index identity,
* index-build identifier,
* explicit Document Version manifest,
* corpus checksum.

### 21.13.7 Metric Averaging

**Decision:** Define how query-level metrics are aggregated.

Questions include:

* macro average,
* category-weighted average,
* treatment of no-answer queries,
* treatment of failed queries,
* treatment of fewer than K returned results.

### 21.13.8 No-Answer Evaluation

**Decision:** Define expected retrieval behaviour for no-answer queries.

Options include:

* no judged-relevant result in top-k,
* empty result after threshold,
* explicit weak-result signal.

This decision depends on weak-result detection.

### 21.13.9 Baseline Acceptance

**Decision:** Define when an Evaluation Run becomes the accepted baseline.

The MVP may initially require explicit Technical Operator selection.

Later versions may require reviewer approval.

### 21.13.10 Regression Thresholds

**Decision:** Define acceptable regression thresholds only after representative baseline results exist.

Possible future rules include:

* aggregate metric threshold,
* no critical-query regression,
* latency boundary,
* minimum corpus coverage.

## 21.14 User Interface

### 21.14.1 Front-End Technology

**Decision:** Select the UI implementation.

Options include:

* FastAPI server-rendered templates,
* Streamlit,
* lightweight React frontend,
* another simple web framework.

The first UI should prioritize:

* functional workflows,
* result inspection,
* low implementation overhead,
* clear API separation.

### 21.14.2 Data Ingest Page Design

**Decision:** Define which metadata is collected during upload and which fields are optional.

The page must avoid overwhelming the user before the metadata schema is stable.

### 21.14.3 Data Monitoring Page Structure

**Decision:** Determine the primary navigation model.

Possible views include:

* Documents,
* Document Versions,
* Processing Runs,
* Indexes,
* Evaluation Runs.

The interface should support drill-down without becoming a generic administration platform.

### 21.14.4 Data Query Page Structure

**Decision:** Determine which technical controls are visible by default.

Potential controls include:

* index,
* retrieval mode,
* top-k,
* filters,
* score details,
* evaluation dataset.

The AI / Search Engineer interface may expose more controls than the Compliance User view.

### 21.14.5 Evaluation UI

**Decision:** Determine whether evaluation execution belongs:

* inside the Data Query page,
* in a separate evaluation section,
* or initially only through API or CLI.

### 21.14.6 Source Artifact Access

**Decision:** Determine how users open or download the original source artifact.

Possible approaches include:

* time-limited S3 pre-signed URL,
* backend streaming endpoint,
* no direct source access in the earliest MVP.

## 21.15 AWS Deployment

### 21.15.1 First AWS Vertical Slice

**Decision:** Define the smallest first deployment.

Likely components:

```text
ECR
ECS Fargate API
S3
OpenSearch
CloudWatch
IAM
CloudFormation
```

The first slice may postpone PostgreSQL, SQS, and a separate worker, but it must not establish container memory as the final operational-state solution.

### 21.15.2 SQS Introduction Point

**Decision:** Determine the deliverable in which asynchronous ingestion becomes mandatory.

The decision should be based on:

* processing duration,
* HTTP timeout risk,
* retry requirements,
* monitoring requirements,
* worker scaling.

### 21.15.3 Worker Scaling

**Decision:** Determine the initial worker concurrency model.

Possible options include:

* one worker task,
* fixed worker count,
* SQS-based autoscaling,
* on-demand ECS tasks.

### 21.15.4 Embedding Compute

**Decision:** Determine whether normal Fargate CPU tasks are sufficient for the selected model.

If not, alternative execution environments may be required.

### 21.15.5 OpenSearch Environment Strategy

**Decision:** Determine whether development and production-like environments use:

* separate OpenSearch domains,
* separate indexes in one non-production domain,
* local OpenSearch for most development.

Production data must remain isolated.

### 21.15.6 VPC Topology

**Decision:** Define:

* public and private subnets,
* ALB placement,
* ECS placement,
* OpenSearch access,
* RDS access,
* VPC endpoints,
* NAT requirements.

The topology should remain proportionate to the application.

### 21.15.7 Authentication Mechanism

**Decision:** Select the authentication method for:

* local development,
* controlled AWS development,
* production-facing deployment.

The MVP may use simplified authentication in a restricted environment.

A public deployment requires a stronger approved mechanism.

### 21.15.8 UI Hosting

**Decision:** Select whether the UI is:

* served by FastAPI,
* hosted through S3 and CloudFront,
* deployed as a separate ECS service.

### 21.15.9 CloudFormation Stack Boundaries

**Decision:** Determine whether infrastructure is organized as:

* one stack,
* application and data stacks,
* foundation, data, and application stacks.

The initial preference should minimize unnecessary cross-stack dependencies.

### 21.15.10 Database Migration Execution

**Decision:** Define how PostgreSQL migrations are executed.

Options include:

* CI/CD step,
* one-off ECS task,
* application startup migration,
* controlled administrative command.

Automatic application-startup migrations may be risky for production deployment.

## 21.16 Security

### 21.16.1 MVP Authentication

**Decision:** Select the minimum acceptable authentication for the first AWS environment.

### 21.16.2 Role Enforcement

**Decision:** Determine whether the first MVP implements:

* Technical Operator,
* Query User,
* or one controlled user role only.

Backend capability boundaries should remain ready for later separation.

### 21.16.3 Document-Level Authorization

**Decision:** Confirm whether document-level access restrictions are required.

The current single-knowledge-base MVP does not appear to require them.

### 21.16.4 Query Retention

**Decision:** Determine whether interactive query text is:

* retained fully,
* retained temporarily,
* redacted,
* hashed,
* or not persisted.

### 21.16.5 Malware Scanning

**Decision:** Determine whether uploaded files require antivirus or malware scanning in the MVP.

This depends on deployment exposure and organizational security requirements.

### 21.16.6 Data Classification

**Decision:** Determine whether the MVP requires formal document-classification labels.

The architecture may support a simple optional field without implementing full classification policy.

### 21.16.7 Customer-Managed KMS Keys

**Decision:** Determine whether AWS-managed encryption keys are sufficient for the initial deployment.

Customer-managed keys should be introduced only when a requirement justifies the added policy and operational complexity.

## 21.17 Observability and Operations

### 21.17.1 Logging Framework

**Decision:** Select the structured logging implementation and shared event schema.

### 21.17.2 Metrics Publication

**Decision:** Determine whether application metrics are published through:

* CloudWatch embedded metric format,
* direct CloudWatch API,
* OpenTelemetry,
* log-derived metrics.

### 21.17.3 Distributed Tracing

**Decision:** Determine whether distributed tracing is required.

The initial MVP may rely on structured logs and correlation identifiers.

### 21.17.4 Alert Thresholds

**Decision:** Define alerts only after normal operational behaviour can be measured.

### 21.17.5 Reconciliation Process

**Decision:** Determine whether reconciliation is:

* manual through an administrative command,
* exposed in Data Monitoring,
* scheduled,
* or event-triggered.

The MVP likely requires at least an on-demand consistency check.

### 21.17.6 Retention Periods

**Decision:** Define retention separately for:

* source artifacts,
* derived artifacts,
* inactive indexes,
* logs,
* audit events,
* query history,
* evaluation reports.

## 21.18 Testing

### 21.18.1 Local Dependency Strategy

**Decision:** Determine whether local development uses:

* local OpenSearch,
* mocked OpenSearch interfaces,
* LocalStack for S3,
* real AWS development resources,
* testcontainers.

A combination is likely required.

### 21.18.2 Integration Test Environment

**Decision:** Define which tests run against real:

* S3,
* OpenSearch,
* PostgreSQL,
* SQS.

### 21.18.3 End-to-End Test Corpus

**Decision:** Select a small controlled document corpus used for automated end-to-end testing.

### 21.18.4 Quality Thresholds

**Decision:** Define required:

* test categories,
* code coverage expectations,
* typing rules,
* Ruff configuration,
* build gates.

Coverage percentage should not replace critical-path testing.

### 21.18.5 Retrieval Regression in CI/CD

**Decision:** Determine whether retrieval evaluation runs in:

* every pull request,
* selected pipeline runs,
* scheduled jobs,
* pre-release validation.

The answer depends on dataset size, model execution cost, and OpenSearch availability.

## 21.19 Decision Dependencies

Some decisions must be resolved in sequence.

### Sequence A — Document Processing

```text
Representative Documents
→ Parser Selection
→ Metadata Schema
→ Normalization Rules
→ Chunking Strategy
→ Chunk Size and Overlap
```

### Sequence B — Vector Retrieval

```text
Embedding Model
→ Vector Dimensions
→ Normalization
→ OpenSearch Vector Mapping
→ Similarity Metric
→ Query Embedding Behaviour
```

### Sequence C — Evaluation

```text
Metadata and Corpus Model
→ Judgment Granularity
→ Golden Dataset Format
→ Metric Calculation Policy
→ Baseline Selection
→ Regression Thresholds
```

### Sequence D — Asynchronous Processing

```text
Processing Duration and State Requirements
→ PostgreSQL Model
→ SQS
→ Worker Contract
→ Idempotency and Retry Model
→ Worker Scaling
```

### Sequence E — Production Access

```text
Deployment Exposure
→ Authentication
→ Authorization
→ Network Design
→ Query Retention
→ Audit Requirements
```

## 21.20 Decisions Required Before Intermediate Deliverables

Before defining detailed intermediate deliverables, the project does not need every decision finalized.

However, the following should have at least a provisional direction:

1. Initial modular application structure.
2. First end-to-end vertical slice.
3. Initial persistence direction.
4. Initial parser choices.
5. Initial metadata schema boundary.
6. Initial chunking baseline.
7. Initial embedding-model evaluation shortlist.
8. Initial OpenSearch retrieval modes to compare.
9. Initial evaluation-judgment granularity.
10. First UI implementation direction.
11. First AWS deployment boundary.
12. Point at which PostgreSQL, SQS, and worker separation are introduced.

## 21.21 Decisions That May Remain Deferred

The following may remain deferred beyond the first MVP:

* LangGraph,
* multi-agent workflows,
* parent-child retrieval,
* reranking,
* distributed tracing,
* customer-managed KMS keys,
* advanced document-level authorization,
* multi-tenancy,
* formal tamper-evident audit storage,
* multi-region deployment,
* advanced autoscaling,
* full configuration-promotion workflow,
* automated regulatory crawling.

## 21.22 Provisional Current Direction

The current working direction is:

```text
Architecture
→ Modular monolith with optional worker

API
→ FastAPI

Processing
→ Deterministic pipeline

Source Storage
→ S3

Operational State
→ PostgreSQL likely required

Background Processing
→ SQS plus ECS worker when asynchronous ingestion is introduced

Retrieval
→ OpenSearch BM25, vector, and hybrid comparison

Configuration
→ Validated YAML and environment settings

Evaluation
→ Versioned golden dataset with Precision@10, Recall@10, and nDCG@10

Deployment
→ ECR, ECS Fargate, S3, OpenSearch, CloudWatch, CloudFormation

Redis
→ Not required without a concrete use case

LangGraph
→ Deferred
```

This direction remains provisional until the relevant decisions are validated.

## 21.23 Decision Validation Methods

Depending on the decision, validation may use:

* representative document inspection,
* small technical prototype,
* automated unit tests,
* integration tests,
* load or latency measurement,
* retrieval evaluation,
* security review,
* infrastructure cost estimate,
* operational failure simulation,
* user workflow review.

Architecture decisions should be supported by the most relevant evidence rather than by one universal evaluation method.

## 21.24 Decision Revisit Triggers

An accepted decision may be revisited when:

* document formats or corpus characteristics change,
* retrieval metrics remain below the required baseline,
* cost becomes unacceptable,
* performance requirements change,
* a security requirement changes,
* user roles expand,
* operational failures expose a weakness,
* a second domain use case is introduced,
* scale exceeds the assumptions behind the original decision.

Revisiting a decision is not architectural failure.

Undocumented change without impact analysis is the failure.

## 21.25 Open Decision Register

A separate decision register should eventually track:

| ID     | Decision                        | Status | Required By                 | Owner | Outcome Reference |
| ------ | ------------------------------- | ------ | --------------------------- | ----- | ----------------- |
| TD-001 | Operational state store         | Open   | Monitoring deliverable      | TBD   | TBD               |
| TD-002 | DOCX parser                     | Open   | Data Ingest deliverable     | TBD   | TBD               |
| TD-003 | Initial chunking strategy       | Open   | Chunking deliverable        | TBD   | TBD               |
| TD-004 | Embedding model                 | Open   | Embedding deliverable       | TBD   | TBD               |
| TD-005 | OpenSearch vector configuration | Open   | Indexing deliverable        | TBD   | TBD               |
| TD-006 | Initial retrieval baseline      | Open   | Data Query deliverable      | TBD   | TBD               |
| TD-007 | Relevance-judgment granularity  | Open   | Evaluation deliverable      | TBD   | TBD               |
| TD-008 | UI framework                    | Open   | UI deliverable              | TBD   | TBD               |
| TD-009 | SQS and worker introduction     | Open   | Async ingestion deliverable | TBD   | TBD               |
| TD-010 | MVP authentication              | Open   | AWS exposure deliverable    | TBD   | TBD               |

The final register may be maintained separately from this Project Reference.

## 21.26 Technical Decision Invariants

The following rules should remain true:

1. Open decisions must not be hidden behind undocumented defaults.
2. A provisional implementation must be labelled as provisional.
3. Decisions affecting reproducibility must be recorded.
4. Model and index compatibility must be validated together.
5. Retrieval decisions must use evaluation evidence where possible.
6. Security decisions must not be deferred beyond the point of exposure.
7. Infrastructure components must not be introduced without a concrete requirement.
8. Reversible decisions should remain reversible until evidence justifies commitment.
9. Configuration must not be used to avoid making core architecture decisions.
10. A second domain should not influence the current architecture unless its requirements are real.
11. Accepted decisions must identify their consequences.
12. Changes to accepted decisions must preserve historical context.

## 21.27 Open Technical Decisions Principle

The decision process must make it impossible to confuse:

```text
Not Yet Decided
with
Not Important

Provisional
with
Permanent

Popular Technology
with
Appropriate Technology

Configurable
with
Decision-Free

Prototype Success
with
Production Validation

Higher Complexity
with
Better Architecture

Future Possibility
with
Current Requirement
```

CVS Review Portal should resolve technical decisions at the point where sufficient evidence and implementation need exist, while preserving clear ownership, rationale, and traceability.



# 22. Project-Level Success Criteria

Project-Level Success Criteria define the outcomes that must be demonstrably true for CVS Review Portal to be considered a successful first release.

These criteria describe system-level results.

They are not the detailed acceptance criteria or Definition of Done for individual intermediate deliverables.

The project succeeds when it provides a complete, controlled, traceable, and measurable lifecycle:

```text
Compliance Source Document
→ Controlled Ingestion
→ Searchable Representation
→ Observable Knowledge State
→ Inspectable Retrieval
→ Reproducible Evaluation
```

## 22.1 Success Evaluation Principle

Success must be demonstrated through:

* working system behaviour,
* persisted system state,
* inspectable evidence,
* automated tests,
* evaluation results,
* deployment reproducibility.

The project must not be considered successful only because:

* containers start,
* documents can be uploaded,
* OpenSearch returns results,
* a small number of example queries appear reasonable,
* or an LLM can generate a convincing answer.

Technical availability and demonstration quality are necessary but not sufficient.

## 22.2 End-to-End Lifecycle Success

The system must demonstrate that a supported compliance document can complete the full lifecycle:

```text
Upload
→ Validation
→ Source Storage
→ Document and Version Registration
→ Parsing
→ Normalization
→ Metadata Handling
→ Chunking
→ Embedding
→ Indexing
→ Verification
→ Retrieval Availability
→ Query
→ Evaluation
```

The lifecycle must be completed without undocumented manual changes to:

* S3,
* OpenSearch,
* operational records,
* configuration,
* processing state.

An authorized user must be able to observe the result through the application interfaces.

## 22.3 Supported Document Success

Before final MVP completion, the system must support:

* TXT,
* Markdown,
* DOCX.

For each supported format, the system must be capable of:

* validating the source,
* preserving the original artifact,
* extracting usable text,
* preserving meaningful structure where available,
* creating traceable chunks,
* indexing the resulting representation.

Unsupported formats must be rejected explicitly.

They must not enter a partially supported processing path.

## 22.4 Canonical Source Preservation Success

Every successfully registered Document Version must reference a canonical Source Artifact stored in S3.

The system must demonstrate that:

* the original file remains available independently of OpenSearch,
* the source is identified through a stable application identifier,
* its checksum or equivalent integrity signal is recorded,
* it can be retrieved for controlled reprocessing,
* deleting or rebuilding an index does not remove the canonical source.

OpenSearch must remain a derived serving layer rather than the only copy of document content.

## 22.5 Document Identity and Version Success

The system must distinguish successfully between:

```text
Document
Document Version
Processing Run
Indexing Run
Search Index
```

It must be possible to demonstrate that:

* one Document may have multiple Document Versions,
* one Document Version may have multiple Processing Runs,
* technical reprocessing does not create a false source version,
* each indexed representation is connected to the run that produced it,
* active and superseded versions remain distinguishable.

The user must not need to infer these relationships from filenames or OpenSearch records.

## 22.6 Processing-Control Success

The ingestion process must expose explicit processing state.

An authorized user must be able to determine:

* whether processing has started,
* which stage is running,
* which stages completed,
* which stage failed,
* how many chunks were generated,
* which configuration was used,
* which target index was selected.

A failed or partially completed Processing Run must not appear as successfully completed.

## 22.7 Failure-Handling Success

The system must demonstrate controlled handling of representative failure scenarios.

At minimum, it should correctly handle cases such as:

* unsupported file,
* invalid metadata,
* parser failure,
* empty chunk output,
* embedding failure,
* vector-dimension mismatch,
* partial OpenSearch bulk failure,
* unavailable retrieval index.

For these failures:

* the failure category must be visible,
* the workflow must stop safely,
* incomplete content must not become active,
* previous successful content must remain protected,
* retry or corrective action must be clear.

## 22.8 Idempotency Success

The system must demonstrate that repeated or retried operations do not create uncontrolled side effects.

This includes:

* repeated upload requests,
* repeated processing commands,
* repeated embedding attempts,
* repeated indexing attempts,
* duplicate worker execution where asynchronous processing exists.

The system must preserve:

* stable identifiers,
* attempt history,
* expected chunk counts,
* controlled duplicate handling.

An accidental repeated request must not silently create multiple active copies of the same searchable content.

## 22.9 Processing Verification Success

A Document Version must not become available for normal retrieval before processing and indexing verification succeed.

Verification must demonstrate, at minimum, that:

* all expected chunks were processed,
* required embeddings were generated,
* vector dimensions match the target mapping,
* required OpenSearch writes succeeded,
* indexed counts are consistent with expected counts,
* required provenance fields are present.

The system must distinguish:

```text
Processing Completed
from
Search Representation Verified
```

## 22.10 Data Monitoring Success

The Data Monitoring area must allow an authorized user to inspect the current and historical state of the knowledge base.

The user must be able to identify:

* available Documents,
* available Document Versions,
* active versions,
* superseded or disabled versions,
* latest Processing Runs,
* failed stages,
* target indexes,
* index readiness,
* configuration references.

The information must be available through application-level interfaces without requiring direct database, S3, or OpenSearch inspection.

## 22.11 Governance Success

The system must support basic Document Version governance.

At minimum, it must distinguish:

```text
ACTIVE
SUPERSEDED
DISABLED
DELETED
```

or an approved equivalent state model.

The system must demonstrate that:

* inactive versions remain identifiable,
* superseded or disabled content is excluded from normal retrieval,
* governance state is enforced by backend logic,
* state changes remain traceable,
* historical source identity is preserved where retention permits.

Technical indexing success must not automatically imply governance approval.

## 22.12 Document-to-Index Traceability Success

For every active searchable Document Version, the system must be able to show:

```text
Document
→ Document Version
→ Source Artifact
→ Processing Run
→ Indexing Run
→ OpenSearch Index
```

For every retrieved Chunk, the relationship must also work in reverse:

```text
Search Result
→ Chunk
→ Processing Run
→ Document Version
→ Source Artifact
```

No retrieval result should exist as an isolated text fragment without source provenance.

## 22.13 Index Lifecycle Success

The system must maintain an application-level registry of indexes.

An authorized Technical Operator must be able to identify:

* the active index,
* candidate or inactive indexes,
* index configuration,
* vector dimensions,
* embedding model,
* chunking configuration,
* indexed document and chunk counts,
* verification status.

The system must support rebuilding or replacing an index without modifying the canonical source documents.

Before final MVP completion, the design should support safe index replacement or promotion without destructive dependency on one physical index.

## 22.14 Query Execution Success

The Data Query area must allow an authorized user to:

* submit a natural-language query,
* execute an approved retrieval configuration,
* apply supported metadata filters,
* retrieve ranked results,
* inspect result provenance,
* distinguish successful, failed, and no-result outcomes.

The Query interface must not require direct OpenSearch access.

## 22.15 Retrieval Result Success

Each returned Search Result must include or reference:

* result rank,
* Chunk identifier,
* Document identifier,
* Document Version identifier,
* document title,
* section or heading where available,
* Chunk content,
* governance status,
* source reference,
* available retrieval scores for technical inspection.

Retrieval results must remain stable application contracts rather than raw OpenSearch responses.

## 22.16 Governance-Aware Retrieval Success

Normal retrieval must include only content permitted by the approved governance rules.

The system must demonstrate that:

* active content can be retrieved,
* disabled content is excluded,
* superseded content is excluded from current-only retrieval,
* diagnostic access to inactive content, where allowed, is explicit,
* governance filtering cannot be bypassed merely by omitting a UI filter.

## 22.17 Retrieval Mode Success

The system must support a measurable retrieval baseline using OpenSearch.

Before final MVP completion, it must be possible to evaluate at least two approved retrieval configurations, potentially including:

* BM25 lexical retrieval,
* vector retrieval,
* hybrid retrieval.

The final accepted production baseline must be selected through evaluation rather than assumption.

Not every supported mode must become active by default.

## 22.18 No-Result and Failure Distinction Success

The system must distinguish clearly between:

```text
Invalid Query
Retrieval Execution Failure
Valid Query With No Results
Valid Query With Weak Results
Successful Retrieval
```

A valid no-result outcome must not be reported as an infrastructure failure.

A retrieval failure must not be presented as an empty but successful result.

The system must not fabricate or substitute unsupported evidence.

## 22.19 Golden Evaluation Dataset Success

The project must include a versioned Golden Evaluation Dataset containing:

* realistic compliance queries,
* approved relevant evidence,
* binary or graded relevance judgments,
* sufficient provenance to identify judged evidence,
* difficult and metadata-sensitive cases,
* no-answer cases where appropriate.

The dataset must not exist only on one developer’s local machine.

Its version, checksum, or equivalent identity must remain traceable.

## 22.20 Evaluation Metric Success

The system must calculate correctly:

* Precision@10,
* Recall@10,
* nDCG@10.

Metric implementations must be covered by automated tests using known expected examples.

The system must preserve:

* query-level results,
* aggregate results,
* failed-query information,
* dataset version,
* target index,
* retrieval configuration.

Evaluation failures must not be silently excluded from the final report.

## 22.21 Evaluation Reproducibility Success

Every Evaluation Run must identify:

```text
Evaluation Dataset Version
+
Source Corpus or Index Build
+
Target Index
+
Retrieval Configuration
+
Metric Implementation
+
Application Version Where Required
```

An authorized user must be able to determine exactly what produced the reported metrics.

A metric value without this context must not become an accepted baseline.

## 22.22 Baseline Comparison Success

The system must allow a candidate retrieval configuration to be compared with an accepted baseline.

The comparison must show at least:

* baseline metric values,
* candidate metric values,
* absolute changes,
* query-level improvements,
* query-level regressions,
* failed queries.

The project must not rely only on aggregate improvements.

Important regressions must remain visible even when the overall average improves.

## 22.23 Configuration Traceability Success

Every significant Processing Run, Indexing Run, and Evaluation Run must reference an immutable Configuration Snapshot.

The system must be able to identify parameters such as:

* parser configuration,
* chunking strategy,
* chunk size,
* chunk overlap,
* embedding model,
* vector dimensions,
* target index,
* retrieval mode,
* top-k,
* fusion parameters,
* evaluation dataset.

Historical runs must not be reinterpreted using the current mutable configuration.

## 22.24 Controlled Configuration Success

The project must support practical configuration for approved experimentation without becoming an arbitrary plugin platform.

Configuration must:

* use explicit supported options,
* be validated before execution,
* reject incompatible combinations,
* exclude secrets,
* create reproducible snapshots.

Configuration must not allow bypassing:

* lifecycle invariants,
* provenance,
* governance filtering,
* mandatory validation,
* security controls.

## 22.25 Observability Success

An authorized Technical Operator must be able to determine:

* whether a request reached the application,
* which run was created,
* which stage is executing,
* where a failure occurred,
* which dependency was involved,
* which configuration was used,
* how many chunks were produced,
* how many records were indexed,
* how long retrieval took,
* whether an Evaluation Run completed.

This must be possible through structured state, logs, and application interfaces without attaching a debugger to a production container.

## 22.26 Auditability Success

Important state-changing actions must remain traceable.

The initial audit scope should include:

* Document upload,
* Document Version creation,
* processing retry,
* governance-state change,
* index activation,
* evaluation-baseline selection,
* permanent deletion where supported.

Audit-relevant records should identify, where available:

* actor,
* timestamp,
* action,
* affected entity,
* previous state,
* new state,
* outcome.

Ordinary debug logs must not be the only evidence of these actions.

## 22.27 Security Baseline Success

The system must demonstrate the agreed baseline security controls:

* private S3 storage,
* encryption in transit,
* encryption at rest,
* IAM Task Roles,
* no static AWS credentials,
* no committed secrets,
* restricted OpenSearch access,
* validated uploads,
* safe filename handling,
* request validation,
* safe logging,
* non-root containers,
* backend governance enforcement.

A production-facing environment must also use an approved authentication mechanism.

## 22.28 Data Protection Success

The application must avoid uncontrolled duplication of sensitive content through:

* logs,
* temporary files,
* configuration snapshots,
* query history,
* evaluation reports.

The system must demonstrate that:

* full document content is not logged by default,
* secrets are redacted or excluded,
* temporary files are controlled,
* query retention follows an explicit policy,
* source access is restricted.

## 22.29 Deployment Reproducibility Success

The AWS environment must be provisionable through CloudFormation.

Container images must be built and stored in ECR.

The deployment must be traceable to:

* source-code version,
* image version or digest,
* infrastructure definition,
* environment configuration.

The application must not depend on undocumented manual AWS resource creation.

## 22.30 Container and Runtime Success

Application containers must:

* start through defined commands,
* expose liveness and readiness endpoints,
* run as non-root,
* avoid local durable state,
* use environment and IAM-based runtime configuration,
* send logs to durable observability storage.

Replacing an ECS task must not remove:

* source documents,
* operational state,
* index history,
* evaluation history.

## 22.31 AWS Integration Success

The deployed system must demonstrate controlled integration with:

* S3,
* OpenSearch,
* ECR,
* ECS Fargate,
* CloudWatch,
* CloudFormation.

Where PostgreSQL, SQS, Secrets Manager, or another service becomes part of the agreed MVP architecture, their integration must also be:

* provisioned through infrastructure as code,
* observable,
* secured through least privilege,
* covered by integration testing.

## 22.32 Health and Readiness Success

The application must expose distinct health and readiness behaviour.

The system must distinguish:

```text
Application Process Is Alive
from
Application Is Ready to Serve Its Intended Workflow
```

Readiness must account for the dependencies required by the relevant service.

A running container with invalid configuration or unavailable required dependencies must not be presented as fully ready.

## 22.33 Automated Testing Success

Critical system behaviour must be protected by automated tests.

The final MVP test suite should cover:

* configuration validation,
* upload validation,
* parser contracts,
* normalization behaviour,
* chunk generation,
* metadata preservation,
* stable identifiers,
* duplicate handling,
* lifecycle transitions,
* embedding-dimension validation,
* OpenSearch indexing,
* partial write detection,
* retrieval result contracts,
* governance filtering,
* evaluation metrics,
* failure and retry behaviour.

The project must prioritize critical-path coverage over an arbitrary coverage percentage.

## 22.34 Code Quality Success

The codebase must maintain the production discipline established by the starter template.

The build and delivery process should include:

* Poetry dependency management,
* Ruff checks,
* static type checking,
* automated tests,
* Docker build validation,
* dependency locking,
* clear module boundaries.

A feature must not be accepted merely because it works manually when it violates agreed quality gates.

## 22.35 Maintainability Success

The implementation must remain understandable and modifiable without becoming a generic framework.

The system should demonstrate:

* clear module responsibilities,
* explicit contracts,
* limited infrastructure leakage into domain logic,
* controlled dependency direction,
* testable processing stages,
* documented configuration,
* documented technical decisions.

The codebase should be structured so that a future Compliance-related project can copy and adapt it without first dismantling unnecessary abstraction layers.

## 22.36 Scope-Control Success

The final MVP must remain focused on:

```text
Data Ingest
Data Monitoring
Data Query
Retrieval Evaluation
```

The project should not require completion of:

* final LLM answer generation,
* multi-agent orchestration,
* PDF and OCR,
* automatic regulatory crawling,
* reranking,
* knowledge graphs,
* multi-tenancy,
* enterprise SSO,
* model fine-tuning,
* multi-cloud support.

A deferred capability must not become an undocumented dependency of the core MVP.

## 22.37 User Workflow Success

The primary Technical Operator must be able to complete the full workflow:

```text
Upload Document
→ Monitor Processing
→ Inspect Document Version
→ Inspect Index State
→ Execute Query
→ Inspect Evidence
→ Run Evaluation
→ Compare With Baseline
```

The workflow may involve multiple pages.

It should not require:

* command-line database modification,
* direct S3 editing,
* direct OpenSearch writes,
* manual creation of internal identifiers.

Administrative technical tools may remain available for diagnosis, but they must not be required for the normal successful path.

## 22.38 Initial Compliance User Success

A Compliance User must be able to:

* submit a natural-language query,
* inspect ranked evidence,
* identify the source Document,
* identify the Document Version,
* identify the relevant section,
* inspect available authority, jurisdiction, and date metadata,
* understand that the result is evidence rather than final legal advice.

The initial interface may remain technical in appearance, but the evidence must be understandable without knowledge of vector dimensions or OpenSearch mappings.

## 22.39 Successful Demonstration Scenario

The final MVP should successfully demonstrate the following controlled scenario:

```text
1. A Technical Operator uploads a DOCX compliance document.

2. The file is validated and stored as a canonical S3 Source Artifact.

3. The system creates or associates the correct Document and Document Version.

4. A Processing Run is created with a Configuration Snapshot.

5. The document is parsed, normalized, chunked, embedded, and indexed.

6. Processing and indexing counts are verified.

7. The Document Version becomes active for retrieval.

8. The Data Monitoring page displays the Document, Version, Run, configuration, and Index relationships.

9. A Query User submits a compliance question.

10. The system returns ranked, governance-compliant evidence with provenance.

11. A Golden Evaluation Dataset is executed against the same index.

12. Precision@10, Recall@10, and nDCG@10 are calculated and stored.

13. A candidate configuration is compared with the accepted baseline.

14. The full workflow remains traceable through identifiers, logs, state, and retained artifacts.
```

Equivalent demonstrations must also confirm TXT and Markdown support before final MVP completion.

## 22.40 Unsuccessful Project Conditions

The project should not be considered complete when any of the following remain true:

* source documents exist only inside OpenSearch,
* Document Versions cannot be distinguished,
* processing failures appear as successful ingestion,
* retries create duplicate indexed content,
* the active index configuration is unknown,
* retrieved chunks lack provenance,
* disabled or superseded content appears in normal retrieval,
* retrieval quality is evaluated only manually,
* evaluation results cannot be reproduced,
* configuration values are hardcoded or undocumented,
* secrets exist in the repository,
* the AWS deployment requires undocumented manual steps,
* application containers contain durable workflow state,
* critical workflows lack automated tests.

## 22.41 Project Success Evidence

Project-level completion should be supported by evidence such as:

* deployed application environment,
* successful end-to-end processing records,
* S3 Source Artifacts,
* Document and Version records,
* Processing and Indexing Run history,
* active and candidate indexes,
* inspectable retrieval results,
* versioned Golden Evaluation Dataset,
* stored Evaluation Reports,
* automated test results,
* CloudFormation deployment records,
* container-image references,
* structured logs and audit events.

A verbal statement that a capability works is not sufficient when objective evidence can be produced.

## 22.42 Relationship to Intermediate Deliverables

These Project-Level Success Criteria will later be decomposed into Intermediate Deliverables.

Each deliverable will define:

* its specific outcome,
* included functionality,
* dependencies,
* acceptance evidence,
* Definition of Done.

No individual deliverable is expected to satisfy the entire project success model.

Collectively, the completed deliverables must demonstrate every required project-level criterion.

## 22.43 Relationship to Definition of Done

The Project-Level Success Criteria answer:

> What must the complete MVP achieve?

The Definition of Done will answer:

> What exact technical, functional, testing, documentation, and evidence conditions must be satisfied for each deliverable to be accepted?

For example:

```text
Project-Level Success Criterion
→ Documents must be stored canonically in S3.

Deliverable Definition of Done
→ Specifies required endpoints, identifiers, checksums, tests, failure cases, IAM permissions, logs, and verification evidence.
```

The Project Reference should remain stable while detailed Definition of Done criteria evolve with implementation planning.

## 22.44 Final MVP Completion Boundary

The CVS Review Portal MVP is complete when the system demonstrably provides:

```text
Controlled Document Ingestion
+
Canonical Source Preservation
+
Document and Version Governance
+
Observable Processing and Index State
+
Traceable OpenSearch Retrieval
+
Versioned Golden Evaluation Data
+
Precision@10, Recall@10, and nDCG@10
+
Configuration Reproducibility
+
Baseline Security and Observability
+
Reproducible AWS Deployment
```

Capabilities beyond this boundary should be treated as later extensions unless they become necessary to protect the correctness of the MVP lifecycle.

## 22.45 Project-Level Success Principle

The success model must make it impossible to confuse:

```text
Uploaded
with
Successfully Ingested

Indexed
with
Verified and Active

Returned
with
Relevant

Relevant
with
Complete or Legally Applicable

Metric Calculated
with
Evaluation Reproducible

Container Running
with
System Ready

Feature Demonstrated
with
Feature Production-Disciplined

Many Capabilities
with
Successful MVP
```

CVS Review Portal succeeds when its compliance knowledge base is controlled, observable, traceable, searchable, and objectively measurable—not merely when it can produce plausible search results or AI-generated text.








