from django import template

register = template.Library()

@register.filter(name='range')
def filter_range(start, end):
    """
    Expose the builtin range function to templates, since django lacks this
    behavior by default.
    """
    return range(start, end)
