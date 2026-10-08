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

## Conversational LLM Flow (Phase 4 — Dynamic Runtime Google Gemini)

In Phase 4, the `/chat` route connects directly to the live Google Gemini API (`LLM_MODEL`) using credentials configured in `.env`.

> [!IMPORTANT]
> **Dynamic Runtime Guarantee:**
> Chat messages and assistant responses are generated dynamically at runtime. No conversation messages or LLM responses are hardcoded.

### Step-by-Step Runtime Message Lifecycle

```
User enters message
  │
  ▼
React captures actual input (ChatPage.jsx)
  │
  ▼
JWT + actual message sent to FastAPI (POST /chat)
  │
  ▼
FastAPI verifies JWT (get_current_customer dependency)
  │
  ▼
FastAPI identifies authenticated customer (PostgreSQL lookup)
  │
  ▼
FastAPI sends actual message to Gemini (via LangChain ChatGoogleGenerativeAI)
  │
  ▼
Gemini dynamically generates response (conditioned on system prompt)
  │
  ▼
FastAPI returns actual response (HTTP 200 ChatMessageResponse)
  │
  ▼
React displays response (dynamically renders assistant message bubble)
```

```
[Customer Browser / React Chat UI]
       │
       │ 1. User enters real message into input field (e.g. "I want to return my shoes")
       │ 2. Submits via Enter or Send button; React captures actual input into state
       │ 3. Dispatches POST /chat with Bearer JWT header and dynamic message payload
       ▼
[FastAPI Backend /chat Endpoint]
       │
       │ 4. `get_current_customer` dependency validates JWT signature & expiration
       │ 5. Identifies authenticated customer record in PostgreSQL
       ▼
[LLM Service Layer (`app.services.llm`)]
       │
       │ 6. Loads LLM_API_KEY and LLM_MODEL dynamically from .env
       │ 7. Assembles SystemMessage with safety guidelines and customer context
       │ 8. Assembles HumanMessage containing the exact user runtime text
       ▼
[Google Gemini API (`ChatGoogleGenerativeAI`)]
       │
       │ 9. Gemini dynamically processes prompt and generates live contextual response
       ▼
[FastAPI Backend /chat Endpoint]
       │
       │ 10. Serializes response into JSON payload { response, customer_id, customer_name, timestamp }
       │ 11. Returns HTTP 200 response (or genuine HTTP 500 / 502 on provider error)
       ▼
[Customer Browser / React Chat UI]
       │
       │ 12. Appends dynamically received assistant response bubble to conversation view
```

---

## Router Agent Orchestration Flow (Phase 5 — LangGraph Intent Classification)

In Phase 5, customer messages are routed through a LangGraph state machine. The Router Agent's **ONLY responsibility is intent understanding and workflow selection**. It does NOT perform business actions (such as querying order tables or executing refunds).

### Core Routing Pipeline

```
message
  │
  ▼
Router Agent (LangGraph node)
  │ (Google Gemini structured JSON classification)
  ▼
intent (one of 13 supported types)
  │
  ▼
Support workflow (conversational node in Phase 5; tool execution in Phase 6+)
```

### Detailed State Machine Flow

```
[Customer Browser / React Frontend]
       │
       │ 1. User enters real message (e.g. "I want to return my shoes")
       │ 2. Submits via Enter/Send → React dispatches POST /chat with Bearer JWT
       ▼
[FastAPI Backend /chat Endpoint]
       │
       │ 3. `get_current_customer` dependency decodes JWT → extracts customer_id (e.g. 1)
       │    Customer never needs to provide customer_id manually
       │ 4. Initializes `AgentState`:
       │    { customer_id, customer_name, customer_email, message, conversation_history }
       ▼
[LangGraph StateGraph — Compiled Pipeline]
       │
       │ 5. Entry point: `router_node`
       ▼
[Router Agent Node (`app.agents.router`)]
       │
       │ 6. Injects authenticated customer context + conversation history into ROUTER_SYSTEM_PROMPT
       │ 7. Calls Google Gemini with structured output contract
       │ 8. Gemini analyzes message and returns JSON:
       │    {
       │      "intent": "ORDER_RETURN",
       │      "confidence": 0.94,
       │      "needs_clarification": false,
       │      "required_information": [],
       │      "acknowledgement": "I understand you'd like to return an item..."
       │    }
       │ 9. Router updates `AgentState` with intent classification
       │    NOTE: Does NOT ask "which shoes yet" — the downstream Support Agent will
       │    use customer context to find possible matching orders
       ▼
[LangGraph Edge: router → conversational]
       ▼
[Conversational Node (`app.agents.conversational`)]
       │
       │ 10. Evaluates Router confidence:
       │     - If confidence >= 0.8 & no clarification: uses Router acknowledgement directly
       │     - Otherwise: invokes Gemini with intent-guided prompt for a richer response
       │ 11. Sets `final_response` in `AgentState`
       ▼
[LangGraph Edge: conversational → END]
       ▼
[FastAPI Serialization & Response]
       │
       │ 12. Packages response into `ChatMessageResponse`:
       │     {
       │       "response": "...",
       │       "customer_id": 1,
       │       "customer_name": "Pushpak Bajanghate",
       │       "timestamp": "...",
       │       "router": {
       │         "intent": "ORDER_RETURN",
       │         "confidence": 0.94,
       │         "needs_clarification": false,
       │         "required_information": []
       │       }
       │     }
       ▼
[Customer Browser / React Frontend]
       │
       │ 13. Displays assistant response bubble
       │ 14. Renders live Intent Badge: [● Intent: ORDER_RETURN (94%)]
```

### Supported Intent Types (13 Total)

| Intent | Description | Downstream Workflow (Phase 6+) |
|---|---|---|
| `ORDER_TRACKING` | Customer wants to track an order | Support Agent queries `shipments` table by `customer_id` |
| `ORDER_CANCEL` | Customer wants to cancel an order | Support Agent checks `orders.status` and validates cancellation |
| `ORDER_RETURN` | Customer wants to return an item | Support Agent checks `return_window_days` on customer's orders |
| `REFUND_STATUS` | Customer asking about a refund | Support Agent queries `refunds` table by `customer_id` |
| `REFUND_REQUEST` | Customer requesting a new refund | Support Agent checks return completion and triggers refund flow |
| `PRODUCT_INFORMATION` | Customer asking about product specs | RAG node retrieves product documentation |
| `DAMAGED_PRODUCT` | Customer received damaged item | Return flow with expedited replacement priority |
| `WRONG_PRODUCT` | Customer received incorrect item | Return flow with item verification |
| `DELIVERY_DELAY` | Customer asking about delayed package | Support Agent checks carrier tracking via `shipments` |
| `PAYMENT_ISSUE` | Payment failed or incorrect charge | Billing verification workflow |
| `HUMAN_ESCALATION` | Customer explicitly requests a human | Support Agent creates a high-priority `support_tickets` record |
| `GENERAL_QUESTION` | Broad questions about store, hours, etc. | Conversational / FAQ RAG retrieval |
| `UNKNOWN` | Intent unclear from context | Clarification flow prompts customer politely |

---

## Phase Changelog

### Phase 5: Router Agent (LangGraph Intent Classification) (2026-10-08)
- **Status:** Completed
- **Changes Introduced:**
  - Implemented the LangGraph Router Agent state machine (`backend/app/agents/`):
    - `state.py`: Defined `AgentState` TypedDict carrying customer context, conversation history, intent, confidence, and responses.
    - `router.py`: Implemented `router_node` using Google Gemini with structured JSON output. Classifies into 13 supported intent types. Returns confidence (0.0–1.0), `needs_clarification`, and `required_information`.
    - `conversational.py`: Implemented `conversational_node` providing intent-guided responses. Uses Router acknowledgements directly for high-confidence cases.
    - `graph.py`: Built and compiled `StateGraph` (`router → conversational → END`). Exported thread-safe `run_support_graph()`.
  - Created router schemas in `backend/app/schemas/router.py`: `IntentType` enum (13 intents) and `RouterOutput` Pydantic model.
  - Updated `backend/app/schemas/chat.py` with `RouterInfo` embedded in `ChatMessageResponse`.
  - Updated `backend/app/api/chat.py` to route all chat traffic through `run_support_graph()`.
  - Updated `frontend/src/pages/ChatPage.jsx` to render live intent badges with confidence percentages on assistant messages (Decagon-style UX).
  - Created automated test suite in `backend/tests/test_router.py` (10 tests) and updated `backend/tests/test_chat.py` (5 tests) — 23 total backend tests passing.
  - Zero hardcoded behavior: all intents, confidences, and responses generated dynamically by Google Gemini at runtime.

### Phase 4: LLM Integration (Google Gemini — Real Dynamic Inference) (2026-10-08)
- **Status:** Completed
- **Changes Introduced:**
  - Implemented modular, provider-agnostic LLM service in `backend/app/services/llm.py`:
    - Reads `LLM_API_KEY` and `LLM_MODEL` from `.env`.
    - Automatically checks fallbacks for `GEMINI_API_KEY` and `GOOGLE_API_KEY`.
    - Configures Google Gemini via `ChatGoogleGenerativeAI` with temperature `0.3`.
    - Structured system prompt defining the assistant as: *"An AI customer-support assistant that helps authenticated customers with orders, returns, refunds, shipping and product questions."*
    - Enforced guidelines: concise, helpful, never invent order information, never claim actions performed unless verified, ask for clarification.
    - Zero hardcoded responses, mock scripts, or fake fallbacks.
    - Genuine error propagation: missing API key returns HTTP 500; external Gemini failure returns HTTP 502 Bad Gateway.
  - Updated `backend/app/api/chat.py` to route customer messages dynamically through `generate_support_response`.
  - Updated `frontend/src/pages/ChatPage.jsx` and `LoginPage.jsx` to start with blank message state and real dynamic user inputs (no prefilled demo accounts or hardcoded chat bubbles).
  - Synchronized PostgreSQL primary key sequences in `backend/seed.py` so dynamic registrations seamlessly succeed.
  - Added unit test suite in `backend/tests/test_chat.py` with mock LLM validation ensuring dynamic message propagation and error handling.
  - Updated `.env.example` to document Google Gemini environment variables.

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
