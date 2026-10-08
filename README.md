# AI Customer Support Agent

An educational, production-minded AI customer support application inspired by modern customer-support platforms (such as Decagon). Built incrementally with strict separation of concerns, safety-bounded tool execution, and clear relational data modeling.

---

## 📌 Project Overview

This application demonstrates how to build a reliable, enterprise-grade AI customer support assistant. The agent can authenticate customers, resolve policy queries via RAG, check order statuses, process returns/refunds, and escalate edge cases to human agents.

### Core Architectural Principles
1. **Chat Only:** Focused solely on text-based conversational workflows.
2. **Relational Source of Truth:** PostgreSQL stores all transactional data (customers, products, orders, returns, refunds, messages, audit logs).
3. **Dedicated Semantic Search:** Qdrant is used strictly for unstructured policy documents (return, refund, shipping, warranty policies) and FAQs—never for mutable transactional data.
4. **Safety & Tool Execution Boundary:** The LLM *never* directly modifies the database. The LLM only proposes structured tool calls; the backend verifies authorization and business rules before executing any write operations.
5. **Provider Agnostic:** Supports configurable LLM providers via environment variables without vendor lock-in.

---

## 🛠️ Tech Stack

- **Frontend:** React (Vite, JavaScript, Plain CSS)
- **Backend:** Python 3.10+, FastAPI, Uvicorn
- **AI & Orchestration:** LangGraph, LangChain Core
- **Database:** PostgreSQL, SQLAlchemy
- **Vector Search (RAG):** Qdrant
- **Authentication:** JWT (JSON Web Tokens)

---

## 📂 Project Directory Structure

```text
AI-Customer-Support-Agent/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application initialization & endpoints
│   │   ├── config.py        # Environment settings and configuration
│   │   ├── database.py      # SQLAlchemy engine and session dependencies
│   │   ├── models/          # Database models (PostgreSQL)
│   │   ├── schemas/         # Pydantic schemas for request/response validation
│   │   ├── api/             # API routes and controllers
│   │   ├── agents/          # LangGraph workflows and state definitions
│   │   ├── tools/           # Customer support execution tools
│   │   ├── rag/             # Qdrant vector retrieval and policy embeddings
│   │   └── services/        # Business logic, auth, and validation
│   └── requirements.txt     # Python backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Application views
│   │   ├── services/        # Frontend API client
│   │   ├── App.jsx          # Root application component
│   │   ├── index.css        # Clean base styling
│   │   └── main.jsx         # React DOM entrypoint
│   ├── package.json         # Frontend dependencies and scripts
│   ├── vite.config.js       # Vite configuration
│   └── index.html           # HTML template
├── data/
│   ├── customers/           # Synthetic customer datasets
│   ├── products/            # Synthetic product catalog
│   ├── orders/              # Synthetic orders and returns
│   └── policies/            # Company policy markdown documents
├── docs/
│   ├── flow.md              # End-to-end application and data flow documentation
│   └── decision.md          # Architectural Decision Records (ADR)
├── .env.example             # Template for required environment variables
├── .gitignore               # Ignored files (secrets, venvs, node_modules)
└── README.md                # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Node.js (v18+) and npm
- PostgreSQL (or local instance)
- Qdrant (local Docker or cloud)

### 1. Clone & Setup Environment

```bash
git clone https://github.com/PushpakBajanghate/AI-Customer-Support-Agent.git
cd AI-Customer-Support-Agent

# Copy configuration template
cp .env.example .env
```

Edit `.env` to configure your API keys and database credentials.

---

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate a virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed the database with synthetic data
python seed.py

# Run the FastAPI server
uvicorn app.main:app --reload --port 8000
```

The API will be available at [http://localhost:8000](http://localhost:8000) and Swagger documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

---

### 3. Frontend Setup

In a separate terminal:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run Vite development server
npm run dev
```

The web UI will be available at [http://localhost:3000](http://localhost:3000).

---

## 🗺️ Incremental Development Roadmap

- [x] **Phase 0:** Project setup, directory structure, architecture documentation & skeletons
- [x] **Phase 1:** Database models & synthetic commerce data (customers, products, orders, returns)
- [x] **Phase 2:** FastAPI backend & JWT customer authentication
- [x] **Phase 3:** Basic chat interface UI
- [ ] **Phase 4:** Provider-agnostic LLM integration
- [ ] **Phase 5:** Router Agent (intent classification)
- [ ] **Phase 6:** Support Agent (LangGraph workflow)
- [ ] **Phase 7:** Customer context and conversational memory
- [ ] **Phase 8:** Customer-support tools (Order lookup, cancellation, return initiation)
- [ ] **Phase 9:** RAG with Qdrant for policy and FAQ retrieval
- [ ] **Phase 10:** Supervisor & policy safety validation
- [ ] **Phase 11:** Human escalation workflow
- [ ] **Phase 12:** Evaluation & testing suite
- [ ] **Phase 13:** Polish & production deployment

---

## 📖 Architecture & Design Logs

For in-depth architectural flows and decision rationale, refer to:
- [Flow Documentation](docs/flow.md): Message lifecycle, database flows, tool interactions, and phase changelog.
- [Architectural Decisions (ADR)](docs/decision.md): Technology trade-offs, principles, and rationale.
