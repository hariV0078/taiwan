# CircularX Redesign Gap Analysis

## Executive Summary

**Current Implementation** is a **fully autonomous AI negotiation platform** with LangGraph-driven price negotiation.  
**Redesigned Spec** is a **human-in-the-loop marketplace** where humans set prices and AI validates.

**Compatibility:** ❌ **FUNDAMENTAL ARCHITECTURE MISMATCH** — Not a small patch, this requires significant service refactoring and new transaction states.

---

## 1. Database Configuration

### Current State
- ✅ **Framework:** FastAPI + SQLModel
- ❌ **Database:** SQLite only (not Supabase)
- ✅ **Vector DB:** ChromaDB (kept)
- ✅ **Audit Trail:** Hash-chained AuditTrail table exists

### Gap
**Missing:** Supabase integration. Currently using local SQLite at `./circularx.db`.

### Action Needed
- [ ] Add `supabase` client library to requirements.txt
- [ ] Update `app/config.py` to read Supabase credentials (URL, API key, service key)
- [ ] Migrate from SQLModel/SQLite to Supabase PostgREST ORM or raw SDK
- [ ] Create migrations for all tables to Supabase

---

## 2. Transaction Status States

### Current States (8)
```
MATCHED 
  ↓
NEGOTIATING        ← AI auto-negotiates
  ↓
AGREED             ← AI found deal
  ↓
LOCKED
  ↓
VERIFIED
  ↓
RELEASED
```
Also: `DISPUTED`, `FAILED`

### Redesigned States (10, with 2 NEW)
```
MATCHED            ← same
  ↓
BUYER_INTERESTED   ← NEW: buyer confirms they want to proceed
  ↓
PRICE_PROPOSED     ← NEW: ZOPA calculated, prices sent to both
  ↓
PRICE_COUNTERED    ← one party counter-offered once (NEW behavior)
  ↓
AGREED             ← both human parties accept
  ↓
LOCKED             ← same
  ↓
INSPECTING         ← RENAMED: was going straight to VERIFIED (needs explicit QAR submission)
  ↓
VERIFIED / DISPUTED
  ↓
RELEASED           ← same
```

### Gap
**Missing:**
- `BUYER_INTERESTED` state — buyer doesn't confirm interest currently
- `PRICE_PROPOSED` state — pricing is automated, no explicit proposal step
- `PRICE_COUNTERED` tracking — AI negotiates silently, no counter-offer audit
- `INSPECTING` state — goes straight to VERIFIED

### Action Needed
- [ ] Add `BUYER_INTERESTED`, `PRICE_PROPOSED`, `PRICE_COUNTERED`, `INSPECTING` to `TransactionStatus` enum
- [ ] Update `Transaction` model to track:
  - `buyer_confirmed_interest_at` (timestamp)
  - `counter_offer_from_seller` (optional float) — seller's one counter-offer
  - `counter_offer_from_buyer` (optional float) — buyer's one counter-offer
  - `counter_offer_expires_at` (optional datetime)
  - `initial_proposed_price` (float) — what ZOPA calculated

---

## 3. Services Architecture

### Current Services
| Service | Purpose | Status |
|---------|---------|--------|
| `classifier.py` | Material classification + restricted check | ✅ Keep |
| `matcher.py` | ChromaDB buyer matching | ✅ Keep |
| `negotiator.py` | LangGraph AI negotiation (5 rounds, agents) | ❌ **REMOVE** |
| `escrow.py` | State transitions + audit hashing | ✅ Keep (extend) |
| `dpp_generator.py` | PDF generation | ✅ Keep |
| `chroma_seed.py` | Buyer profile initialization | ✅ Keep |

### Redesigned Services (New + Modified)
| Service | Purpose | Status |
|---------|---------|--------|
| `classifier.py` | Material classification | ✅ Keep |
| `matcher.py` | ChromaDB buyer matching | ✅ Keep |
| `market_price.py` | **NEW** — commodity reference prices | ❌ Missing |
| `zopa.py` | **NEW** — ZOPA calculation (replaces negotiator) | ❌ Missing |
| `notifier.py` | **NEW** — in-app notifications | ❌ Missing |
| `escrow.py` | State transitions (extend for new states) | ✅ Needs update |
| `dpp_generator.py` | PDF generation | ✅ Keep |
| `chroma_seed.py` | Buyer seeding | ✅ Keep |

### Gap Analysis per Service

#### negotiator.py → **MUST BE REPLACED**
**Current:** LangGraph with 3 nodes (seller, buyer, referee agents) auto-negotiate for up to 5 rounds.

**Redesigned:** Humans negotiate. AI only calculates ZOPA based on human-provided prices.

**Action:**
- [ ] **REMOVE** `negotiator.py` entirely
- [ ] Remove `/ai/negotiate` endpoint (or repurpose as manual price acceptance endpoint)

---

#### market_price.py → **NEW SERVICE**
**Purpose:** Return reference market prices for material categories.

**Current Implementation:** ❌ Missing. Negotiation uses only buyer's `max_price_per_kg` and seller's `ask_price`.

**Redesigned Function Signature:**
```python
def get_market_price_range(material_category: str, grade: str) -> dict:
    """
    Returns market reference price range for a material.
    
    Returns:
    {
        "category": "aluminum",
        "grade": "A1",
        "low_price_per_kg": 1.50,
        "mid_price_per_kg": 1.75,
        "high_price_per_kg": 2.00,
        "source": "LME public data as of 2026-04-21",
        "confidence": 0.95
    }
    """
```

**Data Source for Hackathon:**
- Create `market_prices.json`:
  ```json
  {
    "aluminum": {
      "A1": {"low": 1.50, "mid": 1.75, "high": 2.00},
      "A2": {"low": 1.20, "mid": 1.40, "high": 1.60},
      "B1": {"low": 0.80, "mid": 0.95, "high": 1.10}
    },
    "copper": {
      "A1": {"low": 4.00, "mid": 4.50, "high": 5.00},
      ...
    }
  }
  ```
  Label in UI: **"Reference price as of [date] — source: LME/ICIS public data (hackathon mock)"**

**Validation Rule:**
- If seller's floor > market_high × 1.4 → **warn** "Your price is 40% above market"
- If buyer's ceiling < market_low × 0.6 → **warn** "Your price is 40% below market"
- Do NOT block — only inform

**Action:**
- [ ] Create `services/market_price.py`
- [ ] Create `storage/market_prices.json` with real LME/ICIS data (or mock)
- [ ] Implement `get_market_price_range(category, grade)` function
- [ ] Add validation warnings to both buyer and seller endpoints

---

#### zopa.py → **NEW SERVICE (REPLACES negotiator.py)**
**Purpose:** Calculate Zone of Possible Agreement given human-provided prices.

**Current Implementation:** ❌ Missing. `negotiator.py` does this inline but also auto-negotiates.

**Redesigned Function Signature:**
```python
def calculate_zopa(
    seller_floor_price: float,
    buyer_ceiling_price: float,
    market_low: float,
    market_high: float
) -> dict:
    """
    Calculates ZOPA (zone of possible agreement) between buyer and seller.
    
    Returns:
    {
        "has_zopa": bool,
        "zopa_low": float | None,
        "zopa_high": float | None,
        "proposed_price": float | None,  # midpoint if ZOPA exists
        "reasoning": str
    }
    
    Rules:
    1. If seller_floor > buyer_ceiling → no ZOPA
    2. If ZOPA exists, proposed_price = midpoint of [max(seller_floor, market_low), min(buyer_ceiling, market_high)]
    3. Proposed price must be within market range if market data exists
    """
```

**Example:**
```python
# Seller floor: $2.00/kg, Buyer ceiling: $3.00/kg, Market range: $1.75-$1.95
# ZOPA: [$2.00, $3.00] ∩ [$1.75, $1.95] = [$2.00, $1.95] = INVALID

# Seller floor: $1.50/kg, Buyer ceiling: $2.00/kg, Market range: $1.75-$1.95
# ZOPA: [$1.50, $2.00] ∩ [$1.75, $1.95] = [$1.75, $1.95]
# Proposed: ($1.75 + $1.95) / 2 = $1.85/kg
```

**Action:**
- [ ] Create `services/zopa.py`
- [ ] Implement `calculate_zopa()` function
- [ ] **Remove** all AI negotiation logic from this service
- [ ] Add to `/api/transactions/{id}/propose-price` endpoint

---

#### notifier.py → **NEW SERVICE (IN-APP NOTIFICATIONS)**
**Purpose:** Persist and retrieve user notifications (no email).

**Current Implementation:** ❌ Missing. No notifications at all.

**Database Model:**
```python
# app/models/notification.py
class Notification(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    transaction_id: Optional[UUID] = Field(foreign_key="transaction.id")
    message: str
    notification_type: str  # "MATCH_FOUND", "PRICE_PROPOSED", "BUYER_CONFIRMED", "INSPECTION_PENDING", etc.
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None
```

**Service Functions:**
```python
def create_notification(user_id, message, type, transaction_id=None) → Notification
def get_user_notifications(user_id, unread_only=False) → list[Notification]
def mark_as_read(notification_id) → Notification
```

**Trigger Points (when to notify):**
1. **Seller** after listing created: "Listing created: [material], [qty]kg in [location]"
2. **Buyer** after being matched: "Match found! [Seller Company] has [material] available"
3. **Both** after PRICE_PROPOSED: "Price proposal: $[price]/kg. Review and accept/counter by [deadline]"
4. **Seller** after BUYER_INTERESTED: "[Buyer Company] confirmed interest"
5. **Both** after PRICE_COUNTERED: "[Party] counter-offered $[price]/kg"
6. **Both** after AGREED: "Deal finalized at $[price]/kg. Awaiting escrow lock."
7. **Buyer** after LOCKED: "Please lock escrow to proceed"
8. **TPQC** after LOCKED: "Inspection pending for [material] at [seller location]"
9. **Both** after VERIFIED: "Inspection approved! DPP generated. Download PDF."
10. **Both** after RELEASED: "Transaction complete. ESG impact: [CO2 saved]kg"

**Action:**
- [ ] Create `app/models/notification.py` with `Notification` model
- [ ] Create `services/notifier.py` with CRUD functions
- [ ] Add notifications table to database migration
- [ ] Create `GET /notifications/` endpoint (user polls, filtered by role)
- [ ] Create `PATCH /notifications/{id}/read` endpoint
- [ ] Add notification triggers throughout routers

---

## 4. API Endpoints — What Changes

### Router Changes: `/listings`

#### New Endpoint: Buyer Registration (Profiles)
**Current:** Buyers register via `/auth/register` as role=`buyer`, but no profile created.

**Redesigned:** Need `/buyer-profiles/` endpoints for buyers to set:
- `material_needs` (what they buy)
- `accepted_grades` (A1-C)
- `accepted_countries` (where they source from)
- `max_price_per_kg` (ceiling price for ALL materials — set once at registration)
- `min_quantity_kg`, `max_quantity_kg` (volume constraints)

**New Endpoints:**
- **POST** `/buyer-profiles/` — buyer creates profile (must be role=buyer)
- **GET** `/buyer-profiles/me` — buyer views own profile
- **PATCH** `/buyer-profiles/me` — buyer updates ceiling price or constraints

**Action:**
- [ ] Create `app/routers/buyer_profiles.py`
- [ ] Create `app/models/buyer_profile_update.py` (request/response schemas)

---

### Router Changes: `/ai`
**Current:**
- `POST /ai/classify` — ✅ Keep
- `POST /ai/match` — ✅ Keep (creates MATCHED transactions)
- `POST /ai/negotiate` — ❌ REMOVE (AI no longer negotiates)

**Redesigned: Add Market Price Endpoint**
- **POST** `/ai/market-price?material_category=aluminum&grade=A1` — Get reference price range
  - Returns market low/mid/high + source label + confidence

**Action:**
- [ ] Keep `/ai/classify` and `/ai/match`
- [ ] **Remove** `/ai/negotiate` endpoint
- [ ] Add `/ai/market-price` endpoint (calls `market_price.py`)

---

### Router Changes: `/transactions`

#### New Endpoint: Buyer Confirms Interest
**Current:** Buyer doesn't explicitly confirm interest in matched listing.

**Redesigned:**
- **POST** `/transactions/{id}/buyer-confirms-interest` (buyer only)
  - **Precondition:** status == `MATCHED`
  - **Post-condition:** status → `BUYER_INTERESTED`
  - Action: Send notification to seller
  - Returns: `TransactionOut`

#### New Endpoint: Propose Initial Price (AI Calculates ZOPA)
**Current:** AI negotiates autonomously.

**Redesigned:**
- **POST** `/transactions/{id}/propose-price` (system/admin triggered, not user)
  - **Precondition:** status == `BUYER_INTERESTED`
  - **Request:** None (gets seller_floor from original listing, buyer_ceiling from BuyerProfile)
  - **Action:**
    1. Call `market_price.get_market_price_range()`
    2. Call `zopa.calculate_zopa()`
    3. If has_zopa:
       - Set `Transaction.initial_proposed_price = proposed_price`
       - Update status → `PRICE_PROPOSED`
       - Create notification for both seller and buyer
       - Return: `TransactionOut` with proposal details
    4. If no ZOPA:
       - Update status → `FAILED`
       - Create notification: "No price overlap. Deal failed."
       - Return: error response
  - Returns: `TransactionOut`

#### New Endpoint: Counter-Offer (Single per Party)
**Current:** AI makes counter-offers silently.

**Redesigned:**
- **POST** `/transactions/{id}/counter-offer` (buyer or seller)
  - **Precondition:** status == `PRICE_PROPOSED` AND not already countered by this party
  - **Request:** `{"counter_price": 1.85}`
  - **Action:**
    1. Store counter-offer: `Transaction.counter_offer_from_seller` or `.counter_offer_from_buyer`
    2. Recalculate ZOPA between original proposal and counter
    3. If both parties have countered:
       - Check if `seller_counter > buyer_counter` → FAILED, no ZOPA
       - If `seller_counter ≤ buyer_counter` → can proceed to AGREED
    4. If only one party countered:
       - Update status → `PRICE_COUNTERED`
       - Notify other party: "[Party] counter-offered $[price]/kg"
    5. Return: `TransactionOut`

#### New Endpoint: Accept Final Price
**Current:** AI automatically agrees when price proposal works.

**Redesigned:**
- **POST** `/transactions/{id}/accept-price` (buyer or seller)
  - **Precondition:** status == `PRICE_PROPOSED` OR `PRICE_COUNTERED`
  - **Request:** `{"accept": true}`
  - **Action:**
    1. If other party has already accepted: status → `AGREED`, notify both
    2. If other party hasn't accepted: just mark this party as accepted
    3. Set `Transaction.agreed_price_per_kg` to the accepted price
    4. Create notification: "[Party] accepted the price"
  - Returns: `TransactionOut`

#### Endpoint Changes: `/transactions/{id}/lock` → Add Precondition Check
**Current:** Buyer can lock when status == `AGREED`.

**Redesigned:**
- Add precondition: must be status == `AGREED` AND both parties accepted AND both notified

#### New Endpoint: Get Proposed Price + Counter Offers
**Current:** No endpoint to view price proposals.

**Redesigned:**
- **GET** `/transactions/{id}/pricing` (seller, buyer, admin)
  - Returns:
    ```json
    {
      "market_reference": {
        "low": 1.75,
        "mid": 1.85,
        "high": 1.95
      },
      "seller_floor": 1.50,
      "buyer_ceiling": 2.00,
      "initial_proposed_price": 1.85,
      "seller_counter_offer": null,
      "buyer_counter_offer": null,
      "current_status": "PRICE_PROPOSED"
    }
    ```

**Action:**
- [ ] Add `/transactions/{id}/buyer-confirms-interest` endpoint
- [ ] Add `/transactions/{id}/propose-price` endpoint
- [ ] Add `/transactions/{id}/counter-offer` endpoint
- [ ] Add `/transactions/{id}/accept-price` endpoint
- [ ] Add `/transactions/{id}/pricing` endpoint
- [ ] Remove or repurpose `/ai/negotiate` endpoint

---

### Router Changes: `/tpqc`

#### Renamed State: LOCKED → INSPECTING
**Current:** Transaction goes `LOCKED` → `VERIFIED` immediately when inspector approves.

**Redesigned:** Transaction should go `LOCKED` → `INSPECTING` (when inspector is assigned and starts work) → `VERIFIED` (when QAR approved).

**New Endpoint:**
- **POST** `/tpqc/{id}/start-inspection` (tpqc)
  - **Precondition:** status == `LOCKED`
  - **Post-condition:** status → `INSPECTING`
  - Action: Notify inspector + both parties "Inspection in progress"
  - Returns: `TransactionOut`

**Updated Endpoint:**
- **POST** `/tpqc/{id}/approve` (tpqc)
  - **Precondition:** status == `INSPECTING` (changed from `LOCKED`)
  - **Post-condition:** status → `VERIFIED` → `RELEASED`
  - Rest stays the same

**Action:**
- [ ] Add `INSPECTING` state to `TransactionStatus` enum
- [ ] Add `/tpqc/{id}/start-inspection` endpoint
- [ ] Update `/tpqc/{id}/approve` precondition to check `INSPECTING` not `LOCKED`

---

## 5. Listing Creation Flow — Changes

### Current Flow
1. Seller creates listing with `ask_price`
2. Auto-classified by LLM
3. Listed immediately (unless restricted)
4. Buyer matches automatically via ChromaDB
5. AI negotiates

### Redesigned Flow
1. Seller creates listing with `ask_price` (this is their floor)
2. Auto-classified by LLM
3. Listed immediately (unless restricted)
4. Buyer profile must already exist (registered with ceiling price)
5. AI matches semantically
6. **→ NEW: Buyer confirms interest in match**
7. **→ NEW: System proposes ZOPA price (AI calculates, not negotiates)**
8. **→ NEW: Buyer/Seller counter-offer once (human decision)**
9. **→ NEW: Both must accept (human decision)**
10. Escrow, TPQC, DPP (same as before)

**Change:** Listing still goes to market immediately. But buyer interest is now a gating step.

**Action:**
- [ ] Update `/listings/` POST response to include: "Awaiting buyer confirmation"
- [ ] No changes to `/listings/` creation itself
- [ ] All the gating happens in `/transactions/` endpoints

---

## 6. Database Migrations Needed

### New Tables
- [ ] `Notification` — in-app notifications (user_id, message, type, is_read, transaction_id)

### Modified Tables
- [ ] `Transaction`:
  - Add: `buyer_confirmed_interest_at` (Optional[datetime])
  - Add: `counter_offer_from_seller` (Optional[float])
  - Add: `counter_offer_from_buyer` (Optional[float])
  - Add: `counter_offer_deadline` (Optional[datetime])
  - Add: `initial_proposed_price` (Optional[float])

### Unchanged Tables
- `User`, `WasteListing`, `BuyerProfile`, `NegotiationRound`, `AuditTrail` — kept

---

## 7. Summary: What to Build

### Phase 1: Services (No DB changes needed yet)
- [ ] Create `services/market_price.py` (reads from `market_prices.json`)
- [ ] Create `services/zopa.py` (pure calculation, no state)
- [ ] Create `services/notifier.py` (basic CRUD, but wait for DB)
- [ ] **Remove** `services/negotiator.py`

### Phase 2: Database
- [ ] Add Supabase integration to `config.py`
- [ ] Migrate from SQLite to Supabase (or add Supabase alongside SQLite)
- [ ] Create `Notification` model
- [ ] Update `Transaction` model (add new fields)
- [ ] Run migrations

### Phase 3: API Endpoints
- [ ] Add `/buyer-profiles/` CRUD endpoints
- [ ] Add `/transactions/{id}/buyer-confirms-interest`
- [ ] Add `/transactions/{id}/propose-price`
- [ ] Add `/transactions/{id}/counter-offer`
- [ ] Add `/transactions/{id}/accept-price`
- [ ] Add `/transactions/{id}/pricing`
- [ ] Add `/ai/market-price`
- [ ] Add `/notifications/` endpoints
- [ ] Add `/tpqc/{id}/start-inspection`
- [ ] Update `/tpqc/{id}/approve` precondition
- [ ] **Remove** `/ai/negotiate` endpoint

### Phase 4: Transaction Status States
- [ ] Update `TransactionStatus` enum: add `BUYER_INTERESTED`, `PRICE_PROPOSED`, `PRICE_COUNTERED`, `INSPECTING`
- [ ] Update `escrow.py` state machine validation

### Phase 5: Notifications & Integration
- [ ] Add notification triggers throughout routers
- [ ] Wire up all endpoints to trigger notifications at right times

### Phase 6: Testing
- [ ] Unit tests for `market_price.py`, `zopa.py`, `notifier.py`
- [ ] Integration tests for new endpoints
- [ ] End-to-end flow test: Listing → Match → Interest → ZOPA Proposal → Counter → Accept → Lock → Inspect → Release

---

## Estimated Impact

| Component | Lines of Code | Complexity | Risk |
|-----------|---|---|---|
| market_price.py | 50-100 | Low | Low |
| zopa.py | 80-120 | Medium | Low |
| notifier.py | 100-150 | Low | Low |
| New DB models | 30-50 | Low | Low |
| New API endpoints (7) | 300-500 | Medium | Medium |
| Remove negotiator.py | -300 | Low | Medium (breaking change) |
| Supabase migration | 50-100 | Medium | High |
| Notification triggers | 150-200 | Low | Low |
| **Total** | **~1000-1500** | **Medium** | **Medium-High** |

---

## Honest Assessment

✅ **What's Already Built:** 90% of the platform structure is solid. Classifiers, matchers, auditing, DPP generation, TPQC workflow, and escrow state machines are production-ready.

❌ **What's Wrong:** The negotiation model is wrong. Current system is fully autonomous; redesigned system is human-centric. This is not a patch — it's a deliberate architectural shift away from AI-driven to **human-controlled-with-AI-assistance**.

🎯 **Why It Matters:** Actual B2B marketplaces don't let AI negotiation on their behalf. Humans set their boundaries (floor/ceiling), AI shows fair market rate, humans accept or counter once, then deal. The redesign makes it adoptable by real businesses.

