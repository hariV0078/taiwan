# Deal Intelligence & Autonomous Monitoring

## Overview

CircularX now features an **Autonomous Deal Intelligence Agent** that monitors transactions proactively and intervenes when deals stall. This transforms the system from a reactive matching engine into a true **autonomous broker**.

## Features

### 1. **Stalled Deal Detection**
- Monitors all active transactions for inactivity
- Triggers when negotiations don't progress within threshold (2-5 min configurable)
- Uses transaction state history to determine last activity

### 2. **LLM-Based Analysis**
- When a deal stalls, OpenAI GPT-4o-mini analyzes context:
  - Material type and quantity
  - Price gap between asking and proposed
  - Negotiation round count
  - Seller and buyer company profiles
- Generates risk assessment (high/medium/low)
- Provides specific, actionable recommendations

### 3. **Trust Score System**
- Calculates reputation score for each user (0.0 to 1.0)
- Based on:
  - **40%** - Transaction completion rate
  - **30%** - Negotiation responsiveness (fewer rounds = better)
  - **30%** - Dispute/failure rate
- Scores naturally degrade for bad actors without manual blacklisting
- Used to deprioritize risky parties in future matches

### 4. **Proactive Notifications**
- System automatically sends context-aware notifications to both parties
- Includes AI analysis and specific recommendations
- Encourages deal progression without human intervention

### 5. **Background Scheduler**
- Runs on configurable interval (default 120 seconds)
- Executes deal intelligence cycles automatically
- Can be started, stopped, and reconfigured via API

## Scheduler Control Endpoints

### Start Scheduler
```http
POST /scheduler/start
Content-Type: application/json

{
  "interval_seconds": 120
}
```

**Response** (201):
```json
{
  "success": true,
  "message": "Scheduler started with 120s interval",
  "data": {
    "interval_seconds": 120
  }
}
```

**For demo:** Use 120 seconds (2-minute stall threshold)
**For production:** Use 300 seconds (5-minute stall threshold)

### Stop Scheduler
```http
POST /scheduler/stop
```

### Get Scheduler Status
```http
GET /scheduler/status
```

**Response**:
```json
{
  "success": true,
  "message": "Scheduler status retrieved",
  "data": {
    "status": "running",
    "is_running": true,
    "interval_seconds": 120,
    "jobs": [
      {
        "id": "deal_intelligence_monitor",
        "name": "Deal Intelligence Monitor",
        "next_run": "2026-04-24T10:15:30"
      }
    ]
  }
}
```

### Trigger Immediately
```http
POST /scheduler/trigger
```

**Response**:
```json
{
  "success": true,
  "message": "Deal intelligence cycle triggered",
  "data": {
    "status": "success",
    "stalled_deals": {
      "stalled_deals_found": 2,
      "deals_analyzed": 2,
      "notifications_sent": 4,
      "high_risk_deals": 0,
      "deals": [
        {
          "transaction_id": "abc123...",
          "listing_id": "def456...",
          "material": "HDPE plastic",
          "risk_level": "medium",
          "recommendation": "Suggest price compromise at $0.70/kg"
        }
      ]
    },
    "trust_scores_updated": 8,
    "timestamp": "2026-04-24T10:10:30"
  }
}
```

### Reconfigure Interval
```http
POST /scheduler/reconfigure
Content-Type: application/json

{
  "interval_seconds": 300
}
```

## Trust Score Endpoint

### Get All Trust Scores
```http
GET /deal-intelligence/trust-scores
```

**Response**:
```json
{
  "status": "success",
  "trust_scores": {
    "550e8400-e29b-41d4-a716-446655440000": 0.95,
    "550e8400-e29b-41d4-a716-446655440001": 0.75,
    "550e8400-e29b-41d4-a716-446655440002": 1.0
  }
}
```

## How It Works

### Transaction Lifecycle with Deal Intelligence

```
1. Manufacturer creates listing
   ↓
2. Buyer creates profile
   ↓
3. Manufacturer triggers match
   → Creates transaction (MATCHED state)
   ↓
4. Buyer confirms interest (BUYER_INTERESTED)
   ↓
5. Prices proposed (PRICE_PROPOSED)
   
   *** SCHEDULER MONITORING STARTS ***
   
6. (Optional) Counter-offers (PRICE_COUNTERED)
   
   *** If no activity for threshold, agent triggers: ***
   
   a) Analyzes deal context with LLM
   b) Determines risk level
   c) Generates recommendation
   d) Sends notification to both parties
   
7. Parties accept price (AGREED)
   ↓
8. Buyer locks escrow (LOCKED)
   ↓
9. TPQC inspects
   ↓
10. TPQC approves/rejects
    ↓
11. Trust scores updated based on outcome
```

## Demo Scenario

```bash
python demo_deal_intelligence.py
```

This script demonstrates:
1. ✅ Scheduler running in background
2. ✅ Deal created and enters negotiation
3. ✅ Stall detected after inactivity
4. ✅ LLM analyzes situation
5. ✅ Notification sent with recommendation
6. ✅ Trust scores calculated
7. ✅ System ready for next deal

## Configuration

### Environment Variables

In `.env`:
```
OPENAI_API_KEY=sk-...  # Required for LLM analysis
SCHEDULER_INTERVAL=120  # Seconds between checks (optional, configurable via API)
```

### Default Settings

- Stall threshold: 120 seconds (2 minutes)
- LLM model: gpt-4o-mini (cost-efficient)
- Check interval: Configurable (see endpoints above)
- Trust score update: On every scheduler run

## Performance Notes

- **Lightweight:** Only analyzes transactions in active negotiation states
- **Scalable:** Background scheduler doesn't block API requests
- **Cost-effective:** Uses gpt-4o-mini (~$0.001 per analysis)
- **Failures graceful:** If LLM unavailable, system falls back to heuristic recommendations

## Conceptual Power

This feature demonstrates sophisticated marketplace design:

1. **Incentive alignment:** Bad actors naturally have lower trust scores
2. **Emergent quality:** Trust compounds over time (no manual moderation)
3. **Autonomous operation:** System achieves goals without human oversight
4. **Context-aware:** Recommendations based on actual deal state, not generic rules
5. **Self-correcting:** Each transaction teaches the system

## Visualization & UI

The **QC Authority Portal** (Admin/TPQC Dashboard) provides real-time visibility into the Autonomous Deal Intelligence system:

1. **Reputation Monitoring**: A dedicated panel displays current trust scores for all active users, allowing inspectors to see trust weights at a glance.
2. **Agent Health**: Live status indicator showing if the background scheduler is "ACTIVE" or "PAUSED".
3. **Stall Insights**: Visual breakdown of how many deals are currently under agent monitoring and their respective risk levels.

This ensures that while the system is autonomous, it remains fully transparent to authorized human oversight.

---
**CircularX**: *Waste to Wealth, Autonomously.*

