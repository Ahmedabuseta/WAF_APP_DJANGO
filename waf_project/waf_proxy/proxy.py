import requests
import json
import time
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class ProxyForwardingMiddleware(MiddlewareMixin):
    """
    Middleware to forward requests to backend servers after WAF processing
    """

    def process_response(self, request, response):
        # Only forward if this is a protected site route and WAF has processed it
        if hasattr(request, 'waf_site') and self.should_forward_request(request):
            request_id = getattr(request, 'waf_request_id', 'unknown')
            logger.info(f"🔄 [REQ-{request_id}] Proxy middleware activated - Forwarding to backend")
            return self.forward_to_backend(request)

        return response

    def should_forward_request(self, request):
        """
        Determine if request should be forwarded to backend.

        If the request has waf_site, it means:
        1. It passed WAF bypass checks
        2. A site was found for the host
        3. WAF processing was completed
        4. It should be forwarded to the backend
        """
        request_id = getattr(request, 'waf_request_id', 'unknown')
        path = request.path
        host = request.get_host().split(':')[0]

        logger.debug(f"🤔 [REQ-{request_id}] Checking if request should be forwarded: HOST={host}, PATH={path}")

        # NEVER forward WAF system pages - these always stay on our WAF server
        waf_system_paths = ['/blocked/', '/rate-limited/', '/access-denied/', '/admin/', '/login/', '/logout/', '/register/', '/accounts/', '/api/', '/dashboard/', '/sites/', '/profile/', '/settings/', '/static/', '/media/']
        
        for system_path in waf_system_paths:
            if path.startswith(system_path):
                logger.debug(f"🏠 [REQ-{request_id}] WAF system path - NOT forwarding: {path}")
                return False

        # If request has waf_site AND passed WAF security checks, forward to backend
        if hasattr(request, 'waf_site') and hasattr(request, 'waf_start_time'):
            # This means the request:
            # 1. Was processed by WAF middleware
            # 2. Found a valid site configuration 
            # 3. PASSED all security checks (not blocked)
            # 4. Should be forwarded to the user's backend
            logger.debug(f"✅ [REQ-{request_id}] Safe request - forwarding to backend: {request.waf_site.backend_url}")
            return True
        else:
            logger.debug(f"❌ [REQ-{request_id}] No waf_site or blocked request - not forwarding")
            return False

    def forward_to_backend(self, request):
        """
        Forward the request to the backend server
        """
        request_id = getattr(request, 'waf_request_id', 'unknown')
        proxy_start_time = time.time()

        try:
            site = request.waf_site
            backend_url = site.backend_url.rstrip('/')

            # Build the full URL
            full_url = f"{backend_url}{request.get_full_path()}"
            logger.info(f"🎯 [REQ-{request_id}] Forwarding to backend: {full_url}")

            # Prepare headers
            headers = self.get_forwarded_headers(request)
            logger.debug(f"📋 [REQ-{request_id}] Prepared {len(headers)} headers for forwarding")

            # Prepare request data
            data = None
            files = None

            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = request.content_type or ''
                logger.debug(f"📝 [REQ-{request_id}] Processing {request.method} request with content-type: {content_type}")

                if 'multipart/form-data' in content_type:
                    # Handle file uploads
                    files = request.FILES
                    data = request.POST
                    logger.debug(f"📎 [REQ-{request_id}] File upload detected - {len(files)} files, {len(data)} form fields")
                else:
                    # Handle regular POST data
                    data = request.body
                    logger.debug(f"📄 [REQ-{request_id}] Regular POST data - {len(data) if data else 0} bytes")

            # Make the request to backend
            logger.debug(f"🌐 [REQ-{request_id}] Making {request.method} request to backend...")
            backend_start_time = time.time()

            response = request(
                method=request.method,
                url=full_url,
                headers=headers,
                data=data,
                files=files,
                params=request.GET,
                allow_redirects=False,
                timeout=30,
                stream=True
            )

            backend_time = (time.time() - backend_start_time) * 1000
            logger.info(f"✅ [REQ-{request_id}] Backend responded: {response.status_code} in {backend_time:.2f}ms")
            logger.debug(f"📊 [REQ-{request_id}] Backend response headers: {dict(response.headers)}")

            # Create Django response from backend response
            django_response = self.create_django_response(response)

            total_proxy_time = (time.time() - proxy_start_time) * 1000
            logger.debug(f"⏱️ [REQ-{request_id}] Total proxy processing time: {total_proxy_time:.2f}ms")

            return django_response

        except requests.exceptions.Timeout as e:
            logger.error(f"⏰ [REQ-{request_id}] Backend timeout after 30s: {e}")
            return HttpResponse(
                'Backend server timeout',
                status=504
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 [REQ-{request_id}] Cannot connect to backend {full_url}: {e}")
            return HttpResponse(
                'Backend server unavailable',
                status=502,

            )
        except requests.exceptions.RequestException as e:
            logger.error(f"🚨 [REQ-{request_id}] Backend request error: {e}")
            return HttpResponse(
                f'Backend server error: {str(e)}',
                status=502
            )
        except Exception as e:
            logger.error(f"💥 [REQ-{request_id}] Unexpected proxy error: {e}")
            return HttpResponse(
                'Internal proxy error',
                status=500
            )

    def get_forwarded_headers(self, request):
        """
        Prepare headers for forwarding to backend
        """
        request_id = getattr(request, 'waf_request_id', 'unknown')
        headers = {}

        # Copy important headers
        important_headers = [
            'HTTP_ACCEPT', 'HTTP_ACCEPT_ENCODING', 'HTTP_ACCEPT_LANGUAGE',
            'HTTP_CACHE_CONTROL', 'HTTP_CONNECTION', 'HTTP_COOKIE',
            'HTTP_HOST', 'HTTP_REFERER', 'HTTP_USER_AGENT',
            'CONTENT_TYPE', 'CONTENT_LENGTH'
        ]

        logger.debug(f"📋 [REQ-{request_id}] Preparing headers for backend forwarding")

        copied_count = 0
        for header in important_headers:
            if header in request.META:
                # Convert Django META key to HTTP header
                header_name = header.replace('HTTP_', '').replace('_', '-').title()
                headers[header_name] = request.META[header]
                copied_count += 1

        logger.debug(f"📋 [REQ-{request_id}] Copied {copied_count} original headers")

        # Add forwarding headers
        headers['X-Forwarded-For'] = request.META.get('REMOTE_ADDR', '')
        headers['X-Forwarded-Proto'] = 'https' if request.is_secure() else 'http'
        headers['X-Forwarded-Host'] = request.get_host()
        headers['X-Real-IP'] = request.META.get('REMOTE_ADDR', '')

        # Add WAF identification
        headers['X-WAF-Protected'] = 'true'
        headers['X-WAF-Site-ID'] = str(request.waf_site.id)

        logger.debug(f"📋 [REQ-{request_id}] Added WAF headers: X-WAF-Protected, X-WAF-Site-ID={request.waf_site.id}")
        logger.debug(f"📋 [REQ-{request_id}] Total headers to forward: {len(headers)}")

        return headers

    def create_django_response(self, backend_response):
        """
        Convert requests.Response to Django HttpResponse
        """
        content_length = int(backend_response.headers.get('Content-Length', 0))
        logger.debug(f"📦 Creating Django response from backend - Status: {backend_response.status_code}, Content-Length: {content_length}")

        # Handle streaming responses for large files
        if content_length > 1024 * 1024:  # 1MB
            logger.debug(f"📦 Large response detected ({content_length} bytes) - Using streaming response")
            response = StreamingHttpResponse(
                backend_response.iter_content(chunk_size=8192),
                status=backend_response.status_code
            )
        else:
            logger.debug(f"📦 Regular response ({content_length} bytes) - Loading content")
            response = HttpResponse(
                backend_response.content,
                status=backend_response.status_code
            )

        # Copy response headers
        copied_headers = 0
        skipped_headers = []

        for header, value in backend_response.headers.items():
            # Skip headers that Django handles automatically
            if header.lower() not in ['content-length', 'transfer-encoding', 'connection']:
                response[header] = value
                copied_headers += 1
            else:
                skipped_headers.append(header)

        logger.debug(f"📦 Copied {copied_headers} response headers, skipped: {skipped_headers}")

        return response
