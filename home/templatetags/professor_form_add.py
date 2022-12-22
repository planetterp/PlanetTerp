from django import template
from django.template.context_processors import csrf
from crispy_forms.utils import render_crispy_form

from home.forms.professor_forms import ProfessorFormAdd

register = template.Library()

# https://docs.djangoproject.com/en/3.2/howto/custom-template-tags/#simple-tags
@register.simple_tag(takes_context=True)
def professor_form_add(context):
    request = context['request']
    user = request.user
    add_form = ProfessorFormAdd(user)
    ctx = {}
    ctx.update(csrf(request))

    # https://django-crispy-forms.readthedocs.io/en/latest/crispy_tag_forms.html#render-a-form-within-python-code
    return render_crispy_form(add_form, add_form.helper, context=ctx)
