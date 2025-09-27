# Simple Django Test Backend App

This is a simple Django application designed to test your WAF forwarding functionality.

## Features

✅ **Homepage** - Shows backend is working and displays request info
✅ **JSON API** - Test API endpoints  
✅ **Form Handling** - Test POST requests
✅ **Headers Display** - View all request headers including WAF headers
✅ **Performance Tests** - Slow responses, large responses
✅ **Error Testing** - Test error handling

## Quick Start

### 1. Install Dependencies
```bash
cd test_backend_app
pip install -r requirements.txt
```

### 2. Run the Server
```bash
# Run on port 3000 (default)
python app.py

# Or specify port
python app.py runserver 127.0.0.1:3000
```

### 3. Test Direct Access
Visit: http://127.0.0.1:3000

## Test URLs

- **/** - Homepage with request info
- **/api/test** - JSON API endpoint
- **/form** - Form test page
- **/headers** - View all headers
- **/slow** - 3-second delayed response
- **/large** - Large response (~27KB)
- **/error** - 500 error test

## Using with WAF

### 1. Configure Site in WAF
- **Domain**: example.com
- **Backend URL**: http://127.0.0.1:3000
- **Active**: Yes

### 2. Test WAF Forwarding
```bash
# Test through WAF (assuming nginx on port 80)
curl -H "Host: example.com" http://localhost/

# Test API through WAF
curl -H "Host: example.com" http://localhost/api/test

# Test form POST through WAF
curl -X POST -H "Host: example.com" \
     -d "name=Test&email=test@example.com&message=Hello" \
     http://localhost/form
```

### 3. Check WAF Headers
The app will display WAF-specific headers:
- `X-WAF-Protected: true`
- `X-WAF-Site-ID: [site_id]`
- `X-Forwarded-For: [client_ip]`
- `X-Real-IP: [client_ip]`

## Architecture

```
Client → Nginx → Django WAF → Test Backend App
      :80      :8000         :3000
```

The test app runs on port 3000 and receives forwarded requests from your WAF on port 8000.

## Testing WAF Rules

You can test WAF blocking by accessing:

```bash
# These should be BLOCKED by WAF
curl -H "Host: example.com" "http://localhost/?test=1' UNION SELECT * FROM users--"
curl -H "Host: example.com" "http://localhost/?search=<script>alert('xss')</script>"

# These should be ALLOWED and reach the backend
curl -H "Host: example.com" http://localhost/
curl -H "Host: example.com" http://localhost/api/test
```