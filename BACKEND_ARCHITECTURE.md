# CircularX Backend Architecture

## 1. System Overview

CircularX backend is a FastAPI service that orchestrates a circular-material marketplace flow:

1. User authentication and role-based access (manufacturer, buyer, tpqc, admin).
2. Waste listing ingestion and AI-assisted classification.
3. Semantic buyer matching using ChromaDB + embeddings.
4. Human-in-the-loop pricing with market reference and ZOPA logic.
5. Escrow state transitions and TPQC inspection workflow.
6. DPP generation and audit trail recording.
7. In-app notifications for key transaction events.

The backend is designed as a layered application:

- API layer: routers in app/routers
- Domain/service layer: app/services
- Persistence layer: SQLModel entities in app/models and DB engine/session in app/database
- Shared helpers: app/utils

## 2. Runtime Composition

### Entry point

- main.py creates the FastAPI app, CORS middleware, router registrations, and startup hooks.

### Startup behavior

On startup, the app runs:

1. create_db_and_tables() from app/database.py
2. seed_buyers() from app/services/chroma_seed.py

This guarantees relational tables exist and the Chroma buyer index has initial profiles.

### Router mounting

- /auth -> app/routers/auth.py
- /buyer-profiles -> app/routers/buyer_profiles.py
- /listings -> app/routers/listings.py
- /ai -> app/routers/ai.py
- /transactions -> app/routers/transactions.py
- /notifications -> app/routers/notifications.py
- /tpqc -> app/routers/tpqc.py

### Health endpoint

- GET /health returns service readiness payload.

## 3. Configuration and Database

## Configuration

app/config.py exposes Settings via pydantic-settings with env-based loading.

Key variables:

- OPENAI_API_KEY
- SECRET_KEY
- ALGORITHM
- ACCESS_TOKEN_EXPIRE_MINUTES
- DATABASE_URL
- SUPABASE_DATABASE_URL
- CHROMA_PERSIST_PATH
- DPP_STORAGE_PATH
- PLATFORM_FEE_PCT
- SUPABASE_URL
- SUPABASE_KEY
- USE_SUPABASE

## Database routing

app/database.py picks database URL with precedence:

- SUPABASE_DATABASE_URL if set
- otherwise DATABASE_URL

Engine creation:

- SQLite: create_engine(..., connect_args={"check_same_thread": False})
- Postgres/Supabase: create_engine(...) without sqlite-specific args

Session management is generator-based with SQLModel Session(engine).

## 4. Domain Data Model

## Core entities

### User

File: app/models/user.py

Fields:

- id, name, email, password_hash
- role (manufacturer, buyer, tpqc, admin)
- company, country, created_at, is_active

### WasteListing

File: app/models/listing.py

Fields:

- seller_id, material_type, material_category, grade
- quantity_kg, purity_pct, ask_price_per_kg
- location_city, location_country
- confidence_score, needs_tpqc, is_blocked, block_reason
- status, description, created_at, expires_at

Status enum:

- active, matched, negotiating, sold, blocked, expired

Grade enum:

- A1, A2, B1, B2, C

### Transaction

File: app/models/transaction.py

Fields include:

- listing_id, seller_id, buyer_id
- agreed_price_per_kg, total_value, platform_fee, seller_payout
- status and negotiation metadata
- escrow_hash, qar_hash, qar_notes
- dpp_path, co2_saved_kg
- timestamps for matched/locked/verified/released
- human-in-the-loop pricing fields:
  - buyer_confirmed_interest_at
  - initial_proposed_price
  - counter_offer_from_seller
  - counter_offer_from_buyer
  - counter_offer_expires_at
  - seller_accepted_price_at
  - buyer_accepted_price_at

TransactionStatus enum:

- MATCHED
- BUYER_INTERESTED
- PRICE_PROPOSED
- PRICE_COUNTERED
- AGREED
- LOCKED
- INSPECTING
- VERIFIED
- RELEASED
- DISPUTED
- FAILED

### BuyerProfile

File: app/models/transaction.py

Fields:

- buyer_id (unique)
- material_needs, accepted_grades, accepted_countries
- max_price_per_kg, min_quantity_kg, max_quantity_kg
- chroma_doc_id, updated_at

### Notification

File: app/models/notification.py

Fields:

- user_id, transaction_id
- message, notification_type
- is_read, created_at, read_at

### AuditTrail

File: app/models/audit.py

Fields:

- transaction_id, listing_id
- event_type
- actor_id
- payload
- hash, prev_hash
- created_at

Event types cover listing lifecycle, matching, negotiation, escrow/TPQC, DPP generation.

## 5. API Layer (Routers)

## Authentication Router

File: app/routers/auth.py

Responsibilities:

- User registration
- JWT login
- Authenticated current-user lookup
- Password hashing and verification

Key functions:

- verify_password
- get_password_hash
- create_access_token
- get_current_user
- register_user
- login_user
- me

Endpoints:

- POST /auth/register
- POST /auth/login
- GET /auth/me

## Listings Router

File: app/routers/listings.py

Responsibilities:

- Create and manage listings
- Trigger classification at creation
- Create listing-level audit events

Key functions:

- create_listing
- list_active_listings
- my_listings
- get_listing
- update_listing_status
- soft_delete_listing

Endpoints:

- POST /listings/
- GET /listings/
- GET /listings/my
- GET /listings/{listing_id}
- PATCH /listings/{listing_id}/status
- DELETE /listings/{listing_id}

## AI Router

File: app/routers/ai.py

Responsibilities:

- AI classification endpoint
- Buyer matching endpoint
- Market price reference endpoint

Key functions:

- classify_material_endpoint
- match_buyers_endpoint
- get_market_price_endpoint

Endpoints:

- POST /ai/classify
- POST /ai/match
- POST /ai/market-price

## Buyer Profiles Router

File: app/routers/buyer_profiles.py

Responsibilities:

- Buyer profile CRUD-like operations (create/get self/update)
- Chroma sync via upsert_buyer_profile

Key functions:

- create_buyer_profile
- get_buyer_profile
- update_buyer_profile

Endpoints:

- POST /buyer-profiles/
- GET /buyer-profiles/me
- PATCH /buyer-profiles/me

## Transactions Router

File: app/routers/transactions.py

Responsibilities:

- Transaction visibility and detail retrieval
- Escrow lock operation
- Audit and DPP retrieval
- Human-in-the-loop pricing flow

Key functions:

- list_transactions
- get_transaction_detail
- lock_transaction_escrow
- transaction_audit
- download_dpp
- buyer_confirms_interest
- propose_price
- counter_offer
- accept_price
- get_pricing

Endpoints:

- GET /transactions/
- GET /transactions/{transaction_id}
- POST /transactions/{transaction_id}/lock
- GET /transactions/{transaction_id}/audit
- GET /transactions/{transaction_id}/dpp
- POST /transactions/{transaction_id}/buyer-confirms-interest
- POST /transactions/{transaction_id}/propose-price
- POST /transactions/{transaction_id}/counter-offer
- POST /transactions/{transaction_id}/accept-price
- GET /transactions/{transaction_id}/pricing

## Notifications Router

File: app/routers/notifications.py

Responsibilities:

- User notification retrieval
- Read/unread mutation endpoints

Key functions:

- get_notifications
- mark_notification_as_read
- mark_all_notifications_read

Endpoints:

- GET /notifications/
- PATCH /notifications/{notification_id}/read
- POST /notifications/mark-all-read

## TPQC Router

File: app/routers/tpqc.py

Responsibilities:

- TPQC queue and inspection lifecycle
- Approve/reject decisioning
- Escrow state progression
- DPP generation trigger on approval

Key functions:

- pending_tpqc
- start_inspection
- approve_tpqc
- reject_tpqc
- get_qar

Endpoints:

- GET /tpqc/pending
- POST /tpqc/{transaction_id}/start-inspection
- POST /tpqc/{transaction_id}/approve
- POST /tpqc/{transaction_id}/reject
- GET /tpqc/{transaction_id}/qar

## 6. Service Layer

## classifier.py

Purpose:

- Material categorization and grade assignment
- Pre-check for restricted/banned materials before LLM call

Key function:

- classify_material(description, quantity_kg, purity_pct)

Behavior:

- Immediate block if restricted material detected
- Otherwise structured output from ChatOpenAI
- Conservative fallback if model call fails

## matcher.py

Purpose:

- Buyer semantic matching against listing text
- ChromaDB indexing and query orchestration

Key functions:

- init_chroma
- upsert_buyer_profile
- match_buyers

Behavior:

- Embeds text with OpenAI embeddings
- Queries Chroma and post-filters by:
  - price tolerance
  - quantity range
  - accepted country

## chroma_seed.py

Purpose:

- Seeds Chroma collection with initial buyers

Key functions:

- seed_buyers
- clear_and_reseed

## market_price.py

Purpose:

- Returns market reference pricing used by AI router and transaction pricing flow
- Validates seller floor and buyer ceiling against market bounds

Key functions:

- load_market_prices
- get_market_price_range
- validate_seller_floor_price
- validate_buyer_ceiling_price

Current behavior:

- Uses root-level price dataset first
- Falls back to legacy storage/market_prices.json
- Converts per_tonne source values into per_kg outputs for transaction logic compatibility

## zopa.py

Purpose:

- Deterministic price-overlap computation between seller and buyer

Key functions:

- calculate_zopa
- check_counter_offer_zopa

## escrow.py

Purpose:

- Enforces escrow/verification transition state machine
- Creates escrow/TPQC audit hashes

Key artifacts:

- EscrowResult model
- VALID_TRANSITIONS map

Key functions:

- lock_escrow
- verify_escrow
- reject_escrow
- release_escrow
- get_audit_chain

## dpp_generator.py

Purpose:

- Generates DPP PDF output with QR verification payload
- Computes CO2 saved estimation by material category
- Writes DPP audit entry

Key functions:

- generate_dpp

Outputs:

- PDF in storage/dpps
- DPPResult payload

## notifier.py

Purpose:

- Async helpers for creating and marking notifications

Key functions:

- create_notification
- get_user_notifications
- mark_notification_as_read
- mark_all_as_read

Note:

- Current routers mostly manipulate Notification table directly with sync sessions.
- notifier.py is available for a future consolidation pass.

## 7. Utilities

## restricted_materials.py

- Loads banned/reference terms and checks descriptions for policy blocks.

## hashing.py

- Hash generator utilities used for audit chain continuity.

## 8. Core Business Flows

## Flow A: Listing Creation

1. Manufacturer calls POST /listings/
2. classify_material runs restriction + grade logic
3. Listing inserted with blocked/active status
4. Audit event stored (LISTING_CREATED or LISTING_BLOCKED)

## Flow B: Matching

1. Manufacturer/admin calls POST /ai/match
2. match_buyers returns top candidates from Chroma + filters
3. Transaction records created with status MATCHED
4. Listing marked matched
5. MATCH_FOUND audit entries written

## Flow C: Human-in-the-loop Pricing

1. Buyer confirms interest (MATCHED -> BUYER_INTERESTED)
2. System proposes price from ZOPA + market reference (-> PRICE_PROPOSED)
3. Optional counter offers (PRICE_COUNTERED)
4. Both sides accept -> AGREED
5. Financials populated (total value, fee, seller payout)

## Flow D: Escrow + TPQC + DPP

1. Buyer locks escrow (AGREED -> LOCKED)
2. TPQC starts inspection (LOCKED -> INSPECTING)
3. TPQC approves (INSPECTING -> VERIFIED) or rejects (-> DISPUTED)
4. On approve: escrow release and DPP generation
5. Final release to RELEASED

## Flow E: Notifications

- Transaction and TPQC events write notification rows.
- Clients fetch via GET /notifications/ and mark read via PATCH/POST endpoints.

## 9. Security and Access Control

Authentication:

- OAuth2 password flow with bearer JWT.

Authorization pattern:

- Role and ownership checks enforced in each router function.
- Examples:
  - Only manufacturer can create listing
  - Only assigned buyer can lock escrow
  - TPQC-only inspection endpoints
  - Transaction detail restricted by role and participation

## 10. Persistence and External Dependencies

Relational storage:

- SQLModel over SQLite or Supabase Postgres.

Vector storage:

- ChromaDB persistent local path from CHROMA_PERSIST_PATH.

LLM/Embeddings:

- OpenAI API for classifier and embeddings.

Document storage:

- Generated DPP PDFs under DPP_STORAGE_PATH.

## 11. Testing and Operational Notes

Tests present in tests/ include classifier, matcher, escrow, negotiator legacy references.

Operational notes:

- App currently creates schema with SQLModel metadata on startup.
- For managed Supabase migrations, add migration tooling to avoid startup-driven schema drift.
- Notification creation is partially inline in routers and partially abstracted in notifier service.
