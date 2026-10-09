# Architectural Decision Records (ADR)

This document tracks all architectural decisions, technology selections, trade-offs, limitations, and future improvements for the AI Customer Support Agent application.

---

## Record 011: Lightweight Supervisor Safety Gate

**Date:** 2026-10-09
**Status:** Accepted

The system has three focused agent roles:

- **Router Agent = intent.** It classifies what the customer wants and selects
  the workflow without accessing transactional data or executing actions.
- **Support Agent = reasoning/workflow.** It uses customer context, history,
  RAG policy context, and read tools to identify the relevant record and build
  a requested action when needed.
- **Supervisor Agent = safety/validation.** It runs only for requested state
  changes. It verifies the authenticated customer, ownership, action and policy
  eligibility, and whether the customer explicitly confirmed the action before
  calling a write tool.

The Supervisor is a small LangGraph node with ordinary Python validation; it is
not a second planning framework. Simple policy questions, order lookups, and
tracking requests do not pass through it. Rejected actions return a structured
reason and no write tool is called. Approved actions return the backend tool
result to the customer flow.

This preserves the security boundary: the LLM can reason about a requested
operation, but only the backend Supervisor can approve a validated tool call.

---

## Record 012: Human Escalation Rules and Conversation Preservation

Human escalation is a deterministic graph decision before RAG or ordinary
Support Agent handling. It triggers for explicit human-support requests,
suspected fraud, policy exceptions, repeated tool failures, low-confidence or
unsupported requests, and ambiguous payment state. Simple policy questions and
read-only order lookups do not escalate.

The escalation node creates a structured support-ticket action. The Supervisor
verifies the authenticated customer and invokes the backend ticket tool with
the current conversation id, issue reason, customer message summary, and a
priority derived from severity. Fraud and ambiguous payment cases are urgent;
human requests and policy exceptions are high priority; unresolved unsupported
requests are medium priority.

The ticket stores the conversation id rather than copying an unbounded
transcript. The human agent can load the persisted conversation and messages
using that link, preserving context without sending the entire history to the
LLM. The customer-facing success response is emitted only after the validated
ticket tool succeeds.

---

## Record 009: Simple Backend Tool Design and Ownership Security

**Date:** 2026-10-09
**Status:** Accepted

### Tool design

Support operations are ordinary Python functions in `app.tools.support`. They
return small structured results (`ok`, an error code when rejected, and data
when successful). Read tools cover customer orders, a single owned order,
tracking, products, return eligibility, and refund status. Write tools cover
eligible cancellation, return creation, refund creation, and support tickets.

The LLM never receives a database session and never executes SQL. Backend
orchestration invokes tools and passes their structured result back to the
Support Agent. No MCP server, microservice, or additional tool framework is
introduced.

### Security decisions

Every order lookup filters by both `order_id` and the authenticated
`customer_id`. Order-item, return, refund, cancellation, and tracking tools
reuse that ownership check, so one customer cannot access or mutate another
customer's order. Product lookup is public catalog data; ticket creation first
verifies that the customer exists.

Write validation rejects orders that are not cancellable, products outside the
configured return window, undelivered orders, missing return reasons, and
orders that are not refund-eligible. Existing returns and refunds are checked
before insertion so the same operation is not duplicated. PostgreSQL remains
the source of truth and the tool commits only after validation succeeds.

---

## Record 008: PostgreSQL Conversation Storage Instead of a Memory Framework

**Date:** 2026-10-09
**Status:** Accepted

We store `conversations` and `conversation_messages` in PostgreSQL. Each
message has the conversation id, role, content, and timestamp, and every
conversation is owned by the authenticated customer.

This is intentionally simple. PostgreSQL is already the system of record for
customer and support data, gives us durable history and ownership checks, and
lets us retrieve a small recent window with ordinary indexed queries. A
separate memory framework would add abstractions, state synchronization, and
another persistence boundary without improving this support workflow.

The application loads only five recent orders, five open returns, five recent
refunds, five open tickets, and the latest twelve conversation messages. This
bounded context is enough to resolve references while keeping prompts small.
The client-provided history is not trusted as the source of memory; history is
loaded by conversation id and customer id from PostgreSQL.

---

## Record 010: PostgreSQL Transactional Truth and Qdrant Knowledge Retrieval

**Date:** 2026-10-09
**Status:** Accepted

PostgreSQL remains the source of truth for mutable, customer-specific data:
orders, order items, shipments, returns, refunds, support tickets, customers,
conversations, and messages. Exact ownership and current status require
relational queries and backend validation, so RAG must never answer questions
such as “Where is my order?” from a vector similarity result.

Qdrant is used only for semantic retrieval over short, checked-in knowledge
documents: return, refund, shipping, warranty, and general FAQ policies. The
graph decides whether retrieval is needed after intent classification. Retrieved
passages are bounded and passed as context; they do not become transactional
records and cannot authorize an action.

For mixed questions, the Support Agent combines both sources: PostgreSQL
provides the owned order/item facts and Qdrant provides the applicable policy.
If Qdrant is unavailable, transactional workflows can still use PostgreSQL and
the agent must not invent policy details.

The implementation uses the existing Qdrant client and embedding provider with
a small ingestion script. No MCP server, microservice, or complex RAG
framework is introduced.

---

## Record 007: Phase 6 Support Agent and Read-Only Tool Boundary

**Date:** 2026-10-09
**Status:** Accepted

### Key decisions

1. Use a conditional LangGraph edge from Router to Support Agent. The Router
   remains responsible only for intent classification; transactional intents
   enter the Support Agent and general/unknown intents retain the conversational
   path. Supervisor orchestration is deferred.

2. Expose seven approved read tools instead of giving the agent database access:
   customer information, recent orders, order items, shipments, returns,
   refunds, and support tickets. Every query is constrained by authenticated
   `customer_id`; order-specific lookups also verify ownership.

3. Resolve product references from database data. Return matching compares
   message terms with real product names/categories. One match is selected
   automatically; multiple matches are shown and require a selection. The
   agent does not ask for an order id when records already identify the order.

4. Keep Phase 6 read-only. No create/cancel/refund/update tool is registered;
   the agent cannot mutate the database or claim an action succeeded.

The Router answers “what kind of help is this?” The Support Agent answers “what
records and information are needed?” Keeping those responsibilities separate
makes authorization and tool use auditable. Action execution and Supervisor
orchestration remain future phases.

---

## Record 006: Phase 5 LangGraph Router Agent (Intent Classification)

**Date:** 2026-10-08  
**Status:** Accepted  

### 1. Context & Motivation
Following Decagon's multi-agent architecture, the first step in handling customer requests is **intent understanding**. A single monolithic LLM prompt that tries to understand intent, query databases, check return eligibility, and execute refunds simultaneously is brittle, error-prone, and hard to audit. Instead, the Router Agent acts as a specialized, low-latency classifier whose **sole responsibility** is determining what the customer wants and routing them to the correct downstream workflow.

### 2. Key Decisions

#### Decision 1: LangGraph as the State Machine Framework
- **Rationale:** LangGraph allows modeling agent workflows as deterministic, cyclical state graphs with explicit state management, node isolation, and conditional edges.
- **Topology (Phase 5):** `START → router_node → conversational_node → END`.
- **Future-proofing:** In Phase 6+, conditional edges will route directly from `router_node` to specialized tool nodes (`order_tracking_node`, `returns_node`, `rag_node`, `escalation_node`) based on the classified intent.

#### Decision 2: Router Agent Scope — Strictly Classification, Zero Business Actions
- **Core Principle:** The Router Agent does NOT query order tables, perform cancellations, issue refunds, or access PostgreSQL business entities.
- **Benefit:** Decouples intent classification from execution. The Router operates fast with minimal token overhead and cannot accidentally trigger unauthorized mutations.
- **Example:** If a customer says *"I want to return my shoes"*, the Router identifies `ORDER_RETURN` with high confidence. It does **NOT** ask *"which shoes?"* at this stage. The downstream Support Agent will look up the customer's active orders in PostgreSQL to find possible matching items automatically.

#### Decision 3: Exhaustive 13-Intent Taxonomy
- The Router classifies into exactly 13 supported intent types:
  `ORDER_TRACKING`, `ORDER_CANCEL`, `ORDER_RETURN`, `REFUND_STATUS`, `REFUND_REQUEST`, `PRODUCT_INFORMATION`, `DAMAGED_PRODUCT`, `WRONG_PRODUCT`, `DELIVERY_DELAY`, `PAYMENT_ISSUE`, `HUMAN_ESCALATION`, `GENERAL_QUESTION`, `UNKNOWN`.
- Validated via Pydantic `IntentType` enum — any unrecognized output from the LLM cleanly falls back to `UNKNOWN`.

#### Decision 4: Structured Output Contract via Gemini
- The Router prompt instructs Google Gemini to respond with a strict JSON object:
  ```json
  {
    "intent": "ORDER_RETURN",
    "confidence": 0.94,
    "needs_clarification": false,
    "required_information": [],
    "acknowledgement": "I understand you'd like to return an item..."
  }
  ```
- All responses are dynamically generated at runtime. No intents, confidence values, or acknowledgements are hardcoded.

#### Decision 5: Context Injection Without Customer Friction
- The Router prompt receives:
  1. `customer_id` and `customer_name` (extracted from JWT token, verified against PostgreSQL)
  2. Current customer message
  3. Conversation history (prior turns in the session)
- The customer is **never** asked for their customer ID or account number.

#### Decision 6: Two-Tier Response Strategy for Efficiency
- For high-confidence classifications ($\ge 0.8$) without clarification needs, the Conversational node uses the Router's acknowledgement directly, avoiding an unnecessary second LLM round-trip.
- For lower confidence or ambiguous queries, the Conversational node generates an intent-guided contextual response.

### 3. Known Limitations (Phase 5)
- The Support Agent tool execution nodes are not yet active (scheduled for Phase 6+).
- Conversation history is currently passed from the React client state; server-side LangGraph checkpointers (PostgreSQL-backed) will be introduced in subsequent phases.

---

## Record 005: Phase 4 Real Dynamic LLM Integration (Google Gemini)

**Date:** 2026-10-08  
**Status:** Accepted  

### 1. Context & Motivation
With frontend UI and backend authentication established, the application requires an active language model connection to answer customer inquiries. The LLM connection must be real, dynamic, secure, and configured strictly via environment variables without hardcoding API keys or mocking conversational responses.

### 2. Key Decisions

#### Decision 1: Gemini Selected as Initial LLM Provider
- **Rationale:** Google Gemini provides high throughput, low latency, extensive context windows, and cost-effective performance for production customer support workloads.
- **Library Selection:** Integrated via `langchain-google-genai` (`ChatGoogleGenerativeAI`), ensuring direct compatibility with upcoming LangGraph multi-agent graphs in Phase 5 and Phase 6.

#### Decision 2: LLM Configuration is Loaded from `.env`
- **Configuration Keys:** `LLM_PROVIDER=gemini`, `LLM_API_KEY=...`, `LLM_MODEL=gemini-1.5-flash` (or `gemini-2.5-flash`, `gemini-3.8-flash`).
- **Flexible Key Aliases:** The configuration loader (`app.config.Settings`) automatically checks `LLM_API_KEY`, `GEMINI_API_KEY`, and `GOOGLE_API_KEY`.

#### Decision 3: API Keys are Never Hardcoded
- Credentials are NEVER placed in source code or committed to Git.
- `.env` is ignored by Git (`.gitignore`). Only `.env.example` with placeholder names is version-controlled.
- Swapping keys, updating models, or rotating credentials requires only modifying `.env` without code changes.

#### Decision 4: API Keys are Never Exposed to the Frontend
- The React frontend communicates strictly with the backend (`POST /chat`) using customer JWT tokens.
- The React application has zero access to and zero knowledge of `LLM_API_KEY` or LLM provider endpoints. All model interactions occur strictly on the FastAPI server side.

#### Decision 5: User Messages Come from the Live React Chat Interface
- No hardcoded messages, scripted conversations, or pre-populated welcome messages exist in the React chat UI.
- All messages sent to the backend originate from real user keystrokes submitted through the chat input field.

#### Decision 6: Assistant Responses Come from the Actual Gemini API
- Every assistant response returned by the backend is dynamically generated by Google Gemini in response to the user's actual runtime prompt.
- Handled transient rate limits (503 retries) and structured content blocks cleanly to ensure continuous live inference.

#### Decision 7: No Fake/Mock Responses are Used
- Hardcoded conversation scripts, dummy echo fallbacks (`if message == ...`), and simulated chat outputs are strictly prohibited.
- When errors occur (e.g. unconfigured key or external API downtime), the backend returns genuine HTTP status codes (`HTTP 500` or `HTTP 502 Bad Gateway`) rather than disguising errors as fake successful replies.

#### Decision 8: PostgreSQL Remains the Source of Truth for Application Data
- Relational e-commerce records (customers, orders, shipments, returns, refunds, tickets) reside exclusively in PostgreSQL.
- Primary key sequences are synchronized to guarantee dynamic database operations succeed.
- Customer authentication state and JWT verification are anchored in PostgreSQL.

#### Decision 9: Phase 4 Does Not Implement Tools or Agents
- Phase 4 focuses solely on verifying the live conversational LLM connection with customer context.
- Tool calling, database mutation tools, policy RAG, and LangGraph router/supervisor agents are intentionally deferred to Phase 5 and subsequent phases.

### 3. Known Limitations (Phase 4)
- Multi-turn conversation state is maintained on the React client side in this phase; server-side graph state checkpointing will be introduced in LangGraph phases.
- Tool calling is intentionally not yet active until customer support tools are built in Phase 8.

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
