from django import template

register = template.Library()

@register.filter
def split(value, key=" "):
    """Split the string by the given key (default: space)."""
    if not value:
        return []
    return value.split(key)
