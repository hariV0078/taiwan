# Frontend API Handoff

## Current Backend Endpoint

Production-like tunnel endpoint:
- https://sound-guiding-mammoth.ngrok-free.app

Local development endpoint:
- http://127.0.0.1:8000

Health check:
- GET /health

## Current Auth Mode

Auth is currently bypassed for frontend testing.

Frontend must send header:
- x-test-role: manufacturer
- x-test-role: buyer
- x-test-role: tpqc
- x-test-role: admin

No bearer token is required in the current implementation.

## Shared Request Headers

- Content-Type: application/json
- x-test-role: one of manufacturer, buyer, tpqc, admin

## Endpoint Groups

### 1) Health and Identity

- GET /health
- GET /auth/me
- POST /auth/register (new user creation)

Register sample:

```json
{
  "email": "newuser@company.com",
  "name": "New User",
  "company": "Their Company Ltd",
  "country": "IN",
  "role": "manufacturer"
}
```

Roles allowed: `manufacturer`, `buyer`, `tpqc`, `admin`

Returns: User object with id, name, email, role, company, country, is_active

Error 409: If user with that email already exists

### 2) Listings

- POST /listings/
- GET /listings/
- GET /listings/my
- GET /listings/{listing_id}
- PATCH /listings/{listing_id}/status
- DELETE /listings/{listing_id}

Create listing sample:

{
  "material_type": "HDPE plastic",
  "quantity_kg": 12000,
  "purity_pct": 88,
  "location_city": "Mumbai",
  "location_country": "IN",
  "ask_price_per_kg": 0.65,
  "description": "Clean post-industrial HDPE flakes"
}

Status patch sample:

{
  "status": "expired"
}

### 3) AI

- POST /ai/classify
- POST /ai/market-price
- POST /ai/match

Classify sample:

{
  "description": "Clean HDPE flakes from drums",
  "quantity_kg": 10000,
  "purity_pct": 92
}

Market price sample:

{
  "material_category": "aluminum",
  "grade": "A1"
}

Match sample:

{
  "listing_id": "<uuid>"
}

### 4) Buyer Profile

- POST /buyer-profiles/
- GET /buyer-profiles/me
- PATCH /buyer-profiles/me

Buyer profile sample:

{
  "material_needs": "aluminum, copper, plastic",
  "accepted_grades": "A1,A2,B1,B2",
  "accepted_countries": "India,Germany,Taiwan,Brazil",
  "max_price_per_kg": 2.5,
  "min_quantity_kg": 100,
  "max_quantity_kg": 50000
}

### 5) Transactions and Negotiation

- GET /transactions/
- GET /transactions/{transaction_id}
- POST /transactions/{transaction_id}/buyer-confirms-interest
- POST /transactions/{transaction_id}/propose-price
- POST /transactions/{transaction_id}/counter-offer
- POST /transactions/{transaction_id}/accept-price
- GET /transactions/{transaction_id}/pricing
- POST /transactions/{transaction_id}/lock
- GET /transactions/{transaction_id}/audit
- GET /transactions/{transaction_id}/dpp

Counter-offer sample:

{
  "counter_price": 0.74
}

Accept-price sample:

{}

### 6) TPQC

- GET /tpqc/pending
- POST /tpqc/{transaction_id}/start-inspection
- POST /tpqc/{transaction_id}/approve
- POST /tpqc/{transaction_id}/reject
- GET /tpqc/{transaction_id}/qar

Approve sample:

{
  "qar_notes": "Moisture within tolerance, grade confirmed."
}

Reject sample:

{
  "reason": "Purity too low; heavy contamination."
}

### 7) Notifications

- GET /notifications/
- PATCH /notifications/{notification_id}/read
- POST /notifications/mark-all-read

mark-all-read sample:

{}

## Suggested Frontend Flow

1. Call GET /health
2. Call GET /auth/me with x-test-role based on selected test persona
3. Manufacturer creates listing via POST /listings/
4. Buyer updates profile via POST or PATCH /buyer-profiles/me flow
5. Manufacturer triggers matching via POST /ai/match
6. Buyer and manufacturer complete negotiation endpoints
7. Buyer locks escrow
8. TPQC processes inspection and approval/rejection
9. Frontend polling for notifications and transaction updates

## Role Notes

- manufacturer: create/manage listings, trigger matching
- buyer: maintain buyer profile, negotiation actions, lock escrow
- tpqc: pending inspections, approve/reject, read QAR
- admin: broad visibility for monitoring and debug

## Verified Status

Current local suite run:
- 32 passed
- 0 failed
- 2 skipped (dependent negotiation branches when transaction not in required state)
