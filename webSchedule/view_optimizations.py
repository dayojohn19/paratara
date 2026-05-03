"""
View Caching Decorators and Utilities
Add these to your views for instant performance boost
"""
from django.views.decorators.cache import cache_page, cache_control
from django.views.decorators.http import last_modified
from django.core.cache import cache
from functools import wraps
import hashlib


def cache_page_with_user(timeout):
    """
    Cache page but separate cache per user
    Usage: @cache_page_with_user(300)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            cache_key = f"view_cache:{request.user.id if request.user.is_authenticated else 'anon'}:{request.path}:{hashlib.md5(request.GET.urlencode().encode()).hexdigest()}"
            
            response = cache.get(cache_key)
            if response is None:
                response = view_func(request, *args, **kwargs)
                cache.set(cache_key, response, timeout)
            return response
        return wrapper
    return decorator


def cache_queryset(timeout=300):
    """
    Cache queryset results
    Usage: 
    @cache_queryset(timeout=600)
    def get_all_resorts():
        return Resort.objects.all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"qs:{func.__module__}.{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"
            
            result = cache.get(cache_key)
            if result is None:
                result = list(func(*args, **kwargs))  # Convert to list to cache
                cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def invalidate_cache(pattern):
    """
    Invalidate all cache keys matching pattern
    Usage: invalidate_cache('resort:*')
    """
    from django.core.cache import cache
    if hasattr(cache, 'keys'):
        keys = cache.keys(pattern)
        cache.delete_many(keys)


# Example usage in views:
"""
from django.views.decorators.cache import cache_page
from webSchedule.view_optimizations import cache_page_with_user

# Cache entire page for 5 minutes
@cache_page(300)
def my_view(request):
    # expensive operations
    return render(request, 'template.html', context)

# Cache page per user for 10 minutes
@cache_page_with_user(600)
def profile_view(request):
    # user-specific content
    return render(request, 'profile.html', context)
"""
