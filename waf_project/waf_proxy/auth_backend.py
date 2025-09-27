from django.contrib.auth.backends import ModelBackend
from .models import User


class CustomUserBackend(ModelBackend):
    """
    Custom authentication backend for our custom User model
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Support both 'username' and 'email' parameters
        email = kwargs.get('email') or username
        
        if email is None or password is None:
            return None
        
        try:
            user = User.objects.get(email=email, is_active=True)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None