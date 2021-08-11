from django.forms import CharField, DateTimeField, EmailField, PasswordInput
from django.forms.widgets import DateInput, HiddenInput
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.contrib.auth import authenticate
from django.utils.html import format_html
from django.forms import ModelForm, Form

from crispy_forms.layout import Layout, Div, Field, HTML, Button
from crispy_forms.bootstrap import PrependedText
from crispy_forms.helper import FormHelper

from home.forms.layout_objects.bootstrap_modal import BootstrapModal
from planetterp.settings import DATE_FORMAT
from home.models import User, ResetCode

class ProfileForm(ModelForm):
    username = CharField(
        required=False,
        disabled=True,
        label_suffix=None,
        help_text=User._meta.get_field("username").help_text
    )

    date_joined = DateTimeField(
        required=False,
        disabled=True,
        label_suffix=None,
        widget=DateInput(format=DATE_FORMAT)
    )

    class Meta:
        model = User
        fields = ["username", "email", "date_joined", "send_review_email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.get("instance")

        if self.user.email:
            self.fields['email'].disabled = True
            self.fields['send_review_email'].label = (
                "Email me updates pertaining to the status of my reviews"
            )
        else:
            self.fields.pop("send_review_email")

        self.field_errors = self.create_field_errors()
        self.helper = FormHelper()
        self.helper.form_id = 'profile-form'
        self.helper.field_class = 'px-0'
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def create_field_errors(self):
        field_errors = {}

        for field in self.fields:
            if_condition = f'{{% if form.{field}.errors %}} '
            error_html = (
                f'<div id="{{{{ form.{field}.name }}}}_errors"'
                ' class="invalid-feedback" style="font-size: 15px">'
                f' {{{{ form.{field}.errors|striptags }}}}</div>'
            )
            endif = ' {% endif %}'
            field_errors[field] = HTML(if_condition + error_html + endif)

        return field_errors

    def generate_layout(self):
        if self.user.email:
            email_placeholder = None
            send_review_email_errors = self.field_errors['send_review_email']
            send_review_email = Field(
                'send_review_email',
                wrapper_class="profile-form-field"
            )

        else:
            email_placeholder = "Enter an email address"
            send_review_email = None
            send_review_email_errors = None

        layout = Layout(
            'username',
            'date_joined',
            PrependedText(
                'email',
                mark_safe('<i id="email-field-info" class="fas fa-info-circle"></i>'),
                placeholder=email_placeholder,
                wrapper_class="mb-0"
            ),
            self.field_errors['email'],
            send_review_email,
            send_review_email_errors,
            Div(
                Div(
                    Div(
                        Button(
                            'save',
                            'Save',
                            css_class="btn-primary mt-3",
                            onClick="updateProfile()"
                        ),
                        Div(
                            css_id="profile-form-success",
                            css_class="col text-success text-center d-none",
                            style="font-size: 20px"
                        ),
                        css_class="col-10 pl-0 d-flex"
                    ),
                    css_class="row"
                ),
                css_class="container"
            )
        )

        return layout

class LoginForm(ModelForm):
    username = CharField()

    class Meta:
        model = User
        fields = ["password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        password = self.fields['password']
        password.widget = PasswordInput()
        password.error_messages['required'] = User._meta.get_field("password").error_messages['required']

        username = self.fields['username']
        username.error_messages['required'] = User._meta.get_field("username").error_messages['required']

        self.field_errors = self.create_field_errors()

        self.helper = FormHelper()
        self.helper.form_id = "login-form"
        self.helper.form_show_errors = False
        self.helper.field_class = 'w-75'
        self.helper.label_class = 'mt-2'

        self.helper.layout = Layout(
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
            Button(
                'submit',
                'Login',
                css_class="btn-primary",
                onClick='submitLoginForm()'
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        unique_error_message = (
            'A user with that {} already exists. If you forgot your <br /> password, '
            'please <a href="" data-toggle="modal" data-target="#password-reset-modal" style="color: red;"> '
            '<strong>reset your password</strong></a> or login on the left.'
        )

        password = self.fields['password']
        password.widget = PasswordInput()
        password.error_messages['required'] = User._meta.get_field("password").error_messages['required']

        username = self.fields['username']
        user_model = User._meta.get_field("username")
        username.help_text = user_model.help_text
        username.error_messages['unique'] = format_html(unique_error_message, "username")
        username.error_messages['required'] = user_model.error_messages['required']

        email = self.fields['email']
        email.label = "Email"
        email.error_messages['unique'] = format_html(unique_error_message, "email")

        self.field_errors = self.create_field_errors()

        self.helper = FormHelper()
        self.helper.form_id = "register-form"
        self.helper.form_show_errors = False
        self.helper.field_class = 'w-75'
        self.helper.label_class = 'mt-2'
        self.helper.layout = Layout(
            Div(
                Field('username', placeholder="Username", wrapper_class='mb-0'),
                self.field_errors['username'],
                css_class="username-container mb-1"
            ),
            Div(
                PrependedText(
                    'email',
                    mark_safe('<i id="email-field-info" class="fas fa-info-circle"></i>'),
                    placeholder="Email (optional)",
                    wrapper_class='mb-0'
                ),
                self.field_errors['email'],
                css_class="email-container mb-1"
            ),
            Div(
                Field('password', placeholder="Password", wrapper_class='mb-0'),
                self.field_errors['password'],
                css_class="password-container mb-1"
            ),
            Button(
                'submit',
                'Register',
                css_class="btn-primary mt-2",
                onClick='submitRegisterForm()'
            )
        )

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

# Form on login page prompting the user to input an email
class ForgotPasswordForm(Form):
    email = EmailField(
        required=True,
        label=None,
        help_text="Enter your email for instructions on how to reset your password",
        error_messages={"required": "Please enter an email address"}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = "reset_password_form"
        self.helper.form_show_labels = False
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
            BootstrapModal(
                Field('email', placeholder="Email", wrapper_class="mb-0"),
                HTML('''
                    {% if form.email.errors %}
                        <div id="email_response" class="invalid-feedback" style="font-size: 15px">
                            {{ form.email.errors|striptags }}
                        </div>
                    {% else %}
                        <div id="email_response" class="valid-feedback" style="font-size: 15px; display: none;">
                            <strong>Email sent successfully.</strong> Look for an email from admin@planetterp.com and be sure to check your spam/junk folder if you don't see the email in your inbox.
                        </div>
                    {% endif %}
                '''),
                Button(
                    "submit",
                    "Send Reset Email",
                    id="password-reset-form-submit",
                    css_class="btn-primary mt-3",
                    onClick='submitForgotPasswordForm()'
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
                message = (
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

    def __init__(self, reset_code: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget = PasswordInput()
        self.fields['reset_code'].initial = reset_code

        self.helper = FormHelper()
        self.helper.form_id = "reset-password-form"
        self.helper.form_class = "w-50"
        self.helper.form_show_labels = False
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
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
            Button(
                "submit",
                "Reset Password",
                id="reset-password-form-submit",
                css_class="btn-primary mt-3",
                onClick='submitResetPasswordForm()'
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
