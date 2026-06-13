from django import template

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    """Split a string by the given separator"""
    if value:
        return value.split(arg)
    return []


@register.filter(name='mask_middle')
def mask_middle(value):
    if value is None:
        return ""

    value = str(value)
    if not value:
        return ""

    if len(value) <= 4:
        return "*" * len(value)

    return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
