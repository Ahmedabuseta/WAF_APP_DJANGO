#!/usr/bin/env python3
"""
Simple Django Test Backend App
This app serves as a backend server for testing WAF forwarding functionality.
"""

import os
import sys
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.http import HttpResponse, JsonResponse
from django.urls import path
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf.urls.static import static
import os
import json

# Configure Django settings
if not settings.configured:
    # Get the directory paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR = os.path.join(os.path.dirname(BASE_DIR), 'waf_project', 'static')

    settings.configure(
        DEBUG=True,
        SECRET_KEY='test-backend-secret-key-12345',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
        ],
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.request',
                ],
            },
        }],
        USE_TZ=True,
        STATIC_URL='/static/',
        STATIC_ROOT=STATIC_DIR,
        STATICFILES_DIRS=[STATIC_DIR] if os.path.exists(STATIC_DIR) else [],
    )

# Views
def home(request):
    """Homepage showing that the backend is working"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Backend App</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .status {{ color: #28a745; font-weight: bold; }}
            .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .test-links {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .test-links a {{ display: block; margin: 5px 0; color: #856404; }}
            .headers {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; font-family: monospace; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Test Backend App</h1>
            <p class="status">✅ Backend server is running successfully!</p>

            <div class="info">
                <h3>📊 Request Information</h3>
                <p><strong>Time:</strong> {timezone.now()}</p>
                <p><strong>Method:</strong> {request.method}</p>
                <p><strong>Path:</strong> {request.path}</p>
                <p><strong>Host:</strong> {request.get_host()}</p>
                <p><strong>Client IP:</strong> {request.META.get('REMOTE_ADDR', 'Unknown')}</p>
                <p><strong>User Agent:</strong> {request.META.get('HTTP_USER_AGENT', 'Unknown')}</p>
            </div>

            <div class="test-links">
                <h3>🧪 Test Links</h3>
                <a href="/api/test">JSON API Test</a>
                <a href="/form">Form Test Page</a>
                <a href="/headers">View All Headers</a>
                <a href="/slow">Slow Response Test (3s delay)</a>
                <a href="/large">Large Response Test</a>
                <a href="/error">Error Test (500)</a>
            </div>

            <div class="headers">
                <h3>📋 WAF Headers (if present)</h3>
                <p><strong>X-WAF-Protected:</strong> {request.META.get('HTTP_X_WAF_PROTECTED', 'Not present')}</p>
                <p><strong>X-WAF-Site-ID:</strong> {request.META.get('HTTP_X_WAF_SITE_ID', 'Not present')}</p>
                <p><strong>X-Forwarded-For:</strong> {request.META.get('HTTP_X_FORWARDED_FOR', 'Not present')}</p>
                <p><strong>X-Real-IP:</strong> {request.META.get('HTTP_X_REAL_IP', 'Not present')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

def api_test(request):
    """JSON API endpoint for testing"""
    data = {
        'status': 'success',
        'message': 'Backend API is working',
        'timestamp': timezone.now().isoformat(),
        'method': request.method,
        'path': request.path,
        'client_ip': request.META.get('REMOTE_ADDR'),
        'waf_headers': {
            'x_waf_protected': request.META.get('HTTP_X_WAF_PROTECTED'),
            'x_waf_site_id': request.META.get('HTTP_X_WAF_SITE_ID'),
            'x_forwarded_for': request.META.get('HTTP_X_FORWARDED_FOR'),
            'x_real_ip': request.META.get('HTTP_X_REAL_IP'),
        },
        'query_params': dict(request.GET),
    }

    if request.method == 'POST':
        data['post_data'] = dict(request.POST)

    return JsonResponse(data, json_dumps_params={'indent': 2})

def form_test(request):
    """Form test page"""
    if request.method == 'POST':
        return HttpResponse(f"""
        <h2>Form Submitted Successfully!</h2>
        <p><strong>Name:</strong> {request.POST.get('name', 'Not provided')}</p>
        <p><strong>Email:</strong> {request.POST.get('email', 'Not provided')}</p>
        <p><strong>Message:</strong> {request.POST.get('message', 'Not provided')}</p>
        <a href="/form">Go back</a>
        """)

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Form Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            form { max-width: 500px; }
            label { display: block; margin-top: 10px; }
            input, textarea { width: 100%; padding: 8px; margin-top: 5px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; margin-top: 15px; }
        </style>
    </head>
    <body>
        <h1>📝 Form Test</h1>
        <form method="post">
            <label for="name">Name:</label>
            <input type="text" id="name" name="name" required>

            <label for="email">Email:</label>
            <input type="email" id="email" name="email" required>

            <label for="message">Message:</label>
            <textarea id="message" name="message" rows="4" required></textarea>

            <button type="submit">Submit Form</button>
        </form>
        <p><a href="/">← Back to Home</a></p>
    </body>
    </html>
    """
    return HttpResponse(html)

def headers_view(request):
    """Display all request headers"""
    headers_html = "<h2>📋 All Request Headers</h2><pre>"
    for key, value in request.META.items():
        if key.startswith('HTTP_') or key in ['CONTENT_TYPE', 'CONTENT_LENGTH']:
            headers_html += f"{key}: {value}\n"
    headers_html += "</pre><p><a href='/'>← Back to Home</a></p>"

    return HttpResponse(headers_html)

def slow_response(request):
    """Slow response for testing timeouts"""
    import time
    time.sleep(3)  # 3 second delay
    return HttpResponse(f"""
    <h2>⏱️ Slow Response</h2>
    <p>This response was delayed by 3 seconds.</p>
    <p>Received at: {timezone.now()}</p>
    <p><a href="/">← Back to Home</a></p>
    """)

def large_response(request):
    """Large response for testing buffer limits"""
    content = "This is a large response test. " * 1000  # ~27KB
    return HttpResponse(f"""
    <h2>📦 Large Response Test</h2>
    <p>This response contains approximately 27KB of data.</p>
    <div style="background: #f8f9fa; padding: 20px; font-family: monospace; word-break: break-all;">
    {content}
    </div>
    <p><a href="/">← Back to Home</a></p>
    """)

def error_test(request):
    """Error response for testing error handling"""
    return HttpResponse("Internal Server Error - This is a test error", status=500)


@csrf_exempt
def api_post_test(request):
    """POST API test"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            return JsonResponse({
                'status': 'success',
                'received_data': data,
                'timestamp': timezone.now().isoformat()
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON'
            }, status=400)
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'POST method required'
        }, status=405)

# URL patterns
urlpatterns = [
    path('', home, name='home'),
    path('api/test', api_test, name='api_test'),
    path('api/post', api_post_test, name='api_post_test'),
    path('form', form_test, name='form_test'),
    path('headers', headers_view, name='headers'),
    path('slow', slow_response, name='slow'),
    path('large', large_response, name='large'),
    path('error', error_test, name='error'),
]

# Add static file serving
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# WSGI application
application = get_wsgi_application()

if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    if len(sys.argv) == 1:
        # Default to runserver if no arguments provided
        sys.argv = ['app.py', 'runserver', '127.0.0.1:3000']

    execute_from_command_line(sys.argv)
