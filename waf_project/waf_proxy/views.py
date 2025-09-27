from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse, HttpResponseRedirect
from django.utils import timezone
from django.db.models import Count, Avg
from django.core.paginator import Paginator
from .models import User, Site, Rule, SiteRule, RequestLog, SiteStats, RateLimit, EmailVerificationToken, PasswordResetToken
from .decorators import admin_required, customer_required, login_required_custom, site_owner_required
from .utils import send_verification_email, send_password_reset_email, send_welcome_email
import time
import re

# Authentication Views
@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        captcha_answer = request.POST.get('captcha_answer')
        
        # Simple CAPTCHA validation (in production, use more sophisticated methods)
        # Note: This is a basic implementation. For production, consider using Google reCAPTCHA
        try:
            captcha_value = int(captcha_answer) if captcha_answer else 0
            # Basic validation - in real implementation, you'd store the expected answer in session
            if captcha_value < 2 or captcha_value > 20:  # Basic range check
                messages.error(request, 'Please complete the CAPTCHA correctly')
                return render(request, 'waf_proxy/login.html')
        except (ValueError, TypeError):
            messages.error(request, 'Please complete the CAPTCHA correctly')
            return render(request, 'waf_proxy/login.html')
        
        # Use Django's authenticate function with email as username
        user = authenticate(request, username=email, password=password)
        
        if user:
            if not user.is_email_verified:
                messages.error(request, 'Please verify your email address before signing in')
                return render(request, 'waf_proxy/login.html')
            
            login(request, user)
            user.last_login = timezone.now()
            user.save()
            messages.success(request, f'Welcome back, {user.first_name or user.email}!')
            
            # Redirect based on user type
            if user.user_type == 'admin':
                return redirect('admin_dashboard')
            else:
                return redirect('customer_dashboard')
        else:
            messages.error(request, 'Invalid email or password')
    
    return render(request, 'waf_proxy/login.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully')
    return redirect('login')

# Dashboard Router
@login_required_custom
def dashboard(request):
    """Smart dashboard router based on user type"""
    if request.user.user_type == 'admin':
        return admin_dashboard(request)
    else:
        return customer_dashboard(request)

# Customer Views
@customer_required
def customer_dashboard(request):
    sites = Site.objects.filter(owner=request.user, is_active=True)
    
    # Get today's stats
    today = timezone.now().date()
    total_requests_today = RequestLog.objects.filter(
        site__in=sites, 
        timestamp__date=today
    ).count()
    
    blocked_today = RequestLog.objects.filter(
        site__in=sites, 
        status='BLOCKED',
        timestamp__date=today
    ).count()
    
    # Get recent activity
    recent_logs = RequestLog.objects.filter(
        site__in=sites
    ).order_by('-timestamp')[:10]
    
    context = {
        'sites': sites,
        'total_sites': sites.count(),
        'total_requests_today': total_requests_today,
        'blocked_today': blocked_today,
        'recent_logs': recent_logs,
    }
    return render(request, 'waf_proxy/customer/dashboard.html', context)

@customer_required
def site_list(request):
    sites = Site.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'waf_proxy/customer/site_list.html', {'sites': sites})

@customer_required
def site_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        domain = request.POST.get('domain')
        backend_url = request.POST.get('backend_url')
        description = request.POST.get('description', '')
        
        # Basic validation
        if not all([name, domain, backend_url]):
            messages.error(request, 'Please fill in all required fields')
            return render(request, 'waf_proxy/customer/site_add.html')
        
        # Check if domain already exists
        if Site.objects.filter(domain=domain).exists():
            messages.error(request, 'A site with this domain already exists')
            return render(request, 'waf_proxy/customer/site_add.html')
        
        try:
            site = Site.objects.create(
                name=name,
                domain=domain,
                backend_url=backend_url,
                description=description,
                owner=request.user,
                is_active=True
            )
            messages.success(request, f'Site "{site.name}" created successfully!')
            return redirect('site_detail', site_id=site.id)
            
        except Exception as e:
            messages.error(request, f'Failed to create site: {str(e)}')
    
    return render(request, 'waf_proxy/customer/site_add.html')

@site_owner_required
def site_detail(request, site_id):
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
    except Site.DoesNotExist:
        messages.error(request, 'Site not found')
        return redirect('site_list')
    
    # Get recent stats
    today = timezone.now().date()
    week_ago = today - timezone.timedelta(days=7)
    
    recent_logs = RequestLog.objects.filter(site=site).order_by('-timestamp')[:10]
    total_requests = RequestLog.objects.filter(site=site, timestamp__date__gte=week_ago).count()
    blocked_requests = RequestLog.objects.filter(site=site, status='BLOCKED', timestamp__date__gte=week_ago).count()
    
    # Active rules count
    active_rules_count = SiteRule.objects.filter(site=site, is_active=True).count()
    
    context = {
        'site': site,
        'recent_logs': recent_logs,
        'total_requests': total_requests,
        'blocked_requests': blocked_requests,
        'active_rules_count': active_rules_count,
    }
    return render(request, 'waf_proxy/customer/site_detail.html', context)

@site_owner_required
def site_edit(request, site_id):
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
    except Site.DoesNotExist:
        messages.error(request, 'Site not found')
        return redirect('site_list')
    
    if request.method == 'POST':
        site.name = request.POST.get('name', site.name)
        site.domain = request.POST.get('domain', site.domain)
        site.backend_url = request.POST.get('backend_url', site.backend_url)
        site.description = request.POST.get('description', site.description)
        site.is_active = 'is_active' in request.POST
        
        try:
            site.save()
            messages.success(request, 'Site updated successfully!')
            return redirect('site_detail', site_id=site.id)
        except Exception as e:
            messages.error(request, f'Failed to update site: {str(e)}')
    
    return render(request, 'waf_proxy/customer/site_edit.html', {'site': site})

@site_owner_required
def site_delete(request, site_id):
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
    except Site.DoesNotExist:
        messages.error(request, 'Site not found')
        return redirect('site_list')
    
    if request.method == 'POST':
        site_name = site.name
        site.delete()
        messages.success(request, f'Site "{site_name}" deleted successfully!')
        return redirect('site_list')
    
    return render(request, 'waf_proxy/customer/site_delete.html', {'site': site})

@site_owner_required
def site_rules(request, site_id):
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
    except Site.DoesNotExist:
        messages.error(request, 'Site not found')
        return redirect('site_list')
    
    # Get active rules for this site
    active_rules = SiteRule.objects.filter(site=site, is_active=True).select_related('rule')
    
    # Get available rules to add
    available_rules = Rule.objects.filter(is_global=True).exclude(
        id__in=active_rules.values_list('rule_id', flat=True)
    )
    
    if request.method == 'POST':
        if 'add_rule' in request.POST:
            rule_id = request.POST.get('rule_id')
            try:
                rule = Rule.objects.get(id=rule_id)
                SiteRule.objects.create(site=site, rule=rule)
                messages.success(request, f'Rule "{rule.name}" added to site')
            except Rule.DoesNotExist:
                messages.error(request, 'Rule not found')
        
        elif 'toggle_rule' in request.POST:
            site_rule_id = request.POST.get('site_rule_id')
            try:
                site_rule = SiteRule.objects.get(id=site_rule_id, site=site)
                site_rule.is_active = not site_rule.is_active
                site_rule.save()
                status = 'activated' if site_rule.is_active else 'deactivated'
                messages.success(request, f'Rule "{site_rule.rule.name}" {status}')
            except SiteRule.DoesNotExist:
                messages.error(request, 'Site rule not found')
        
        return redirect('site_rules', site_id=site_id)
    
    context = {
        'site': site,
        'active_rules': active_rules,
        'available_rules': available_rules,
    }
    return render(request, 'waf_proxy/customer/site_rules.html', context)

@site_owner_required
def site_rule_add(request, site_id):
    """Add custom rule to site"""
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
    except Site.DoesNotExist:
        messages.error(request, 'Site not found')
        return redirect('site_list')
    
    if request.method == 'POST':
        rule_name = request.POST.get('rule_name')
        rule_pattern = request.POST.get('rule_pattern')
        rule_type = request.POST.get('rule_type')
        rule_action = request.POST.get('rule_action')
        rule_description = request.POST.get('rule_description', '')
        
        if not all([rule_name, rule_pattern, rule_type, rule_action]):
            messages.error(request, 'Please fill in all required fields')
            return render(request, 'waf_proxy/customer/site_rule_add.html', {'site': site})
        
        try:
            # Create custom rule for this site
            rule = Rule.objects.create(
                name=f"{site.domain} - {rule_name}",
                pattern=rule_pattern,
                rule_type=rule_type,
                action=rule_action,
                description=rule_description,
                is_global=False
            )
            
            # Add rule to site
            SiteRule.objects.create(site=site, rule=rule, is_active=True)
            
            messages.success(request, f'Custom rule "{rule_name}" created and added to site')
            return redirect('site_rules', site_id=site_id)
            
        except Exception as e:
            messages.error(request, f'Failed to create rule: {str(e)}')
    
    # Get rule templates for suggestions
    rule_templates = [
        {
            'name': 'SQL Injection Protection',
            'pattern': r'(union|select|insert|update|delete|drop|alter|create)\s+',
            'type': 'sql_injection',
            'description': 'Blocks common SQL injection keywords'
        },
        {
            'name': 'XSS Protection',
            'pattern': r'<script.*?>|javascript:|onload=|onerror=',
            'type': 'xss',
            'description': 'Prevents cross-site scripting attacks'
        },
        {
            'name': 'Path Traversal Protection',
            'pattern': r'\.\./|\.\.\\/|%2e%2e%2f',
            'type': 'path_traversal',
            'description': 'Blocks directory traversal attempts'
        },
        {
            'name': 'Bot Protection',
            'pattern': r'(bot|crawler|spider|scraper)',
            'type': 'bot_detection',
            'description': 'Blocks common bot user agents'
        }
    ]
    
    context = {
        'site': site,
        'rule_templates': rule_templates,
        'rule_types': Rule.RULE_TYPE_CHOICES,
        'actions': Rule.ACTION_CHOICES,
    }
    return render(request, 'waf_proxy/customer/site_rule_add.html', context)

@site_owner_required
def site_rule_edit(request, site_id, rule_id):
    """Edit site-specific rule configuration"""
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
        site_rule = SiteRule.objects.get(id=rule_id, site=site)
    except (Site.DoesNotExist, SiteRule.DoesNotExist):
        messages.error(request, 'Site or rule not found')
        return redirect('site_list')
    
    if request.method == 'POST':
        # Update site rule configuration
        site_rule.is_active = 'is_active' in request.POST
        site_rule.custom_action = request.POST.get('custom_action', '')
        
        # If it's a custom rule (not global), update the rule itself
        if not site_rule.rule.is_global:
            site_rule.rule.name = request.POST.get('rule_name', site_rule.rule.name)
            site_rule.rule.pattern = request.POST.get('rule_pattern', site_rule.rule.pattern)
            site_rule.rule.rule_type = request.POST.get('rule_type', site_rule.rule.rule_type)
            site_rule.rule.action = request.POST.get('rule_action', site_rule.rule.action)
            site_rule.rule.description = request.POST.get('rule_description', site_rule.rule.description)
            site_rule.rule.save()
        
        site_rule.save()
        messages.success(request, 'Rule configuration updated successfully')
        return redirect('site_rules', site_id=site_id)
    
    context = {
        'site': site,
        'site_rule': site_rule,
        'rule_types': Rule.RULE_TYPE_CHOICES,
        'actions': Rule.ACTION_CHOICES,
    }
    return render(request, 'waf_proxy/customer/site_rule_edit.html', context)

@site_owner_required
def site_rule_delete(request, site_id, rule_id):
    """Delete site rule"""
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
        site_rule = SiteRule.objects.get(id=rule_id, site=site)
    except (Site.DoesNotExist, SiteRule.DoesNotExist):
        messages.error(request, 'Site or rule not found')
        return redirect('site_list')
    
    if request.method == 'POST':
        rule_name = site_rule.rule.name
        
        # If it's a custom rule, delete the rule itself
        if not site_rule.rule.is_global:
            site_rule.rule.delete()
        else:
            # For global rules, just remove from site
            site_rule.delete()
        
        messages.success(request, f'Rule "{rule_name}" removed from site')
        return redirect('site_rules', site_id=site_id)
    
    context = {
        'site': site,
        'site_rule': site_rule,
    }
    return render(request, 'waf_proxy/customer/site_rule_delete.html', context)

@site_owner_required
def site_rules_import(request, site_id):
    """Import rules from templates or other sites"""
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
    except Site.DoesNotExist:
        messages.error(request, 'Site not found')
        return redirect('site_list')
    
    if request.method == 'POST':
        import_type = request.POST.get('import_type')
        
        if import_type == 'template':
            template_name = request.POST.get('template_name')
            
            # Predefined rule sets
            templates = {
                'basic_security': [
                    ('SQL Injection Basic', r'(union|select|insert|update|delete|drop)\s+', 'sql_injection', 'BLOCK'),
                    ('XSS Basic', r'<script.*?>|javascript:', 'xss', 'BLOCK'),
                    ('Path Traversal Basic', r'\.\./|\.\.\/', 'path_traversal', 'BLOCK'),
                ],
                'advanced_security': [
                    ('SQL Injection Advanced', r'(union|select|insert|update|delete|drop|alter|create|exec|execute)\s+', 'sql_injection', 'BLOCK'),
                    ('XSS Advanced', r'<script.*?>|javascript:|onload=|onerror=|onclick=|<iframe|<object|<embed', 'xss', 'BLOCK'),
                    ('Path Traversal Advanced', r'\.\./|\.\.\\/|%2e%2e%2f|%2e%2e%5c|\.\.%2f|\.\.%5c', 'path_traversal', 'BLOCK'),
                    ('Command Injection', r'(;|&|\|).*?(ls|cat|wget|curl|nc|netcat)', 'custom', 'BLOCK'),
                    ('Bot Protection', r'(bot|crawler|spider|scraper|scan)', 'bot_detection', 'BLOCK'),
                ],
                'ecommerce': [
                    ('Payment Protection', r'(credit.*card|visa|mastercard|paypal)', 'custom', 'LOG'),
                    ('Price Manipulation', r'price=|amount=|total=', 'custom', 'LOG'),
                    ('Cart Tampering', r'quantity=.*[^0-9]|qty=.*[^0-9]', 'custom', 'BLOCK'),
                ]
            }
            
            if template_name in templates:
                rules_added = 0
                for name, pattern, rule_type, action in templates[template_name]:
                    # Check if rule already exists
                    if not Rule.objects.filter(name=f"{site.domain} - {name}").exists():
                        rule = Rule.objects.create(
                            name=f"{site.domain} - {name}",
                            pattern=pattern,
                            rule_type=rule_type,
                            action=action,
                            is_global=False
                        )
                        SiteRule.objects.create(site=site, rule=rule, is_active=True)
                        rules_added += 1
                
                messages.success(request, f'Imported {rules_added} rules from {template_name} template')
                
        elif import_type == 'copy_site':
            source_site_id = request.POST.get('source_site_id')
            try:
                source_site = Site.objects.get(id=source_site_id, owner=request.user)
                source_rules = SiteRule.objects.filter(site=source_site, is_active=True)
                
                rules_copied = 0
                for source_rule in source_rules:
                    # Check if rule is already applied to target site
                    if not SiteRule.objects.filter(site=site, rule=source_rule.rule).exists():
                        SiteRule.objects.create(
                            site=site,
                            rule=source_rule.rule,
                            is_active=True,
                            custom_action=source_rule.custom_action
                        )
                        rules_copied += 1
                
                messages.success(request, f'Copied {rules_copied} rules from {source_site.domain}')
                
            except Site.DoesNotExist:
                messages.error(request, 'Source site not found')
        
        return redirect('site_rules', site_id=site_id)
    
    # Get user's other sites for copying rules
    other_sites = Site.objects.filter(owner=request.user).exclude(id=site_id)
    
    context = {
        'site': site,
        'other_sites': other_sites,
    }
    return render(request, 'waf_proxy/customer/site_rules_import.html', context)

@site_owner_required
def site_rules_export(request, site_id):
    """Export site rules configuration"""
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
    except Site.DoesNotExist:
        messages.error(request, 'Site not found')
        return redirect('site_list')
    
    site_rules = SiteRule.objects.filter(site=site).select_related('rule')
    
    import json
    from django.http import JsonResponse
    
    # Export as JSON
    export_data = {
        'site_domain': site.domain,
        'export_date': timezone.now().isoformat(),
        'rules': []
    }
    
    for site_rule in site_rules:
        export_data['rules'].append({
            'name': site_rule.rule.name,
            'pattern': site_rule.rule.pattern,
            'rule_type': site_rule.rule.rule_type,
            'action': site_rule.custom_action or site_rule.rule.action,
            'description': site_rule.rule.description,
            'is_active': site_rule.is_active,
            'is_global': site_rule.rule.is_global,
        })
    
    response = JsonResponse(export_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="{site.domain}_rules.json"'
    return response

@site_owner_required
def site_stats(request, site_id):
    try:
        site = Site.objects.get(id=site_id, owner=request.user)
    except Site.DoesNotExist:
        messages.error(request, 'Site not found')
        return redirect('site_list')
    
    # Get stats for last 7 days
    end_date = timezone.now().date()
    start_date = end_date - timezone.timedelta(days=7)
    
    stats = SiteStats.objects.filter(
        site=site, 
        date__gte=start_date
    ).order_by('date')
    
    # Get recent logs
    recent_logs = RequestLog.objects.filter(site=site).order_by('-timestamp')[:20]
    
    context = {
        'site': site,
        'stats': stats,
        'recent_logs': recent_logs,
    }
    return render(request, 'waf_proxy/customer/site_stats.html', context)

# Admin Views
@admin_required
def admin_dashboard(request):
    # Get overall stats
    total_customers = User.objects.filter(user_type='customer', is_active=True).count()
    total_sites = Site.objects.filter(is_active=True).count()
    
    # Today's stats
    today = timezone.now().date()
    total_requests_today = RequestLog.objects.filter(timestamp__date=today).count()
    blocked_today = RequestLog.objects.filter(status='BLOCKED', timestamp__date=today).count()
    
    # Top blocked rules
    top_blocked_rules = RequestLog.objects.filter(
        status='BLOCKED',
        timestamp__date=today
    ).values('rule_matched__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Recent activity
    recent_logs = RequestLog.objects.order_by('-timestamp')[:20]
    
    context = {
        'total_customers': total_customers,
        'total_sites': total_sites,
        'total_requests_today': total_requests_today,
        'blocked_today': blocked_today,
        'top_blocked_rules': top_blocked_rules,
        'recent_logs': recent_logs,
    }
    return render(request, 'waf_proxy/admin/dashboard.html', context)

@admin_required
def customer_list(request):
    customers = User.objects.filter(user_type='customer').order_by('-created_at')
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'waf_proxy/admin/customer_list.html', {'page_obj': page_obj})

@admin_required
def admin_site_list(request):
    sites = Site.objects.select_related('owner').order_by('-created_at')
    paginator = Paginator(sites, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'waf_proxy/admin/site_list.html', {'page_obj': page_obj})

@admin_required
def rule_list(request):
    rules = Rule.objects.order_by('-created_at')
    return render(request, 'waf_proxy/admin/rule_list.html', {'rules': rules})

@admin_required
def log_list(request):
    logs = RequestLog.objects.select_related('site', 'rule_matched').order_by('-timestamp')
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'waf_proxy/admin/log_list.html', {'page_obj': page_obj})

# Test view to demonstrate WAF protection
# Profile and Settings Views
@login_required_custom
def profile(request):
    return render(request, 'waf_proxy/profile.html', {'user': request.user})

@login_required_custom
def user_settings(request):
    if request.method == 'POST':
        # Update user information
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.company_name = request.POST.get('company_name', request.user.company_name)
        request.user.phone = request.POST.get('phone', request.user.phone)
        
        # Password change
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if current_password and new_password:
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect')
                return render(request, 'waf_proxy/settings.html')
            
            if new_password != confirm_password:
                messages.error(request, 'New passwords do not match')
                return render(request, 'waf_proxy/settings.html')
            
            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long')
                return render(request, 'waf_proxy/settings.html')
            
            request.user.set_password(new_password)
            messages.success(request, 'Password updated successfully! Please log in again.')
        
        try:
            request.user.save()
            if not (current_password and new_password):
                messages.success(request, 'Settings updated successfully!')
        except Exception as e:
            messages.error(request, f'Failed to update settings: {str(e)}')
    
    return render(request, 'waf_proxy/settings.html')

# Admin Management Views
@admin_required
def customer_detail(request, customer_id):
    try:
        customer = User.objects.get(id=customer_id, user_type='customer')
    except User.DoesNotExist:
        messages.error(request, 'Customer not found')
        return redirect('customer_list')
    
    # Get customer's sites and stats
    sites = Site.objects.filter(owner=customer)
    total_requests = RequestLog.objects.filter(site__owner=customer).count()
    blocked_requests = RequestLog.objects.filter(site__owner=customer, status='BLOCKED').count()
    
    context = {
        'customer': customer,
        'sites': sites,
        'total_requests': total_requests,
        'blocked_requests': blocked_requests,
    }
    return render(request, 'waf_proxy/admin/customer_detail.html', context)

@admin_required
def rule_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        pattern = request.POST.get('pattern')
        rule_type = request.POST.get('rule_type')
        action = request.POST.get('action')
        description = request.POST.get('description', '')
        is_global = 'is_global' in request.POST
        
        if not all([name, pattern, rule_type, action]):
            messages.error(request, 'Please fill in all required fields')
            return render(request, 'waf_proxy/admin/rule_add.html')
        
        try:
            rule = Rule.objects.create(
                name=name,
                pattern=pattern,
                rule_type=rule_type,
                action=action,
                description=description,
                is_global=is_global,
                is_active=True
            )
            messages.success(request, f'Rule "{rule.name}" created successfully!')
            return redirect('rule_list')
        except Exception as e:
            messages.error(request, f'Failed to create rule: {str(e)}')
    
    return render(request, 'waf_proxy/admin/rule_add.html')

@admin_required
def rule_edit(request, rule_id):
    try:
        rule = Rule.objects.get(id=rule_id)
    except Rule.DoesNotExist:
        messages.error(request, 'Rule not found')
        return redirect('rule_list')
    
    if request.method == 'POST':
        rule.name = request.POST.get('name', rule.name)
        rule.pattern = request.POST.get('pattern', rule.pattern)
        rule.rule_type = request.POST.get('rule_type', rule.rule_type)
        rule.action = request.POST.get('action', rule.action)
        rule.description = request.POST.get('description', rule.description)
        rule.is_global = 'is_global' in request.POST
        rule.is_active = 'is_active' in request.POST
        
        try:
            rule.save()
            messages.success(request, 'Rule updated successfully!')
            return redirect('rule_list')
        except Exception as e:
            messages.error(request, f'Failed to update rule: {str(e)}')
    
    return render(request, 'waf_proxy/admin/rule_edit.html', {'rule': rule})

@admin_required
def rule_delete(request, rule_id):
    try:
        rule = Rule.objects.get(id=rule_id)
    except Rule.DoesNotExist:
        messages.error(request, 'Rule not found')
        return redirect('rule_list')
    
    if request.method == 'POST':
        rule_name = rule.name
        rule.delete()
        messages.success(request, f'Rule "{rule_name}" deleted successfully!')
        return redirect('rule_list')
    
    return render(request, 'waf_proxy/admin/rule_delete.html', {'rule': rule})

@admin_required
def system_status(request):
    import psutil
    import datetime
    
    # System information
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Database stats
    total_users = User.objects.count()
    total_sites = Site.objects.count()
    total_rules = Rule.objects.count()
    total_logs = RequestLog.objects.count()
    
    # Recent activity
    today = timezone.now().date()
    requests_today = RequestLog.objects.filter(timestamp__date=today).count()
    blocks_today = RequestLog.objects.filter(timestamp__date=today, status='BLOCKED').count()
    
    context = {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_used': memory.used // (1024**3),  # GB
        'memory_total': memory.total // (1024**3),  # GB
        'disk_percent': (disk.used / disk.total) * 100,
        'disk_used': disk.used // (1024**3),  # GB
        'disk_total': disk.total // (1024**3),  # GB
        'total_users': total_users,
        'total_sites': total_sites,
        'total_rules': total_rules,
        'total_logs': total_logs,
        'requests_today': requests_today,
        'blocks_today': blocks_today,
    }
    return render(request, 'waf_proxy/admin/system_status.html', context)

# API Documentation
def api_docs(request):
    return render(request, 'waf_proxy/api_docs.html')

# WAF Security Views
def blocked_request(request):
    """Handle blocked requests from WAF"""
    # Get block information from session or URL parameters
    block_reason = request.GET.get('reason', 'Security policy violation')
    rule_name = request.GET.get('rule', 'Security Rule')
    client_ip = request.META.get('REMOTE_ADDR', 'Unknown')
    timestamp = timezone.now()
    
    # Get the original URL that was blocked
    blocked_url = request.GET.get('url', request.META.get('HTTP_REFERER', '/'))
    
    # Get site information if available
    site_domain = request.GET.get('site', request.get_host())
    
    context = {
        'block_reason': block_reason,
        'rule_name': rule_name,
        'client_ip': client_ip,
        'timestamp': timestamp,
        'blocked_url': blocked_url,
        'site_domain': site_domain,
        'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
    }
    
    # Return blocked page with 403 status
    response = render(request, 'waf_proxy/blocked.html', context)
    response.status_code = 403
    return response

def access_denied(request):
    """Generic access denied page"""
    context = {
        'error_code': '403',
        'error_title': 'Access Denied',
        'error_message': 'You do not have permission to access this resource.',
    }
    response = render(request, 'waf_proxy/error.html', context)
    response.status_code = 403
    return response

def rate_limited(request):
    """Handle rate-limited requests"""
    context = {
        'error_code': '429',
        'error_title': 'Too Many Requests',
        'error_message': 'You have exceeded the rate limit. Please wait before trying again.',
        'retry_after': '60', # seconds
    }
    response = render(request, 'waf_proxy/error.html', context)
    response.status_code = 429
    return response

def test_protected_site(request):
    """
    Test view to demonstrate WAF protection.
    This should be accessible when visiting the demo site domain.
    """
    return HttpResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Protected Site Test - WAF Security</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
            .container { margin-top: 50px; }
            .card { background: rgba(255,255,255,0.95); color: #333; border-radius: 15px; }
            .test-link { margin: 10px 0; }
            .test-link a { color: #dc3545; text-decoration: none; }
            .test-link a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header text-center">
                            <h1><i class="fas fa-shield-alt text-primary"></i> WAF Protected Site</h1>
                            <p class="mb-0">Test the Web Application Firewall protection</p>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-info">
                                <strong>Welcome to the WAF Test Site!</strong><br>
                                This page demonstrates how our Web Application Firewall protects against various attacks.
                                Click the links below to test different security scenarios.
                            </div>
                            
                            <h3><i class="fas fa-bug text-danger"></i> Security Tests</h3>
                            <p>Click any of these links to see how the WAF blocks malicious requests:</p>
                            
                            <div class="row">
                                <div class="col-md-6">
                                    <h5>SQL Injection Tests</h5>
                                    <div class="test-link">
                                        <i class="fas fa-database text-warning"></i>
                                        <a href="/?id=1' UNION SELECT * FROM users--">Basic Union Injection</a>
                                    </div>
                                    <div class="test-link">
                                        <i class="fas fa-database text-warning"></i>
                                        <a href="/?search=admin'--">Admin Comment Injection</a>
                                    </div>
                                    <div class="test-link">
                                        <i class="fas fa-database text-warning"></i>
                                        <a href="/?query=DROP TABLE users">Drop Table Attack</a>
                                    </div>
                                </div>
                                
                                <div class="col-md-6">
                                    <h5>XSS Tests</h5>
                                    <div class="test-link">
                                        <i class="fas fa-code text-danger"></i>
                                        <a href="/?search=<script>alert('XSS')</script>">Script Tag Injection</a>
                                    </div>
                                    <div class="test-link">
                                        <i class="fas fa-code text-danger"></i>
                                        <a href="/?name=<img src=x onerror=alert('XSS')>">Image Onerror XSS</a>
                                    </div>
                                    <div class="test-link">
                                        <i class="fas fa-code text-danger"></i>
                                        <a href="/?url=javascript:alert('XSS')">JavaScript Protocol</a>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row mt-4">
                                <div class="col-md-6">
                                    <h5>Path Traversal Tests</h5>
                                    <div class="test-link">
                                        <i class="fas fa-folder text-warning"></i>
                                        <a href="/file?path=../../../etc/passwd">Linux Path Traversal</a>
                                    </div>
                                    <div class="test-link">
                                        <i class="fas fa-folder text-warning"></i>
                                        <a href="/file?path=..\\..\\windows\\system32\\config\\sam">Windows Path Traversal</a>
                                    </div>
                                </div>
                                
                                <div class="col-md-6">
                                    <h5>Rate Limiting Test</h5>
                                    <div class="test-link">
                                        <i class="fas fa-clock text-info"></i>
                                        <button class="btn btn-sm btn-outline-primary" onclick="testRateLimit()">
                                            Trigger Rate Limit
                                        </button>
                                    </div>
                                    <div id="rateTestStatus" class="mt-2"></div>
                                </div>
                            </div>
                            
                            <hr>
                            
                            <div class="alert alert-success">
                                <h5><i class="fas fa-check-circle"></i> Normal Operation</h5>
                                <p class="mb-0">
                                    This page loads normally because it doesn't contain any malicious patterns.
                                    The WAF allows legitimate traffic while blocking threats.
                                </p>
                            </div>
                            
                            <div class="text-center">
                                <a href="/login/" class="btn btn-primary">
                                    <i class="fas fa-sign-in-alt"></i> Go to Admin Login
                                </a>
                                <a href="/api/docs/" class="btn btn-outline-secondary">
                                    <i class="fas fa-book"></i> API Documentation
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            function testRateLimit() {
                const statusDiv = document.getElementById('rateTestStatus');
                statusDiv.innerHTML = '<div class="alert alert-warning">Sending multiple requests...</div>';
                
                // Send multiple rapid requests to trigger rate limiting
                let requests = 0;
                const maxRequests = 20;
                
                function sendRequest() {
                    fetch(window.location.href + '?ratetest=' + Date.now())
                        .then(response => {
                            requests++;
                            if (requests >= maxRequests) {
                                statusDiv.innerHTML = '<div class="alert alert-info">Rate limit test completed. Try refreshing the page multiple times quickly.</div>';
                            }
                        })
                        .catch(error => {
                            statusDiv.innerHTML = '<div class="alert alert-danger">Rate limit triggered! Requests are now being limited.</div>';
                        });
                }
                
                // Send requests rapidly
                for (let i = 0; i < maxRequests; i++) {
                    setTimeout(sendRequest, i * 100);
                }
            }
        </script>
    </body>
    </html>
    """)

# Registration and Email Verification Views
@csrf_protect
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        company_name = request.POST.get('company_name', '')
        phone = request.POST.get('phone', '')
        agree_terms = request.POST.get('agree_terms')
        captcha_answer = request.POST.get('captcha_answer')
        
        # CAPTCHA validation
        try:
            captcha_value = int(captcha_answer) if captcha_answer else 0
            if captcha_value < 2 or captcha_value > 20:  # Basic range check
                messages.error(request, 'Please complete the CAPTCHA correctly')
                return render(request, 'waf_proxy/auth/register.html')
        except (ValueError, TypeError):
            messages.error(request, 'Please complete the CAPTCHA correctly')
            return render(request, 'waf_proxy/auth/register.html')
        
        # Basic validation
        if not all([email, password, password_confirm, first_name, last_name]):
            messages.error(request, 'Please fill in all required fields')
            return render(request, 'waf_proxy/auth/register.html')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            return render(request, 'waf_proxy/auth/register.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return render(request, 'waf_proxy/auth/register.html')
        
        if not agree_terms:
            messages.error(request, 'Please agree to the Terms of Service')
            return render(request, 'waf_proxy/auth/register.html')
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists')
            return render(request, 'waf_proxy/auth/register.html')
        
        # Create user
        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                company_name=company_name,
                phone=phone,
                user_type='customer',
                is_active=False,  # Will be activated after email verification
                is_email_verified=False
            )
            
            # Send verification email
            if send_verification_email(user):
                messages.success(request, 'Registration successful! Please check your email to verify your account.')
                return render(request, 'waf_proxy/auth/email_sent.html', {'email': email})
            else:
                messages.error(request, 'Registration successful, but we could not send the verification email. Please contact support.')
                return render(request, 'waf_proxy/auth/email_sent.html', {'email': email})
                
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'waf_proxy/auth/register.html')
    
    return render(request, 'waf_proxy/auth/register.html')

def verify_email(request, token):
    try:
        verification = EmailVerificationToken.objects.get(token=token, is_used=False)
        
        if verification.is_expired():
            messages.error(request, 'Verification link has expired. Please request a new one.')
            return redirect('register')
        
        # Activate user
        user = verification.user
        user.is_active = True
        user.is_email_verified = True
        user.save()
        
        # Mark token as used
        verification.is_used = True
        verification.save()
        
        # Send welcome email
        send_welcome_email(user)
        
        messages.success(request, 'Email verified successfully! Your account is now active.')
        return render(request, 'waf_proxy/auth/email_verified.html', {'user': user})
        
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, 'Invalid or expired verification link.')
        return redirect('register')

@csrf_protect
def resend_verification(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email, is_email_verified=False)
            
            # Send new verification email (with built-in rate limiting)
            if send_verification_email(user):
                messages.success(request, 'Verification email sent successfully!')
                return render(request, 'waf_proxy/auth/email_sent.html', {'email': email})
            else:
                # Check if it's due to rate limiting
                from django.utils import timezone
                recent_tokens = EmailVerificationToken.objects.filter(
                    user=user,
                    created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
                ).count()
                
                max_resends = getattr(settings, 'EMAIL_MAX_RESEND_ATTEMPTS', 3)
                if recent_tokens >= max_resends:
                    messages.error(request, 'Too many verification emails sent. Please wait 5 minutes before requesting another one.')
                else:
                    messages.error(request, 'Failed to send verification email. Please try again later.')
                
                return render(request, 'waf_proxy/auth/email_sent.html', {'email': email})
                
        except User.DoesNotExist:
            messages.error(request, 'No unverified account found with this email address.')
            return redirect('register')
    
    return redirect('register')

# Password Reset Views
@csrf_protect
def forgot_password(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email, is_active=True)
            
            # Delete any existing unused tokens for this user
            PasswordResetToken.objects.filter(user=user, is_used=False).delete()
            
            # Send password reset email
            if send_password_reset_email(user):
                messages.success(request, 'Password reset link sent to your email address.')
            else:
                messages.error(request, 'Failed to send reset email. Please try again.')
                
            return render(request, 'waf_proxy/auth/email_sent.html', {
                'email': email,
                'reset_email': True
            })
            
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            messages.success(request, 'If an account with this email exists, you will receive a password reset link.')
            return render(request, 'waf_proxy/auth/email_sent.html', {
                'email': email,
                'reset_email': True
            })
    
    return render(request, 'waf_proxy/auth/forgot_password.html')

@csrf_protect
def reset_password(request, token):
    try:
        reset_token = PasswordResetToken.objects.get(token=token, is_used=False)
        
        if reset_token.is_expired():
            messages.error(request, 'Password reset link has expired. Please request a new one.')
            return redirect('forgot_password')
        
        user = reset_token.user
        
        if request.method == 'POST':
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')
            
            if not password or not password_confirm:
                messages.error(request, 'Please fill in all fields')
                return render(request, 'waf_proxy/auth/reset_password.html', {'user': user})
            
            if password != password_confirm:
                messages.error(request, 'Passwords do not match')
                return render(request, 'waf_proxy/auth/reset_password.html', {'user': user})
            
            if len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters long')
                return render(request, 'waf_proxy/auth/reset_password.html', {'user': user})
            
            # Update password
            user.set_password(password)
            user.save()
            
            # Mark token as used
            reset_token.is_used = True
            reset_token.save()
            
            messages.success(request, 'Password reset successfully! You can now sign in with your new password.')
            return redirect('login')
        
        return render(request, 'waf_proxy/auth/reset_password.html', {'user': user})
        
    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Invalid or expired password reset link.')
        return redirect('forgot_password')
