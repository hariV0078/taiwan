# CircularX Backend Test Suite

Automated comprehensive testing for all backend endpoints with role-based auth bypass for development/testing.

## Prerequisites

- Backend running on http://localhost:8000 (or specify custom URL)
- `AUTH_BYPASS=true` in `.env` (already added)
- Python 3.11+ with `requests` library installed

```bash
pip install requests
```

## Running Tests

### On Windows (PowerShell/CMD)
```powershell
# Run with default URL (127.0.0.1:8000)
python test_suite.py

# Run with custom URL
python test_suite.py --base-url http://YOUR_PUBLIC_IP:8000

# Run with verbose output
python test_suite.py -v
```

### On Linux/Mac
```bash
# Simple
bash run_tests.sh

# Custom URL
bash run_tests.sh http://YOUR_PUBLIC_IP:8000

# Non-verbose (less output)
bash run_tests.sh http://YOUR_PUBLIC_IP:8000 ""
```

## Test Coverage

### A. Health & Auth (4 tests)
- Health check endpoint
- Current user endpoint for each role (admin, buyer, manufacturer, tpqc)

### B. Listings (8 tests)
- Create listing as manufacturer
- Create as buyer (negative test)
- List all active listings
- Get user's listings
- Get single listing
- Update listing status
- Soft delete listing
- Invalid listing ID (negative test)

### C. AI Endpoints (8 tests)
- Material classification
- Missing field validation
- Low purity classification
- Market price lookup
- Unknown category handling
- Match buyers to listing (creates transactions)
- Match as buyer (negative test)
- Invalid listing ID (negative test)

### D. Buyer Profiles (6 tests)
- Create buyer profile
- Duplicate creation (negative test)
- Get profile
- Update profile
- Access as non-buyer (negative test)

### E. Transactions & Negotiation (10 tests)
- List transactions (manufacturer view)
- List transactions (buyer view)
- Get transaction detail
- Buyer confirms interest
- Propose price (AI-calculated ZOPA)
- Counter-offer from seller
- Counter-offer from buyer
- Accept price from both parties
- Get pricing snapshot
- Lock escrow for inspection

### F. TPQC Flow (6 tests)
- List pending inspections
- Start inspection
- Approve with QAR notes
- Get QAR details
- Reject inspection (negative test setup)
- TPQC role enforcement

### G. Notifications (4 tests)
- Get all notifications
- Filter unread only
- Mark single notification as read
- Mark all as read

**Total: 46 test cases covering:**
- ✅ All CRUD operations
- ✅ Role-based access control
- ✅ Business flow (matching → negotiation → escrow → TPQC)
- ✅ AI endpoints (classify, match, market-price)
- ✅ Negative/error cases
- ✅ Cross-endpoint data linking

## How It Works

1. **Role-based auth**: Uses `x-test-role` header to impersonate different user roles
2. **Test chaining**: Captures IDs from responses to use in dependent tests
3. **Business flow**: Tests simulate real user journey (create listing → match → negotiate → lock → inspect)
4. **Negative tests**: Validates error cases (403, 404, 422 responses)

## Example Flow Tested

```
1. Create buyer profile (as buyer)
2. Create listing (as manufacturer)
3. Classify material (AI)
4. Get market price (AI)
5. Match buyers to listing (AI - creates transaction)
6. Buyer confirms interest
7. Propose ZOPA price
8. Counter-offers from both sides
9. Both accept price
10. Lock escrow
11. TPQC inspects and approves
12. Transaction released
13. Check notifications
```

## Sample Output

```
================================================================================
CircularX Backend Test Suite
Base URL: http://127.0.0.1:8000
================================================================================

=== A. HEALTH & AUTH ===
  [GET   ] /health                                       ✓ PASS
  [GET   ] /auth/me                                      ✓ PASS
  [GET   ] /auth/me                                      ✓ PASS
  [GET   ] /auth/me                                      ✓ PASS
  [GET   ] /auth/me                                      ✓ PASS

=== B. LISTINGS ===
  [POST  ] /listings/                                    ✓ PASS (id=550e8400-e29b-41d4-a716-446655440000)
  [POST  ] /listings/                                    ✓ PASS (correctly failed)
  [GET   ] /listings/                                    ✓ PASS
  [GET   ] /listings/my                                  ✓ PASS
  [GET   ] /listings/550e8400-e29b-41d4-a716-446655440000 ✓ PASS
  [PATCH ] /listings/550e8400-e29b-41d4-a716-446655440000/status ✓ PASS
  [DELETE] /listings/550e8400-e29b-41d4-a716-446655440000 ✓ PASS
  [GET   ] /listings/00000000-0000-0000-0000-000000000000 ✓ PASS (correctly failed)

... (more sections)

================================================================================
SUMMARY: 43/46 passed, 0 failed, 3 skipped
Time: 12.45s
================================================================================
```

## Troubleshooting

### "Connection refused"
```
The backend is not running. Start it:
  uvicorn main:app --host 0.0.0.0 --port 8000
```

### "401 Unauthorized / Could not validate credentials"
```
Make sure AUTH_BYPASS=true is set in .env and the app has been restarted.
```

### "Module not found: requests"
```
Install dependencies:
  pip install requests
```

### Tests skipped for transactions/TPQC
```
These require a listing to be matched first. The test automatically creates
and matches a listing, so if they're skipped, the earlier steps failed.
Check the listing creation and AI match tests.
```

## Customization

Edit `test_suite.py` to:
- Change test data (material types, quantities, prices)
- Add new test cases in new `run_section_*()` methods
- Adjust expected HTTP status codes
- Add custom assertions on response bodies

## Important Notes

⚠️ **AUTH_BYPASS is for development only!** Disable in production:
```bash
# In .env
AUTH_BYPASS=false
```

⚠️ **Each test run creates new database entries**. The SQLite database will grow. Reset it:
```bash
rm circularx.db
# Restart backend to recreate schema
```

⚠️ **Credentials exposed in .env** - The shared .env file contains real API keys. Rotate all secrets after testing!

## Integration with CI/CD

To use in GitHub Actions or similar:
```yaml
- name: Run Backend Tests
  run: python test_suite.py --base-url http://localhost:8000
```

Exit code is 0 on success, 1 on any test failure.

