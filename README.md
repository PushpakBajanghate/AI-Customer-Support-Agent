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
- [x] **Phase 4:** Provider-agnostic LLM integration (Google Gemini)
- [x] **Phase 5:** Router Agent (intent classification with LangGraph)
- [ ] **Phase 6:** Support Agent (LangGraph workflow)
- [ ] **Phase 7:** Customer context and conversational memory
- [ ] **Phase 8:** Customer-support tools (Order lookup, cancellation, return initiation)
- [ ] **Phase 9:** RAG with Qdrant for policy and FAQ retrieval
- [ ] **Phase 10:** Supervisor & policy safety validation
- [ ] **Phase 11:** Human escalation workflow
- [x] **Phase 12:** Evaluation & testing suite (12 categories, 8 dimensions, reports)
- [ ] **Phase 13:** Polish & production deployment

---

## 🔬 Evaluation Framework & Benchmark Results

The project features a **multi-dimensional evaluation framework** that evaluates the production agent pipeline without fine-tuning the underlying model weights. It tests prompt orchestration, LangGraph state machine routing, read/write tool selection, parameter accuracy, policy compliance, and cross-tenant security isolation against a synthetic evaluation dataset.

### Evaluation Cohort (12 Categories)

| # | Test Category | Target Scope |
|---|---|---|
| 1 | **Order Tracking** | Courier tracking, carrier status lookup (`shipments` table) |
| 2 | **Cancellation** | Processing order cancellation and user confirmation gating |
| 3 | **Return** | Return window validation, item matching, return record creation |
| 4 | **Refund** | Refund status tracking and post-cancellation refund processing |
| 5 | **Damaged Product** | Expedited damage return and replacement validation |
| 6 | **Delivery Delay** | Delayed shipment inquiries and carrier tracking checks |
| 7 | **Product Question** | Policy/FAQ knowledge retrieval (return windows, warranties) |
| 8 | **Ambiguous Requests** | Clarification requests and safe bounded fallbacks |
| 9 | **Multi-Intent Requests** | Handling combined queries (e.g. tracking + return inquiry) |
| 10 | **Human Escalation** | Direct human requests, fraud alerts, out-of-policy exceptions |
| 11 | **Unauthorized Access** | Cross-tenant order access rejection and data leakage prevention |
| 12 | **Policy Violations** | Expired return window rejection, ineligible order cancellation |

### Measured Dimensions & Actual Benchmark Results

Performance numbers are derived from executing test scenarios through the complete LangGraph state machine:

| # | Operational Measure | Score | 95% Confidence Interval | Sample Size | Mathematical Formulation |
|---|---|---|---|---|---|
| 1 | **Intent Accuracy** | **100.00%** | [87.5%, 100.0%] | n=27 | $A_{\text{intent}} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\hat{y}_i = y_i)$ |
| 2 | **Tool Selection Accuracy** | **85.19%** | [67.5%, 94.1%] | n=27 | $A_{\text{tool}} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\hat{\tau}_i = \tau_i^*)$ |
| 3 | **Tool Parameter Correctness** | **76.92%** | [49.7%, 91.8%] | n=13 | $PMR = \frac{1}{\|N_{\text{tool}}\|} \sum \frac{\|\hat{\theta}_i \cap \theta_i^*\|}{\|\theta_i^*\|}$ |
| 4 | **Workflow Completion Rate** | **100.00%** | [87.5%, 100.0%] | n=27 | $WCR = \frac{1}{N} \sum \mathbb{I}(\text{state}.\text{error} = \emptyset \land \text{response} \neq \emptyset)$ |
| 5 | **Policy Compliance Rate** | **85.19%** | [67.5%, 94.1%] | n=27 | $PCR = \frac{1}{N} \sum \mathbb{I}(\text{compliant} \land \neg \text{unconfirmed})$ |
| 6 | **Unauthorized Access Prevention** | **100.00%** | [43.9%, 100.0%] | n=3 | $UAPR = \frac{1}{\|N_{\text{sec}}\|} \sum \mathbb{I}(\text{blocked} \land \neg \text{leak})$ |
| 7 | **Escalation Correctness** | **100.00%** | [87.5%, 100.0%] | n=27 | $F1_{\text{esc}} = \frac{2 \cdot P \cdot R}{P + R}$ |
| 8 | **Final Response Correctness** | **80.99%** | [73.5%, 88.5%] | n=27 | $S_{\text{final}} = 0.4 S_{\text{facts}} + 0.4 S_{\text{safety}} + 0.2 S_{\text{tone}}$ |

* **Overall Evaluation Index:** **91.04%**  
* **Statistical Intervals:** 95% binomial confidence bounds computed via the **Wilson score formula**.

### Running the Evaluation Suite

```powershell
cd backend

# Run the complete evaluation runner (outputs ASCII tables, JSON, and Markdown reports)
python -m app.evaluation.runner

# Run live with Google Gemini API
python -m app.evaluation.runner --mode live

# Run unit tests verifying evaluation dataset and mathematical formulas
python -m unittest tests/test_evaluation.py -v
```

Generated reports are exported to:
- `backend/reports/evaluation_report.json`
- `backend/reports/evaluation_report.md`

---

## 📖 Architecture & Design Logs

For in-depth architectural flows and decision rationale, refer to:
- [Flow Documentation](docs/flow.md): Message lifecycle, database flows, tool interactions, and phase changelog.
- [Architectural Decisions (ADR)](docs/decision.md): Technology trade-offs, principles, and rationale.
