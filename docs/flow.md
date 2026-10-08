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

## Relational Entity Flow (PostgreSQL Source of Truth)

The business logic of the customer support agent follows a clear relational hierarchy:

```
                  ┌─────────────────────┐
                  │      Customer       │
                  │ (id, name, email)   │
                  └──────────┬──────────┘
                             │
            ┌────────────────┴────────────────┐
            │ 1:N                             │ 1:N
            ▼                                 ▼
   ┌─────────────────┐             ┌─────────────────────┐
   │      Order      │             │    SupportTicket    │
   │  (status, etc)  │             │ (subject, priority) │
   └────────┬────────┘             └─────────────────────┘
            │
    ┌───────┼──────────────────────────────┐
1:N │       │ 1:1                          │ 1:N
    ▼       ▼                              ▼
┌──────────────┐  ┌───────────────────┐  ┌───────────────────┐
│  OrderItem   │  │     Shipment      │  │      Refund       │
│  (qty, price)│  │(carrier, tracking)│  │  (amount, status) │
└───────┬──────┘  └───────────────────┘  └───────────────────┘
        │
    1:N │ (linked to order & specific order item)
        ▼
┌──────────────┐
│    Return    │
│(reason, status)
└──────────────┘
```

### Detailed Relational Operations:
1. **Customer → PostgreSQL:**
   - A customer logs in and establishes their verified identity (`customer_id`).
   - All relational lookups query records filtered strictly by `customer_id`.
2. **Customer → Orders:**
   - A customer has zero or more orders (`orders.customer_id = customers.id`).
   - Order statuses: `processing`, `shipped`, `delivered`, `cancelled`.
3. **Order → Order Items:**
   - Each order has one or more line items (`order_items.order_id = orders.id`), pointing to specific products (`products.id`).
   - Holds the agreed purchase price and quantity at the time of purchase.
4. **Order → Shipment:**
   - Each fulfilled order has a 1:1 linked shipment (`shipments.order_id = orders.id`).
   - Contains logistics details: carrier (`Blue Dart`, `Delhivery`, `DTDC`), tracking number, delivery status (`in_transit`, `out_for_delivery`, `delivered`), and estimated delivery date.
5. **Order & Order Item → Return:**
   - When an eligible item is returned, a return request record is generated (`returns.order_id = orders.id`, `returns.order_item_id = order_items.id`).
   - The backend checks product `return_window_days` against `orders.order_date` before creating or approving returns.
   - Return statuses: `requested`, `approved`, `completed`, `rejected`.
6. **Order → Refund:**
   - When an order is cancelled or a return reaches `completed`, a refund record is generated (`refunds.order_id = orders.id`).
   - Refund statuses: `completed`, `pending`, `failed`.
7. **Customer → Support Tickets:**
   - Complex inquiries or human escalations generate a support ticket (`support_tickets.customer_id = customers.id`).
   - Ticket statuses: `open`, `in_progress`, `resolved`, `closed` with priorities (`low`, `medium`, `high`, `urgent`).

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

## Authentication & Customer Context Flow (Phase 2)

A core tenet of this architecture is that **the AI support agent operates strictly within the verified identity of the authenticated customer**.

```
[Customer Client]
       │
       │ 1. POST /auth/login { email, password }
       ▼
[FastAPI / Backend Service]
       │ 2. Verify password with bcrypt against PostgreSQL
       │ 3. Generate signed JWT { sub: str(customer.id), email, exp }
       ▼
[Customer Client]
       │
       │ 4. Authenticated Request (e.g. "Where is my order?")
       │    Headers: Authorization: Bearer <JWT>
       ▼
[FastAPI `get_current_customer` Dependency]
       │ 5. Validate JWT signature and decode token
       │ 6. Extract `customer_id` from subject (`sub`)
       │ 7. Query PostgreSQL for Customer record
       ▼
[Backend Context Assembly]
       │ 8. Inject verified `customer_id` into Agent Execution State
       ▼
[Future LangGraph AI Support Agent]
       │ 9. Tool execution scoped automatically:
       │    get_customer_orders(customer_id=customer_id)
       │    No need to ask the customer: "What is your customer ID?"
       ▼
[Safe, Personalized Response Returned to Customer]
```

### Context Isolation Guarantee:
- The agent **never prompts the customer for their customer ID or account number**.
- The backend guarantees that any tool executed (such as order lookup, cancellation, or refund processing) is bound to `customer.id` extracted from the cryptographically verified JWT token.
- This prevents horizontal privilege escalation where Customer A could attempt to query or cancel Customer B's orders.

## Client-Server Chat Flow (Phase 3)

The complete end-to-end interactive communication between the React chat UI and FastAPI:

```
Customer (Browser)
       │
       │ 1. Submits email + password on LoginPage.jsx (or clicks demo account)
       ▼
React Client (api.js)
       │
       │ 2. POST /auth/login { email, password }
       ▼
FastAPI Backend
       │
       │ 3. Verifies bcrypt hash in PostgreSQL, issues signed JWT
       ▼
React Client (App.jsx)
       │
       │ 4. Stores JWT in localStorage & React state
       │ 5. Displays Navbar with customer badge and switches to ChatPage.jsx
       ▼
Customer (ChatPage.jsx)
       │
       │ 6. Types support message (e.g. "Where is my order #1?") and clicks Send
       ▼
React Client (api.js)
       │
       │ 7. POST /chat
       │    Headers: Authorization: Bearer <JWT>
       │    Body: { "message": "Where is my order #1?" }
       ▼
FastAPI Backend (`/chat` endpoint)
       │
       │ 8. `get_current_customer` dependency decodes token
       │ 9. Identifies customer (`customer_id=1`, `Pushpak Bajanghate`)
       │ 10. Returns personalized response acknowledging request
       ▼
React Client (ChatPage.jsx)
       │
       │ 11. Receives JSON { response, customer_id, customer_name, timestamp }
       │ 12. Renders assistant message bubble in message list
       │ 13. Resets loading state & automatically scrolls to bottom
```

---

## Phase Changelog

### Phase 3: Customer Support Chat Interface (2026-10-08)
- **Status:** Completed
- **Changes Introduced:**
  - Designed and built modern, functional React customer-support interface:
    - `LoginPage.jsx`: Clean sign-in & sign-up forms with 1-click demo account selector (Pushpak, Virat, Pranav).
    - `Navbar.jsx`: Displays live customer identity (`customer.name`, `customer.id`, email) and sign-out action.
    - `ChatPage.jsx`: Full messaging interface featuring:
      - Chronological message list with distinct user and assistant bubble styling.
      - Dynamic typing indicator (loading state with animated bouncing dots).
      - Inline error banner for network or backend connectivity issues.
      - Text input supporting Enter key submission and active/disabled button states.
      - Automatic smooth scroll to newest message.
  - Added backend chat route in `backend/app/api/chat.py`:
    - `POST /chat`: Protected by `get_current_customer` dependency; extracts `customer_id` from JWT Bearer token and returns personalized response.
  - Updated `backend/app/schemas/chat.py` with `ChatMessageRequest` and `ChatMessageResponse`.
  - Added automated test suite in `backend/tests/test_chat.py` verifying authorized chat, unauthorized access rejection, and payload validation.
  - Verified production bundle build with Vite (`npm run build`).

### Phase 2: FastAPI Backend & JWT Authentication (2026-10-08)
- **Status:** Completed
- **Changes Introduced:**
  - Implemented secure password hashing and verification using `bcrypt` (10 rounds, salt-protected).
  - Implemented JWT token creation and verification using `python-jose` (HS256).
  - Created authentication schemas in `backend/app/schemas/auth.py`:
    - `CustomerRegisterRequest` (validates name, email, phone, and password).
    - `CustomerLoginRequest` (validates email and password).
    - `CustomerResponse` (safe public profile; excludes password hash).
    - `TokenResponse` (returns access_token, token_type, and customer profile).
  - Built auth service with `get_current_customer` dependency in `backend/app/services/auth.py`.
  - Added endpoints in `backend/app/api/auth.py`:
    - `POST /auth/register` (creates new customer account with hashed password).
    - `POST /auth/login` (verifies credentials and issues JWT token).
    - `GET /auth/me` (retrieves current authenticated customer context).
    - `GET /health` (checks environment and database connection status).
  - Created automated test suite in `backend/tests/test_auth.py` covering health check, registration, duplicate emails, password validation, login, token generation, and `/auth/me` authorization.

### Phase 1: Database & Synthetic Commerce Data (2026-10-08)
- **Status:** Completed
- **Changes Introduced:**
  - Designed and created 8 relational SQLAlchemy models in `backend/app/models/`:
    - `Customer`: User profile and credentials.
    - `Product`: Catalog items with pricing, category, return window, and warranty days.
    - `Order`: Customer orders with statuses (`delivered`, `shipped`, `processing`, `cancelled`).
    - `OrderItem`: Line items connecting orders to products with quantities and locked prices.
    - `Shipment`: Courier tracking and delivery status.
    - `Return`: Item-level return requests with statuses (`requested`, `approved`, `completed`, `rejected`).
    - `Refund`: Order-level monetary refunds (`completed`, `pending`, `failed`).
    - `SupportTicket`: Customer support escalation tickets with priorities.
  - Created human-readable synthetic datasets in `data/`:
    - 10 Indian customer personas (`data/customers/customers.json`).
    - 20 diverse products with varying return/warranty windows (`data/products/products.json`).
    - 28 realistic orders with items (`data/orders/orders.json`).
    - 7 logistics shipments (`data/orders/shipments.json`).
    - 7 returns testing valid and expired return windows (`data/orders/returns.json`).
    - 7 refund records (`data/orders/refunds.json`).
    - 8 support tickets (`data/orders/tickets.json`).
  - Created automated database seed script in `backend/seed.py` that builds tables and seeds data cleanly.
  - Documented relational data flow and schema decisions.

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
