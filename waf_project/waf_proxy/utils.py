"""
Utility functions for WAF authentication
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from .models import EmailVerificationToken, PasswordResetToken
import logging
logger = logging.getLogger(__name__)
def send_verification_email(user):
    """Send email verification to user"""

    # Create or get existing token
    token, created = EmailVerificationToken.objects.get_or_create(
        user=user,
        is_used=False,
        defaults={}
    )

    # If token exists but is expired, create a new one
    if not created and token.is_expired():
        token.delete()
        token = EmailVerificationToken.objects.create(user=user)

    # Build verification URL
    verification_url = f"{settings.SITE_URL}{reverse('verify_email', args=[token.token])}"

    # Email context
    context = {
        'user': user,
        'verification_url': verification_url,
        'site_name': 'WAF Security',
        'expires_hours': 24,
    }

    # Render email templates
    subject = f"{settings.EMAIL_SUBJECT_PREFIX}Please verify your email address"
    text_content = render_to_string('waf_proxy/emails/verification_email.txt', context)
    html_content = render_to_string('waf_proxy/emails/verification_email.html', context)

    # Send email
    try:
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
        )
        logger.info(f"Verification email sent to {user.email}")
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False


def send_password_reset_email(user):
    """Send password reset email to user"""

    # Create password reset token
    token = PasswordResetToken.objects.create(user=user)

    # Build reset URL
    reset_url = f"{settings.SITE_URL}{reverse('reset_password', args=[token.token])}"

    # Email context
    context = {
        'user': user,
        'reset_url': reset_url,
        'site_name': 'WAF Security',
        'expires_hours': 1,
    }

    # Render email templates
    subject = f"{settings.EMAIL_SUBJECT_PREFIX}Password Reset Request"
    text_content = render_to_string('waf_proxy/emails/password_reset_email.txt', context)
    html_content = render_to_string('waf_proxy/emails/password_reset_email.html', context)

    # Send email
    try:
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
        )
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False


def send_welcome_email(user):
    """Send welcome email after successful registration"""

    context = {
        'user': user,
        'site_name': 'WAF Security',
        'login_url': f"{settings.SITE_URL}{reverse('login')}",
    }

    # Render email templates
    subject = f"{settings.EMAIL_SUBJECT_PREFIX}Welcome to WAF Security!"
    text_content = render_to_string('waf_proxy/emails/welcome_email.txt', context)
    html_content = render_to_string('waf_proxy/emails/welcome_email.html', context)

    # Send email
    try:
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
        )
        return True
    except Exception as e:
        print(f"Failed to send welcome email: {e}")
        return False
