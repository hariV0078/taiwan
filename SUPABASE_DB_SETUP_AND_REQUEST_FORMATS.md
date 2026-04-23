# Supabase DB Setup and Request Formats

This document collects the Supabase/Postgres setup SQL and the request-body formats used by the current FastAPI app.

## 1) Supabase Setup Notes

The app already prefers `SUPABASE_DATABASE_URL` when it is set. For Supabase, use a SQLAlchemy-compatible Postgres URL such as:

```env
SUPABASE_DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

If you are provisioning the database manually in Supabase, run the SQL below in the Supabase SQL editor.

**Note for Hackathon:** The SQLModel app automatically creates tables on startup, so you may not need to run this SQL manually. Only run it if you want to pre-provision the schema.

## 2) SQL Queries for Supabase DB Setup

**Copy and paste each query separately in the Supabase SQL editor** (don't run all at once):

### Query 1: Create Extensions & Enums

```sql
create extension if not exists "pgcrypto";

create type user_role as enum ('manufacturer', 'buyer', 'tpqc', 'admin');
create type listing_status as enum ('active', 'matched', 'negotiating', 'sold', 'blocked', 'expired');
create type material_grade as enum ('A1', 'A2', 'B1', 'B2', 'C');
create type transaction_status as enum ('MATCHED', 'BUYER_INTERESTED', 'PRICE_PROPOSED', 'PRICE_COUNTERED', 'AGREED', 'LOCKED', 'INSPECTING', 'VERIFIED', 'RELEASED', 'DISPUTED', 'FAILED');
create type audit_event_type as enum ('LISTING_CREATED', 'LISTING_BLOCKED', 'MATCH_FOUND', 'NEGOTIATION_START', 'NEGOTIATION_ROUND', 'DEAL_AGREED', 'ESCROW_LOCKED', 'TPQC_VERIFIED', 'TPQC_REJECTED', 'ESCROW_RELEASED', 'DPP_GENERATED');
```

### Query 2: Core Tables

```sql
create table if not exists "user" (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    email text not null unique,
    password_hash text not null,
    role user_role not null,
    company text not null,
    country text not null,
    created_at timestamptz not null default now(),
    is_active boolean not null default true
);

create table if not exists wastelisting (
    id uuid primary key default gen_random_uuid(),
    seller_id uuid not null references "user" (id),
    material_type text not null,
    material_category text not null,
    grade material_grade,
    quantity_kg double precision not null,
    purity_pct double precision not null,
    location_city text not null,
    location_country text not null,
    ask_price_per_kg double precision not null,
    confidence_score double precision,
    needs_tpqc boolean not null default false,
    is_blocked boolean not null default false,
    block_reason text,
    status listing_status not null default 'active',
    description text,
    created_at timestamptz not null default now(),
    expires_at timestamptz
);

create table if not exists buyerprofile (
    id uuid primary key default gen_random_uuid(),
    buyer_id uuid not null unique references "user" (id),
    material_needs text not null,
    accepted_grades text not null,
    accepted_countries text not null,
    max_price_per_kg double precision not null,
    min_quantity_kg double precision not null,
    max_quantity_kg double precision not null,
    chroma_doc_id text,
    updated_at timestamptz not null default now()
);

create table if not exists "transaction" (
    id uuid primary key default gen_random_uuid(),
    listing_id uuid not null references wastelisting (id),
    seller_id uuid not null references "user" (id),
    buyer_id uuid not null references "user" (id),
    agreed_price_per_kg double precision,
    total_value double precision,
    platform_fee double precision,
    seller_payout double precision,
    status transaction_status not null default 'MATCHED',
    negotiation_rounds integer not null default 0,
    negotiation_transcript text,
    escrow_hash text,
    qar_hash text,
    qar_notes text,
    dpp_path text,
    co2_saved_kg double precision,
    matched_at timestamptz not null default now(),
    buyer_confirmed_interest_at timestamptz,
    initial_proposed_price double precision,
    counter_offer_from_seller double precision,
    counter_offer_from_buyer double precision,
    counter_offer_expires_at timestamptz,
    seller_accepted_price_at timestamptz,
    buyer_accepted_price_at timestamptz,
    locked_at timestamptz,
    verified_at timestamptz,
    released_at timestamptz
);

create table if not exists negotiationround (
    id uuid primary key default gen_random_uuid(),
    transaction_id uuid not null references "transaction" (id),
    round_number integer not null,
    role text not null,
    offered_price double precision not null,
    reasoning text not null,
    accepted boolean not null,
    created_at timestamptz not null default now()
);

create table if not exists notification (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references "user" (id),
    transaction_id uuid references "transaction" (id),
    message text not null,
    notification_type text not null,
    is_read boolean not null default false,
    created_at timestamptz not null default now(),
    read_at timestamptz
);

create table if not exists audittrail (
    id uuid primary key default gen_random_uuid(),
    transaction_id uuid references "transaction" (id),
    listing_id uuid references wastelisting (id),
    event_type audit_event_type not null,
    actor_id uuid,
    payload text not null,
    hash text not null,
    prev_hash text not null,
    created_at timestamptz not null default now()
);
```

### Query 3: Create Indexes

```sql
create index if not exists ix_user_email on "user" (email);
create index if not exists ix_wastelisting_seller_id on wastelisting (seller_id);
create index if not exists ix_wastelisting_status on wastelisting (status);
create index if not exists ix_buyerprofile_buyer_id on buyerprofile (buyer_id);
create index if not exists ix_transaction_listing_id on "transaction" (listing_id);
create index if not exists ix_transaction_seller_id on "transaction" (seller_id);
create index if not exists ix_transaction_buyer_id on "transaction" (buyer_id);
create index if not exists ix_transaction_status on "transaction" (status);
create index if not exists ix_negotiationround_transaction_id on negotiationround (transaction_id);
create index if not exists ix_notification_user_id on notification (user_id);
create index if not exists ix_notification_transaction_id on notification (transaction_id);
create index if not exists ix_notification_created_at on notification (created_at);
create index if not exists ix_audittrail_transaction_id on audittrail (transaction_id);
create index if not exists ix_audittrail_listing_id on audittrail (listing_id);
create index if not exists ix_audittrail_created_at on audittrail (created_at);
```

## 3) Request Format Types

### Auth (Supabase OAuth)

#### `POST /auth/oauth/login`

Initiate OAuth flow with Supabase. Client receives OAuth URL to redirect to.

```json
{
  "provider": "google"
}
```

Supported providers: `google`, `github`, `microsoft`, etc.

**Response:**
```json
{
  "url": "https://yvpyazoizinxvdyegxlo.supabase.co/auth/v1/authorize?..."
}
```

User browser redirects to this URL, signs in with their provider (Google, GitHub, etc.), then Supabase redirects back to your frontend.

#### `POST /auth/oauth/callback`

After OAuth provider redirects back to frontend, frontend calls this with the OAuth token and user profile.

```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "user": {
    "id": "6ce4583e-39e3-4e4e-9df4-095755146a93",
    "email": "asha@gmail.com",
    "user_metadata": {
      "name": "Asha Rao"
    }
  },
  "role": "manufacturer",
  "company": "Maker Mills",
  "country": "IN"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

Use this `access_token` for all subsequent requests.

#### `GET /auth/me`

Get current user profile. Requires `Authorization: Bearer <access_token>`.

**Response:**
```json
{
  "id": "6ce4583e-39e3-4e4e-9df4-095755146a93",
  "name": "Asha Rao",
  "email": "asha@gmail.com",
  "role": "manufacturer",
  "company": "Maker Mills",
  "country": "IN",
  "is_active": true
}
```

### Listings

#### `POST /listings/`

```json
{
  "material_type": "HDPE plastic",
  "quantity_kg": 12000,
  "purity_pct": 88,
  "location_city": "Mumbai",
  "location_country": "IN",
  "ask_price_per_kg": 0.65,
  "description": "Clean post-industrial HDPE flakes",
  "expires_at": "2026-05-01T00:00:00Z"
}
```

#### `PATCH /listings/{listing_id}/status`

```json
{
  "status": "expired"
}
```

#### `GET /listings/`, `GET /listings/my`, `GET /listings/{listing_id}`, `DELETE /listings/{listing_id}`

No request body.

### AI

#### `POST /ai/classify`

```json
{
  "description": "Clean HDPE flakes from drums",
  "quantity_kg": 10000,
  "purity_pct": 92
}
```

#### `POST /ai/match`

```json
{
  "listing_id": "6ce4583e-39e3-4e4e-9df4-095755146a93"
}
```

#### `POST /ai/market-price`

```json
{
  "material_category": "aluminum",
  "grade": "A1"
}
```

### Buyer Profiles

#### `POST /buyer-profiles/`

```json
{
  "material_needs": "aluminum, copper, plastic",
  "accepted_grades": "A1,A2,B1,B2",
  "accepted_countries": "India,Germany,Taiwan,Brazil",
  "max_price_per_kg": 2.5,
  "min_quantity_kg": 100,
  "max_quantity_kg": 50000
}
```

#### `PATCH /buyer-profiles/me`

Same request body as `POST /buyer-profiles/`.

#### `GET /buyer-profiles/me`

No request body.

### Notifications

#### `GET /notifications/`

Query params only:

- `unread_only: bool = false`
- `limit: int = 50`
- `skip: int = 0`

No request body.

#### `PATCH /notifications/{notification_id}/read`

No request body.

#### `POST /notifications/mark-all-read`

No request body.

### Transactions

#### `POST /transactions/{transaction_id}/buyer-confirms-interest`

Empty JSON body is accepted, but the request model has no fields.

```json
{}
```

#### `POST /transactions/{transaction_id}/propose-price`

No request body.

#### `POST /transactions/{transaction_id}/counter-offer`

```json
{
  "counter_price": 1.75
}
```

#### `POST /transactions/{transaction_id}/accept-price`

Empty JSON body is accepted, but the request model has no fields.

```json
{}
```

#### `GET /transactions/`, `GET /transactions/{transaction_id}`, `GET /transactions/{transaction_id}/audit`, `GET /transactions/{transaction_id}/dpp`, `GET /transactions/{transaction_id}/pricing`

No request body.

#### `POST /transactions/{transaction_id}/lock`

No request body.

### TPQC

#### `POST /tpqc/{transaction_id}/start-inspection`

No request body.

#### `POST /tpqc/{transaction_id}/approve`

```json
{
  "qar_notes": "Moisture within tolerance, grade confirmed."
}
```

#### `POST /tpqc/{transaction_id}/reject`

```json
{
  "reason": "Purity too low; heavy contamination."
}
```

#### `GET /tpqc/pending`, `GET /tpqc/{transaction_id}/qar`

No request body.

## 4) Practical Notes

- The current app uses SQLModel on startup, so these tables are already created automatically when the app runs against Supabase.
- The SQL above is useful when you want to provision the schema manually in Supabase before the app starts.
- Table names follow SQLModel defaults used by the codebase: `user`, `wastelisting`, `buyerprofile`, `transaction`, `negotiationround`, `notification`, and `audittrail`.
