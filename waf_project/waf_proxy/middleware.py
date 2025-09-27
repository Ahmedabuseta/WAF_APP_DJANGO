import time
import re
import logging
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from .models import Site, SiteRule, RequestLog, RateLimit

# Get logger for this module
logger = logging.getLogger(__name__)

class WAFMiddleware(MiddlewareMixin):
    """
    Web Application Firewall Middleware
    Intercepts requests and applies security rules
    """

    # Note: Bypass logic is now handled in should_bypass_middleware()
    # using HOST-AWARE logic instead of this simple path list

    def process_request(self, request):
        start_time = time.time()
        request_id = f"{int(start_time * 1000000)}"  # Unique request ID

        logger.info("==============================================")
        logger.info(f"🚀 [REQ-{request_id}] NEW REQUEST: {request.method} {request.get_full_path()} from {request.get_host()}")
        logger.debug(f"📊 [REQ-{request_id}] User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")

        # CRITICAL: Check exempt paths FIRST before any processing
        # This prevents WAF from interfering with CSRF tokens on login/admin routes
        logger.debug(f"🔍 [REQ-{request_id}] Checking if path should bypass WAF: {request.path}")
        if self.should_bypass_middleware(request):
            logger.info(f"⏭️  [REQ-{request_id}] BYPASSING WAF - Exempt path: {request.path}")
            return None

        logger.info(f"🛡️  [REQ-{request_id}] Processing through WAF protection")

        # Get client IP
        ip_address = self.get_client_ip(request)
        logger.debug(f"🌐 [REQ-{request_id}] Client IP: {ip_address}")

        # Find site by domain
        host = request.get_host().split(':')[0]
        logger.debug(f"🔎 [REQ-{request_id}] Looking up site for host: {host}")
        site = self.get_site_by_domain(host)

        if not site:
            logger.info(f"📋 [REQ-{request_id}] No site configuration found for host: {host}")
            logger.info(f"🏠 [REQ-{request_id}] This appears to be admin/management interface - continue to Django")
            return None

        if not site.is_active:
            logger.warning(f"❌ [REQ-{request_id}] Site found but inactive: {site.domain} (ID: {site.id})")
            logger.info(f"🏠 [REQ-{request_id}] Inactive site - continue to Django")
            return None

        logger.info(f"✅ [REQ-{request_id}] Site found: {site.domain} (ID: {site.id}) -> Backend: {site.backend_url}")
        logger.info(f"🛡️  [REQ-{request_id}] This is a PROTECTED SITE - applying WAF rules")

        # Get active rules for this site
        logger.debug(f"📋 [REQ-{request_id}] Loading active rules for site: {site.domain}")
        rules = SiteRule.objects.filter(
            site=site,
            is_active=True
        ).select_related('rule')

        rule_count = rules.count()
        logger.debug(f"📋 [REQ-{request_id}] Found {rule_count} active rules to check")

        # Check rate limiting first
        logger.debug(f"⏱️  [REQ-{request_id}] Checking rate limits for IP: {ip_address}")
        if self.check_rate_limit(site, ip_address):
            logger.warning(f"🚫 [REQ-{request_id}] RATE LIMITED - IP: {ip_address}")
            self.log_request(request, site, 'RATE_LIMITED', None, start_time, ip_address)

            # Redirect to OUR WAF rate limited page (not user's backend)
            params = urlencode({
                'reason': 'Rate limit exceeded',
                'rule': 'Rate Limiting',
                'url': request.build_absolute_uri(),
                'site': site.domain,
            })
            # Force redirect to WAF server's rate limited page (our server)
            rate_limited_url = f"{reverse('rate_limited')}?{params}"
            logger.info(f"🚫 [REQ-{request_id}] Redirecting to WAF rate limited page: {rate_limited_url}")
            return HttpResponseRedirect(rate_limited_url)

        logger.debug(f"✅ [REQ-{request_id}] Rate limit check passed")

        # Check security rules
        logger.debug(f"🔍 [REQ-{request_id}] Starting security rule evaluation")
        for i, site_rule in enumerate(rules):
            rule = site_rule.rule
            logger.debug(f"🔍 [REQ-{request_id}] Checking rule {i+1}/{rule_count}: {rule.name} ({rule.rule_type})")

            if self.matches_rule(request, rule):
                action = site_rule.custom_action or rule.action
                logger.warning(f"🚫 [REQ-{request_id}] RULE MATCHED: {rule.name} -> Action: {action}")

                # Log the blocked request
                self.log_request(request, site, 'BLOCKED', rule, start_time, ip_address)

                if action == 'BLOCK':
                    logger.error(f"🔒 [REQ-{request_id}] REQUEST BLOCKED by rule: {rule.name}")

                    # Redirect to OUR WAF blocked page (not user's backend)
                    params = urlencode({
                        'reason': self.get_block_reason(rule.rule_type),
                        'rule': rule.name,
                        'url': request.build_absolute_uri(),
                        'site': site.domain,
                    })
                    # Force redirect to WAF server's blocked page (our server)
                    blocked_url = f"{reverse('blocked_request')}?{params}"
                    logger.info(f"🚫 [REQ-{request_id}] Redirecting to WAF blocked page: {blocked_url}")
                    return HttpResponseRedirect(blocked_url)
                elif action == 'LOG':
                    logger.warning(f"📝 [REQ-{request_id}] Rule matched but logging only: {rule.name}")
                    break
            else:
                logger.debug(f"✅ [REQ-{request_id}] Rule passed: {rule.name}")

        logger.info(f"✅ [REQ-{request_id}] All security checks passed - Request allowed")

        # Store site in request for later use
        request.waf_site = site
        request.waf_start_time = start_time
        request.waf_ip = ip_address
        request.waf_request_id = request_id

        logger.debug(f"📦 [REQ-{request_id}] Stored WAF data in request object")
        logger.info(f"🎯 [REQ-{request_id}] WAF processing complete - Forwarding to proxy middleware")

        return None

    def should_bypass_middleware(self, request):
        """
        Check if the request should bypass WAF middleware.
        NEW APPROACH: Only bypass static files, everything else goes through WAF.
        """
        path = request.path
        host = request.get_host().split(':')[0]  # Remove port

        logger.debug(f"🔍 Checking bypass rules for HOST: {host}, PATH: {path}")

        # ONLY bypass static/system files - everything else goes through WAF
        system_paths = [
            '/static/',
            '/media/',
            '/favicon.ico',
            '/robots.txt',
        ]

        for exempt_path in system_paths:
            if path.startswith(exempt_path):
                logger.debug(f"✅ System file bypass: {exempt_path}")
                return True

        # ALL OTHER requests (including admin) go through WAF middleware
        logger.debug(f"🛡️ ALL requests go through WAF - HOST: {host}, PATH: {path}")
        return False

    def process_response(self, request, response):
        # Log allowed requests
        if hasattr(request, 'waf_site'):
            request_id = getattr(request, 'waf_request_id', 'unknown')
            logger.info(f"✅ [REQ-{request_id}] Response ready: {response.status_code} - Logging allowed request")

            self.log_request(
                request,
                request.waf_site,
                'ALLOWED',
                None,
                request.waf_start_time,
                request.waf_ip
            )

            response_time = (time.time() - request.waf_start_time) * 1000
            logger.debug(f"⏱️ [REQ-{request_id}] Total response time: {response_time:.2f}ms")

        return response

    def get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def get_site_by_domain(self, host):
        """Find site by domain/host"""
        try:
            # Remove port if present
            domain = host.split(':')[0]
            return Site.objects.get(domain__icontains=domain, is_active=True)
        except Site.DoesNotExist:
            return None

    def check_rate_limit(self, site, ip_address):
        """Check if IP has exceeded rate limit"""
        # Default rate limit: 100 requests per minute
        max_requests = 100
        window_minutes = 1

        now = timezone.now()
        window_start = now - timezone.timedelta(minutes=window_minutes)

        # Get or create rate limit record
        rate_limit, created = RateLimit.objects.get_or_create(
            site=site,
            ip_address=ip_address,
            defaults={'request_count': 1, 'window_start': now}
        )

        # Reset counter if window has passed
        if rate_limit.window_start < window_start:
            rate_limit.request_count = 1
            rate_limit.window_start = now
            rate_limit.save()
            return False

        # Check if limit exceeded
        if rate_limit.request_count >= max_requests:
            return True

        # Increment counter
        rate_limit.request_count += 1
        rate_limit.save()

        return False

    def matches_rule(self, request, rule):
        """Check if request matches a security rule"""
        url = request.get_full_path()
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        logger.debug(f"🔍 Evaluating rule: {rule.name} ({rule.rule_type})")

        # URL decode the path to catch encoded attacks
        from urllib.parse import unquote
        decoded_url = unquote(url)

        # Combine all request data to check (both original and decoded)
        request_data = f"{url} {decoded_url} {user_agent}"

        # Add POST data if present (but be careful not to interfere with CSRF)
        if request.method == 'POST':
            try:
                # Only read body if it's not an exempt path
                if not self.should_bypass_middleware(request):
                    body_data = request.body.decode('utf-8', errors='ignore')
                    request_data += f" {body_data}"
                    logger.debug(f"📝 Added POST data to rule check (length: {len(body_data)})")
            except Exception as e:
                logger.debug(f"⚠️ Could not read POST body: {e}")
                pass

        logger.debug(f"📊 Request data for rule check (first 200 chars): {request_data[:200]}...")

        # Check pattern match
        try:
            result = False
            if rule.rule_type != 'bot_detection':
                result = self.check(request_data,rule.pattern)
            elif rule.rule_type == 'bot_detection':
                result = self.check_bot(request_data, user_agent)
            elif rule.rule_type != '':
                result = self.check_custom_pattern(request_data, rule.pattern)

            if result:
                logger.warning(f"🚨 Rule MATCHED: {rule.name} - Pattern detected in request")
            else:
                logger.debug(f"✅ Rule passed: {rule.name}")

            return result

        except Exception as e:
            logger.error(f"❌ Error in rule pattern matching for {rule.name}: {e}")
            # If pattern matching fails, don't block the request
            return False

    def check(self, data,pattern):
        data_lower = data.lower()
        pattern = re.compile(pattern)
        return bool(pattern.search(data_lower))

    def check_bot(self, data, user_agent):
        """Check for bot patterns"""
        bot_patterns = [
            r'bot',
            r'crawler',
            r'spider',
            r'scraper',
            r'curl',
            r'wget',
            r'python-requests',
        ]

        user_agent_lower = user_agent.lower()
        for pattern in bot_patterns:
            if re.search(pattern, user_agent_lower):
                return True
        return False

    def check_custom_pattern(self, data, pattern):
        """Check custom regex pattern"""
        try:
            return bool(re.search(pattern, data, re.IGNORECASE))
        except re.error:
            return False

    def is_protected_site_route(self, request):
        """
        Check if this request is for a protected site route.
        Returns True if WAF rules should be applied.

        Since we now handle all bypass logic in should_bypass_middleware(),
        if we reach this point, the request should be protected.
        """
        # If we reached this point, the request passed bypass checks
        # and has a valid site, so it should be protected
        return True

    def get_block_reason(self, rule_type):
        """Get user-friendly block reason based on rule type"""
        reasons = {
            'sql_injection': 'Potential SQL injection attack detected',
            'xss': 'Cross-site scripting (XSS) attempt blocked',
            'path_traversal': 'Directory traversal attack prevented',
            'bot_detection': 'Automated bot or crawler blocked',
            'custom': 'Custom security rule violation',
            'rate_limiting': 'Too many requests from your IP address',
        }
        return reasons.get(rule_type, 'Security policy violation detected')

    def log_request(self, request, site, status, rule, start_time, ip_address):
        """Log the request"""
        try:
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            RequestLog.objects.create(
                site=site,
                ip_address=ip_address,
                url=request.build_absolute_uri(),
                method=request.method,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                status=status,
                rule_matched=rule,
                response_time=response_time
            )
        except Exception:
            # Don't let logging errors break the request
            pass
