"""
Demo script: Autonomous Deal Intelligence in Action

This script demonstrates the predictive and proactive AI features:
1. Create a manufacturer listing
2. Create a buyer profile
3. Trigger a match
4. Watch as the deal intelligence agent detects stalled negotiations
5. Receive context-aware recommendations automatically
"""

import time
import json
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

# Test users
MANUFACTURER_HEADERS = {"x-test-role": "manufacturer"}
BUYER_HEADERS = {"x-test-role": "buyer"}
ADMIN_HEADERS = {"x-test-role": "admin"}


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def demo():
    """Run the autonomous deal intelligence demo."""
    
    print_section("AUTONOMOUS DEAL INTELLIGENCE DEMO")
    print("This demonstrates how CircularX works as a true autonomous broker:\n")
    print("✓ System monitors deals proactively")
    print("✓ AI analyzes stalled negotiations in real-time")
    print("✓ Intelligent recommendations sent automatically")
    print("✓ Trust scores compound over transaction history\n")
    
    # === STEP 1: Scheduler Status ===
    print_section("Step 1: Check Scheduler Status")
    
    response = requests.get(f"{BASE_URL}/scheduler/status")
    status = response.json()
    print(f"Status: {status['data']['status']}")
    print(f"Running: {status['data']['is_running']}")
    print(f"Check interval: {status['data']['interval_seconds']}s")
    print(f"Jobs: {status['data']['jobs']}")
    
    # === STEP 2: Create Manufacturer & Listing ===
    print_section("Step 2: Manufacturer Creates a Listing")
    
    listing_data = {
        "material_type": "HDPE plastic flakes",
        "quantity_kg": 15000,
        "purity_pct": 88,
        "location_city": "Mumbai",
        "location_country": "IN",
        "ask_price_per_kg": 0.68,
        "description": "Premium post-industrial HDPE flakes, consistently high quality"
    }
    
    response = requests.post(
        f"{BASE_URL}/listings/",
        json=listing_data,
        headers=MANUFACTURER_HEADERS
    )
    listing = response.json()
    listing_id = listing["id"]
    
    print(f"Listing created: {listing_id}")
    print(f"  Material: {listing['material_type']}")
    print(f"  Quantity: {listing['quantity_kg']} kg")
    print(f"  Asking price: ${listing['ask_price_per_kg']}/kg")
    print(f"  Status: {listing['status']}")
    
    # Check if listing is blocked by AI (normal behavior for demo)
    if listing['status'] == 'blocked':
        print("  (AI blocked this listing - adjusting parameters)\n")
        
        # Try with different parameters
        listing_data = {
            "material_type": "Aluminum scrap",
            "quantity_kg": 8000,
            "purity_pct": 92,
            "location_city": "Mumbai",
            "location_country": "IN",
            "ask_price_per_kg": 1.50,
            "description": "Clean aluminum extrusion offcuts"
        }
        
        response = requests.post(
            f"{BASE_URL}/listings/",
            json=listing_data,
            headers=MANUFACTURER_HEADERS
        )
        listing = response.json()
        listing_id = listing["id"]
        
        print(f"New listing created: {listing_id}")
        print(f"  Material: {listing['material_type']}")
        print(f"  Quantity: {listing['quantity_kg']} kg")
        print(f"  Asking price: ${listing['ask_price_per_kg']}/kg")
        print(f"  Status: {listing['status']}")
    
    # === STEP 3: Create Buyer Profile ===
    print_section("Step 3: Buyer Creates Profile")
    
    buyer_profile_data = {
        "material_needs": "Aluminum, HDPE, LDPE, plastic waste",
        "accepted_grades": "A1,A2,B1",
        "accepted_countries": "IN,BD,PK,DE",
        "max_price_per_kg": 2.50,
        "min_quantity_kg": 5000,
        "max_quantity_kg": 50000
    }
    
    response = requests.post(
        f"{BASE_URL}/buyer-profiles/",
        json=buyer_profile_data,
        headers=BUYER_HEADERS
    )
    buyer_profile = response.json()
    
    print(f"Buyer profile created")
    if 'material_needs' in buyer_profile:
        print(f"  Material needs: {buyer_profile['material_needs']}")
    if 'max_price_per_kg' in buyer_profile:
        print(f"  Max price: ${buyer_profile['max_price_per_kg']}/kg")
    if 'min_quantity_kg' in buyer_profile:
        print(f"  Quantity range: {buyer_profile['min_quantity_kg']} - {buyer_profile['max_quantity_kg']} kg")
    
    # === STEP 4: Get Existing Transaction or Create Match ===
    print_section("Step 4: Create or Get Existing Transaction")
    
    # Try to get existing transactions
    response = requests.get(
        f"{BASE_URL}/transactions/",
        headers=MANUFACTURER_HEADERS
    )
    
    transactions = response.json() if isinstance(response.json(), list) else response.json().get("transactions", [])
    
    # Filter for active transactions
    active_transactions = [t for t in transactions if t.get('status') in ['MATCHED', 'BUYER_INTERESTED', 'PRICE_PROPOSED']]
    
    if active_transactions:
        transaction = active_transactions[0]
        transaction_id = transaction['id']
        print(f"Using existing transaction: {transaction_id}")
        print(f"  Status: {transaction['status']}")
    else:
        # Try match again
        match_request = {"listing_id": listing_id}
        response = requests.post(
            f"{BASE_URL}/ai/match",
            json=match_request,
            headers=MANUFACTURER_HEADERS
        )
        
        match_result = response.json()
        
        if "matches" in match_result and len(match_result["matches"]) > 0:
            transaction_id = match_result["matches"][0]["transaction_id"]
            print(f"Match found! Transaction created: {transaction_id}")
        else:
            print(f"Match response: {match_result}")
            print("\nNo matches found. Creating synthetic transaction for demo...")
            print("Skipping rest of demo.")
            return
    
    # === STEP 5: Start Negotiation ===
    print_section("Step 5: Buyer Confirms Interest (Deal Enters Negotiation)")
    
    response = requests.post(
        f"{BASE_URL}/transactions/{transaction_id}/buyer-confirms-interest",
        json={},
        headers=BUYER_HEADERS
    )
    
    if response.status_code == 200:
        transaction = response.json()
        print(f"Buyer confirmed interest")
        print(f"  Status: {transaction['status']}")
        print(f"  Time: {transaction['buyer_confirmed_interest_at']}")
    
    # === STEP 6: Propose Price ===
    print_section("Step 6: AI Calculates ZOPA & Proposes Price")
    
    response = requests.post(
        f"{BASE_URL}/transactions/{transaction_id}/propose-price",
        json={},
        headers=MANUFACTURER_HEADERS
    )
    
    if response.status_code == 200:
        transaction = response.json()
        print(f"Price proposal generated")
        print(f"  Proposed price: ${transaction['initial_proposed_price']}/kg")
        print(f"  Status: {transaction['status']}")
    
    # === STEP 7: Wait for Stall Detection ===
    print_section("Step 7: Wait for Deal Intelligence Detection")
    print("Monitoring for stalled negotiations...")
    print("(Scheduler configured to check every 120 seconds)")
    print("Demo uses 2-minute stall threshold for visibility.\n")
    
    print("⏱️  Waiting 5 seconds before triggering scheduler...")
    time.sleep(5)
    
    # === STEP 8: Manually Trigger Scheduler ===
    print_section("Step 8: Manually Trigger Deal Intelligence Cycle")
    
    response = requests.post(f"{BASE_URL}/scheduler/trigger")
    result = response.json()
    
    print(f"Trigger result: {result['data']['status']}")
    print(f"\nStalled Deals Detected:")
    stalled_data = result['data'].get('stalled_deals', {})
    print(f"  - Found: {stalled_data.get('stalled_deals_found', 0)}")
    print(f"  - Analyzed: {stalled_data.get('deals_analyzed', 0)}")
    print(f"  - Notifications sent: {stalled_data.get('notifications_sent', 0)}")
    print(f"  - High risk: {stalled_data.get('high_risk_deals', 0)}")
    
    if stalled_data.get('deals'):
        print(f"\nDetailed Analysis:")
        for deal in stalled_data['deals']:
            print(f"\n  Transaction: {deal['transaction_id'][:8]}...")
            print(f"  Material: {deal['material']}")
            print(f"  Risk Level: {deal['risk_level']}")
            print(f"  Recommendation: {deal['recommendation']}")
    
    # === STEP 9: Check Trust Scores ===
    print_section("Step 9: Trust Score System (Reputation)")
    
    response = requests.get(f"{BASE_URL}/deal-intelligence/trust-scores")
    scores = response.json()
    
    print("User Trust Scores (0.0 = high risk, 1.0 = fully trusted):")
    for user_id, score in list(scores['trust_scores'].items())[:5]:
        print(f"  {user_id[:8]}... : {score:.2f}")
    
    # === STEP 10: Check Notifications ===
    print_section("Step 10: Notifications Sent to Parties")
    
    response = requests.get(f"{BASE_URL}/notifications/", headers=BUYER_HEADERS)
    notifications = response.json()
    
    if notifications.get("notifications"):
        print(f"Buyer received {len(notifications['notifications'])} notifications:")
        for notif in notifications['notifications'][-3:]:  # Last 3
            print(f"\n  Title: {notif.get('title', 'N/A')}")
            print(f"  Type: {notif['notification_type']}")
            print(f"  Message: {notif['message'][:100]}...")
            print(f"  Read: {notif['is_read']}")
    
    # === FINAL INSIGHTS ===
    print_section("Key Insights: Why This is 'Autonomous'")
    
    print("""
✅ PREDICTIVE: System doesn't just react to events. It monitors background states
   and predicts deal breakdowns before they happen.

✅ PROACTIVE: When stalls are detected, AI analyzes context (prices, history,
   market conditions) and sends intelligent nudges automatically.

✅ INTELLIGENT: Trust scores compound over time. After 10 transactions, bad actors
   are naturally deprioritized in matches without manual blacklisting.

✅ SELF-MANAGING: Backend runs deal intelligence independently on a schedule.
   Frontend gets notifications of system-generated insights, not raw data.

This transforms your system from "matching engine" → "autonomous broker"
    """)
    
    print_section("Demo Complete")
    print("The deal intelligence agent is now running in the background.")
    print(f"Check scheduler status: POST {BASE_URL}/scheduler/status")
    print(f"Reconfigure interval: POST {BASE_URL}/scheduler/reconfigure")
    print(f"View trust scores: GET {BASE_URL}/deal-intelligence/trust-scores")
    

if __name__ == "__main__":
    try:
        demo()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
