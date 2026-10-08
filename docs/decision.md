# Architectural Decision Records (ADR)

This document tracks all architectural decisions, technology selections, trade-offs, limitations, and future improvements for the AI Customer Support Agent application.

---

## Record 004: Phase 3 Chat Interface UI & Client-Server Contract

**Date:** 2026-10-08  
**Status:** Accepted  

### 1. Context & Motivation
An AI support agent application requires a frictionless interface for customers to authenticate, view their current profile status, and converse in real time. Before introducing complex LangGraph multi-agent routing, we must establish a verified client-server communication contract (`POST /chat`) and clean visual primitives (messages, typing state, error state).

### 2. Key Decisions

#### Decision 1: Functional, Lightweight CSS & Component Architecture
- **Rationale:** Built with pure React and clean standard CSS instead of heavy component frameworks (e.g. Material UI, AntD) or utility CSS transpilers (Tailwind).
- **Benefits for Students:**
  - Zero build step complications or CSS framework version mismatches.
  - Every styling property is transparent and directly editable in JavaScript objects / `index.css`.
  - Minimal bundle size (155 kB JS bundle, 0.8 kB CSS).

#### Decision 2: One-Click Demo Account Switching
- **Rationale:** To make testing simple and educational, `LoginPage.jsx` includes quick-select buttons for seeded accounts (`Pushpak Bajanghate`, `Virat Kohli`, `Pranav Tapdiya`).
- **Benefit:** Testers can switch accounts within seconds without having to remember mock emails or re-type passwords.

#### Decision 3: Client-Side Session Hydration
- **Rationale:** JWT tokens and customer profile metadata are preserved in `localStorage`. On page load, `App.jsx` pings `GET /auth/me` to re-validate the token against the backend. If valid, the chat loads immediately; if expired, the storage is wiped and the user is redirected cleanly to `LoginPage`.

#### Decision 4: Phased Chat Contract (`POST /chat`) Before Agent Wiring
- **Rationale:** The `POST /chat` contract was implemented with a placeholder echo response before integrating LangGraph or LLM APIs.
- **Benefit:** Isolates network latency, authorization validation, request/response schema serialization, and UI state management from LLM inference latency. Ensures frontend and backend communication is 100% stable first.

### 3. Known Limitations (Phase 3)
- `POST /chat` currently returns a placeholder response; LangGraph router and support agent nodes will be wired in Phases 4–6.
- Chat history is currently stored in React client state; persistence to PostgreSQL `messages` table will be enabled alongside conversation session management.

---

## Record 003: Phase 2 Authentication & Customer Identity Context

**Date:** 2026-10-08  
**Status:** Accepted  

### 1. Context & Motivation
An AI support agent must understand who is asking a question without ever asking the user: "What is your customer ID?". Furthermore, actions (like order tracking, cancellation, and refund requests) must be cryptographically locked to the caller's identity to prevent unauthorized access across accounts.

### 2. Key Decisions

#### Decision 1: JWT (JSON Web Tokens) with HS256 for Stateless Authentication
- **Rationale:** JWTs allow the React client to make authenticated requests with a standard Bearer token (`Authorization: Bearer <token>`). The token payload contains the verified `customer.id` (in the `sub` claim), email, and expiration time.
- **Alternatives Considered:**
  - *Server-side session cookies:* Requires shared session storage (Redis/database) and CSRF protection headers, adding operational complexity.
  - *OAuth2 with Third-Party Providers (Google/GitHub/Auth0):* Overkill for this educational application, makes local student setup harder without registered app credentials.

#### Decision 2: Bcrypt for Secure One-Way Password Hashing
- **Rationale:** Plaintext passwords are never stored. Bcrypt with 10 salt rounds provides industry-standard brute-force resistance. Direct `bcrypt` usage was selected over legacy wrappers to ensure full compatibility with modern Python runtimes (Python 3.12+ / 3.13).
- **Alternatives Considered:**
  - *PBKDF2/SHA-256:* Faster, but less resistant to GPU-based hardware attacks.
  - *Argon2:* High memory overhead, slightly more complex setup for simple student projects.

#### Decision 3: Dependency-Injected Customer Identity (`get_current_customer`)
- **Rationale:** The FastAPI dependency `get_current_customer` validates the JWT token, decodes the `sub` claim, and fetches the `Customer` record from the database.
- **Agent Integration Principle:** When a customer sends a chat message, the backend extracts `current_customer.id` from the dependency and directly injects it into the LangGraph state/context. The agent therefore has immediate access to the user's order history, active returns, and open tickets—without asking the user to identify themselves.

### 3. Known Limitations (Phase 2)
- Refresh tokens are omitted for simplicity; access tokens have a configurable lifespan (default 60 minutes).
- Chat endpoints and agent graph states are not yet built (scheduled for subsequent phases).

---

## Record 002: Phase 1 Database Schema & Synthetic Commerce Data

**Date:** 2026-10-08  
**Status:** Accepted  

### 1. Context & Motivation
An AI support agent must reason over reliable customer information: past purchases, item specifications, shipment statuses, return eligibility, and payment refunds. We need a clean, structured schema and realistic test data to evaluate agent reasoning and tool executions.

### 2. Key Decisions

#### Decision 1: PostgreSQL Chosen Exclusively for Transactional Data
- **Rationale:** E-commerce operations require ACID guarantees. An order cannot be partially cancelled or refunded. PostgreSQL provides strong relational integrity, foreign key constraints, and transactional rollbacks.
- **Why Qdrant is NOT used for transactional data:**
  1. *Mutability & Consistency:* Order statuses and inventory change rapidly. Vector databases are not designed for frequent updates or transactional locks.
  2. *Exact Matches vs Semantic Similarity:* When looking up "Order #3", the system requires an exact match on `orders.id = 3`, not a cosine-similarity guess.
  3. *Security & Privacy:* Filtering transactional data across vector spaces introduces risks of cross-customer leakage. SQL foreign key constraints ensure strict tenancy filtering by `customer_id`.
  4. *RAG Role Clarification:* Qdrant is strictly reserved for static/semi-static unstructured knowledge (company return policies, shipping FAQs, warranty disclaimers).

#### Decision 2: Schema Design & Normalization Choices
- **Item-Level Returns (`returns.order_item_id`):** Customers typically return a specific product (e.g. ill-fitting shoes) rather than an entire multi-item order. Linking returns to `order_items` enables item-level policy checks against `products.return_window_days`.
- **Decoupled Refunds (`refunds` vs `returns`):** Not every refund originates from a return (e.g. an order cancelled before shipping produces an immediate refund without an item return). Decoupling them allows flexible refund tracking across both cancellations and returns.
- **Single-Table Shipment (`shipments.order_id` unique):** Models 1:1 order fulfillment for simplicity while maintaining carrier tracking info.
- **Plain SQLAlchemy Relationships:** Avoided over-abstracted repository layers; models use standard SQLAlchemy `relationship()` declarations for clear, beginner-friendly readability.

#### Decision 3: Synthetic Dataset Sizing (10 Customers, 20 Products, 28 Orders)
- **Rationale:** Massive datasets make debugging test cases cumbersome and clutter version control. A small, handcrafted dataset of ~10 customers, 20 products, and 28 orders is compact enough to inspect in seconds, yet rich enough to test:
  - Return window expiration (e.g. orders placed 60 days ago vs 3 days ago).
  - Multi-status workflows (`delivered`, `shipped`, `processing`, `cancelled`).
  - Varying refund states (`completed`, `pending`, `failed`).
  - Realistic escalation scenarios via support tickets.

### 3. Known Limitations (Phase 1)
- Passwords are saved as bcrypt hashes in seed data, but FastAPI auth token generation endpoints are not yet wired up (scheduled for Phase 2).
- Direct database seeding is tested and verified; production migration tooling (Alembic) is deferred to deployment phases to avoid premature complexity.

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
