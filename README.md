# SQLens — Full-Stack AI-Powered Database Intelligence & Natural Language SQL Workspace

> **Technical Interview & System Design Study Guide**  
> This documentation provides a comprehensive, codebase-grounded technical reference for **SQLens**. Every architecture component, prompt flow, security constraint, data pipeline, and API signature described herein corresponds directly to the production implementation.

---

## 📋 Table of Contents
1. [Project Overview](#1-project-overview)
2. [Complete Architecture & System Topology](#2-complete-architecture--system-topology)
3. [Main Components & Module Breakdown](#3-main-components--module-breakdown)
4. [Complete End-to-End Execution Workflow](#4-complete-end-to-end-execution-workflow)
5. [AI Layer & Prompt Architecture](#5-ai-layer--prompt-architecture)
6. [Database Architecture & Dataset Isolation](#6-database-architecture--dataset-isolation)
7. [SQL Security & AST Validation Engine](#7-sql-security--ast-validation-engine)
8. [API Documentation](#8-api-documentation)
9. [Frontend Architecture & UI Subsystems](#9-frontend-architecture--ui-subsystems)
10. [Technology Stack & Architectural Rationale](#10-technology-stack--architectural-rationale)
11. [Deployment & Infrastructure Setup](#11-deployment--infrastructure-setup)
12. [Key Technical Decisions & Trade-Offs](#12-key-technical-decisions--trade-offs)
13. [Error Handling & Resiliency Strategy](#13-error-handling--resiliency-strategy)
14. [Security & Isolation Safeguards](#14-security--isolation-safeguards)
15. [Performance & Scalability Optimization](#15-performance--scalability-optimization)
16. [Testing & Quality Assurance](#16-testing--quality-assurance)
17. [35+ Technical Interview Questions & Model Answers](#17-35-technical-interview-questions--model-answers)

---

## 1. Project Overview

### What is SQLens?
**SQLens** is an enterprise-grade, full-stack AI database intelligence application that translates natural language questions into safe, read-only PostgreSQL queries, executes them against isolated dataset schemas, generates dynamic data visualizations, and synthesizes executive AI summaries.

### Problem Statement
Non-technical business stakeholders, data analysts, and executive teams frequently require real-time database insights but face two key friction points:
1. **Dependency Bottlenecks**: Writing SQL requires engineering expertise or waiting on data teams for report generation.
2. **Security & Reliability Risks**: Direct LLM-to-Database execution (text-to-SQL without validation) suffers from SQL injection vulnerabilities, schema hallucination, non-deterministic outputs, and accidental data mutation (`DROP`, `DELETE`, `UPDATE`).

### Proposed Solution
SQLens introduces a **multi-stage, deterministic AI-to-SQL pipeline** featuring:
- **Phase 1–4 Schema Grounding & Ingestion**: Automated CSV/Excel/SQLite parsing into isolated PostgreSQL schemas with data type normalization and foreign key/relationship inference.
- **Phase 5 Intent Analysis & Ambiguity Detection**: Disambiguates user intent before query creation. Triggers interactive multi-turn clarification cards when queries are underspecified.
- **Phase 6 Text-to-SQL Generation**: Generates targeted SQL grounded strictly in schema tokens.
- **Phase 7 AST Security Validation (SQLGlot Engine)**: Compiles untrusted SQL into an Abstract Syntax Tree (AST) to enforce read-only policies, single-statement constraints, and block system catalog access before database touching.
- **Phase 8 Safe Execution & High-Res Visualization**: Executes read-only queries with strict timeouts, renders dynamic charts, and captures pixel-perfect static images for PDF and Word exports.

### Real-World Use Case
An e-commerce business analyst uploads a 100,000-row `sales_dataset.xlsx`. Using plain English or voice input, they ask:  
*"Which customer segment generated the highest revenue in 2025?"*  
SQLens validates table metadata, confirms intent, generates a read-only `SELECT` query, executes it safely in 18ms, renders a bar chart, summarizes key takeaways, and allows a 1-click export of the exact UI chart to a PDF report.

---

## 2. Complete Architecture & System Topology

SQLens follows a decoupled **Client-Server-AI-Database Architecture**:

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT LAYER                                      |
|  React 18 + TypeScript + Vite + Tailwind CSS (Port 5173)                           |
|  - Ask Your Data Chat Interface       - Voice Input (Web Speech API)               |
|  - Dynamic Recharts (Line/Bar/Area/Pie) - html2canvas (3x High-Res Capture)       |
|  - HTML5 LocalStorage Persistence     - Toast Notification Subsystem              |
+------------------------------------------+----------------------------------------+
                                           | HTTP / REST (Axios)
                                           v
+-----------------------------------------------------------------------------------+
|                                 BACKEND LAYER                                     |
|  FastAPI + Uvicorn + Pydantic v2 (Port 8000)                                      |
|                                                                                   |
|  +---------------------------+  +----------------------------------------------+  |
|  |     Ingestion Service     |  |               Schema Service                 |  |
|  | (CSV, Excel, SQLite, Normal)|  | (Type Inference, FK Analysis, Stats Engine)  |  |
|  +-------------+-------------+  +----------------------+-----------------------+  |
|                |                                       |                          |
|                v                                       v                          |
|  +---------------------------+  +----------------------------------------------+  |
|  |    AI Orchestration Layer |  |           SQL Security Engine                |  |
|  |  (Gemini 3.5 Flash Lite)  |  |   (SQLGlot AST Parsing & Validation)         |  |
|  | - Intent Analysis         |  | - Read-Only AST Enforcement                  |  |
|  | - Ambiguity Detection     |  | - Single-Statement Constraint                |  |
|  | - Schema Selector         |  | - System Catalog & Cross-Schema Shielding    |  |
|  | - Text-to-SQL Generator   |  +----------------------+-----------------------+  |
|  | - Insight Summarizer      |                         |                          |
|  +-------------+-------------+                         |                          |
+----------------|---------------------------------------|--------------------------+
                 |                                       |
                 v                                       v
+----------------------------------+   +--------------------------------------------+
|            AI PROVIDER           |   |              DATABASE ENGINE               |
|   Google Gemini API (google-genai|   |  PostgreSQL / Supabase (or SQLite fallback)|
|   SDK via JSON Schema config)    |   |  - Isolated Schemas: "ds_<id>"             |
|                                  |   |  - System Metadata: sqlens.db / postgres   |
+----------------------------------+   +--------------------------------------------+
```

### Communication Flow Matrix
| From | To | Protocol / Transport | Payload / Format | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | **Backend API** | HTTP / JSON | REST API (`/api/...`) | Dataset uploads, pipeline execution, history, export requests |
| **Backend AI Service** | **Google Gemini** | HTTPS / TLS 1.3 | JSON Schema Structured Outputs (`google-genai` SDK) | Intent extraction, SQL generation, executive insights |
| **Backend Ingestion** | **Database** | SQLAlchemy / psycopg2 | DDL (`CREATE SCHEMA`, `CREATE TABLE`) | Persistent storage of uploaded user datasets |
| **Backend Query Engine** | **Database** | SQLAlchemy Core | DML (`SELECT ...`) | Safe, read-only query execution with 30s timeout |

---

## 3. Main Components & Module Breakdown

### 3.1 Dataset Ingestion Engine
- **Files**:
  - [`backend/app/services/ingestion/ingestion_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ingestion/ingestion_service.py)
  - [`backend/app/services/ingestion/csv_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ingestion/csv_service.py)
  - [`backend/app/services/ingestion/excel_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ingestion/excel_service.py)
  - [`backend/app/services/ingestion/sqlite_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ingestion/sqlite_service.py)
  - [`backend/app/services/ingestion/normalizer.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ingestion/normalizer.py)
- **Purpose**: Parses uploaded raw files (`.csv`, `.xlsx`, `.xls`, `.db`, `.sqlite`), normalizes column/table names into SQL-compliant identifiers, infers strict data types, and persists them into isolated database schemas.
- **Key Methods**: `IngestionService.ingest_file()`, `DataNormalizer.sanitize_identifier()`, `CSVIngestionService.process()`.
- **Input**: Uploaded file buffer + dataset metadata.
- **Output**: Populated database tables in schema `ds_<uuid>` + `Dataset` ORM record.

### 3.2 Schema Discovery & Intelligence Subsystem
- **Files**:
  - [`backend/app/services/schema/schema_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/schema/schema_service.py)
  - [`backend/app/services/schema/metadata_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/schema/metadata_service.py)
  - [`backend/app/services/schema/relationship_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/schema/relationship_service.py)
  - [`backend/app/services/schema/statistics_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/schema/statistics_service.py)
- **Purpose**: Inspects ingested database schemas to discover tables, column data types, null counts, distinct values, auto-infers Primary Key / Foreign Key relationships (via name matching `*_id`), and computes summary metrics.
- **Key Methods**: `SchemaService.get_full_schema()`, `RelationshipService.infer_relationships()`, `StatisticsService.get_table_statistics()`.

### 3.3 AI Service & Intent Orchestration Engine
- **Files**:
  - [`backend/app/services/ai/ai_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ai/ai_service.py)
  - [`backend/app/services/ai/gemini_provider.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ai/gemini_provider.py)
  - [`backend/app/services/ai/ambiguity_detector.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ai/ambiguity_detector.py)
  - [`backend/app/services/ai/schema_selector.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ai/schema_selector.py)
  - [`backend/app/services/ai/intent_validator.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ai/intent_validator.py)
  - [`backend/app/services/ai/text_to_sql_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ai/text_to_sql_service.py)
  - [`backend/app/services/ai/insight_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ai/insight_service.py)
- **Purpose**: Interfaces with Google Gemini 3.5 Flash Lite using structured Pydantic response schemas (`response_mime_type="application/json"`). Performs token-filtered schema selection, intent analysis, ambiguity detection, SQL generation, and post-execution executive insights.

### 3.4 SQL Security & AST Validation Engine (Phase 7)
- **File**: [`backend/app/services/ai/sql_validator.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ai/sql_validator.py)
- **Purpose**: Enforces zero-trust database access by parsing AI-generated SQL into a SQLGlot AST *before* database execution.
- **Key Class**: `SQLValidationService.validate_sql(dataset_id, sql, db)`.

### 3.5 Query Execution & Chart Recommendation Engine
- **Files**:
  - [`backend/app/services/query/query_execution_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/query/query_execution_service.py)
  - [`backend/app/services/query/chart_engine.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/query/chart_engine.py)
  - [`backend/app/services/query/query_history_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/query/query_history_service.py)
- **Purpose**: Executes validated SQL queries with a hard 30-second timeout and 1,000-row result cap. Recommends visual chart representations (`line`, `bar`, `area`, `pie`, `kpi`, `scatter`, `none`) based on statistical result characteristics.

### 3.6 Multiformat Export Engine
- **File**: [`backend/app/services/export_service.py`](file:///Users/vineet/Downloads/SQLens/backend/app/services/export_service.py)
- **Purpose**: Generates high-fidelity downloadable reports for CSV, Excel (`openpyxl`), Word (`python-docx`), and PDF (`reportlab`). Embeds base64-encoded high-res UI chart captures statically above result data tables.

---

## 4. Complete End-to-End Execution Workflow

```
[User Uploads File] ──> Ingestion Engine ──> Normalize Identifiers ──> Create Schema "ds_<id>"
                                                                             │
                                                                             v
[AI Insight Summary] <── [Render Chart/Table] <── [Safe Execution] <── [AST Validated?]
        │                                             ▲                      │
        v                                             │ Yes                  │ No
[Export PDF/Word]                               Read-Only SELECT        [Return Security Violation]
```

### Detailed Step-by-Step Breakdown:
1. **File Ingestion**: User uploads a file. `IngestionService` validates file type, sanitizes names (e.g. `Customer Name` $\rightarrow$ `customer_name`), creates isolated PostgreSQL schema `ds_<uuid>`, and populates tables.
2. **Schema Metadata Discovery**: `SchemaService` extracts column data types, null counts, distinct values, and sample values into structured JSON metadata stored in `dataset_tables` and `dataset_columns`.
3. **User Asks Question**: User types or speaks a natural language question in `QueryWorkspace.tsx`.
4. **Schema Selection & Intent Analysis (Phase 5)**: `SchemaSelector` scores and ranks relevant tables/columns to build a minimal prompt context. `GeminiProvider.analyze_intent()` calls Gemini with `response_schema=IntentAnalysis`.
5. **Ambiguity Detection & Clarification**: `AmbiguityDetector` checks if entity/filter mappings are underspecified. If ambiguous, `needs_clarification=True` returns an interactive `ClarificationCard` to the UI, pausing execution until the user selects an option.
6. **Text-to-SQL Generation (Phase 6)**: Once intent is clear, `TextToSQLService` invokes Gemini (`temperature=0.1`) with schema constraints and relationship context to output a structured `SQLGenerationResult`.
7. **AST Security Validation (Phase 7)**: `SQLValidationService` passes the raw SQL through `sqlglot.parse(sql, read="postgres")`. It enforces a single statement, verifies statement type is `SELECT`/`UNION`/`WITH`, checks AST nodes against forbidden operations (`INSERT`, `UPDATE`, `DROP`, etc.), verifies table existence against `schema_tables`, checks complexity limits (max 10 joins, max 5 CTEs), and blocks system catalogs (`pg_catalog`, `information_schema`).
8. **Safe Query Execution (Phase 8)**: `QueryExecutionService` executes the validated `SELECT` statement in an isolated transaction setting `SET search_path TO "ds_<id>"`. Sets a 30s timeout and truncates output at 1,000 rows.
9. **Visualization & Insight Generation**: `ChartEngine` evaluates output column types to recommend `bar`, `line`, `area`, `pie`, `kpi`, or `none`. Concurrently, `InsightService` passes sample result rows back to Gemini to synthesize an executive summary.
10. **UI Render & Export**: `QueryWorkspace.tsx` displays the `ResultInsightCard`, `ResultChart`, `ResultTable`, and `SQLViewerCard`. Clicking **Export** captures the exact rendered chart container using `html2canvas` at 3x resolution and sends it to `/api/export/pdf` or `/api/export/docx`.

---

## 5. AI Layer & Prompt Architecture

### Gemini SDK Integration
SQLens utilizes the official `google-genai` SDK (`from google import genai`). To guarantee deterministic schema adherence, all AI calls enforce strict JSON mode via `GenerateContentConfig`:

```python
config = types.GenerateContentConfig(
    system_instruction=SYSTEM_INTENT_PROMPT,
    response_mime_type="application/json",
    response_schema=IntentAnalysis,
    temperature=0.1,
    max_output_tokens=2048,
)
```

### Prompt Engineering Pipeline
Prompts are isolated in [`backend/app/services/ai/prompts/`](file:///Users/vineet/Downloads/SQLens/backend/app/services/ai/prompts/):
- **`intent_prompt.py`**: Extracts entities, metrics, filters, grouping, and limit. Identifies ambiguity.
- **`clarification_prompt.py`**: Refines intent when user selects a clarification option.
- **`followup_prompt.py`**: Merges conversational history and previous intent with follow-up questions.
- **`sql_prompt.py`**: Provides PostgreSQL dialect rules, schema definitions, foreign key paths, and explicit instructions to output raw valid SQL without markdown quotes.
- **`insight_prompt.py`**: Constrains LLM to synthesize summaries strictly from returned data rows.

### Hallucination & Invented Column Prevention
1. **Schema Context Grounding**: Only schema tables and columns selected by `SchemaSelector` are passed to Gemini.
2. **Intent Grounding Validation (`IntentValidator`)**: Compares detected entities/columns in `IntentAnalysis` against `schema_tables`. Any entity not present in actual metadata is stripped or flagged.
3. **AST Column Validation (`SQLValidationService`)**: SQLGlot extracts all column AST nodes and checks them against `all_dataset_columns`. Unmatched columns generate warnings or validation rejections.

---

## 6. Database Architecture & Dataset Isolation

```
SQLens Database Engine
├── Metadata / Application Tables (Default Schema: public / main)
│   ├── datasets (id, name, file_type, storage_path, schema_name, row_count, created_at)
│   ├── dataset_tables (id, dataset_id, table_name, row_count, columns_json)
│   ├── dataset_relationships (id, dataset_id, source_table, target_table, constraint_type)
│   └── query_history (id, conversation_id, dataset_id, user_question, generated_sql, status)
│
└── Dataset-Specific Schemas (Multi-Tenant Isolation)
    ├── ds_b0369ae2_49a9_403f... (Schema for Dataset A)
    │   ├── customer_master
    │   └── orders
    └── ds_9f81a7b2_12c4_89de... (Schema for Dataset B)
        └── sales_data
```

### Multitenancy & Schema Isolation Engine
- **PostgreSQL**: When a dataset is uploaded, SQLens executes `CREATE SCHEMA IF NOT EXISTS "ds_<uuid>"`. All dataset tables are created inside this isolated schema namespace. During query execution, SQLens sets `SET search_path TO "ds_<uuid>"`, preventing queries from accessing other datasets or system metadata.
- **SQLite Fallback**: In SQLite mode, tables are created with schema prefixes (e.g. `ds_<uuid>__table_name`), and SQLGlot rewrites table references to match the prefix.

---

## 7. SQL Security & AST Validation Engine

SQLens enforces a **Zero-Trust Security Policy** before any query touches the database.

```
Incoming SQL String
       │
       v
[Length Check (<= 4000)]
       │
       v
[SQLGlot AST Parsing] ──(Parse Error?)──> Reject
       │
       v
[Single Statement Check] ──(Multiple Statements?)──> Reject
       │
       v
[AST Node Blacklist Check] ──(Contains INSERT, DROP, etc.?)──> Reject
       │
       v
[System Catalog Shielding] ──(Access pg_catalog, public, information_schema?)──> Reject
       │
       v
[Cross-Dataset Check] ──(Access other ds_<id> schema?)──> Reject
       │
       v
[Schema Metadata Grounding] ──(Table/Column missing?)──> Reject
       │
       v
[Complexity Limits (Max 10 Joins, Max 5 CTEs)] ──(Exceeded?)──> Reject
       │
       v
APPROVED FOR READ-ONLY EXECUTION
```

### AST Security Rules Summary:
1. **Length Cap**: Max 4,000 characters.
2. **Single Statement Constraint**: Rejects multi-statement queries separated by semicolons (`SELECT 1; DROP TABLE users;`).
3. **AST Node Blacklist**: Rejects any AST node of type `Insert`, `Update`, `Delete`, `Drop`, `Create`, `Alter`, `Merge`, `Copy`, `Command`.
4. **Statement Type Whitelist**: Accepts ONLY `exp.Select`, `exp.Union`, `exp.With`.
5. **System Schema Shielding**: Hard blocks `pg_catalog`, `information_schema`, `pg_toast`, `public`.
6. **Cross-Dataset Isolation**: Blocks references to schemas other than the target `ds_<uuid>`.
7. **Complexity Caps**: Maximum 10 `JOIN` operations, maximum 5 `CTE` definitions, maximum 5 `UNION` operations.

---

## 8. API Documentation

### 1. Upload Dataset
- **POST** `/api/datasets/upload`
- **Purpose**: Uploads a CSV, Excel, or SQLite file, normalizes schema, creates DB tables.
- **Request**: `multipart/form-data` (`file: UploadFile`)
- **Response**: `UploadResponse` (`dataset_id`, `name`, `tables`, `row_count`, `message`)

### 2. Analyze Question Intent (Phase 5)
- **POST** `/api/ai/analyze`
- **Purpose**: Extracts query intent, entities, metrics, filters, and ambiguity status.
- **Request**: `AIAnalysisRequest` (`dataset_id`, `question`, `clarification_round`)
- **Response**: `AIAnalysisResponse` (`status`, `analysis`: `IntentAnalysis`)

### 3. Submit Intent Clarification
- **POST** `/api/ai/clarify`
- **Purpose**: Submits user-selected option from `ClarificationCard` to refine query intent.
- **Request**: `AIClarificationRequest` (`dataset_id`, `original_question`, `clarification`)
- **Response**: `AIAnalysisResponse` (`analysis`: `IntentAnalysis` with `needs_clarification=False`)

### 4. Generate SQL (Phase 6)
- **POST** `/api/ai/generate-sql`
- **Purpose**: Generates PostgreSQL query based on schema and Phase 5 intent.
- **Request**: `SQLGenerationRequest` (`dataset_id`, `question`, `intent`)
- **Response**: `SQLGenerationResponse` (`sql_result`: `SQLGenerationResult`)

### 5. Validate SQL AST (Phase 7)
- **POST** `/api/ai/validate-sql`
- **Purpose**: Performs AST security validation using SQLGlot without database execution.
- **Request**: `SQLValidationRequest` (`dataset_id`, `sql`)
- **Response**: `SQLValidationResponse` (`valid`: `bool`, `errors`, `warnings`, `tables_used`)

### 6. Full Analysis & Execution (Phase 8)
- **POST** `/api/query/full-analysis`
- **Purpose**: Executes validated SQL, recommends charts, logs query history, generates AI insights.
- **Request**: `FullAnalysisRequest` (`dataset_id`, `question`, `sql`, `intent`, `conversation_id`)
- **Response**: `FullQueryAnalysisResponse` (`execution`, `chart`, `insight`, `validation`)

### 7. Multiformat Export
- **POST** `/api/export/{excel|docx|pdf}`
- **Purpose**: Generates downloadable binary report embedding base64 high-res static UI chart capture.
- **Request**: `ExportRequest` (`columns`, `rows`, `question`, `insight`, `include_visualization`, `chart_image_base64`)
- **Response**: File stream (`application/pdf`, `application/vnd.openxmlformats-officedocument...`)

---

## 9. Frontend Architecture & UI Subsystems

The frontend is built with **React 18 + TypeScript + Vite + Tailwind CSS**.

### Key UI Subsystems:
1. **Ask Your Data Workspace (`QueryWorkspace.tsx`)**:
   - Conversational AI interface supporting multi-turn threads, sample prompts derived dynamically from active schema, collapsible read-only SQL viewer (`SQLViewerCard.tsx`), and error banners.
2. **Interactive Clarification Card (`ClarificationCard.tsx`)**:
   - Renders when `needs_clarification=True`. Presents radio buttons for user option selection.
3. **Voice Input Subsystem (`VoiceInputButton.tsx`)**:
   - Leverages Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`).
   - Translates speech to text in real-time directly into the question input field.
   - **Does NOT auto-submit** to prevent transcription errors from triggering query execution.
   - Provides animated pulse recording states and error toast notifications.
4. **Dynamic Chart Rendering (`ResultChart.tsx`)**:
   - Built on `recharts`. Supports `LineChart`, `BarChart`, `AreaChart`, `PieChart`, and `KPI` summary cards.
5. **Exact UI Chart Capture Export (`ExportControl.tsx` & `exportService.ts`)**:
   - Captures the exact rendered chart DOM element using `html2canvas` at **3x retina scale**.
   - Sends PNG data URL (`chart_image_base64`) to backend PDF/Word export endpoints.
   - CSV and Excel exports are strictly table-only.
6. **Conversation State Persistence**:
   - Active chat turns persist in `localStorage` under `sqlens_active_conv_<datasetId>`, preserving conversation history across view/tab navigation.

---

## 10. Technology Stack & Architectural Rationale

| Technology | Role | Why Chosen over Alternatives |
| :--- | :--- | :--- |
| **FastAPI** | Backend Framework | High-performance async I/O, native Pydantic v2 validation, automatic OpenAPI doc generation. |
| **React 18 + Vite** | Frontend Framework | Lightning-fast HMR, component modularity, type safety with TypeScript, fast production builds. |
| **Google Gemini 3.5 Flash Lite** | LLM Engine | Ultra-fast inference, high text-to-SQL accuracy, native JSON Schema structured output support via `google-genai` SDK. |
| **SQLGlot** | SQL Security Engine | True AST parsing engine for Python. Superior to regex matching or LLM self-validation for enforcing read-only policies. |
| **PostgreSQL / Supabase** | Primary Database | Robust multi-schema support (`CREATE SCHEMA`), JSONB indexing, enterprise reliability. |
| **SQLite (SQLAlchemy Fallback)** | Local Storage Fallback | Zero-configuration local database capability. Enables SQLens to run immediately out-of-the-box without cloud setup. |
| **Recharts** | Data Visualization | Composability, React-native responsive container support, smooth animations. |
| **html2canvas** | Export Chart Capture | Captures actual rendered UI chart DOM node at 3x DPI rather than re-generating charts on backend with matplotlib. |
| **ReportLab & python-docx** | Document Generation | Programmatic, precise PDF and Word document formatting with embedded inline image support. |

---

## 11. Deployment & Infrastructure Setup

### Current / Intended Architecture
- **Frontend**: Deployed on **Vercel** (`vercel.json` configured for SPA routing).
- **Backend API**: Deployed on **Render / Railway / Docker** running Uvicorn (`uvicorn app.main:app`).
- **Database**: **Supabase PostgreSQL** via IPv4 Connection Pooler (`DATABASE_URL=postgresql://postgres.<ref>:<pass>@aws-0-<region>.pooler.supabase.com:6543/postgres`).
- **AI**: Google Gemini API via `GEMINI_API_KEY`.

---

## 12. Key Technical Decisions & Trade-Offs

### 1. Two-Stage Intent Analysis vs. Direct Text-to-SQL
- **Decision**: Separate Phase 5 Intent Analysis from Phase 6 Text-to-SQL Generation.
- **Trade-off**: Slightly higher latency (2 LLM calls), but prevents wrong SQL generation, enables ambiguity detection, and allows user clarification *before* SQL construction.

### 2. AST Validation (SQLGlot) vs. LLM Self-Validation
- **Decision**: Use a deterministic Python AST parser (SQLGlot) instead of asking the LLM "Is this query safe?".
- **Trade-off**: Requires strict maintenance of AST rules, but provides 100% mathematical guarantee against DDL/DML mutation and system schema leakage.

### 3. Client-Side DOM Capture for Report Exports vs. Backend Chart Generation
- **Decision**: Use `html2canvas` at 3x scale in the browser to capture the exact rendered Recharts DOM element.
- **Trade-off**: Transmits base64 PNG over HTTP payload, but guarantees exported charts look **100% identical** to the UI screen (theme, colors, fonts, legends).

---

## 13. Error Handling & Resiliency Strategy

| Failure Scenario | Catching Mechanism | User Experience / Fallback |
| :--- | :--- | :--- |
| **PostgreSQL Down / Disconnected** | `create_app_engine()` in `database.py` | Automatically falls back to local SQLite `sqlens.db`. |
| **Gemini API Key Missing/Invalid** | `GeminiProvider.test_connection()` | Displays warning in UI; fallback to basic SQL templates. |
| **Ambiguous User Question** | `AmbiguityDetector` in Phase 5 | Renders interactive `ClarificationCard` with explicit options. |
| **Unsafe SQL (`DROP`, `DELETE`)** | `SQLValidationService` (SQLGlot AST) | Rejects execution; returns `Security Violation` badge with AST error. |
| **Long-running Query (>30s)** | `QueryExecutionService` (async timeout) | Terminates query thread; returns execution timeout notification. |
| **Unsupported Browser Voice API** | `VoiceInputButton` feature detection | Shows toast: `"Voice input is not supported in this browser."` Text input unaffected. |

---

## 14. Security & Isolation Safeguards

1. **Read-Only Transaction Policy**: All executed queries run in `SELECT`-only mode.
2. **Schema Isolation**: Each uploaded dataset lives in an isolated PostgreSQL schema `ds_<uuid>`.
3. **System Schema Shielding**: Queries targeting `pg_catalog`, `information_schema`, `public`, or `pg_toast` are blocked by AST analysis.
4. **No Raw String Concatenation**: SQL queries are generated via structured LLM grounding and sanitized before AST parsing.
5. **CORS Security**: Backend configures explicit `allow_origins` and regex matching for authorized domains.
6. **Secret Masking**: Sensitive keys (`GEMINI_API_KEY`, `DATABASE_URL`) are loaded exclusively from `.env` and excluded from git repositories via `.gitignore`.

---

## 15. Performance & Scalability Optimization

1. **Token Optimization (`SchemaSelector`)**: Instead of dumping 50+ tables into the LLM prompt, `SchemaSelector` filters and ranks only relevant tables and columns based on query keywords.
2. **Result Truncation**: Query results are capped at 1,000 rows (`truncated=True`) to prevent memory overflow.
3. **High-Res Canvas Exporting**: `html2canvas` uses `scale: 3` for vector-like clarity without requiring backend rendering engines.
4. **Async Non-Blocking Architecture**: FastAPI async endpoints prevent thread blocking during long-running LLM API calls.

---

## 16. Testing & Quality Assurance

The backend includes a comprehensive **pytest** test suite in `backend/tests/`:
- **`test_ai_service.py`**: Validates Gemini provider initialization and prompt formatting.
- **`test_sql_validator.py`**: Tests AST security rules against 20+ safe and malicious SQL payloads.
- **`test_ingestion.py`**: Tests CSV, Excel, and SQLite file parsing and type inference.
- **`test_query_execution_service.py`**: Verifies read-only execution, timeout enforcement, and row caps.
- **`test_export_service.py`**: Verifies Excel, Word, and PDF report generation with base64 image payloads.

Run tests via terminal:
```bash
cd backend
venv/bin/pytest
```

---

## 17. 35+ Technical Interview Questions & Model Answers

### Q1: What is the core problem SQLens solves?
**Answer**: SQLens bridges the gap between natural language questions and database insights for non-technical stakeholders while solving the critical security and accuracy risks of unvalidated LLM text-to-SQL generation.

### Q2: Why did you choose FastAPI over Flask or Django?
**Answer**: FastAPI provides native async support (`async/await`), high throughput with Uvicorn, automatic Pydantic v2 data validation, and automated OpenAPI documentation, making it ideal for AI orchestration pipelines.

### Q3: Why PostgreSQL over MySQL or MongoDB?
**Answer**: PostgreSQL offers robust schema isolation (`CREATE SCHEMA`), rich data types, JSONB support, and strict ANSI SQL compliance required for complex analytical queries.

### Q4: How does SQLens handle dataset isolation?
**Answer**: Every uploaded dataset is assigned a UUID and stored in a separate PostgreSQL schema (e.g. `ds_b0369ae2...`). Queries are executed with `SET search_path TO "ds_<uuid>"`, preventing cross-dataset data access.

### Q5: What happens if PostgreSQL is unavailable when the app starts?
**Answer**: `create_app_engine()` in `database.py` catches the connection failure and gracefully falls back to a local SQLite database (`sqlite:///./sqlens.db`).

### Q6: Why Gemini 3.5 Flash Lite instead of GPT-4o or Claude?
**Answer**: Gemini 3.5 Flash Lite offers extremely low latency, cost efficiency, and native support for JSON Schema structured outputs (`response_mime_type="application/json"`) via the official `google-genai` SDK.

### Q7: How does SQLens prevent LLM hallucinations (invented columns/tables)?
**Answer**: Through a 3-layer defense:
1. `SchemaSelector` filters prompt context to actual dataset metadata.
2. `IntentValidator` compares detected intent entities against schema tables/columns.
3. `SQLValidationService` parses the AST and verifies all column nodes against database metadata.

### Q8: How does SQL security validation work in SQLens?
**Answer**: `SQLValidationService` uses SQLGlot to parse the query into an AST *before* database execution. It enforces single-statement execution, blocks forbidden AST nodes (`INSERT`, `UPDATE`, `DROP`, `DELETE`), checks table existence, limits join count (max 10), and blocks access to system schemas (`pg_catalog`, `information_schema`).

### Q9: Why use AST parsing with SQLGlot instead of Regex or LLM verification?
**Answer**: Regex can be bypassed by comments, whitespace, nested subqueries, or obfuscated SQL. LLMs are non-deterministic and can be jailbroken. AST parsing provides 100% deterministic, structural validation of the query grammar.

### Q10: What happens if a user asks an ambiguous question?
**Answer**: Phase 5 Intent Analysis detects missing entities or underspecified filters. `AmbiguityDetector` sets `needs_clarification=True` and returns a structured `ClarificationCard` with explicit options to the user before generating SQL.

### Q11: Does speech recognition automatically execute the query?
**Answer**: No. `VoiceInputButton` uses Web Speech API to convert speech to text and populates the text input field only. The user must review the transcription and manually click **Ask**, preventing accidental execution from misheard speech.

### Q12: How does the chart export functionality work?
**Answer**: When exporting to PDF or Word, `ExportControl.tsx` uses `html2canvas` to capture the rendered Recharts DOM container at 3x retina scale. The resulting PNG base64 string is sent to the backend, where `reportlab` (PDF) or `python-docx` (Word) embeds it directly into the generated document.

### Q13: Why use client-side canvas capture for exports instead of backend chart generation?
**Answer**: Client-side capture guarantees that the exported report image matches the UI screen **100% pixel-for-pixel** (including active theme, font sizing, legends, and colors) without re-implementing chart rendering logic in Python.

### Q14: How does conversation history persist across tab/page navigation?
**Answer**: Active conversation turns are stored in `localStorage` under `sqlens_active_conv_<datasetId>`. When the user returns to the dataset's Ask Your Data tab, the state is reloaded immediately.

### Q15: How does file ingestion infer column data types?
**Answer**: `DataNormalizer` parses columns using Pandas and custom type-inference rules, mapping values to Integer, Float, Boolean, DateTime, or Text types before creating SQLAlchemy table columns.

### Q16: How does relationship discovery work for multi-table datasets?
**Answer**: `RelationshipService` analyzes primary keys and foreign key naming conventions (e.g. `customer_id` in `orders` matching `customer_id` in `customers`) and infers `ONE_TO_MANY` or `MANY_TO_ONE` relationships.

### Q17: What limits are placed on query execution?
**Answer**: Queries have a hard 30-second timeout to prevent DB blocking, and result rows are truncated at 1,000 records to protect frontend memory.

### Q18: What is the purpose of `SQLViewerCard.tsx`?
**Answer**: It displays the generated PostgreSQL query, its security validation status badge (`Security Approved`), an explanation of the query, and dialect metadata in a collapsible UI card.

### Q19: How are CSV exports formatted for Excel compatibility?
**Answer**: `exportCSV` prepends a UTF-8 BOM (`\uFEFF`) to the CSV string, ensuring Excel opens special characters and UTF-8 encoding correctly.

### Q20: How does follow-up query processing work?
**Answer**: `FollowupService` passes the follow-up question along with the previous turn's intent and SQL context to Gemini, allowing stateful multi-turn analytical conversations.

### Q21: What is the role of `Pydantic` in SQLens?
**Answer**: Pydantic v2 defines strict data models for API requests/responses (`schemas/ai.py`, `schemas/dataset.py`) and serves as the JSON Schema structure enforced during Gemini LLM generation.

### Q22: Why use `html2canvas` scale factor 3?
**Answer**: A scale factor of 3 renders the canvas at 3x retina resolution, ensuring text, lines, and chart borders remain sharp when zoomed in PDF and Word documents.

### Q23: How does SQLens block SQL injection attacks?
**Answer**: 
1. Queries are generated by structured LLMs, not string concatenation.
2. SQLGlot AST parsing rejects malicious syntax, multiple statements, and DDL/DML statements.
3. Execution runs strictly in read-only transactions.

### Q24: What happens if a user uploads an invalid file format?
**Answer**: `IngestionService` validates file extensions and magic headers. If unsupported, it raises an HTTP 400 exception: `"Unsupported file format. SQLens accepts CSV, Excel (.xlsx/.xls), and SQLite (.db/.sqlite) files."`

### Q25: How does `ChartEngine` choose chart types?
**Answer**: It evaluates result columns:
- 1 numeric column $\rightarrow$ KPI Card
- Temporal/Date X-axis + Numeric Y-axis $\rightarrow$ Line/Area Chart
- Categorical X-axis + Numeric Y-axis $\rightarrow$ Bar Chart
- Proportion/Percentage dataset $\rightarrow$ Pie Chart

### Q26: How would you scale SQLens for 100,000 concurrent users?
**Answer**:
1. **Database Read Replicas**: Separate analytical read-queries to PostgreSQL read-replicas.
2. **Celery Worker Queues**: Move ingestion and heavy PDF generation to background Redis/Celery workers.
3. **Caching Layer**: Cache schema metadata and LLM intent analysis in Redis.
4. **Connection Pooling**: Use PgBouncer for efficient PostgreSQL connection reuse.

### Q27: What are the current limitations of SQLens?
**Answer**:
1. Large files (>50MB) ingest synchronously rather than via async background job queues.
2. Voice recognition depends on browser Web Speech API availability.
3. Database fallback to SQLite in local mode does not support PostgreSQL-specific window functions.

### Q28: How are CORS policy origins configured?
**Answer**: In `main.py`, `CORSMiddleware` dynamically matches authorized origins from `settings.CORS_ORIGINS` and regex matches local dev ports (`http://localhost:5173`).

### Q29: What is the role of `Uvicorn` in SQLens?
**Answer**: Uvicorn is an ASGI (Asynchronous Server Gateway Interface) web server implementation for Python, executing FastAPI's asynchronous event loop.

### Q30: How does SQLens handle dataset deletion?
**Answer**: `drop_dataset_schema(schema_name)` drops the dataset schema and all its tables using `DROP SCHEMA "ds_<id>" CASCADE` in PostgreSQL, removing all user data cleanly.

### Q31: Why is `isAnimationActive={!isExporting}` used in Recharts?
**Answer**: Disabling chart animations during export capture ensures `html2canvas` captures the final, fully-rendered static state of lines and bars without capturing mid-animation transitions.

### Q32: How is the database session managed in FastAPI endpoints?
**Answer**: Via the `get_db()` dependency in `database.py`, which yields a SQLAlchemy `SessionLocal()` session per request and automatically closes it in a `finally` block.

### Q33: What is `openpyxl` used for?
**Answer**: `openpyxl` is used in `export_service.py` to programmatically build styled Excel `.xlsx` workbooks with auto-adjusted column widths.

### Q34: What is `reportlab` used for?
**Answer**: `reportlab` is used in `export_service.py` to construct structured PDF documents with custom typography, tables, headers, and embedded base64 chart images.

### Q35: How does SQLens ensure high performance for intent prompt building?
**Answer**: By utilizing `SchemaSelector` to trim unneeded schema tables and columns, keeping prompt token counts minimal and reducing Gemini inference latency.

---

## 🛠️ Setup & Local Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- Google Gemini API Key

### 1. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Configure GEMINI_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
npm install
npm run dev
```

- **Frontend App**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **OpenAPI Docs**: `http://localhost:8000/docs`
