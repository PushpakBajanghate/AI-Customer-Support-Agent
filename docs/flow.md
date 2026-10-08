# Application Flow Documentation

This document describes the operational flow of the AI Customer Support Agent application across its lifecycle. It details the end-to-end user message lifecycle, component interactions, database access, agent orchestration, tool executions, and security boundaries.

---

## High-Level Message Processing Flow (Target Architecture)

When a customer sends a message in the chat interface, the system processes it through a strict, safety-bounded flow:

```
[Customer Browser / React Frontend]
               │  1. Send message with JWT Bearer Token
               ▼
[FastAPI Backend / Auth Middleware]
               │  2. Validate JWT & extract Customer ID
               ▼
[Conversation & Context Service]
               │  3. Fetch Customer Profile & Active Context from PostgreSQL
               ▼
[Router / Supervisor Agent (LangGraph)]
               │  4. Evaluate intent (General question, Policy RAG, or Actionable Tool)
      ┌────────┴──────────────────────────┐
      ▼                                   ▼
[Policy Query -> RAG / Qdrant]    [Action Request -> Support Agent]
      │                                   │
      │ 5a. Retrieve policy text           │ 5b. Propose Tool Call (e.g. create_return)
      │                                   ▼
      │                          [Backend Business Validation & Auth]
      │                                   │ 6. Verify eligibility & execute in PostgreSQL
      │                                   ▼
      └───────────────┬───────────────────┘
                      ▼
[LLM Synthesizes Verified Response]
                      │
                      │ 7. Persist message history & audit log in PostgreSQL
                      ▼
[FastAPI Returns Verified JSON Response to Customer]
```

---

## Detailed Component Lifecycle

### 1. Customer Authentication Flow
- Customer logs in via the React frontend.
- Backend validates credentials against PostgreSQL and issues a signed JWT token.
- Every subsequent HTTP request includes `Authorization: Bearer <token>`.
- The backend FastAPI dependency extracts and verifies the customer identity (`customer_id`), preventing cross-customer data leakage.

### 2. Message Lifecycle
- **Input Received:** FastAPI receives the incoming chat payload (`message`, `conversation_id`).
- **Context Loading:** Backend queries PostgreSQL for recent messages, customer metadata, and order summary.
- **Agent Processing:** LangGraph workflow executes state nodes:
  - Router classifies customer intent.
  - If informational: RAG node queries Qdrant vector store.
  - If transactional: Agent determines required support tool.
- **Safety & Tool Execution Boundary:** The LLM NEVER writes directly to the database. The agent can only emit structured tool calls. Backend service layer performs parameter validation, business logic checks, and executes database changes.
- **Response Synthesis:** The LLM receives the backend tool response and synthesizes a natural, helpful reply.
- **Persistence:** Both customer message and agent response are saved into the PostgreSQL `messages` table.

### 3. Database Flow
- **PostgreSQL** acts as the single source of truth for:
  - Customers, authentication credentials, and profiles
  - Products, inventory, orders, and order items
  - Returns, refunds, and support tickets
  - Conversation histories, message records, and audit logs
- Read-heavy queries fetch current order statuses; write operations occur exclusively through validated backend service functions.

### 4. RAG Flow (Qdrant)
- Qdrant stores vectorized chunks of:
  - Return, refund, warranty, and shipping policies
  - Product specifications and FAQ articles
- Never used for transactional data (e.g. specific order statuses or customer balances).
- Embeddings are generated using the configured embedding model; cosine similarity retrieval returns top-$k$ reference chunks to augment the LLM context.

---

## Phase Changelog

### Phase 0: Initial Foundation & Architecture (2026-10-08)
- **Status:** Completed
- **Changes Introduced:**
  - Initialized clean project repository structure (`backend/`, `frontend/`, `data/`, `docs/`).
  - Created `.env.example` defining provider-agnostic LLM variables, PostgreSQL credentials, Qdrant URLs, and JWT secrets.
  - Created `.gitignore` covering Python, React, build artifacts, and secrets.
  - Set up FastAPI backend skeleton with basic health endpoints (`/`, `/health`) and CORS configuration.
  - Set up React frontend skeleton with Vite and backend health connectivity check.
  - Established data directory structure (`customers`, `products`, `orders`, `policies`).
  - Formulated initial architecture documentation in `docs/flow.md` and `docs/decision.md`.
