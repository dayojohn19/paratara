from django.http import HttpResponseForbidden
import time
from django.core.cache import cache
from home.models import RequestLog, RequestPage, BlockedIP
from django.contrib.gis.geoip2 import GeoIP2
import os
import ipaddress
from typing import Optional

from django.conf import settings


"""
Middleware to block or throttle requests based on IP address.
Prevents SPAMMING and excessive requests.
"""


# --- Moved from home.middleware.py ---
from datetime import timedelta
from django.http import HttpResponse
from django.utils import timezone

class NotFoundIPBlockMiddleware:
    
    """Blocks an IP for 1 hour after 3x 404 responses within 1 hour.
    retun   
    Important: this middleware does *no* DB work unless the response is a 404.
    """

    THRESHOLD = 8
    WINDOW = timedelta(hours=1)
    BLOCK_FOR = timedelta(hours=1)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only run logic on 404 responses (no overhead on normal requests).
        if getattr(response, "status_code", None) != 404:
            return response
        print('Initializing NotFoundIPBlockMiddleware')
        ip_address = self._get_client_ip(request)
        if not ip_address:
            return response

        # Avoid blocking local development traffic.
        # if ip_address in {"127.0.0.1", "::1"}:
        #     return response

        now = timezone.now()

        try:
            # If currently blocked, convert 404 -> 429.
            active_block = BlockedIP.objects.filter(
                ip_address=ip_address,
                expires_at__gt=now,
            ).first()
            if active_block:
                return HttpResponse(
                    "Too many not-found requests. Try again later.",
                    status=429,
                )

            # Log this 404 attempt.
            RequestPage.objects.create(
                page_name=request.path,
                requesting_ip=ip_address,
                status_code=404,
            )

            # Count 404 attempts in the last hour.
            recent_count = RequestPage.objects.filter(
                requesting_ip=ip_address,
                status_code=404,
                timesmtamp__gte=now - self.WINDOW,
            ).count()

            # Warn on the second 404 within the window.
            if recent_count == 5:
                return HttpResponse(
                    "Warning: repeated not-found requests may temporarily block your IP.",
                    status=404,
                )

            if recent_count >= self.THRESHOLD:
                BlockedIP.objects.update_or_create(
                    ip_address=ip_address,
                    defaults={
                        "expires_at": now + self.BLOCK_FOR,
                        "reason": "3x 404 responses within 1 hour",
                    },
                )
                return HttpResponse(
                    "Your IP has been temporarily blocked for 1 hour.",
                    status=429,
                )

        except Exception:
            # Fail open (e.g., during migrations or DB issues).
            return response

        return response

    from typing import Optional
    @staticmethod
    def _get_client_ip(request) -> Optional[str]:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

BLOCKED_IPS = []

# class BlockIPMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         ip = self.get_client_ip(request)
#         
#         if ip in BLOCKED_IPS:
#             return HttpResponseForbidden("Access denied.")
#         return self.get_response(request)

#     def get_client_ip(self, request):
#         # Handle proxies/load balancers
#         x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
#         if x_forwarded_for:
#             ip = x_forwarded_for.split(",")[0]
#         else:
#             ip = request.META.get("REMOTE_ADDR")
#         return ip


def get_location(ip):
    try:
        geoip_path = getattr(settings, "GEOIP_PATH", None)
        if not geoip_path or not os.path.exists(geoip_path):
            return {"error": "GeoIP path missing or invalid"}

        g = GeoIP2(path=geoip_path)

        # Attempt city and country lookups independently to avoid hard failures
        try:
            city_data = g.city(ip)
        except Exception as e:
            city_data = {"error": str(e)}

        try:
            country_data = g.country(ip)
        except Exception as e:
            country_data = {"error": str(e)}

        return {
            "city_info": city_data,
            "country_info": country_data,
        }
    except Exception as e:
        return {"error": str(e)}

class SimpleThrottleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        ip = self.get_client_ip(request)
        
        path = request.path


        # Record every page visit
        try:
            RequestPage.objects.create(page_name=path, requesting_ip=ip)
        except Exception as e:
            # Handle database errors gracefully (e.g., table doesn't exist during migrations)
            pass

        return self.get_response(request)

    # def get_client_ip(self, request):
    #     # works with proxies
    #     x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    #     if x_forwarded_for:
    #         return x_forwarded_for.split(",")[0]
    #     return request.META.get("REMOTE_ADDR")

    def get_client_ip(self, request):
        def _normalize_ip(value: Optional[str]) -> Optional[str]:
            if not value:
                return None
            try:
                ip_obj = ipaddress.ip_address(value.strip())
            except ValueError:
                return None

            # Normalize IPv4-mapped IPv6 (e.g. ::ffff:1.2.3.4) back to IPv4
            if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
                return str(ip_obj.ipv4_mapped)
            return str(ip_obj)

        def _is_public(ip_str: str) -> bool:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                return False
            return ip_obj.is_global

        # Prefer common proxy/CDN headers if present
        for header in ("HTTP_CF_CONNECTING_IP", "HTTP_X_REAL_IP"):
            candidate = _normalize_ip(request.META.get(header))
            if candidate and _is_public(candidate):
                return candidate

        # X-Forwarded-For is a comma-separated list: client, proxy1, proxy2...
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            for part in [p.strip() for p in x_forwarded_for.split(",") if p.strip()]:
                candidate = _normalize_ip(part)
                if candidate and _is_public(candidate):
                    return candidate
            # Fall back to the first parseable entry
            first = _normalize_ip(x_forwarded_for.split(",")[0].strip())
            if first:
                return first

        # Last resort
        return _normalize_ip(request.META.get("REMOTE_ADDR")) or "0.0.0.0"









# for obj in RequestLog.objects.all():
#     if obj.ip_location_json:  # existing CharField
#         try:
#             # Convert Python dict string → real dict
#             py_dict = ast.literal_eval(obj.ip_location_json)
#             # Convert to proper JSON string
#             obj.ip_location_json = json.dumps(py_dict)
#             obj.save(update_fields=['ip_location_json'])
#         except Exception as e:
#             