from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Decorator to ensure only admin users can access a view.
    Redirects to login if user is not authenticated or not an admin.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')

        if request.user.user_type != 'admin':
            messages.error(request, 'Admin access required.')
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper


def customer_required(view_func):
    """
    Decorator to ensure only customer users can access a view.
    Redirects to login if user is not authenticated or not a customer.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')

        if request.user.user_type != 'customer':
            messages.error(request, 'Customer access required.')
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_custom(view_func):
    """
    Custom login required decorator that works with our User model.
    Redirects to login if user is not authenticated.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper


def site_owner_required(view_func):
    """
    Decorator to ensure only the site owner can access site-specific views.
    Expects site_id in kwargs.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')

        site_id = kwargs.get('site_id')
        if site_id:
            from .models import Site
            try:
                site = Site.objects.get(id=site_id)
                if site.owner != request.user and request.user.user_type != 'admin':
                    messages.error(request, 'You do not have permission to access this site.')
                    return redirect('site_list')
            except Site.DoesNotExist:
                messages.error(request, 'Site not found.')
                return redirect('site_list')

        return view_func(request, *args, **kwargs)
    return wrapper
