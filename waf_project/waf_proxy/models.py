from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from datetime import timedelta
from allauth.account.signals import user_signed_up
from allauth.socialaccount.signals import social_account_added
from django.dispatch import receiver
import uuid
import secrets

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('user_type', 'admin')
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)

# Unified User Model
class User(AbstractBaseUser):
    USER_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    ]
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)

    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='customer')
    is_active = models.BooleanField(default=False)  # Changed to False for email verification
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    # Customer-specific fields
    company_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)

    # Admin-specific fields
    admin_level = models.CharField(max_length=20, choices=[
        ('super', 'Super Admin'),
        ('support', 'Support Admin'),
    ], blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.email} ({self.user_type})"

    def has_perm(self, perm, obj=None):
        return self.user_type == 'admin'

    def has_module_perms(self, app_label):
        return self.user_type == 'admin'

    def get_all_permissions(self, obj=None):
        """Return a set of permission strings that this user has."""
        if self.user_type == 'admin':
            # Return common Django permissions for admin users
            return {
                'auth.add_user', 'auth.change_user', 'auth.delete_user', 'auth.view_user',
                'waf_proxy.add_site', 'waf_proxy.change_site', 'waf_proxy.delete_site', 'waf_proxy.view_site',
                'waf_proxy.add_rule', 'waf_proxy.change_rule', 'waf_proxy.delete_rule', 'waf_proxy.view_rule',
                'waf_proxy.view_requestlog', 'waf_proxy.delete_requestlog'
            }
        return set()

    def get_group_permissions(self, obj=None):
        """Return a set of permission strings that this user has through their groups."""
        return set()

    def get_user_permissions(self, obj=None):
        """Return a set of permission strings that this user has directly."""
        if self.user_type == 'admin':
            return {
                'auth.add_user', 'auth.change_user', 'auth.delete_user', 'auth.view_user',
                'waf_proxy.add_site', 'waf_proxy.change_site', 'waf_proxy.delete_site', 'waf_proxy.view_site',
                'waf_proxy.add_rule', 'waf_proxy.change_rule', 'waf_proxy.delete_rule', 'waf_proxy.view_rule',
                'waf_proxy.view_requestlog', 'waf_proxy.delete_requestlog'
            }
        return set()

    @property
    def is_staff(self):
        return self.user_type == 'admin'

    @property
    def is_superuser(self):
        return self.user_type == 'admin' and self.admin_level == 'super'

# Signal handlers for Google OAuth
@receiver(user_signed_up)
def activate_user_on_google_signup(request, user, **kwargs):
    """لو اليوزر عامل تسجيل أول مرة بجوجل"""
    if user and not user.is_active:
        user.is_active = True
        user.is_email_verified = True
        user.save()

@receiver(social_account_added)
def activate_user_on_google_connect(request, sociallogin, **kwargs):
    """لو يوزر قديم وربط حساب جوجل"""
    user = sociallogin.user
    if user and not user.is_active:
        user.is_active = True
        user.is_email_verified = True
        user.save()
# Site Model
class Site(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    domain = models.CharField(max_length=255)
    backend_url = models.URLField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.domain} - {self.owner.email}"

# Rule Templates
class Rule(models.Model):
    RULE_TYPE_CHOICES = [
        ('sql_injection', 'SQL Injection'),
        ('xss', 'Cross-Site Scripting'),
        ('path_traversal', 'Path Traversal'),
        ('rate_limit', 'Rate Limiting'),
        ('bot_detection', 'Bot Detection'),
        ('custom', 'Custom Pattern'),
    ]

    ACTION_CHOICES = [
        ('BLOCK', 'Block'),
        ('ALLOW', 'Allow'),
        ('LOG', 'Log Only'),
    ]

    name = models.CharField(max_length=100)
    pattern = models.TextField()
    rule_type = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='BLOCK')
    description = models.TextField(blank=True)
    is_global = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.rule_type})"

# Site-specific Rule Activation
class SiteRule(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    rule = models.ForeignKey(Rule, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    custom_action = models.CharField(max_length=20, choices=Rule.ACTION_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['site', 'rule']

    def __str__(self):
        return f"{self.site.domain} - {self.rule.name}"

# Request Logs
class RequestLog(models.Model):
    STATUS_CHOICES = [
        ('BLOCKED', 'Blocked'),
        ('ALLOWED', 'Allowed'),
        ('RATE_LIMITED', 'Rate Limited'),
    ]

    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    url = models.URLField()
    method = models.CharField(max_length=10)
    user_agent = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    rule_matched = models.ForeignKey(Rule, null=True, blank=True, on_delete=models.SET_NULL)
    response_time = models.FloatField(null=True)  # milliseconds
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.site.domain} - {self.status} - {self.timestamp}"

# Daily Statistics
class SiteStats(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    date = models.DateField()
    total_requests = models.IntegerField(default=0)
    blocked_requests = models.IntegerField(default=0)
    allowed_requests = models.IntegerField(default=0)
    avg_response_time = models.FloatField(default=0)

    class Meta:
        unique_together = ['site', 'date']

    def __str__(self):
        return f"{self.site.domain} - {self.date}"

# Rate Limiting Counter
class RateLimit(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    request_count = models.IntegerField(default=1)
    window_start = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['site', 'ip_address']

    def __str__(self):
        return f"{self.site.domain} - {self.ip_address} - {self.request_count}"

# Email Verification Model
class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(50)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Email verification for {self.user.email}"

# Password Reset Model
class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(50)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)  # 1 hour expiry
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Password reset for {self.user.email}"
