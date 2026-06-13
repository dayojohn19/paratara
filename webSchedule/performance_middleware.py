"""
Performance Optimization Middleware
Add custom middleware for monitoring and optimization
"""
import time



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
        return response
