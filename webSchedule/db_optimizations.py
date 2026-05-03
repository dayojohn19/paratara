"""
Database Optimization Utilities
Add these to your models and views for better performance
"""
from django.db import models
from django.core.cache import cache
from functools import wraps
import hashlib
import json


def cache_query(timeout=300):
    """
    Decorator to cache database queries
    Usage: @cache_query(timeout=600)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__module__}.{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"
            
            result = cache.get(cache_key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


class OptimizedQuerySetMixin:
    """
    Mixin to add to your models for optimized queries
    
    Example:
    class MyModel(OptimizedQuerySetMixin, models.Model):
        # your fields
        pass
    """
    
    @classmethod
    def get_optimized_queryset(cls):
        """
        Returns an optimized queryset with select_related and prefetch_related
        Override this in your models to specify relationships
        """
        return cls.objects.all()
    
    @classmethod
    def get_cached(cls, **kwargs):
        """
        Get object with caching
        """
        cache_key = f"{cls.__name__}:{json.dumps(kwargs, sort_keys=True)}"
        obj = cache.get(cache_key)
        if obj is None:
            obj = cls.objects.get(**kwargs)
            cache.set(cache_key, obj, 300)
        return obj


def bulk_create_optimized(model_class, objects_list, batch_size=1000):
    """
    Optimized bulk create with batching
    
    Usage:
    bulk_create_optimized(MyModel, [obj1, obj2, obj3, ...], batch_size=1000)
    """
    from django.db import transaction
    
    with transaction.atomic():
        for i in range(0, len(objects_list), batch_size):
            batch = objects_list[i:i + batch_size]
            model_class.objects.bulk_create(batch, batch_size=batch_size)


def bulk_update_optimized(queryset, fields, batch_size=1000):
    """
    Optimized bulk update with batching
    
    Usage:
    bulk_update_optimized(MyModel.objects.filter(...), ['field1', 'field2'], batch_size=1000)
    """
    from django.db import transaction
    
    objects = list(queryset)
    with transaction.atomic():
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            queryset.model.objects.bulk_update(batch, fields, batch_size=batch_size)
