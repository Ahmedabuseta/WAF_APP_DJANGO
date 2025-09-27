#!/bin/bash
# Test script to verify WAF integration with backend app

echo "🧪 WAF Integration Test Script"
echo "=============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local test_name="$1"
    local url="$2"
    local expected_status="$3"
    local host_header="$4"
    
    echo -n "Testing $test_name... "
    
    if [ -n "$host_header" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -H "Host: $host_header" "$url" 2>/dev/null)
    else
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$url" 2>/dev/null)
    fi
    
    http_code=$(echo $response | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    
    if [ "$http_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $http_code)"
    else
        echo -e "${RED}❌ FAIL${NC} (Expected $expected_status, got $http_code)"
    fi
}

echo "1️⃣  Testing Direct Backend Access"
echo "--------------------------------"
test_endpoint "Homepage" "http://127.0.0.1:3000/" 200
test_endpoint "API endpoint" "http://127.0.0.1:3000/api/test" 200
test_endpoint "Form page" "http://127.0.0.1:3000/form" 200
test_endpoint "Headers page" "http://127.0.0.1:3000/headers" 200
test_endpoint "Error page" "http://127.0.0.1:3000/error" 500

echo ""
echo "2️⃣  Testing WAF Forwarding (requires WAF running on port 80)"
echo "-----------------------------------------------------------"
test_endpoint "WAF → Backend homepage" "http://localhost/" 200 "example.com"
test_endpoint "WAF → Backend API" "http://localhost/api/test" 200 "example.com"
test_endpoint "WAF → Backend form" "http://localhost/form" 200 "example.com"

echo ""
echo "3️⃣  Testing WAF Security Rules"
echo "------------------------------"
test_endpoint "SQL Injection (should block)" "http://localhost/?test=1' UNION SELECT * FROM users--" 403 "example.com"
test_endpoint "XSS Attack (should block)" "http://localhost/?search=<script>alert('xss')</script>" 403 "example.com"
test_endpoint "Path Traversal (should block)" "http://localhost/../../../etc/passwd" 403 "example.com"

echo ""
echo "4️⃣  Testing WAF Admin Interface"
echo "-------------------------------"
test_endpoint "WAF Admin Login" "http://waf-admin.localhost/login/" 200

echo ""
echo "📋 Setup Checklist:"
echo "==================="
echo "✅ Backend app running on port 3000"
echo "⚠️  WAF running on port 8000 (python manage.py runserver 0.0.0.0:8000)"
echo "⚠️  Nginx running on port 80 (sudo systemctl start nginx)"
echo "⚠️  Hosts file configured (127.0.0.1 example.com waf-admin.localhost)"
echo "⚠️  Site configured in WAF (Domain: example.com, Backend: http://127.0.0.1:3000)"
echo ""
echo "💡 If tests fail, check that all services are running and configured correctly."