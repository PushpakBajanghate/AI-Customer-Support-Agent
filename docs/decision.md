# Architectural Decision Records (ADR)

This document tracks all architectural decisions, technology selections, trade-offs, limitations, and future improvements for the AI Customer Support Agent application.

---

## Record 001: Phase 0 Foundation & Architecture

**Date:** 2026-10-08  
**Status:** Accepted  

### 1. Technology Selection & Rationale

| Layer | Chosen Technology | Rationale | Alternatives Considered |
|---|---|---|---|
| **Frontend** | React (Vite, JavaScript, Plain CSS) | Fast development, readable component hierarchy, high industry standard, accessible to student developers. | Next.js (unnecessary server-side overhead for client-side chat app), Vue (less common in multi-agent reference repos). |
| **Backend** | Python + FastAPI | Native asynchronous handling, automatic OpenAPI/Swagger docs, seamless integration with AI libraries. | Flask (lacks modern async & auto-validation), Django (too heavy and monolithic for an agentic backend). |
| **Orchestration** | LangGraph | Deterministic multi-step state machine workflows with explicit routing, human-in-the-loop readiness, and cyclic capability. | Raw LangChain chains (too rigid for complex branching), AutoGen/CrewAI (excessive autonomous agent chattiness and hard to strictly govern). |
| **Relational DB** | PostgreSQL + SQLAlchemy | ACID compliance, strong relational integrity for orders/customers/returns, robust transactions. | SQLite (good for dev, but PostgreSQL matches production target), MongoDB (not suitable for transactional ecommerce integrity). |
| **Vector DB** | Qdrant | Dedicated high-performance vector search engine, easy local Docker setup or cloud hosting, excellent payload filtering. | ChromaDB (good for toy apps, less production-grade), Pinecone (cloud-only, proprietary vendor lock-in). |
| **Authentication**| JWT (JSON Web Tokens) | Stateless, industry standard for REST APIs, straightforward to understand and test. | Session cookies (stateful across scaling boundaries), OAuth/Auth0 (excessive configuration for educational prototype). |

### 2. Core Architectural Principles

#### Principle 1: Strict Database vs Vector Store Separation
- **PostgreSQL** is the sole source of truth for all transactional business entities: Customers, Products, Orders, Order Items, Shipments, Returns, Refunds, Tickets, Conversations, Messages, and Audit Logs.
- **Qdrant** is solely reserved for semantic similarity search over unstructured policies (Return Policy, Shipping Policy, Warranty FAQ).
- **Rule:** Never duplicate mutable transactional records into the vector database.

#### Principle 2: Safe Tool Execution Boundary (LLM as Reasoner, Backend as Executor)
- The LLM never writes to or executes queries directly against PostgreSQL.
- When an action is required (e.g. `cancel_order`, `create_return`), the LLM requests a structured tool call.
- The FastAPI service layer receives the request, validates customer authorization, enforces business rules (e.g. 30-day return window, order status check), modifies the database, and returns the deterministic result back to the LLM.

#### Principle 3: Provider-Agnostic LLM Configuration
- All provider configurations reside in environment variables (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`).
- No provider is hardcoded in the codebase.

### 3. Known Limitations (Phase 0)
- Database schema and tables have not been created yet (scheduled for Phase 1).
- No actual LLM or agent nodes are running yet (scheduled for Phases 4–6).
- Synthetic data files are placeholders.

### 4. Next Phase Roadmap
- **Phase 1:** Define PostgreSQL SQLAlchemy models and populate initial synthetic ecommerce dataset (10 customers, 20 products, 25-30 orders, returns, refunds, tickets).
- **Phase 2:** Implement FastAPI authentication endpoints and user session handling.
