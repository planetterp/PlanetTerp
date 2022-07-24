import secrets
from datetime import datetime, timedelta

from django.shortcuts import redirect, render
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http.response import HttpResponseBadRequest, HttpResponse

from home.mail import send_email
from home.models import User, ResetCode


class Login(View):
    template = "login_register.html"

    def get(self, request):
        if request.session.get("logged_in", False):
            return redirect('/')

        return render(request, self.template)

    def post(self, request):
        if request.session.get("logged_in", False):
            return redirect('/')

        data = request.POST
        context = {"error_msg": None}

        if not data.get('username'):
            context["error_msg"] = "You must enter a username."
            return render(request, self.template, context)
        if not data.get('password'):
            context["error_msg"] = "You must enter a password."
            return render(request, self.template, context)

        username = data.get("username")
        password = data.get("password")

        user = authenticate(request, username=username, password=password)
        if not user:
            context["error_msg"] = "Incorrect username/password combination."
            return render(request, self.template, context)

        login(request, user)
        return redirect("/profile")


class Logout(View):

    @method_decorator(login_required)
    def get(self, request):
        logout(request)
        return redirect("/")


class PasswordReset(View):
    RESET_LINK_LENGTH = 80

    def post(self, request):
        user_email = request.POST["email"]
        user = User.objects.filter(email=user_email).first()

        if not user:
            return HttpResponseBadRequest("There is no account registered "
                "with that email.")

        # token_hex generates two hex digits per number, so halve our length
        reset_code = secrets.token_hex(int(self.RESET_LINK_LENGTH / 2))

        message = ("A request has been made to reset your password. To do so, please follow this link: <br /><br />" +
                   f"https://planetterp.com/profile/resetpassword/{reset_code} <br><br>" +
                   "If you did not request a password reset, you may disregard this email.")
        send_email(user_email, "PlanetTerp Password Reset", message)

        expires_at = datetime.now() + timedelta(days=1)
        reset_code = ResetCode(user_id=user.id, reset_code=reset_code,
            expires_at=expires_at)
        # ensure the user only has one reset code active at a time
        ResetCode.objects.filter(user_id=user.id).update(invalid=True)
        reset_code.save()
        return HttpResponse()


class Register(View):
    template = "login_register.html"

    def post(self, request):
        if request.session.get("logged_in", False):
            return redirect('/')

        data = request.POST

        context = {"error_msg": None }

        if 'username' not in data or not data["username"]:
            context["error_msg"] = "You must enter a username."
            return render(request, self.template, context)
        if 'email' not in data:
            context["error_msg"] = "Did you remove the email input?"
            return render(request, self.template, context)
        if 'password' not in data or not data["password"]:
            context["error_msg"] = "You must enter a password."
            return render(request, self.template, context)

        username = data["username"].strip()
        email = data["email"].strip()
        password = data["password"].strip()

        user = User.objects.create_user(username=username, email=email,
            password=password)
        login(request, user)

        return redirect("profile")
