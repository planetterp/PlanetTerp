from home.models import Professor, Review
from django import template

register = template.Library()

@register.simple_tag()
def unverified_count():
    num_professors = Professor.pending.count()
    num_reviews = Review.pending.count()
    return num_professors + num_reviews
