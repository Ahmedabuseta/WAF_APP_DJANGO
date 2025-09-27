#!/bin/bash

echo "🛡️ Simple WAF Test Examples"
echo "============================"
echo ""

WAF_SERVER="127.0.0.1:8000"
TEST_SITE="testo"

echo "Server: $WAF_SERVER"
echo "Test Site: $TEST_SITE"
echo ""

# Test 1: Safe request (should be forwarded to backend)
echo "✅ Test 1: Safe Request (should forward to backend)"
echo "curl -v 'http://$WAF_SERVER/home' -H 'Host: $TEST_SITE'"
curl -v "http://$WAF_SERVER/home" -H "Host: $TEST_SITE"
echo ""
echo "----------------------------------------"
echo ""

# Test 2: SQL Injection (should be blocked and redirect to your blocked page)
echo "🚫 Test 2: SQL Injection Attack (should redirect to blocked page)"
echo "curl -v 'http://$WAF_SERVER/products?id=1' UNION SELECT * FROM users--' -H 'Host: $TEST_SITE'"
curl -v "http://$WAF_SERVER/products?id=1%27%20UNION%20SELECT%20*%20FROM%20users--" -H "Host: $TEST_SITE"
echo ""
echo "----------------------------------------"
echo ""

# Test 3: XSS Attack (should be blocked)
echo "🚫 Test 3: XSS Attack (should redirect to blocked page)"
echo "curl -v 'http://$WAF_SERVER/search?q=<script>alert(\"xss\")</script>' -H 'Host: $TEST_SITE'"
curl -v "http://$WAF_SERVER/search?q=%3Cscript%3Ealert(%22xss%22)%3C/script%3E" -H "Host: $TEST_SITE"
echo ""
echo "----------------------------------------"
echo ""

# Test 4: Path Traversal (should be blocked)
echo "🚫 Test 4: Path Traversal (should redirect to blocked page)"
echo "curl -v 'http://$WAF_SERVER/files?path=../../../etc/passwd' -H 'Host: $TEST_SITE'"
curl -v "http://$WAF_SERVER/files?path=../../../etc/passwd" -H "Host: $TEST_SITE"
echo ""
echo "----------------------------------------"
echo ""

# Test 5: Direct access to blocked page (should show your video page)
echo "🎬 Test 5: Direct Blocked Page Access (should show video page)"
echo "curl -v 'http://$WAF_SERVER/blocked/?reason=Test&rule=Manual&site=$TEST_SITE'"
curl -v "http://$WAF_SERVER/blocked/?reason=Test&rule=Manual&site=$TEST_SITE"
echo ""
echo "----------------------------------------"
echo ""

echo "📋 Expected Results:"
echo "✅ Safe requests: Should be forwarded to backend (or 404 if backend not running)"
echo "🚫 Attack requests: Should return 302 redirect to /blocked/"
echo "🎬 Blocked page: Should display with video functionality"
echo ""
echo "🔍 To follow redirects and see blocked page content:"
echo "curl -L 'http://$WAF_SERVER/test?attack=yes' -H 'Host: $TEST_SITE'"