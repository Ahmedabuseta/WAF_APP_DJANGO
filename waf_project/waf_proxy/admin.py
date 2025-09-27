
from django.contrib import admin
from .models import User, Site, Rule, SiteRule, RequestLog, SiteStats, RateLimit

# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'user_type', 'is_active', 'created_at']
    list_filter = ['user_type', 'is_active']
    search_fields = ['email', 'company_name']

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['domain', 'owner', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['domain', 'owner__email']

@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'action', 'is_global', 'created_at']
    list_filter = ['rule_type', 'action', 'is_global']
    search_fields = ['name', 'description']

@admin.register(SiteRule)
class SiteRuleAdmin(admin.ModelAdmin):
    list_display = ['site', 'rule', 'is_active', 'created_at']
    list_filter = ['is_active', 'rule__rule_type']
    search_fields = ['site__domain', 'rule__name']

@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ['site', 'ip_address', 'method', 'status', 'timestamp']
    list_filter = ['status', 'method', 'timestamp']
    search_fields = ['site__domain', 'ip_address', 'url']

@admin.register(SiteStats)
class SiteStatsAdmin(admin.ModelAdmin):
    list_display = ['site', 'date', 'total_requests', 'blocked_requests', 'allowed_requests']
    list_filter = ['date']
    search_fields = ['site__domain']

@admin.register(RateLimit)
class RateLimitAdmin(admin.ModelAdmin):
    list_display = ['site', 'ip_address', 'request_count', 'window_start']
    list_filter = ['window_start']
    search_fields = ['site__domain', 'ip_address']

