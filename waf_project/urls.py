"""
URL configuration for waf_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from waf_proxy import views

urlpatterns = [
    # Authentication
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    
    # OAuth URLs
    path('accounts/', include('allauth.urls')),
    
    # Customer views
    path('customer/', views.customer_dashboard, name='customer_dashboard'),
    path('sites/', views.site_list, name='site_list'),
    path('sites/add/', views.site_add, name='site_add'),
    path('sites/<int:site_id>/', views.site_detail, name='site_detail'),
    path('sites/<int:site_id>/edit/', views.site_edit, name='site_edit'),
    path('sites/<int:site_id>/delete/', views.site_delete, name='site_delete'),
    path('sites/<int:site_id>/rules/', views.site_rules, name='site_rules'),
    path('sites/<int:site_id>/rules/add/', views.site_rule_add, name='site_rule_add'),
    path('sites/<int:site_id>/rules/<int:rule_id>/edit/', views.site_rule_edit, name='site_rule_edit'),
    path('sites/<int:site_id>/rules/<int:rule_id>/delete/', views.site_rule_delete, name='site_rule_delete'),
    path('sites/<int:site_id>/rules/import/', views.site_rules_import, name='site_rules_import'),
    path('sites/<int:site_id>/rules/export/', views.site_rules_export, name='site_rules_export'),
    path('sites/<int:site_id>/stats/', views.site_stats, name='site_stats'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.user_settings, name='user_settings'),
    
    # Custom Admin views (MUST come before Django admin to avoid conflicts)
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/customers/', views.customer_list, name='customer_list'),
    path('admin/customers/<int:customer_id>/', views.customer_detail, name='customer_detail'),
    path('admin/sites/', views.admin_site_list, name='admin_site_list'),
    path('admin/rules/', views.rule_list, name='rule_list'),
    path('admin/rules/add/', views.rule_add, name='rule_add'),
    path('admin/rules/<int:rule_id>/edit/', views.rule_edit, name='rule_edit'),
    path('admin/rules/<int:rule_id>/delete/', views.rule_delete, name='rule_delete'),
    path('admin/logs/', views.log_list, name='log_list'),
    path('admin/system/', views.system_status, name='system_status'),
    
    # API Documentation
    path('api/docs/', views.api_docs, name='api_docs'),
    
    # WAF Security Pages
    path('blocked/', views.blocked_request, name='blocked_request'),
    path('access-denied/', views.access_denied, name='access_denied'),
    path('rate-limited/', views.rate_limited, name='rate_limited'),
    
    # Django built-in admin (MUST come after custom admin routes)
    path('admin/', admin.site.urls),
    
    # Test route for WAF demonstration
    path('test/', views.test_protected_site, name='test_protected_site'),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
