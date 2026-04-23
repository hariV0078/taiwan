# CircularX Codebase Analysis & Summary

**Framework:** FastAPI (Python)  
**Database:** SQLite (default: `circularx.db`) via SQLModel ORM  
**Vector DB:** ChromaDB (persistent, for buyer profile semantic matching)  
**LLM Integration:** OpenAI GPT-4o-mini (for classification, negotiation, embedding)  
**State Management:** LangGraph (for negotiation workflow)

---

## 1. DATABASE SETUP

### Database System
- **Primary:** SQLite with SQLModel ORM (relational persistence)
- **Persistent Path:** `circularx.db` (local file, configurable via `DATABASE_URL` in `config.py`)
- **Vector Store:** ChromaDB at `./chroma_store` (for buyer profile embeddings)
- **Configuration:** [app/config.py](app/config.py)
  - `DATABASE_URL`: Defaults to `sqlite:///./circularx.db`
  - `CHROMA_PERSIST_PATH`: `./chroma_store`
  - `DPP_STORAGE_PATH`: `./storage/dpps`
  - `PLATFORM_FEE_PCT`: 2.0%

### Supabase Integration
❌ **NOT CONFIGURED** – No Supabase connection strings in config. Only SQLite is used.

### Database Models (Tables)

#### User
- **File:** [app/models/user.py](app/models/user.py)
- **Roles:** `manufacturer`, `buyer`, `tpqc`, `admin`
- **Fields:**
  - `id` (UUID, primary key)
  - `name`, `email` (unique), `password_hash`
  - `role` (enum)
  - `company`, `country`
  - `created_at`, `is_active`

#### WasteListing
- **File:** [app/models/listing.py](app/models/listing.py)
- **Statuses:** `active`, `matched`, `negotiating`, `sold`, `blocked`, `expired`
- **Material Grades:** `A1`, `A2`, `B1`, `B2`, `C`
- **Fields:**
  - `id`, `seller_id` (FK to User)
  - `material_type`, `material_category` (classified)
  - `grade` (optional, AI-enriched)
  - `quantity_kg`, `purity_pct`
  - `location_city`, `location_country`
  - `ask_price_per_kg`
  - `confidence_score` (classifier confidence)
  - `needs_tpqc`, `is_blocked`, `block_reason`
  - `status`, `description`, `created_at`, `expires_at`

#### Transaction
- **File:** [app/models/transaction.py](app/models/transaction.py)
- **Statuses:** `MATCHED` → `NEGOTIATING` → `AGREED` → `LOCKED` → `VERIFIED` → `RELEASED`  
  - Also: `DISPUTED` (from LOCKED), `FAILED` (from MATCHED/NEGOTIATING)
- **Fields:**
  - `id`, `listing_id`, `seller_id`, `buyer_id` (all FK)
  - `agreed_price_per_kg`, `total_value`, `platform_fee`, `seller_payout`
  - `status`, `negotiation_rounds`, `negotiation_transcript`
  - `escrow_hash`, `qar_hash`, `qar_notes`
  - `dpp_path` (PDF location), `co2_saved_kg`
  - `matched_at`, `locked_at`, `verified_at`, `released_at`

#### NegotiationRound
- **File:** [app/models/transaction.py](app/models/transaction.py)
- **Purpose:** Audit trail for each round of AI negotiation
- **Fields:**
  - `id`, `transaction_id` (FK)
  - `round_number`, `role` (seller/buyer)
  - `offered_price`, `reasoning` (LLM-generated)
  - `accepted` (boolean)
  - `created_at`

#### BuyerProfile
- **File:** [app/models/transaction.py](app/models/transaction.py)
- **Purpose:** Buyer preferences for matching and negotiation
- **Fields:**
  - `id`, `buyer_id` (FK, unique)
  - `material_needs`, `accepted_grades`, `accepted_countries` (comma-separated strings)
  - `max_price_per_kg`, `min_quantity_kg`, `max_quantity_kg`
  - `chroma_doc_id` (vector store reference)
  - `updated_at`

#### AuditTrail
- **File:** [app/models/audit.py](app/models/audit.py)
- **Purpose:** Immutable blockchain-like audit log with hash chain
- **Event Types:**
  - `LISTING_CREATED`, `LISTING_BLOCKED`
  - `MATCH_FOUND`, `NEGOTIATION_START`, `NEGOTIATION_ROUND`, `DEAL_AGREED`
  - `ESCROW_LOCKED`, `TPQC_VERIFIED`, `TPQC_REJECTED`, `ESCROW_RELEASED`
  - `DPP_GENERATED`
- **Fields:**
  - `id`, `transaction_id` (nullable FK), `listing_id` (nullable FK)
  - `event_type` (enum)
  - `actor_id` (optional user FK)
  - `payload` (JSON string)
  - `hash`, `prev_hash` (SHA256 chain)
  - `created_at`

---

## 2. API ENDPOINTS & ROUTERS

### Router: `/auth` ([app/routers/auth.py](app/routers/auth.py))
- **POST** `/auth/register` – User registration (any role)
  - Request: `name`, `email`, `password`, `role`, `company`, `country`
  - Response: `UserOut` (user details)
- **POST** `/auth/login` – JWT token generation
  - Request: `email`, `password`
  - Response: `TokenResponse` (access_token)
- **GET** `/auth/me` – Current user profile
  - Response: `UserOut`

### Router: `/listings` ([app/routers/listings.py](app/routers/listings.py))
- **POST** `/listings/` – Create waste listing (manufacturer only)
  - Auto-classifies material via LLM
  - Request: material details, quantity, purity, location, ask_price
  - Response: `ListingOut` (full listing with confidence score)
- **GET** `/listings/` – List active marketplace listings (paginated)
  - Query: `skip=0, limit=20`
  - Response: `list[ListingOut]`
- **GET** `/listings/my` – My listings (authenticated)
  - Response: `list[ListingOut]`
- **GET** `/listings/{listing_id}` – Single listing details
  - Response: `ListingOut`
- **PATCH** `/listings/{listing_id}/status` – Update status (manufacturer/admin)
  - Request: new `status`
  - Response: `ListingOut`
- **DELETE** `/listings/{listing_id}` – Soft-delete (mark expired)
  - Response: `ListingOut`

### Router: `/ai` ([app/routers/ai.py](app/routers/ai.py))
- **POST** `/ai/classify` – AI material classification (any authenticated user)
  - Request: `description`, `quantity_kg`, `purity_pct`
  - Response: `ClassificationResult` (category, grade A1-C, confidence, needs_tpqc, is_blocked)
- **POST** `/ai/match` – Find matching buyers for listing (manufacturer/admin)
  - Request: `listing_id`
  - Returns: `list[MatchResult]` (top 3 buyers with scores)
  - **Side effect:** Creates `MATCHED` transactions
  - Updates listing status to `matched`
- **POST** `/ai/negotiate` – Run AI negotiation (any authenticated user)
  - Request: `transaction_id`, `seller_floor_price`, `buyer_ceiling_price`
  - Returns: `NegotiationResult` (success, agreed_price, rounds, transcript)
  - **Side effects:**
    - Persists negotiation rounds to DB
    - Updates transaction status (→ `NEGOTIATING` or `AGREED` or `FAILED`)
    - Calculates platform fee & seller payout

### Router: `/transactions` ([app/routers/transactions.py](app/routers/transactions.py))
- **GET** `/transactions/` – List transactions (role-filtered)
  - `manufacturer`: seller's transactions
  - `buyer`: buyer's transactions
  - `tpqc`: all LOCKED transactions
  - `admin`: all transactions
  - Response: `list[TransactionOut]`
- **GET** `/transactions/{transaction_id}` – Transaction + audit trail
  - Returns: dict with `transaction` (TransactionOut) + `audit` (list[AuditOut])
  - **Access:** Must be seller, buyer, or admin
- **POST** `/transactions/{transaction_id}/lock` – Lock escrow (buyer only)
  - **Precondition:** Transaction status == `AGREED`
  - **Post-condition:** Status → `LOCKED`
  - Returns: `EscrowResult` (hash, timestamp)
- **GET** `/transactions/{transaction_id}/audit` – Full audit chain
  - Returns: `list[AuditOut]` (chronological events)
- **GET** `/transactions/{transaction_id}/dpp` – Download DPP PDF
  - Returns: FileResponse (PDF file)

### Router: `/tpqc` ([app/routers/tpqc.py](app/routers/tpqc.py))
- **GET** `/tpqc/pending` – List pending TPQC inspections (tpqc role only)
  - Returns: `list[TPQCTransactionOut]` (all LOCKED transactions)
- **POST** `/tpqc/{transaction_id}/approve` – Approve inspection (tpqc only)
  - Request: `qar_notes` (Quality Assurance Report)
  - **Side effects:**
    - Transaction status: `LOCKED` → `VERIFIED` → `RELEASED`
    - Generates DPP PDF
    - Calculates CO2 savings
  - Returns: `TPQCTransactionOut`
- **POST** `/tpqc/{transaction_id}/reject` – Reject inspection (tpqc only)
  - Request: `reason`
  - **Post-condition:** Status → `DISPUTED`
  - Returns: `EscrowResult`
- **GET** `/tpqc/{transaction_id}/qar` – Get QAR details (tpqc/admin)
  - Returns: dict (qar_notes, qar_hash, verified_at)

### System Endpoint
- **GET** `/health` – Health check

---

## 3. SERVICES IMPLEMENTED

### classifier.py ([app/services/classifier.py](app/services/classifier.py))
- **Function:** `classify_material(description, quantity_kg, purity_pct) → ClassificationResult`
- **What it does:**
  - Checks for restricted materials first (PCB, asbestos, radioactive, etc.)
  - If not restricted, calls GPT-4o-mini with few-shot prompt
  - Returns: category, grade (A1-C), confidence score, needs_tpqc, is_blocked flag
  - Fallback: Returns grade C with confidence 0.5 if LLM fails
- **Used by:** Listing creation endpoint

### matcher.py ([app/services/matcher.py](app/services/matcher.py))
- **Purpose:** Semantic matching of listings to buyers using ChromaDB
- **Functions:**
  - `init_chroma() → chromadb.Collection`: Initialize/get buyer profiles collection
  - `upsert_buyer_profile(profile, buyer)`: Add buyer to vector DB
  - `match_buyers(listing, top_k=3) → list[MatchResult]`: Find top matching buyers
- **How it works:**
  - Embeds listing material info using OpenAI `text-embedding-3-small`
  - Queries ChromaDB for closest buyer profiles
  - Filters by price, quantity, country constraints
  - Returns top K matches with similarity scores
- **Limitations:** No market price lookup or ZOPA calculation

### negotiator.py ([app/services/negotiator.py](app/services/negotiator.py))
- **Purpose:** AI-driven price negotiation using LangGraph
- **Structure:** LangGraph state machine with 3 nodes:
  - **seller_node**: Generates seller's counter-offer (floor price secret)
  - **buyer_node**: Generates buyer's counter-offer (ceiling price secret)
  - **referee_node**: Determines if agreement reached or continues
- **Logic:**
  - Max 5 rounds
  - Agreement if either party accepts OR offers cross
  - Returns: NegotiationResult (success, agreed_price, rounds, transcript)
- **Fallback:** Returns "no_zopa" if seller_floor > buyer_ceiling

### escrow.py ([app/services/escrow.py](app/services/escrow.py))
- **Purpose:** State machine for transaction lifecycle with audit hashing
- **Functions:**
  - `lock_escrow(tx_id) → EscrowResult`: AGREED → LOCKED
  - `verify_escrow(tx_id, inspector_id, qar_notes) → EscrowResult`: LOCKED → VERIFIED
  - `reject_escrow(tx_id, inspector_id, reason) → EscrowResult`: LOCKED → DISPUTED
  - `release_escrow(tx_id) → EscrowResult`: VERIFIED → RELEASED
  - `get_audit_chain(tx_id) → list[AuditTrail]`: Full chronological audit
- **Validation:** `VALID_TRANSITIONS` dict prevents invalid state changes
- **Hashing:** Each transition generates event hash (SHA256 of event_type + payload + prev_hash)

### dpp_generator.py ([app/services/dpp_generator.py](app/services/dpp_generator.py))
- **Purpose:** Generate Digital Product Passport (PDF with environmental impact)
- **Function:** `generate_dpp(tx_id, session) → DPPResult`
- **Generates PDF with sections:**
  - DPP ID, timestamp, QR code (for verification)
  - Material info (type, category, grade, quantity, purity, origin)
  - Transaction details (sellers/buyers, pricing, fees)
  - Trust verification (escrow hash, QAR hash, TPQC notes, verified timestamp)
  - Environmental impact (CO2 saved, equivalent trees planted, landfill diverted)
  - Last 5 audit trail entries
- **CO2 Calculation:** Lookup table by material category (plastic 1.9, aluminum 8.24, etc.)
- **Output:** PDF saved to `storage/dpps/{transaction_id}.pdf`

### chroma_seed.py ([app/services/chroma_seed.py](app/services/chroma_seed.py))
- **Purpose:** Populate ChromaDB with buyer profiles at startup
- **Function:** `seed_buyers()` – Seeds 15 global buyers (e.g., IndoPoly Recyclers, Bayern Aluminium Loop)
- **Each buyer includes:** needs, accepted grades, countries, max price, min/max quantity

---

## 4. MISSING SERVICES

❌ **market_price.py** – NOT IMPLEMENTED
- No real-time commodity price lookup (e.g., London Metals Exchange)
- Negotiation uses static floor/ceiling prices passed in request

❌ **zopa.py** – NOT IMPLEMENTED (implied via negotiator.py)
- "ZOPA" (Zone of Possible Agreement) is checked via `if seller_floor > buyer_ceiling`
- No dedicated service; logic is inline in negotiation flow

❌ **notifier.py** – NOT IMPLEMENTED
- No email/SMS/in-app notifications
- No notification triggers on transaction state changes
- **Gap:** Users won't receive updates on matches, approvals, or rejections

---

## 5. TRANSACTION FLOW & STATUS STATES

### Full Lifecycle Diagram
```
CREATION (Listing)
  ↓
MATCHING
  Listing.status: active → matched
  Transaction.status: MATCHED (created)
  ↓
NEGOTIATION
  Transaction.status: MATCHED → NEGOTIATING → AGREED (if success)
  - AI runs negotiation rounds
  - NegotiationRound records created for each round
  - Pricing calculated (total_value = qty × agreed_price)
  - Platform fee deducted (2% default)
  - Seller payout = total_value - platform_fee
  ↓
ESCROW LOCK (Buyer initiates)
  Transaction.status: AGREED → LOCKED
  - escrow_hash generated
  ↓
TPQC VERIFICATION (TPQC Inspector)
  Transaction.status: LOCKED → VERIFIED (or DISPUTED if rejected)
  - qar_notes recorded
  - qar_hash generated
  ↓
ESCROW RELEASE
  Transaction.status: VERIFIED → RELEASED
  ↓
DPP GENERATION (Post-TPQC approval)
  - PDF generated with environmental metrics
  - co2_saved_kg calculated
  - dpp_path stored in transaction
```

### Valid State Transitions (State Machine)
[app/services/escrow.py](app/services/escrow.py) defines:
```
MATCHED → NEGOTIATING, FAILED
NEGOTIATING → AGREED, FAILED
AGREED → LOCKED
LOCKED → VERIFIED, DISPUTED
VERIFIED → RELEASED
RELEASED → (end)
DISPUTED → VERIFIED, FAILED
FAILED → (end)
```

### Audit Trail Entries
Each status change creates an AuditTrail record with:
- event_type (enum)
- payload (JSON of change details)
- hash (SHA256 chain)
- prev_hash (previous hash for chain integrity)

---

## 6. OVERALL ARCHITECTURE

### Framework & Stack
- **FastAPI** (main.py, routers)
- **SQLModel** (ORM for relational DB)
- **ChromaDB** (vector store for semantic matching)
- **LangChain + LangGraph** (AI workflow orchestration)
- **OpenAI GPT-4o-mini** (classification, negotiation, embeddings)
- **JWT + bcrypt** (authentication)
- **FPDF2** (PDF generation)
- **QRCode** (DPP verification codes)

### Notification System
❌ **NOT IMPLEMENTED** – Zero notification infrastructure
- No email service (e.g., SendGrid, AWS SES)
- No SMS provider
- No WebSocket or Server-Sent Events for real-time updates
- **Impact:** Users must manually check endpoints for transaction status

### Data Flow
1. **User Registration** → Creates User record with role
2. **Listing Creation** → Classified by LLM → Checked for restricted materials → Stored
3. **Matching** → Buyers queried from ChromaDB → Transactions created in MATCHED state
4. **Negotiation** → LLM negotiates via LangGraph → Persists rounds → Updates price
5. **Escrow Lock** → Buyer locks → Status → LOCKED
6. **TPQC Verification** → Inspector reviews → Approves or rejects → DPP generated
7. **Download** → User can download PDF

### Authentication
- JWT tokens (default 1440 min expiry, ~24 hours)
- OAuth2PasswordBearer scheme
- Roles enforced at endpoint level with `depends(get_current_user)`

---

## 7. WHAT'S IMPLEMENTED vs. MISSING

### ✅ IMPLEMENTED
- [x] SQLite database with full ORM
- [x] User roles (manufacturer, buyer, tpqc, admin)
- [x] Listing creation with AI classification
- [x] Restricted materials blocking
- [x] Semantic buyer matching via ChromaDB + embeddings
- [x] AI price negotiation (LangGraph state machine)
- [x] Escrow state machine with hash chain audit trail
- [x] TPQC verification workflow
- [x] DPP PDF generation with CO2 metrics
- [x] Comprehensive API endpoints
- [x] JWT authentication
- [x] Role-based access control

### ❌ MISSING / GAPS
- [ ] **Notifications** – No email/SMS/in-app notification system
- [ ] **Market Price Service** – No real-time commodity lookup
- [ ] **ZOPA Calculation** – Only implicit via floor/ceiling check
- [ ] **Supabase** – Not configured (only SQLite)
- [ ] **Payment/Wallet** – No Stripe/payment gateway
- [ ] **Dispute Resolution** – DISPUTED state exists but no resolution workflow
- [ ] **Multi-language Support** – All prompts/messages in English
- [ ] **Reporting/Analytics** – No dashboard or analytics endpoints
- [ ] **Environmental Offset Integration** – No link to carbon credit issuance

---

## 8. KEY CONFIGURATION

**File:** [app/config.py](app/config.py)
```python
DATABASE_URL: str = "sqlite:///./circularx.db"  # SQLite default
CHROMA_PERSIST_PATH: str = "./chroma_store"
DPP_STORAGE_PATH: str = "./storage/dpps"
PLATFORM_FEE_PCT: float = 2.0
OPENAI_API_KEY: str  # Required from .env
SECRET_KEY: str  # Required for JWT
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
```

**Dependencies:** [requirements.txt](requirements.txt)
- fastapi, uvicorn, sqlmodel, chromadb
- langchain, langgraph, openai
- fpdf2, qrcode, bcrypt, python-jose
- pydantic, pytest

---

## 9. ALIGNMENT WITH REDESIGNED SPEC

### 🟢 FULLY ALIGNED
- Listing creation & classification
- Buyer-seller matching workflow
- AI-powered price negotiation
- Escrow state management
- TPQC verification
- Audit trail with hash chain

### 🟡 PARTIALLY ALIGNED
- DPP generation (implemented but no blockchain integration)
- Transaction statuses (match the flow but no complex dispute resolution)

### 🔴 NOT ALIGNED / MISSING
- Notifications (CRITICAL for user experience)
- Market price feed (needed for fair negotiation)
- Supabase integration (using SQLite instead)
- Payment processing (no buyer/seller wallet)
- Analytics/reporting dashboard
- Multi-language support for global markets

---

## 10. RECOMMENDED NEXT STEPS

1. **Add Notification Service** (HIGH PRIORITY)
   - Implement email notifications on transaction state changes
   - Consider Celery + Redis for async task queue

2. **Integrate Market Price Feed** (HIGH)
   - Add LME or commodity price API
   - Use in negotiation to suggest ZOPA range

3. **Payment Gateway** (MEDIUM)
   - Stripe Connect for escrow management
   - Seller payout automation

4. **Dispute Resolution Workflow** (MEDIUM)
   - Implement escalation from DISPUTED state
   - Arbitration logic

5. **Supabase Migration** (LOW)
   - Optional if cloud postgres needed
   - Would require minimal ORM changes (SQLModel → SQLAlchemy)

6. **Analytics Dashboard** (LOW)
   - Transaction volume, average deal price
   - Environmental impact metrics
