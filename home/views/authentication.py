import secrets
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.template.context_processors import csrf
from django.shortcuts import redirect, render
from django.contrib.auth import login, logout
from django.http.response import JsonResponse
from django.utils.timezone import now
from django.urls import reverse
from django.views import View

from crispy_forms.utils import render_crispy_form

from home.models import User, ResetCode
from home.forms.auth_forms import LoginForm, RegisterForm, ForgotPasswordForm
from home.utils import send_email

class Login(View):
    template = "login_register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("/profile")

        context = {
            "login_form": LoginForm(),
            "register_form": RegisterForm(),
            "password_reset_form": ForgotPasswordForm(),
            "next": request.GET.get("next", "/profile")
        }

        return render(request, self.template, context=context)

    def post(self, request):
        login_form = LoginForm(data=request.POST)
        context = {
            "success": True
        }

        if login_form.is_valid():
            login(request, login_form.cleaned_data['user'])
        else:
            ctx = {}
            ctx.update(csrf(request))
            login_form_html = render_crispy_form(login_form, login_form.helper, context=ctx)
            context["login_form"] = login_form_html
            context["success"] = False

        return JsonResponse(context)


class Logout(LoginRequiredMixin, View):
    redirect_field_name = "index"

    def get(self, request):
        logout(request)
        redirect_page = request.GET.get("next")
        return redirect(redirect_page if redirect_page is not None else "/")

class ForgotPassword(View):
    RESET_LINK_LENGTH = 80

    def post(self, request):
        form = ForgotPasswordForm(data=request.POST)
        ctx = {}
        ctx.update(csrf(request))
        form_html = render_crispy_form(form, form.helper, context=ctx)
        context = {
            "success": False,
            "form": form_html
        }

        if form.is_valid():
            user = form.cleaned_data['user']

            # token_hex generates two hex digits per number, so halve our length
            reset_code = secrets.token_hex(int(self.RESET_LINK_LENGTH / 2))
            email_url = request.build_absolute_uri(reverse('reset-password', args=[reset_code]))
            message = (f"Dear {user.username},<br /><br />A request has been made to "
                "reset your password. To do "
                f'so, please follow <a href="{email_url}">this</a> link. '
                "<br /><br /> If you did not request a password reset, you may "
                "safely disregard this email.")

            send_email(user, "Planetterp Password Reset", message)

            expires_at = now() + timedelta(days=1)
            reset_code = ResetCode(user_id=user.id, reset_code=reset_code,
                expires_at=expires_at)
            # ensure the user only has one reset code active at a time
            ResetCode.objects.filter(user_id=user.id).update(invalid=True)
            reset_code.save()
            context["success"] = True

        return JsonResponse(context)


class Register(View):
    template = "login_register.html"

    def post(self, request):
        register_form = RegisterForm(data=request.POST)
        context = {
            "success": True
        }

        if register_form.is_valid():
            data = register_form.cleaned_data
            username = data['username']
            email = data['email']
            password = data['password']
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            login(request, user)
        else:
            ctx = {}
            ctx.update(csrf(request))
            register_form_html = render_crispy_form(register_form, register_form.helper, context=ctx)
            context["register_form"] = register_form_html
            context["success"] = False

        return JsonResponse(context)
