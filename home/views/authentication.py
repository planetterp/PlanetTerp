import secrets
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.template.context_processors import csrf
from crispy_forms.utils import render_crispy_form
from django.utils.safestring import mark_safe
from django.shortcuts import redirect, render
from django.views import View
from django.contrib.auth import login, logout
from django.http.response import JsonResponse
from django.utils.timezone import now

from home.models import User, ResetCode
from home.forms.basic import LoginForm, RegisterForm, ResetPasswordForm

class Login(View):
    template = "login_register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("/profile")

        context = {
            "login_form": LoginForm(),
            "register_form": RegisterForm(),
            "reset_password_form": ResetPasswordForm()
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
        return redirect("/")


class PasswordReset(View):
    RESET_LINK_LENGTH = 80

    def post(self, request):
        form = ResetPasswordForm(data=request.POST)
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

            message = (
                f"Dear {user.username},\nA request has been made to reset your password. To do "
                f"so, please follow this link: \nhttps://planetterp.com/profile/resetpassword/{reset_code}\n\n If you did not "
                "request a password reset, you may safely disregard this email."
            )
            html_message = mark_safe(
                f"Dear {user.username},<br />A request has been made to reset your password. To do "
                f'so, please follow <a href="https://planetterp.com/profile/resetpassword/{reset_code}">this</a> link. '
                "<br /><br /> If you did not request a password reset, you may "
                "safely disregard this email."

            )

            user.email_user(
                subject="Planetterp Password Reset",
                message=message,
                html_message=html_message
            )

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
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        else:
            ctx = {}
            ctx.update(csrf(request))
            register_form_html = render_crispy_form(register_form, register_form.helper, context=ctx)
            context["register_form"] = register_form_html
            context["success"] = False

        return JsonResponse(context)
