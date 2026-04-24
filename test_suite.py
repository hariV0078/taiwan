#!/usr/bin/env python3
"""
CircularX Backend Comprehensive Test Suite
Automated testing for all endpoints with auth bypass mode
Run: python test_suite.py --base-url http://YOUR_IP:8000
"""

import requests
import json
import argparse
import time
import sys
from typing import Optional, Dict, Any
from uuid import UUID


class TestSuite:
    def __init__(self, base_url: str, verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.verbose = verbose
        self.session = requests.Session()
        self.test_results = {"passed": 0, "failed": 0, "skipped": 0}
        
        # Store IDs for cross-test references
        self.listing_id: Optional[str] = None
        self.transaction_id: Optional[str] = None
        self.notification_id: Optional[str] = None
        self.buyer_user_id: Optional[str] = None
        self.manufacturer_user_id: Optional[str] = None
        
    def _request(self, method: str, endpoint: str, role: str = "admin", body: Dict = None, expected_status: int = None) -> Optional[Dict]:
        """Make HTTP request with role-based auth header."""
        headers = {
            "Content-Type": "application/json",
            "x-test-role": role
        }
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                resp = self.session.get(url, headers=headers)
            elif method.upper() == "POST":
                resp = self.session.post(url, json=body, headers=headers)
            elif method.upper() == "PATCH":
                resp = self.session.patch(url, json=body, headers=headers)
            elif method.upper() == "DELETE":
                resp = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            if expected_status and resp.status_code != expected_status:
                if self.verbose:
                    print(f"  ✗ Expected {expected_status}, got {resp.status_code}")
                    print(f"    Response: {resp.text[:200]}")
                return None
            
            return resp.json() if resp.text else {}
        except Exception as e:
            if self.verbose:
                print(f"  ✗ Request failed: {str(e)}")
            return None

    def test(self, name: str, method: str, endpoint: str, role: str = "admin", body: Dict = None, expected_status: int = 200, extract_id: str = None) -> bool:
        """Run a single test."""
        print(f"  [{method:6}] {endpoint:50}", end=" ")
        
        result = self._request(method, endpoint, role, body, expected_status)
        
        if result is None and expected_status:
            print(f"✗ FAIL")
            self.test_results["failed"] += 1
            return False
        
        if extract_id and result:
            setattr(self, extract_id, result.get("id"))
            if self.verbose:
                print(f"✓ PASS (id={result.get('id')})")
            else:
                print(f"✓ PASS")
        elif result is not None:
            if self.verbose:
                print(f"✓ PASS")
            else:
                print(f"✓ PASS")
            self.test_results["passed"] += 1
            return True
        else:
            print(f"✗ FAIL")
            self.test_results["failed"] += 1
            return False
        
        self.test_results["passed"] += 1
        return True

    def test_negative(self, name: str, method: str, endpoint: str, role: str = "admin", body: Dict = None, expected_status: int = 400) -> bool:
        """Run a negative test (expecting failure)."""
        print(f"  [{method:6}] {endpoint:50} (negative)", end=" ")

        headers = {
            "Content-Type": "application/json",
            "x-test-role": role,
        }
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                resp = self.session.get(url, headers=headers)
            elif method.upper() == "POST":
                resp = self.session.post(url, json=body, headers=headers)
            elif method.upper() == "PATCH":
                resp = self.session.patch(url, json=body, headers=headers)
            elif method.upper() == "DELETE":
                resp = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unknown method: {method}")

            if resp.status_code == expected_status:
                print(f"✓ PASS (correctly failed)")
                self.test_results["passed"] += 1
                return True

            print(f"✗ FAIL (expected {expected_status}, got {resp.status_code})")
            if self.verbose:
                print(f"    Response: {resp.text[:200]}")
            self.test_results["failed"] += 1
            return False
        except Exception as e:
            print(f"✗ FAIL (request error: {str(e)})")
            self.test_results["failed"] += 1
            return False

    # =========================== SECTION A: HEALTH & AUTH ===========================
    def run_section_a(self):
        print("\n=== A. HEALTH & AUTH ===")
        self.test("health", "GET", "/health", expected_status=200)
        
        self.test("me as admin", "GET", "/auth/me", role="admin", expected_status=200)
        self.test("me as buyer", "GET", "/auth/me", role="buyer", expected_status=200)
        self.test("me as manufacturer", "GET", "/auth/me", role="manufacturer", expected_status=200)
        self.test("me as tpqc", "GET", "/auth/me", role="tpqc", expected_status=200)

    # =========================== SECTION B: LISTINGS ===========================
    def run_section_b(self):
        print("\n=== B. LISTINGS ===")
        
        # Create listing as manufacturer
        listing_body = {
            "material_type": "HDPE plastic",
            "quantity_kg": 12000,
            "purity_pct": 88,
            "location_city": "Mumbai",
            "location_country": "IN",
            "ask_price_per_kg": 0.65,
            "description": "Clean post-industrial HDPE flakes"
        }
        result = self._request("POST", "/listings/", role="manufacturer", body=listing_body, expected_status=201)
        if result:
            self.listing_id = result.get("id")
            print(f"  [POST  ] /listings/                                     ✓ PASS (id={self.listing_id})")
            self.test_results["passed"] += 1
        else:
            print(f"  [POST  ] /listings/                                     ✗ FAIL")
            self.test_results["failed"] += 1
            return
        
        # Try create as buyer (should fail)
        self.test_negative("create as buyer", "POST", "/listings/", role="buyer", body=listing_body, expected_status=403)
        
        # List all
        self.test("list active", "GET", "/listings/", expected_status=200)
        
        # My listings
        self.test("my listings", "GET", "/listings/my", role="manufacturer", expected_status=200)
        
        # Get single
        self.test("get single", "GET", f"/listings/{self.listing_id}", expected_status=200)
        
        # Update status
        self.test("update status", "PATCH", f"/listings/{self.listing_id}/status", role="manufacturer", 
                 body={"status": "expired"}, expected_status=200)
        
        # Delete (soft)
        listing_body_2 = {**listing_body, "ask_price_per_kg": 0.75, "description": "Another batch"}
        result = self._request("POST", "/listings/", role="manufacturer", body=listing_body_2, expected_status=201)
        if result:
            listing_id_2 = result.get("id")
            self.test("soft delete", "DELETE", f"/listings/{listing_id_2}", role="manufacturer", expected_status=200)
        
        # Invalid ID
        self.test_negative("get invalid", "GET", "/listings/00000000-0000-0000-0000-000000000000", expected_status=404)

    # =========================== SECTION C: AI ENDPOINTS ===========================
    def run_section_c(self):
        print("\n=== C. AI ENDPOINTS ===")
        
        # Classify
        classify_body = {
            "description": "Clean HDPE flakes from drums",
            "quantity_kg": 10000,
            "purity_pct": 92
        }
        self.test("classify", "POST", "/ai/classify", role="manufacturer", body=classify_body, expected_status=200)
        
        # Missing field
        self.test_negative("classify missing field", "POST", "/ai/classify", role="manufacturer",
                          body={"description": "test", "quantity_kg": 10000}, expected_status=422)
        
        # Low purity
        classify_body_low = {
            "description": "Mixed contaminated plastic scrap",
            "quantity_kg": 5000,
            "purity_pct": 20
        }
        self.test("classify low purity", "POST", "/ai/classify", role="buyer", body=classify_body_low, expected_status=200)
        
        # Market price
        price_body = {
            "material_category": "aluminum",
            "grade": "A1"
        }
        self.test("market price", "POST", "/ai/market-price", role="buyer", body=price_body, expected_status=200)
        
        # Unknown category
        price_body_unknown = {
            "material_category": "unknown_material_xyz",
            "grade": "A1"
        }
        self.test("market price unknown", "POST", "/ai/market-price", role="admin", body=price_body_unknown, expected_status=200)
        
        # Match (requires valid listing)
        if self.listing_id:
            match_body = {"listing_id": self.listing_id}
            result = self._request("POST", "/ai/match", role="manufacturer", body=match_body, expected_status=200)
            if result and isinstance(result, list) and len(result) > 0:
                print(f"  [POST  ] /ai/match                                      ✓ PASS (found {len(result)} matches)")
                self.test_results["passed"] += 1
                # Store first transaction for later tests
                self.transaction_id = result[0].get("transaction_id") or result[0].get("id")
            elif result is not None:
                print(f"  [POST  ] /ai/match                                      ✓ PASS (no matches)")
                self.test_results["passed"] += 1
            else:
                print(f"  [POST  ] /ai/match                                      ✗ FAIL")
                self.test_results["failed"] += 1
        
        # Match as buyer (should fail)
        if self.listing_id:
            self.test_negative("match as buyer", "POST", "/ai/match", role="buyer",
                              body={"listing_id": self.listing_id}, expected_status=403)
        
        # Match invalid listing
        self.test_negative("match invalid listing", "POST", "/ai/match", role="manufacturer",
                          body={"listing_id": "00000000-0000-0000-0000-000000000000"}, expected_status=404)

    # =========================== SECTION D: BUYER PROFILES ===========================
    def run_section_d(self):
        print("\n=== D. BUYER PROFILES ===")
        
        profile_body = {
            "material_needs": "aluminum, copper, plastic",
            "accepted_grades": "A1,A2,B1,B2",
            "accepted_countries": "India,Germany,Taiwan,Brazil",
            "max_price_per_kg": 2.5,
            "min_quantity_kg": 100,
            "max_quantity_kg": 50000
        }
        
        # Create
        headers = {
            "Content-Type": "application/json",
            "x-test-role": "buyer",
        }
        resp = self.session.post(f"{self.base_url}/buyer-profiles/", json=profile_body, headers=headers)
        if resp.status_code in {201, 400}:
            print(f"  [POST  ] /buyer-profiles/                               ✓ PASS")
            self.test_results["passed"] += 1
        else:
            print(f"  [POST  ] /buyer-profiles/                               ✗ FAIL")
            if self.verbose:
                print(f"    Response: {resp.text[:200]}")
            self.test_results["failed"] += 1
        
        # Create again (should fail)
        self.test_negative("create duplicate", "POST", "/buyer-profiles/", role="buyer", body=profile_body, expected_status=400)
        
        # Get
        self.test("get profile", "GET", "/buyer-profiles/me", role="buyer", expected_status=200)
        
        # Update
        profile_body_updated = {**profile_body, "max_price_per_kg": 2.8}
        self.test("update profile", "PATCH", "/buyer-profiles/me", role="buyer", body=profile_body_updated, expected_status=200)
        
        # As manufacturer (should fail)
        self.test_negative("get as manufacturer", "GET", "/buyer-profiles/me", role="manufacturer", expected_status=403)

    # =========================== SECTION E: TRANSACTIONS ===========================
    def run_section_e(self):
        print("\n=== E. TRANSACTIONS & NEGOTIATION ===")
        
        # List
        self.test("list as manufacturer", "GET", "/transactions", role="manufacturer", expected_status=200)
        self.test("list as buyer", "GET", "/transactions", role="buyer", expected_status=200)
        
        if not self.transaction_id:
            print("  ⊘ Skipping transaction negotiation tests (no transaction from match)")
            self.test_results["skipped"] += 1
            return
        
        # Get detail
        self.test("get detail", "GET", f"/transactions/{self.transaction_id}", role="admin", expected_status=200)
        
        # Buyer confirms interest
        result = self._request("POST", f"/transactions/{self.transaction_id}/buyer-confirms-interest", 
                              role="buyer", body={}, expected_status=200)
        if result:
            print(f"  [POST  ] /transactions/{{id}}/buyer-confirms-interest    ✓ PASS")
            self.test_results["passed"] += 1
        else:
            print(f"  [POST  ] /transactions/{{id}}/buyer-confirms-interest    ✗ FAIL")
            self.test_results["failed"] += 1
        
        # Propose price
        result = self._request("POST", f"/transactions/{self.transaction_id}/propose-price",
                              role="admin", body={}, expected_status=200)
        if result:
            print(f"  [POST  ] /transactions/{{id}}/propose-price              ✓ PASS")
            self.test_results["passed"] += 1
        else:
            print(f"  [POST  ] /transactions/{{id}}/propose-price              ✗ FAIL (may be no ZOPA)")
            self.test_results["failed"] += 1
        
        # Counter-offer from seller
        result = self._request("POST", f"/transactions/{self.transaction_id}/counter-offer",
                              role="manufacturer", body={"counter_price": 0.72}, expected_status=200)
        if result:
            print(f"  [POST  ] /transactions/{{id}}/counter-offer (seller)    ✓ PASS")
            self.test_results["passed"] += 1
        else:
            print(f"  [POST  ] /transactions/{{id}}/counter-offer (seller)    ✗ FAIL")
            self.test_results["failed"] += 1
        
        # Counter-offer from buyer
        result = self._request("POST", f"/transactions/{self.transaction_id}/counter-offer",
                              role="buyer", body={"counter_price": 0.74}, expected_status=200)
        if result:
            print(f"  [POST  ] /transactions/{{id}}/counter-offer (buyer)     ✓ PASS")
            self.test_results["passed"] += 1
        else:
            print(f"  [POST  ] /transactions/{{id}}/counter-offer (buyer)     ✗ FAIL")
            self.test_results["failed"] += 1
        
        # Accept price from both sides
        result = self._request("POST", f"/transactions/{self.transaction_id}/accept-price",
                              role="manufacturer", body={}, expected_status=200)
        if result:
            print(f"  [POST  ] /transactions/{{id}}/accept-price (seller)     ✓ PASS")
            self.test_results["passed"] += 1
        
        result = self._request("POST", f"/transactions/{self.transaction_id}/accept-price",
                              role="buyer", body={}, expected_status=200)
        if result:
            print(f"  [POST  ] /transactions/{{id}}/accept-price (buyer)      ✓ PASS")
            self.test_results["passed"] += 1
        
        # Get pricing
        self.test("get pricing", "GET", f"/transactions/{self.transaction_id}/pricing", role="admin", expected_status=200)
        
        # Lock escrow
        result = self._request("POST", f"/transactions/{self.transaction_id}/lock",
                              role="buyer", body={}, expected_status=200)
        if result:
            print(f"  [POST  ] /transactions/{{id}}/lock                       ✓ PASS")
            self.test_results["passed"] += 1
        else:
            print(f"  [POST  ] /transactions/{{id}}/lock                       ✗ FAIL")
            self.test_results["failed"] += 1
        
        # Audit
        self.test("get audit", "GET", f"/transactions/{self.transaction_id}/audit", role="admin", expected_status=200)
        
        # DPP (should not exist yet)
        self.test_negative("get dpp (not ready)", "GET", f"/transactions/{self.transaction_id}/dpp", role="admin", expected_status=404)

    # =========================== SECTION F: TPQC FLOW ===========================
    def run_section_f(self):
        print("\n=== F. TPQC FLOW ===")
        
        # List pending
        self.test("pending inspections", "GET", "/tpqc/pending", role="tpqc", expected_status=200)
        
        if not self.transaction_id:
            print("  ⊘ Skipping TPQC operations (no transaction)")
            self.test_results["skipped"] += 1
            return
        
        # Start inspection
        result = self._request("POST", f"/tpqc/{self.transaction_id}/start-inspection",
                              role="tpqc", body={}, expected_status=200)
        if result:
            print(f"  [POST  ] /tpqc/{{id}}/start-inspection                  ✓ PASS")
            self.test_results["passed"] += 1
        else:
            print(f"  [POST  ] /tpqc/{{id}}/start-inspection                  ✗ FAIL")
            self.test_results["failed"] += 1
        
        # Approve
        result = self._request("POST", f"/tpqc/{self.transaction_id}/approve",
                              role="tpqc",
                              body={"qar_notes": "Moisture within tolerance, grade confirmed."},
                              expected_status=200)
        if result:
            print(f"  [POST  ] /tpqc/{{id}}/approve                           ✓ PASS")
            self.test_results["passed"] += 1
        else:
            print(f"  [POST  ] /tpqc/{{id}}/approve                           ✗ FAIL")
            self.test_results["failed"] += 1
        
        # Get QAR
        self.test("get qar", "GET", f"/tpqc/{self.transaction_id}/qar", role="tpqc", expected_status=200)
        
        # As buyer (should fail)
        self.test_negative("pending as buyer", "GET", "/tpqc/pending", role="buyer", expected_status=403)

    # =========================== SECTION G: NOTIFICATIONS ===========================
    def run_section_g(self):
        print("\n=== G. NOTIFICATIONS ===")
        
        # Get all
        result = self._request("GET", "/notifications", role="buyer", expected_status=200)
        if result and isinstance(result, list) and len(result) > 0:
            self.notification_id = result[0].get("id")
            print(f"  [GET   ] /notifications                                 ✓ PASS ({len(result)} total)")
            self.test_results["passed"] += 1
        elif result is not None:
            print(f"  [GET   ] /notifications                                 ✓ PASS (empty)")
            self.test_results["passed"] += 1
        else:
            print(f"  [GET   ] /notifications                                 ✗ FAIL")
            self.test_results["failed"] += 1
        
        # Unread only
        self.test("unread only", "GET", "/notifications?unread_only=true", role="buyer", expected_status=200)
        
        # Mark as read
        if self.notification_id:
            result = self._request("PATCH", f"/notifications/{self.notification_id}/read",
                                  role="buyer", body={}, expected_status=200)
            if result:
                print(f"  [PATCH ] /notifications/{{id}}/read                  ✓ PASS")
                self.test_results["passed"] += 1
            else:
                print(f"  [PATCH ] /notifications/{{id}}/read                  ✗ FAIL")
                self.test_results["failed"] += 1
        
        # Mark all read
        self.test("mark all read", "POST", "/notifications/mark-all-read", role="buyer", body={}, expected_status=200)

    def run_all(self):
        """Run all test sections."""
        print("=" * 80)
        print("CircularX Backend Test Suite")
        print(f"Base URL: {self.base_url}")
        print("=" * 80)
        
        start_time = time.time()
        
        self.run_section_a()
        self.run_section_b()
        self.run_section_c()
        self.run_section_d()
        self.run_section_e()
        self.run_section_f()
        self.run_section_g()
        
        elapsed = time.time() - start_time
        
        # Summary
        total = self.test_results["passed"] + self.test_results["failed"]
        print("\n" + "=" * 80)
        print(f"SUMMARY: {self.test_results['passed']}/{total} passed, {self.test_results['failed']} failed, {self.test_results['skipped']} skipped")
        print(f"Time: {elapsed:.2f}s")
        print("=" * 80)
        
        return self.test_results["failed"] == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CircularX Backend Test Suite")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of backend")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    suite = TestSuite(args.base_url, verbose=args.verbose)
    success = suite.run_all()
    
    sys.exit(0 if success else 1)
