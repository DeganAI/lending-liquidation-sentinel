#!/bin/bash

# Test script for Lending Liquidation Sentinel endpoints
# Usage: ./test_endpoints.sh [BASE_URL]

BASE_URL=${1:-"http://localhost:8000"}

echo "=========================================="
echo "Lending Liquidation Sentinel - Endpoint Tests"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo "Test 1: Health Check"
echo "GET $BASE_URL/health"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - HTTP $http_code"
    echo "$body" | jq .
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    echo "$body"
fi
echo ""

# Test 2: Landing Page
echo "Test 2: Landing Page"
echo "GET $BASE_URL/"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/")
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - HTTP $http_code"
    echo "HTML content received ($(echo "$response" | head -n-1 | wc -c) bytes)"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Test 3: agent.json (HTTP 200)
echo "Test 3: AP2 Metadata (agent.json)"
echo "GET $BASE_URL/.well-known/agent.json"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/.well-known/agent.json")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - HTTP $http_code"
    echo "$body" | jq '{name, description, version, payments: .payments[0]}'
else
    echo -e "${RED}✗ FAIL${NC} - Expected HTTP 200, got $http_code"
    echo "$body"
fi
echo ""

# Test 4: x402 Metadata (HTTP 402)
echo "Test 4: x402 Protocol Metadata"
echo "GET $BASE_URL/.well-known/x402"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/.well-known/x402")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "402" ]; then
    echo -e "${GREEN}✓ PASS${NC} - HTTP $http_code"
    echo "$body" | jq '.accepts[0]'
else
    echo -e "${RED}✗ FAIL${NC} - Expected HTTP 402, got $http_code"
    echo "$body"
fi
echo ""

# Test 5: Monitor Endpoint (will return 402 or 503 depending on FREE_MODE)
echo "Test 5: Monitor Lending Position"
echo "POST $BASE_URL/lending/monitor"

test_request='{
  "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "protocol_ids": ["aave_v3"],
  "chain_id": 1
}'

response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/lending/monitor" \
  -H "Content-Type: application/json" \
  -d "$test_request")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ] || [ "$http_code" = "402" ] || [ "$http_code" = "503" ]; then
    echo -e "${YELLOW}⚠ INFO${NC} - HTTP $http_code (expected if FREE_MODE=false or no position)"
    echo "$body" | jq . 2>/dev/null || echo "$body"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    echo "$body"
fi
echo ""

# Test 6: AP2 Entrypoint (HTTP 402 without payment)
echo "Test 6: AP2 Entrypoint"
echo "POST $BASE_URL/entrypoints/lending-liquidation-sentinel/invoke"

response=$(curl -s -w "\n%{http_code}" -X POST \
  "$BASE_URL/entrypoints/lending-liquidation-sentinel/invoke" \
  -H "Content-Type: application/json" \
  -d "$test_request")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ] || [ "$http_code" = "402" ] || [ "$http_code" = "503" ]; then
    echo -e "${YELLOW}⚠ INFO${NC} - HTTP $http_code (expected if FREE_MODE=false or no position)"
    echo "$body" | jq . 2>/dev/null || echo "$body"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    echo "$body"
fi
echo ""

# Test 7: Invalid Protocol
echo "Test 7: Invalid Protocol Validation"
echo "POST $BASE_URL/lending/monitor (invalid protocol)"

invalid_request='{
  "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "protocol_ids": ["invalid_protocol"],
  "chain_id": 1
}'

response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/lending/monitor" \
  -H "Content-Type: application/json" \
  -d "$invalid_request")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "400" ] || [ "$http_code" = "402" ]; then
    echo -e "${GREEN}✓ PASS${NC} - HTTP $http_code (validation working)"
    echo "$body" | jq . 2>/dev/null || echo "$body"
else
    echo -e "${RED}✗ FAIL${NC} - Expected HTTP 400/402, got $http_code"
    echo "$body"
fi
echo ""

# Test 8: HEAD method support
echo "Test 8: HEAD Method Support"
echo "HEAD $BASE_URL/.well-known/agent.json"
head_code=$(curl -s -I "$BASE_URL/.well-known/agent.json" | grep HTTP | awk '{print $2}')

if [ "$head_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - HEAD returns HTTP $head_code"
else
    echo -e "${RED}✗ FAIL${NC} - HEAD returns HTTP $head_code (expected 200)"
fi
echo ""

# Summary
echo "=========================================="
echo "Test Suite Complete"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Fix any failing tests"
echo "2. Deploy to Railway"
echo "3. Test production endpoint"
echo "4. Register on x402scan"
echo ""
