"""
Example: How to Apply Optimizations to Your Views

This file shows you how to use the optimization utilities created.
You can copy these patterns to your actual view files.
"""

# ============================================
# EXAMPLE 1: Cache entire page
# ============================================
from django.views.decorators.cache import cache_page
from django.shortcuts import render

@cache_page(60 * 5)  # Cache for 5 minutes
def resort_list_view(request):
    """
    Public page - cache the entire response
    Good for: landing pages, resort listings, blog posts
    """
    from resorts.models import Resort
    resorts = Resort.objects.all()
    return render(request, 'resorts/list.html', {'resorts': resorts})


# ============================================
# EXAMPLE 2: Cache per-user (authenticated content)
# ============================================
from webSchedule.view_optimizations import cache_page_with_user

@cache_page_with_user(60 * 10)  # Cache for 10 minutes per user
def user_dashboard(request):
    """
    User-specific page - cache separately for each user
    Good for: user dashboards, profile pages
    """
    user_data = {
        'bookings': request.user.bookings.all(),
        'favorites': request.user.favorites.all(),
    }
    return render(request, 'dashboard.html', user_data)


# ============================================
# EXAMPLE 3: Cache database queries
# ============================================
from webSchedule.db_optimizations import cache_query

@cache_query(timeout=60 * 15)  # Cache for 15 minutes
def get_popular_resorts():
    """
    Cache expensive database queries
    Good for: frequently accessed data that doesn't change often
    """
    from resorts.models import Resort
    return Resort.objects.filter(
        is_active=True
    ).select_related('location').prefetch_related('amenities')[:10]


def resort_view_with_cached_query(request):
    """Use the cached query in your view"""
    popular_resorts = get_popular_resorts()
    return render(request, 'popular.html', {'resorts': popular_resorts})


# ============================================
# EXAMPLE 4: Optimize queryset with select_related
# ============================================
def optimized_resort_detail(request, resort_id):
    """
    Use select_related and prefetch_related to reduce queries
    """
    from resorts.models import Resort
    
    # BAD: Multiple queries
    # resort = Resort.objects.get(id=resort_id)
    # location = resort.location  # Query 2
    # reviews = resort.reviews.all()  # Query 3
    
    # GOOD: Single query with joins
    resort = Resort.objects.select_related(
        'location',
        'owner'
    ).prefetch_related(
        'reviews',
        'amenities',
        'packages'
    ).get(id=resort_id)
    
    return render(request, 'resort_detail.html', {'resort': resort})


# ============================================
# EXAMPLE 5: Bulk operations
# ============================================
from webSchedule.db_optimizations import bulk_create_optimized, bulk_update_optimized

def import_resorts_from_api(request):
    """
    Efficiently create many objects at once
    """
    from resorts.models import Resort
    
    # Fetch data from external API
    api_data = fetch_resorts_from_external_api()
    
    # Create Resort objects
    resort_objects = [
        Resort(
            name=item['name'],
            location=item['location'],
            price=item['price']
        )
        for item in api_data
    ]
    
    # BAD: Loop and save (N queries)
    # for resort in resort_objects:
    #     resort.save()
    
    # GOOD: Bulk create (1 query)
    bulk_create_optimized(Resort, resort_objects, batch_size=1000)
    
    return render(request, 'import_success.html')


# ============================================
# EXAMPLE 6: Invalidate cache when data changes
# ============================================
from webSchedule.view_optimizations import invalidate_cache
from django.views.decorators.http import require_POST

@require_POST
def update_resort(request, resort_id):
    """
    Invalidate relevant caches when updating data
    """
    from resorts.models import Resort
    
    resort = Resort.objects.get(id=resort_id)
    resort.name = request.POST.get('name')
    resort.save()
    
    # Clear caches related to this resort
    invalidate_cache(f'resort:{resort_id}:*')
    invalidate_cache('popular_resorts:*')
    
    return redirect('resort_detail', resort_id=resort_id)


# ============================================
# EXAMPLE 7: Use model optimization mixin
# ============================================
"""
In your models.py file:

from webSchedule.db_optimizations import OptimizedQuerySetMixin
from django.db import models

class Resort(OptimizedQuerySetMixin, models.Model):
    name = models.CharField(max_length=200)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    
    @classmethod
    def get_optimized_queryset(cls):
        # Define how to optimize queries for this model
        return cls.objects.select_related('location').prefetch_related('amenities')

# Then in views:
resorts = Resort.get_optimized_queryset()
"""


# ============================================
# EXAMPLE 8: Template fragment caching
# ============================================
"""
In your templates, cache expensive parts:

{% load cache %}

{% cache 600 resort_sidebar resort.id %}
    <div class="sidebar">
        <h3>{{ resort.name }}</h3>
        {% for amenity in resort.amenities.all %}
            <span>{{ amenity.name }}</span>
        {% endfor %}
    </div>
{% endcache %}
"""


# ============================================
# EXAMPLE 9: API endpoint with caching
# ============================================
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.core.cache import cache

@api_view(['GET'])
def api_resort_list(request):
    """
    Cache API responses
    """
    cache_key = 'api:resorts:list'
    
    # Try to get from cache
    data = cache.get(cache_key)
    
    if data is None:
        # Not in cache, fetch from database
        from resorts.models import Resort
        from resorts.serializers import ResortSerializer
        
        resorts = Resort.objects.all()
        serializer = ResortSerializer(resorts, many=True)
        data = serializer.data
        
        # Store in cache for 5 minutes
        cache.set(cache_key, data, 60 * 5)
    
    return Response(data)


# ============================================
# QUICK WINS - Apply These First
# ============================================
"""
1. Add @cache_page(300) to all public list/detail views
2. Use select_related() for all ForeignKey lookups
3. Use prefetch_related() for all reverse ForeignKey and ManyToMany
4. Add database indexes to frequently filtered fields
5. Use bulk_create for creating multiple objects
6. Cache expensive computations and API calls
"""
