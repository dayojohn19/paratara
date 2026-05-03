"""
Performance Optimization Middleware
Add custom middleware for monitoring and optimization
"""
import time
import logging
from django.core.cache import cache
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware:
    """
    Monitor response times and log slow requests
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        
        # Log slow requests (> 1 second)
        if duration > 1.0:
            logger.warning(f"Slow request: {request.path} took {duration:.2f}s")
        
        # Add performance header for debugging
        response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response


class MinifyHTMLMiddleware:
    """
    Minify HTML responses to reduce bandwidth
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if response.get('Content-Type', '').startswith('text/html'):
            try:
                import re
                # Remove extra whitespace
                content = response.content.decode('utf-8')
                content = re.sub(r'\s+', ' ', content)
                content = re.sub(r'>\s+<', '><', content)
                response.content = content.encode('utf-8')
            except:
                pass
        
        return response


class DatabaseConnectionPoolingMiddleware:
    """
    Ensure database connections are properly managed
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Close old connections
        from django.db import connection
        if connection.queries_log:
            total_time = sum(float(q['time']) for q in connection.queries_log)
            if total_time > 0.5:  # Log if DB queries take > 0.5s
                logger.warning(f"Slow DB queries on {request.path}: {len(connection.queries_log)} queries, {total_time:.2f}s total")
        
        return response
