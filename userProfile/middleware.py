import threading

# Thread-local storage for request
_thread_locals = threading.local()

def get_current_request():
    """Get the current request from thread-local storage"""
    return getattr(_thread_locals, 'request', None)

def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class RequestMiddleware:
    """Middleware to store request in thread-local storage"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store request in thread-local storage
        _thread_locals.request = request
        response = self.get_response(request)
        return response
