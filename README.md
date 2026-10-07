# SQLens — AI-Powered Conversational Database Intelligence System

SQLens is an enterprise-grade, conversational database intelligence platform that converts natural-language questions into secure, read-only SQL queries, executes them safely against PostgreSQL schemas, visualizes results automatically with dynamic charts, and produces grounded AI insights.

---

## 🏗️ Architecture & Data Flow

```
[ User Question ]
       │
       ▼
[ Intent Understanding Layer ] ◄─── (Cached Schema Selector)
       │
       ├──► [ Smart Clarification Engine ] (If Ambiguous)
       │
       ▼
[ Text-to-SQL Generation Engine ]
       │
       ▼
[ SQL Validation & Security Engine ] ◄── MANDATORY SECURITY BOUNDARY
       │   ├── SQLGlot AST Parser (Read-only SELECT guard)
       │   ├── Schema Boundary & CTE Security Checks
       │   └── System Schema / DDL Injection Rejection
       ▼
[ Safe Database Execution Service ] (PostgreSQL isolated schemas / SQLite fallback)
       │
       ├──► [ Result Table ] (Instant UI Render ~15-50ms)
       ├──► [ Deterministic Chart Engine ] (Bar, Line, KPI, Scatter)
       └──► [ Async AI Insights ] (Grounded on returned rows)
       │
       ▼
[ Dataset-Isolated Query History ]
```

---

## 🌟 Key Features

1. **Multi-Format Dataset Ingestion & Schema Discovery**:
   - Ingests CSV, Excel (`.xlsx`), and SQLite databases into PostgreSQL isolated schemas (`search_path`).
   - Automatically computes table structures, primary keys, foreign key constraints, and column statistics.

2. **Schema Engine & Explorer**:
   - High-performance cached metadata selector that dynamically feeds relevant schema fragments to Gemini while shielding raw dataset contents.

3. **Phase 5 Intent & Smart Clarification Engine**:
   - Multi-round clarification flow that detects ambiguous terms (e.g. *"best customers"*, *"top performance"*) and presents schema-grounded interpretation choices.

4. **Phase 6 Text-to-SQL Generation**:
   - Produces read-only PostgreSQL SELECT queries using schema constraints and extracted intent models.

5. **Phase 7 Mandatory SQL Security Boundary**:
   - Evaluates SQL via AST parsing (`sqlglot`), blocking multi-statement execution, DDL/DML mutation attempts, CTE loops, system schema queries (`pg_catalog`, `information_schema`), and cross-dataset boundary violations.
   - **Enforced on every query execution AND historical re-run**.

6. **Phase 8 Execution, Visualizations & Insights**:
   - 15-second timeout and 1000-row result truncation safeguards.
   - Deterministic chart engine (Bar, Line, KPI, Scatter).
   - Grounded AI insights generated strictly from returned result rows using `gemini-3.5-flash-lite`.

7. **Phase 9 Conversational Experience & Query History**:
   - Context-aware follow-up engine that refines intent across conversation turns (e.g., *"Show revenue by region"* → *"What about only 2026?"*).
   - Dataset-isolated query history with search, pagination, single-item deletion, and safe Phase 7 re-runs.

8. **Phase 10 Performance Optimization & Non-Blocking Insights**:
   - Asynchronous, non-blocking AI insight loading: Result Tables and Recharts Visuals render **immediately** without waiting for text generation.

---

## 🛠️ Technology Stack

- **Frontend**: React + TypeScript + Vite + Tailwind CSS + Recharts + Lucide Icons
- **Backend**: Python + FastAPI + SQLAlchemy + Pydantic v2
- **Database**: PostgreSQL (with local SQLite fallback for testing)
- **SQL Parser & Security Engine**: SQLGlot
- **AI / LLM Integration**: Official Google GenAI SDK (`gemini-3.5-flash-lite`)

---

## 🚀 Quick Start Guide

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- PostgreSQL (or local SQLite fallback)
- Gemini API Key

---

### Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp ../.env.example .env
# Edit .env and set GEMINI_API_KEY="your_api_key_here"

# 5. Start backend development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Backend API will run on `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

---

### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start Vite development server
npm run dev
```
- Frontend Web App will run on `http://localhost:5173`

---

## 🧪 Testing Suite

### Run Backend Unit & Integration Tests (38 tests)
```bash
cd backend
venv/bin/pytest -v tests
```

### Run Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 🔒 Security Architecture

- **Zero Direct Execution**: User natural language input is NEVER passed directly to database engines.
- **Mandatory Re-Validation**: Re-running any query stored in history re-triggers full Phase 7 security validation.
- **Read-Only Scope**: Only single `SELECT` statements (or safe `WITH` CTEs resolving to `SELECT`) are permitted.
- **Credential Protection**: Gemini API keys and database credentials strictly reside in backend `.env` variables and are never transmitted to the client browser.
