from django.contrib.auth.mixins import LoginRequiredMixin
from django.http.response import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.contrib.auth import login
from django.template.context_processors import csrf

from crispy_forms.utils import render_crispy_form

from home.models import ResetCode
from home.tables.reviews_table import ProfileReviewsTable
from home.forms.basic import ProfileForm
from home.forms.auth_forms import ResetPasswordForm
from planetterp.settings import DATE_FORMAT

# LoginRequiredMixin needs to be first
#   https://stackoverflow.com/a/47250953
class Profile(LoginRequiredMixin, View):
    template = "profile.html"

    def get(self, request):
        reviews = request.user.review_set.order_by("created_at")

        context = {
            "reviews_table": ProfileReviewsTable(reviews, request),
            "form": ProfileForm(instance=request.user)
        }
        return render(request, self.template, context)

    def post(self, request):
        user = request.user
        initial = {
            "username": user.username,
            "email": user.email,
            "date_joined": user.date_joined.date().strftime(DATE_FORMAT),
            "send_review_email": user.send_review_email
        }

        form = ProfileForm(
            data=request.POST,
            initial=initial,
            instance=request.user
        )

        context = {
           "message": None,
           "success": False,
           "form": None
        }

        if form.has_changed():
            if form.is_valid():
                form.save()
                context["success"] = True
                context['message'] = "Settings updated successfully"
                form = ProfileForm(instance=request.user)
        else:
            context["message"] = "Nothing to update"
            context["success"] = True

        ctx = {}
        ctx.update(csrf(request))
        form_html = render_crispy_form(form, form.helper, context=ctx)
        context['form'] = form_html

        return JsonResponse(context)

class ResetPassword(View):
    RESET_LINK_LENGTH = 80
    template = "reset_password.html"

    def get(self, request, reset_code: str):
        reset_code = ResetCode.objects.filter(reset_code=reset_code).first()
        if not reset_code or reset_code.invalid:
            return HttpResponseBadRequest("<html>Invalid reset code. It may have expired. <a href=\"/\">Home</a>.</html>")

        context = {
            "reset_code": reset_code.reset_code,
            "reset_password_form": ResetPasswordForm(reset_code=reset_code.reset_code)
        }
        return render(request, self.template, context)

    def post(self, request, reset_code: str):
        form = ResetPasswordForm(reset_code=reset_code, data=request.POST)
        ctx = {}
        ctx.update(csrf(request))
        form_html = render_crispy_form(form, form.helper, context=ctx)
        context = {
            "form" : form_html,
            "success": False
        }

        if form.is_valid():
            cleaned_reset_code = form.cleaned_data['reset_code']
            user = cleaned_reset_code.user
            user.set_password(form.cleaned_data['password'])
            user.save()

            cleaned_reset_code.invalid = True
            cleaned_reset_code.save()
            context["success"] = True

            login(request, user)


        return JsonResponse(context)
