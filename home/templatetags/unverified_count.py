from home.models import Professor, Review
from django import template

register = template.Library()

@register.simple_tag()
def unverified_count():
    num_professors = Professor.objects.filter(status=Professor.Status.PENDING).count()
    num_reviews = Review.objects.filter(status=Review.Status.PENDING).count()
    return num_professors + num_reviews
