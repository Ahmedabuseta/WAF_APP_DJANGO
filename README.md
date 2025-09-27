# WAF (Web Application Firewall) Project

A Django-based Web Application Firewall (WAF) proxy system that provides security protection for web applications.

## Features

- **Request Filtering**: SQL injection, XSS, and path traversal protection
- **Rate Limiting**: Configurable rate limiting per IP address
- **Bot Detection**: Advanced bot detection and blocking
- **User Management**: Customer and admin user roles with authentication
- **Site Management**: Multi-site support with individual configurations
- **Real-time Monitoring**: Request logging and statistics
- **Email Notifications**: User verification and password reset
- **Admin Dashboard**: Comprehensive management interface

## Project Structure

- `waf_project/` - Main Django project
- `waf_project/waf_proxy/` - WAF application module
- `test_backend_app/` - Test backend application
- `requirements.txt` - Python dependencies
- `manage.py` - Django management script

## Quick Start

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

3. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

4. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

## Key Components

### WAF Middleware
- **`middleware.py`**: Core WAF security processing
- **`proxy.py`**: Request forwarding to backend servers

### Models
- **User**: Custom user model with customer/admin roles
- **Site**: Protected site configurations
- **Rule**: Security rules and patterns
- **RequestLog**: Request logging and monitoring
- **RateLimit**: Rate limiting counters

### Security Features
- SQL injection detection
- Cross-site scripting (XSS) protection
- Path traversal prevention
- Rate limiting
- Bot detection
- Custom security rules

## Configuration

The WAF can be configured through the Django admin interface or programmatically through the models.

## Testing

Run the test scripts to verify WAF functionality:
- `simple_waf_test.sh` - Basic WAF testing
- `test_waf_curl_examples.sh` - cURL-based testing
- `test_backend_app/test_waf_integration.sh` - Integration testing

## License

This project is for educational and development purposes.