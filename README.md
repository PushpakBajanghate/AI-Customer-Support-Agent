# Autonomous AI Customer Support Agent

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2018-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-FF6F00)](https://langchain-ai.github.io/langgraph/)
[![Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Qdrant](https://img.shields.io/badge/Vector%20DB-Qdrant-DC2626)](https://qdrant.tech/)
[![Evaluation Index](https://img.shields.io/badge/Benchmark-91.04%25%20Overall-10B981)](#-evaluation-framework--benchmark-results)

An enterprise-ready, production-minded **Autonomous AI Customer Support Agent** inspired by modern conversational AI platforms such as **Decagon**. Built with strict separation of concerns, deterministic safety gating, relational source-of-truth grounding, RAG corporate policy retrieval, and a comprehensive 12-cohort evaluation framework.

---

## 📌 Table of Contents

- [Project Overview](#-project-overview)
- [The Problem](#-the-problem)
- [The Solution](#-the-solution)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Key Features](#-key-features)
- [Agent Architecture (LangGraph State Machine)](#-agent-architecture-langgraph-state-machine)
- [Database Design](#-database-design)
- [RAG Architecture](#-rag-architecture)
- [Example Customer Conversations](#-example-customer-conversations)
- [API Documentation](#-api-documentation)
- [Environment Variables](#-environment-variables)
- [Setup & Installation](#-setup--installation)
  - [1. Database Seeding](#1-database-seeding)
  - [2. Running the Backend](#2-running-the-backend)
  - [3. Running the Frontend](#3-running-the-frontend)
- [Evaluation Framework & Benchmark Results](#-evaluation-framework--benchmark-results)
- [Portfolio & Interview Demonstration](#-portfolio--interview-demonstration)
- [Future Improvements](#-future-improvements)

---

## 🎯 Project Overview

This project implements an end-to-end, multi-agent AI customer support platform. Unlike demo chatbots that execute blind tool calling or hallucinate customer records, this system grounds every response in real-time **PostgreSQL** relational tables and unstructured **Qdrant / markdown** policy documents. 

A authenticated customer communicates naturally through a modern React chat interface. The backend uses a **LangGraph** multi-agent state machine with distinct node responsibilities:
1. **Router Agent:** Classifies intent into 13 supported categories with confidence scoring.
2. **Support Agent:** Inspects customer order history via read-only tools and resolves references.
3. **Supervisor Gate:** Enforces tenant isolation, verifies policy bounds, and requires customer confirmation before executing state mutations (cancellations, returns, refunds, support tickets).
4. **Escalation Engine:** Automatically routes fraud, policy exceptions, and human agent requests to support tickets.
5. **RAG Node:** Embeds and searches company policy documents (returns, refunds, warranties, shipping) to answer policy inquiries factually.

---

## 🛑 The Problem

Most conversational AI support prototypes suffer from critical architectural flaws:
* **Hallucination & Fabrication:** LLMs invent fake tracking numbers, order statuses, or policy windows.
* **Unsafe Autonomy (Blind Mutation):** An LLM executing tools directly can cancel already-delivered orders, process unauthorized refunds, or perform actions without user confirmation.
* **Multi-Tenant Security Vulnerabilities:** Agents ask customers for their IDs or accept arbitrary order IDs from chat prompts, allowing Customer A to cancel or view Customer B's orders.
* **Brittle Fine-Tuning:** Fine-tuning models on specific support logs embeds obsolete policies into static weights, requiring expensive retraining whenever store policies change.
* **Lack of Observable State:** Monolithic chains do not expose structured routing or intermediate decisions to the frontend or audit logs.

---

## 💡 The Solution

This system adheres to production architecture principles inspired by Decagon:
* **Deterministic Relational Source of Truth:** PostgreSQL is the single source of truth for transactional data. The LLM only proposes actions; ordinary Python validation enforces business rules.
* **Strict JWT Authentication:** The customer ID is extracted exclusively from signed JWT Bearer tokens. The agent **never** asks the customer for their customer ID.
* **Lightweight Supervisor Safety Gate:** Sensitive mutations (`cancel_order`, `create_return`, `create_refund`, `create_support_ticket`) require affirmative customer confirmation ("yes", "confirm", "proceed") and ownership validation before execution.
* **Evaluation Without Fine-Tuning:** The system relies on prompt orchestration, deterministic state graphs, and policy grounding—evaluated on a synthetic 27-scenario benchmark across 12 categories with mathematical metrics.
* **Real-Time Observability:** The API returns structured intent classification, confidence percentages, and action proposals, rendered live in the UI as Decagon-style badges.

---

## 🏛️ System Architecture

```
[ Customer (React 18 + Vite) ]
             │
             │ HTTP (JWT Bearer Token + Message)
             ▼
[ FastAPI Backend (/chat) ]
             │
             ├── Validates JWT & Identifies Customer (PostgreSQL)
             ├── Loads Bounded History (Last 12 messages) & Context
             │
             ▼
[ LangGraph Support Graph (`run_support_graph`) ]
             │
   ┌─────────┴────────────────────────┐
   ▼                                  ▼
[ Router Node ]             [ Escalation Node ]
(Gemini 13-Intent JSON)     (Fraud / Human / Priority Triager)
   │                                  │
   ├─────── Needs Policy? ────────┐   │
   │                              ▼   │
   │                     [ RAG Retrieval Node ]
   │                     (Qdrant Vector / Local Policy Index)
   ▼                              │
[ Support Agent Node ] ◄──────────┘
(PostgreSQL Read Tools:
 Orders, Items, Shipments)
   │
   ├────── Proposes State Mutation? ───┐
   │                                   ▼
   │                         [ Supervisor Safety Gate ]
   │                         (1. Tenant Ownership Check
   │                          2. Policy Window Validation
   │                          3. Customer Confirmation Gate
   │                          4. PostgreSQL Write Tools)
   ▼                                   │
[ Conversational Response Node ] ◄─────┘
             │
             ▼
[ Sanitized HTTP 200 ChatMessageResponse ]
(Message + Intent Badge + Confidence + Action Metadata)
```

---

## 💻 Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 18, Vite, Plain CSS | Interactive customer portal, Decagon-style intent badges, typing indicators, suggestion chips |
| **Backend** | Python 3.10+, FastAPI, Uvicorn | Asynchronous REST API, JWT auth, dependency injection, CORS |
| **Agent Orchestration**| LangGraph 1.2+, LangChain Core | Cyclic state machine, conditional routing, state persistence |
| **LLM Provider** | Google Gemini (`gemini-3.8-flash`) | Intent classification, conversational synthesis, structured JSON extraction |
| **Database** | PostgreSQL, SQLAlchemy ORM | Relational source of truth: customers, orders, shipments, returns, refunds, tickets |
| **Vector DB (RAG)** | Qdrant, Google Embeddings | Semantic policy retrieval (returns, refunds, warranties, shipping policies) |
| **Security** | Python-Jose, Bcrypt | HS256 JWT tokens, 10-round salted password hashing, tenant isolation |
| **Evaluation** | Python `unittest`, Custom Evaluator | 12-category synthetic benchmark, 8 mathematical metrics, Wilson score intervals |

---

## 🌟 Key Features

1. **Autonomous Order Tracking:** Identifies customer shipments, retrieves carriers (DHL Express, FedEx, UPS), and delivers tracking numbers and delivery estimates.
2. **Safe Order Cancellation:** Verifies order status (`processing` only). Delivers a confirmation prompt before calling `cancel_order`. Rejects cancellations for already shipped/delivered orders.
3. **Item Return Validation:** Checks delivery timestamps against product `return_window_days`. Verifies whether a return already exists for the item. Confirms with customer before saving return requests.
4. **Refund Processing:** Checks return completion or order cancellation status before issuing refunds.
5. **RAG Policy Grounding:** Answers store policy and FAQ questions grounded in corporate markdown policies (`return_policy.md`, `warranty_policy.md`, `shipping_policy.md`).
6. **Multi-Tenant Cross-Customer Protection:** Automatically blocks Customer A from querying or altering Customer B's orders, returning a safe `ORDER_NOT_FOUND` response with zero data leakage.
7. **Deterministic Escalation Routing:** Detects fraud keywords ("stolen card", "unauthorized charge"), explicit human requests ("talk to a person"), and policy exception demands, routing them to high-priority support tickets.
8. **Decagon-Style UI Badges:** Live visual feedback displaying classified intent, confidence scores, and safety status chips.

---

## 🤖 Agent Architecture (LangGraph State Machine)

The state graph is defined in `backend/app/agents/graph.py` and coordinates state across 5 primary nodes:

```
START ──► router_node
             │
             ├──► [escalation_needed?] ──► escalation_node ──► supervisor_node ──► END
             │
             ├──► [knowledge_retrieval_needed?] ──► rag_node ──► support_agent_node
             │                                                         │
             │                                              [action proposed?]
             │                                                ├── Yes ──► supervisor_node ──► END
             │                                                └── No  ──► END
             │
             └──► conversational_node ──► END
```

### The 13 Supported Intents
* `ORDER_TRACKING`: Courier tracking and carrier status lookups.
* `ORDER_CANCEL`: Order cancellation with confirmation gating.
* `ORDER_RETURN`: Return eligibility checking and return creation.
* `REFUND_STATUS`: Tracking refund progress on completed returns or cancellations.
* `REFUND_REQUEST`: Requesting a refund for an eligible cancelled order.
* `PRODUCT_INFORMATION`: Product specs, return windows, warranties.
* `DAMAGED_PRODUCT`: Reporting damaged items with expedited return routing.
* `WRONG_PRODUCT`: Reporting incorrect items received.
* `DELIVERY_DELAY`: Inquiring about transit delays or overdue shipments.
* `PAYMENT_ISSUE`: Billing inquiries or failed transactions (escalates on ambiguity).
* `HUMAN_ESCALATION`: Direct customer requests for a human representative.
* `GENERAL_QUESTION`: Broad store questions, hours, contact info.
* `UNKNOWN`: Ambiguous queries triggering clarification or graceful fallback.

---

## 🗄️ Database Design

PostgreSQL serves as the relational source of truth via SQLAlchemy models in `backend/app/models/`:

```
┌──────────────┐       1:N       ┌──────────────┐       1:N       ┌──────────────┐
│  customers   │────────────────►│    orders    │────────────────►│ order_items  │
└──────────────┘                 └──────────────┘                 └──────────────┘
       │                                │                                │
       │ 1:N                            │ 1:1                            │ 1:1
       ▼                                ▼                                ▼
┌──────────────┐                 ┌──────────────┐                 ┌──────────────┐
│support_ticket│                 │  shipments   │                 │   returns    │
└──────────────┘                 └──────────────┘                 └──────────────┘
                                        │                                │
                                        │ 1:N                            │ 1:N
                                        ▼                                ▼
                                 ┌──────────────┐                 ┌──────────────┐
                                 │   refunds    │                 │   products   │
                                 └──────────────┘                 └──────────────┘
```

* **`customers`:** User profile, email, phone, salted bcrypt password hash.
* **`products`:** SKU, name, category, brand, price, `return_window_days`, `warranty_days`.
* **`orders`:** Order date, status (`processing`, `shipped`, `delivered`, `cancelled`), `total_amount`, shipping address.
* **`order_items`:** Line items connecting orders to products with locked purchase prices and quantities.
* **`shipments`:** Courier carrier (`FedEx`, `DHL Express`, `UPS`), tracking code, delivery status, estimated delivery.
* **`returns`:** Item-level return requests with statuses (`requested`, `approved`, `completed`, `rejected`).
* **`refunds`:** Monetary refund amounts and statuses (`pending`, `completed`, `failed`).
* **`support_tickets`:** Customer escalations with priorities (`low`, `medium`, `high`, `urgent`).
* **`conversations` & `conversation_messages`:** Multi-turn conversation persistence.

---

## 🔍 RAG Architecture

Unstructured policy documents live in `data/policies/`:
* `return_policy.md`: 14-30 day window conditions, resalable state requirements.
* `refund_policy.md`: Processing timelines, payment method destination.
* `shipping_policy.md`: Carrier partners, standard and expedited shipping rules.
* `warranty_policy.md`: Manufacturer warranty coverage details.
* `general_faq.md`: Common questions about customer support.

### Hybrid RAG Pipeline:
1. **Semantic Vector Search:** Searches Qdrant collection `support_knowledge` using Google Generative AI embeddings.
2. **Resilient Local Lexical Fallback:** If Qdrant is unavailable, automatically searches policy markdown files using token overlap scoring, ensuring 100% policy grounding without infrastructure dependencies.

---

## 💬 Example Customer Conversations

### 1. Order Tracking
> **Customer:** "Where is my order #104 right now?"  
> **Assistant:** *[Badge: ORDER_TRACKING • 94%]* "I checked your shipment records. Order #104 is in_transit with DHL Express (tracking DHL-104-TRANSIT) with estimated delivery by tomorrow."

### 2. Order Cancellation with Confirmation Gate
> **Customer:** "I want to cancel order #102 please."  
> **Assistant:** *[Badge: ORDER_CANCEL • 94%]* "I have validated your request for order #102 (Arctic Windbreaker Jacket, $85.00, Status: Processing). Please confirm if you want me to proceed with cancelling the order."  
> **Customer:** "Yes, please confirm and cancel order #102."  
> **Assistant:** *[Badge: ORDER_CANCEL • 94%]* "Your cancellation was submitted successfully. Order #102 status has been updated to cancelled."

### 3. Expired Return Window (Policy Compliance)
> **Customer:** "Can I return headphones from order #103?"  
> **Assistant:** *[Badge: ORDER_RETURN • 94%]* "Order #103 was delivered 65 days ago, which exceeds our 30-day return policy window. Unfortunately, this item is no longer eligible for a return."

### 4. Cross-Tenant Security Block (Tenant Isolation)
> **Customer Alice (ID #1):** "Please cancel order #201 right now."  
> *(Order #201 belongs to Bob Jones, ID #2)*  
> **Assistant:** *[Badge: ORDER_CANCEL • 94%]* "I could not find that order in your account. Please verify your order number."  
> *(Zero data leaked; Bob's name and details remain completely shielded).*

### 5. Urgent Fraud Escalation
> **Customer:** "There is an unauthorized fraudulent transaction on my account that is stolen!"  
> **Assistant:** *[Badge: PAYMENT_ISSUE • 94%]* "Your issue has been escalated to a support representative with urgent priority. A specialist will follow up with you immediately to secure your account."

---

## 📡 API Documentation

Interactive OpenAPI / Swagger documentation is available at:  
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Core Endpoints:

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/` | API service health, version, and documentation link | No |
| `GET` | `/health` | Live database connectivity status | No |
| `POST` | `/auth/register` | Register a new customer profile | No |
| `POST` | `/auth/login` | Authenticate customer credentials & receive JWT | No |
| `GET` | `/auth/me` | Fetch authenticated customer profile | Yes (Bearer) |
| `POST` | `/chat` | Send customer message through LangGraph agent pipeline | Yes (Bearer) |

---

## ⚙️ Environment Variables

Create a `.env` file in the project root:

```env
# LLM Provider Configuration
LLM_PROVIDER=gemini
LLM_API_KEY=your_google_gemini_api_key_here
LLM_MODEL=gemini-3.8-flash

# Database Configuration (PostgreSQL source of truth)
DATABASE_URL=postgresql://postgres:root@localhost:5432/customer_support_db

# Vector Database Configuration (Qdrant for RAG)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=support_knowledge

# Authentication Configuration (JWT)
JWT_SECRET_KEY=your_super_secret_jwt_signing_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Application Configuration
APP_ENV=development
API_PORT=8000
API_HOST=0.0.0.0
```

---

## 🚀 Setup & Installation

### Prerequisites
* Python 3.10+ (tested on Python 3.12 and 3.13)
* Node.js v18+ and npm
* PostgreSQL 14+ running locally or in Docker

### 1. Database Seeding

```powershell
# From project root:
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the automated database seed script
python seed.py
```
*Populates 10 synthetic customer profiles, 20 products, 28 orders, shipments, returns, refunds, and support tickets.*

### 2. Running the Backend

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend API online at [http://127.0.0.1:8000](http://127.0.0.1:8000).*

### 3. Running the Frontend

In a separate terminal window:

```powershell
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev -- --host 127.0.0.1 --port 3000
```
*Web application live at [http://127.0.0.1:3000](http://127.0.0.1:3000).*

---

## 🔬 Evaluation Framework & Benchmark Results

The system includes a **multi-dimensional evaluation framework** that evaluates the production agent pipeline without fine-tuning model weights. It tests prompt orchestration, LangGraph state machine routing, read/write tool selection, parameter accuracy, policy compliance, and cross-tenant security isolation against a synthetic evaluation dataset.

### Measured Dimensions & Actual Benchmark Results

All metrics are computed via explicit mathematical formulas with 95% Wilson score confidence intervals:

| # | Operational Measure | Actual Score | 95% Confidence Interval (Wilson Score) | Sample Size | Mathematical Formulation |
|---|---|---|---|---|---|
| 1 | **Intent Accuracy** | **100.00%** | $[87.5\%, 100.0\%]$ | $n=27$ | $A_{\text{intent}} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\hat{y}_i = y_i)$ |
| 2 | **Tool Selection Accuracy** | **85.19%** | $[67.5\%, 94.1\%]$ | $n=27$ | $A_{\text{tool}} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\hat{\tau}_i = \tau_i^*)$ |
| 3 | **Tool Parameter Correctness** | **76.92%** | $[49.7\%, 91.8\%]$ | $n=13$ | $PMR = \frac{1}{\|N_{\text{tool}}\|} \sum \frac{\|\hat{\theta}_i \cap \theta_i^*\|}{\|\theta_i^*\|}$ |
| 4 | **Workflow Completion Rate** | **100.00%** | $[87.5\%, 100.0\%]$ | $n=27$ | $WCR = \frac{1}{N} \sum \mathbb{I}(\text{state}.\text{error} = \emptyset \land \text{response} \neq \emptyset)$ |
| 5 | **Policy Compliance Rate** | **85.19%** | $[67.5\%, 94.1\%]$ | $n=27$ | $PCR = \frac{1}{N} \sum \mathbb{I}(\text{compliant} \land \neg \text{unconfirmed})$ |
| 6 | **Unauthorized Access Prevention** | **100.00%** | $[43.9\%, 100.0\%]$ | $n=3$ | $UAPR = \frac{1}{\|N_{\text{sec}}\|} \sum \mathbb{I}(\text{blocked} \land \neg \text{leak})$ |
| 7 | **Escalation Correctness** | **100.00%** | $[87.5\%, 100.0\%]$ | $n=27$ | $F1_{\text{esc}} = \frac{2 \cdot P \cdot R}{P + R}$ |
| 8 | **Final Response Correctness** | **80.99%** | $[73.5\%, 88.5\%]$ | $n=27$ | $S_{\text{final}} = 0.4 S_{\text{facts}} + 0.4 S_{\text{safety}} + 0.2 S_{\text{tone}}$ |

* **Overall Evaluation Index:** **91.04%**  
* **Statistical Rigor:** 95% binomial confidence bounds computed via the **Wilson score formula**.

### Running the Evaluation Suite:

```powershell
cd backend

# Run the complete evaluation runner (generates ASCII summary table, JSON, and Markdown reports)
python -m app.evaluation.runner

# Run live with Google Gemini API
python -m app.evaluation.runner --mode live

# Run all 30 backend unit tests
python -m unittest discover -s tests -v
```

Generated reports are exported to:
* `reports/evaluation_report.json`
* `reports/evaluation_report.md`

---

## 🎨 Portfolio & Interview Demonstration

An interactive demonstration dashboard is included in the project for technical reviews and portfolio walk-throughs:
* **Interactive Architecture Visualizer:** Click any state node (Router, Escalation, RAG, Support, Supervisor) to inspect its inputs, outputs, and safety invariants.
* **Live Scenario Simulator:** Simulate real workflows (Order Tracking, Cancellation Gating, Return Window Check, RAG Grounding, Fraud Escalation, Cross-Tenant Attack Block) and view real-time execution traces.
* **Benchmark Radar:** View live metrics and confidence intervals.

Open the interactive showcase:
👉 `portfolio_showcase.html` in your browser.

---

## 🔮 Future Improvements

1. **Streaming Tokens via WebSockets / SSE:** Stream agent responses token-by-token to enhance user engagement.
2. **Multi-Modal Visual Support:** Allow customers to upload photos of damaged goods; use Gemini Vision to inspect damage severity automatically.
3. **Omnichannel Webhooks:** Integrate with Zendesk, Intercom, or WhatsApp Business API.
4. **Automated Return Shipping Labels:** Connect with carrier APIs (EasyPost, FedEx Web Services) to generate printable PDF return labels dynamically.

---

## 📄 License & Attribution

Developed as an educational and production-minded architecture demonstration by Pushpak Bajanghate.  
Inspired by enterprise customer support architectures (Decagon). Open-sourced under the MIT License.
