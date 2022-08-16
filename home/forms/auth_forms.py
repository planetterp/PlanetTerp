from django.forms import CharField, EmailField, PasswordInput
from django.forms.widgets import HiddenInput
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.contrib.auth import authenticate
from django.forms import ModelForm, Form

from crispy_forms.layout import Layout, Div, Field, HTML, Button, Submit
from crispy_forms.helper import FormHelper
from crispy_forms.bootstrap import Modal

from home.models import User, ResetCode

class LoginForm(ModelForm):
    username = CharField()

    class Meta:
        model = User
        fields = ["password"]
        widgets = {
            "password": PasswordInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].error_messages = {
            "required": User._meta.get_field("username").error_messages["required"]
        }

        self.fields['password'].error_messages = {
            "required": User._meta.get_field("password").error_messages["required"]
        }
        self.field_errors = self.create_field_errors()

        self.helper = FormHelper()
        self.helper.form_id = "login-form"
        self.helper.form_show_errors = False
        self.helper.field_class = 'w-75'
        self.helper.label_class = 'mt-2'
        self.helper.layout = self.generate_layout()

    def generate_layout(self):
        return Layout(
            Div(
                Field('username', placeholder="Username", wrapper_class='mb-0'),
                self.field_errors['username'],
                css_class="username-container mb-1"
            ),
            Div(
                Field('password', placeholder="Password", wrapper_class='mb-0'),
                self.field_errors['password'],
                css_class="password-container mb-1"
            ),
            Div(
                Div(
                    HTML('<a href="" data-toggle="modal" data-target="#password-reset-modal" style="color: blue;">Forgot password?</a>')
                ),
                css_class="pb-2"
            ),
            Submit(
                "submit",
                "Login",
                css_class="btn-primary",
                onclick="submitLoginForm()"
            )
        )

    def create_field_errors(self):
        field_errors = {}

        for field in self.fields:
            if_condition = f'{{% if form.{field}.errors %}} '
            error_html = (
                f'<div id="{{{{ form.{field}.name }}}}_errors"'
                ' class="invalid-feedback login-error" style="font-size: 15px">'
                f' {{{{ form.{field}.errors|striptags }}}}</div>'
            )
            endif = ' {% endif %}'
            field_errors[field] = HTML(if_condition + error_html + endif)

        return field_errors

    def clean(self):
        super().clean()

        if 'username' in self.cleaned_data and 'password' in self.cleaned_data:
            credentials = {
                "username": self.cleaned_data['username'],
                "password": self.cleaned_data['password']
            }

            user = authenticate(request=None, **credentials)
            if not user:
                message = "Username or password is incorrect"
                self.add_error('username', ValidationError(message, code="BAD_CREDENTIALS"))
                self.add_error('password', ValidationError(message, code="BAD_CREDENTIALS"))
            else:
                self.cleaned_data['user'] = user

        return self.cleaned_data

class RegisterForm(ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "password"]
        widgets = {
            "password": PasswordInput()
        }
        labels = {
            'email': "Email"
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields['username'].error_messages = {
            "required": User._meta.get_field("username").error_messages["required"]
        }

        self.fields['password'].error_messages = {
            "required": User._meta.get_field("password").error_messages["required"]
        }


        self.field_errors = self.create_field_errors()

        self.helper = FormHelper()
        self.helper.form_id = "register-form"
        self.helper.form_show_errors = False
        self.helper.field_class = 'w-75'
        self.helper.label_class = 'mt-2'
        self.helper.layout = self.generate_layout()

    def create_field_errors(self):
        field_errors = {}

        for field in self.fields:
            if_condition = f'{{% if form.{field}.errors %}} '
            error_html = (
                f'<div id="{{{{ form.{field}.name }}}}_errors"'
                ' class="invalid-feedback register-error" style="font-size: 15px">'
                f' {{{{ form.{field}.errors|first }}}}</div>'
            )
            endif = ' {% endif %}'
            field_errors[field] = HTML(if_condition + error_html + endif)

        return field_errors

    def generate_layout(self):
        return Layout(
            Div(
                Field('username', placeholder="Username", wrapper_class='mb-0'),
                self.field_errors['username'],
                css_class="username-container mb-1"
            ),
            Div(
                Field('email', placeholder="Email (optional)", wrapper_class='mb-0'),
                self.field_errors['email'],
                css_class="email-container mb-1"
            ),
            Div(
                Field('password', placeholder="Password", wrapper_class='mb-0'),
                self.field_errors['password'],
                css_class="password-container mb-1"
            ),
            Submit(
                "submit",
                "Register",
                css_class="btn-primary mt-2"
            )
        )

# Form on login page prompting the user to input an email
class ForgotPasswordForm(Form):
    email = EmailField(
        required=True,
        label=None,
        help_text="Enter your email for instructions on how to reset your password",
        error_messages={"required": "Please enter an email address"}
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.helper = FormHelper()
        self.helper.form_id = "reset-password-form"
        self.helper.form_show_labels = False
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def generate_layout(self):
        return Layout(
            Modal(
                Field('email', placeholder="Email", wrapper_class="mb-0"),
                HTML('''
                    {% if form.email.errors %}
                        <div id="email_response" class="invalid-feedback" style="font-size: 15px">
                            {{ form.email.errors|striptags }}
                        </div>
                    {% else %}
                        <div id="email_response" class="valid-feedback" style="font-size: 15px; display: none;">
                            <strong>Email sent successfully.</strong> Look for an email from admin@planetterp.com, and be sure to check your spam/junk folder if you don't see the email in your inbox.
                        </div>
                    {% endif %}
                '''),
                Submit(
                    "submit",
                    "Send Reset Email",
                    css_class="btn-primary mt-3"
                ),
                css_id="password-reset-modal",
                title_id="password-reset-title",
                title="Reset Password"
            )
        )

    def clean(self):
        super().clean()
        if 'email' in self.cleaned_data:
            clean_email = self.cleaned_data['email']
            users = User.objects.filter(email=clean_email)
            if not users.first():
                message = "There is no account assoicated with that email"
                self.add_error('email', ValidationError(message, "DNE"))
            elif users.count() > 1:
                message = mark_safe(
                    "There are multiple accounts associated with this email."
                    "Please copy this message and email it along with your username to "
                    "<a href='mailto:admin@planetterp.com'>admin@planetterp.com</a>"
                )
                self.add_error('email', ValidationError(message, "DUP_EMAIL"))


            self.cleaned_data['user'] = users.first()
        return self.cleaned_data

# The form where the user actually inputs the new password
class ResetPasswordForm(ModelForm):
    reset_code = CharField(widget=HiddenInput)

    class Meta:
        model = User
        fields = ["password"]
        widgets = {
            "password": PasswordInput()
        }

    def __init__(self, reset_code: str, **kwargs):
        super().__init__(**kwargs)
        self.fields['reset_code'].initial = reset_code

        self.helper = FormHelper()
        self.helper.form_id = "reset-password-form"
        self.helper.form_class = "w-50"
        self.helper.form_show_labels = False
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def generate_layout(self):
        return Layout(
            Field(
                'password',
                placeholder="Enter your new password...",
                wrapper_class="mb-0"
            ),
            'reset_code',
            HTML('''
                {% if form.password.errors %}
                    <div id="password_response" class="invalid-feedback" style="font-size: 15px">
                        {{ form.password.errors|first|striptags }}
                    </div>
                {% endif %}
            '''),
            Submit(
                "submit",
                "Reset Password",
                css_class="btn-primary mt-3"
            )
        )

    def clean(self):
        super().clean()
        if 'password' in self.cleaned_data:
            reset_code = ResetCode.objects.filter(reset_code=self.cleaned_data['reset_code']).first()
            if not reset_code or reset_code.invalid:
                self.add_error('password', ValidationError("Invalid reset code"))

            self.cleaned_data['reset_code'] = reset_code
        return self.cleaned_data
