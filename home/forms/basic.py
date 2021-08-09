from django.core.exceptions import ValidationError
from django.forms import CharField, DateTimeField
from django.utils.safestring import mark_safe
from django.contrib.auth import authenticate
from django.forms.widgets import DateInput
from django.forms import ModelForm

from crispy_forms.layout import Layout, Div, Field, HTML, Button
from crispy_forms.helper import FormHelper
from crispy_forms.bootstrap import AppendedText

from planetterp.settings import DATE_FORMAT
from home.models import User

class ProfileForm(ModelForm):
    username = CharField(
        required=False,
        disabled=True,
        label_suffix=None
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

        self.fields['email'].help_text =  mark_safe(
            '<span id="email_hint_text" style="display: none;">'
            'PlanetTerp will only send you emails when a review of yours is'
            ' approved, rejected, or unverified. Your email and any other'
            ' personal data on our site is kept confidential and isn\'t shared'
            ' with anyone else. If you have any questions about how PlanetTerp'
            ' handles your data, please email'
            ' <a href="mailto:admin@planetterp.com">admin@planetterp.com</a>'
            '</span>'
        )

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
        self.helper.label_class = 'float-left'
        self.helper.field_class = 'col-6 pl-0'
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def create_field_errors(self):
        field_errors = {}

        for field in self.fields:
            if_condition = f'{{% if form.{field}.errors %}} '
            error_html = (
                f'<div id="{{{{ form.{field}.name }}}}_errors"'
                ' class="invalid-feedback text-center" style="font-size: 15px">'
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
                wrapper_class="profile-form-field pl-0"
            )
        else:
            email_placeholder = "Enter an email address"
            send_review_email = None
            send_review_email_errors = None

        info_icon_html = mark_safe('<i id="profile-page-info" class="fas fa-info-circle"></i>')

        layout = Layout(
            Field('username', wrapper_class="profile-form-field"),
            Field('date_joined', wrapper_class="profile-form-field"),
            AppendedText(
                'email',
                info_icon_html,
                wrapper_class="profile-form-field",
                placeholder=email_placeholder
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
                            css_class="btn-primary",
                            onClick="updateProfile()"
                        ),
                        Div(
                            HTML("Profile updated successfully"),
                            css_id="profile-form-success",
                            css_class="col text-success text-center d-none",
                            style="font-size: 20px"
                        ),
                        css_class="col-6 pl-0 d-flex"
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
                    HTML('<a href="javascript:void(0);" onclick="showForgotPassword()" style="color: blue;">Forgot password?</a>')
                ),
                css_class="forgot-password-link pb-2"
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
        self.fields['username'].help_text = None
        self.fields['email'].label = "Email"
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
                Field('email', placeholder="Email (optional)", wrapper_class='mb-0'),
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
                css_class="btn-primary",
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
                f' {{{{ form.{field}.errors|first|striptags }}}}</div>'
            )
            endif = ' {% endif %}'
            field_errors[field] = HTML(if_condition + error_html + endif)

        return field_errors
