#!/bin/bash
# Run CircularX backend test suite

BASE_URL="${1:-http://127.0.0.1:8000}"
VERBOSE="${2:--v}"

echo "Starting CircularX Backend Test Suite..."
echo "Base URL: $BASE_URL"
echo ""

python test_suite.py --base-url "$BASE_URL" $VERBOSE

exit $?
