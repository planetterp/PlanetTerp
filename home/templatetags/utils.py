from django import template
from django.urls import reverse
from django.templatetags.static import static

from home import utils


register = template.Library()

@register.filter(name='range')
def filter_range(start, end):
    """
    Expose the builtin range function to templates, since django lacks this
    behavior by default.
    """
    return range(start, end)

@register.simple_tag(takes_context=True)
def full_url(context, name):
    return context.request.build_absolute_uri(reverse(name))

@register.simple_tag(takes_context=True)
def full_static(context, name):
    return context.request.build_absolute_uri(static(name))

@register.simple_tag
def current_semester():
    return utils.Semester.current().number()
