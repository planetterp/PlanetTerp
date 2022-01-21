from django.forms import CharField, DateTimeField
from django.forms.widgets import DateInput, Select
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.forms import ModelForm, Form

from crispy_forms.layout import Layout, Div, Field, HTML, Button
from crispy_forms.bootstrap import PrependedText
from crispy_forms.helper import FormHelper

from home.models import Professor, User, Grade, Course
from home.utils import Semester
from planetterp.settings import DATE_FORMAT

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
        # This is a temporary workaround for
        # https://discord.com/channels/784561204289994753/879121341159186453/879124088226992209
        # and needs to be resolved properly in the future
        model = User()
        fields = ["username", "email", "date_joined", "send_review_email"]
        help_text = {
            "username": User._meta.get_field("username").help_text
        }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user = kwargs.get("instance")
        email = self.fields['email']

        if self.user.email:
            email.disabled = True
            self.fields['send_review_email'].label = (
                "Email me when one of my reviews is accepted or rejected"
            )
        else:
            self.fields.pop("send_review_email")
            email.error_messages['unique'] = "A user with that email already exists."

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
                Button(
                    'save',
                    'Save',
                    css_class="btn-primary",
                    onClick="updateProfile()"
                ),
                Div(
                    css_id="profile-form-success",
                    css_class="col text-success text-center d-none",
                    style="font-size: 20px"
                ),
                css_class="mt-3"
            )
        )

        return layout

# The "Lookup by course" feature on /grades
class HistoricCourseGradeForm(Form):
    course = CharField(required=False)
    semester = CharField(required=False, widget=Select())
    section = CharField(required=False, widget=Select())

    def __init__(self, course_name=None, semester=None, **kwargs):
        super().__init__(**kwargs)
        self.course_name = course_name
        self.semester = semester
        self.initialize_semester()
        self.initialize_section()
        self.field_errors = self.create_field_errors()

        self.helper = FormHelper()
        self.helper.field_class = 'col-sm-4'
        self.helper.label_class = 'col-form-label'
        self.helper.form_id = "course-lookup-form"
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def initialize_semester(self):
        if self.course_name and self.course_name != '':
            # If user specified the course, only display semesters when
            # that course was offered
            course_obj = Course.objects.filter(name=self.course_name).first()
            grades = Grade.objects.filter(course=course_obj).values('semester').distinct()
        else:
            # Otherwise, only display semesters we have data for
            grades = Grade.objects.all().values('semester').distinct()

        def _semester_tuple(semester):
            return (str(semester.number()), semester.name())

        semester_choices = [_semester_tuple(grade["semester"]) for grade in grades]
        self.fields['semester'].widget.choices = [("", "All semesters")] + semester_choices

    def initialize_section(self):
        if self.semester and self.semester != '':
            course = Course.objects.filter(name=self.course_name).first()
            grades = Grade.objects.filter(
                course=course, semester=Semester(self.semester)
            ).values('section').distinct()

            section_choices = [(grade['section'], grade['section']) for grade in grades]
            self.fields['section'].widget.choices = [("", "All sections")] + section_choices

    def create_field_errors(self):
        field_errors = {}

        for field in self.fields:
            if_condition = f'{{% if form.{field}.errors %}} '
            error_html = (
                f'<div id="{{{{ form.{field}.name }}}}_errors"'
                ' class="invalid-feedback lookup-error" style="font-size: 13px">'
                f' {{{{ form.{field}.errors|first|striptags }}}}</div>'
            )
            endif = ' {% endif %}'
            field_errors[field] = HTML(if_condition + error_html + endif)

        return field_errors

    def generate_layout(self):
        return Layout(
            Field(
                'course',
                placeholder="Search for a course...",
                id="course-search",
                css_class="autocomplete",
                wrapper_class="row justify-content-center mb-0"
            ),
            self.field_errors['course'],
            Div(
                Field(
                    'semester',
                    id="semester-search",
                    wrapper_class="row justify-content-center mb-0 mt-3",
                    onChange="submitCourseSearch()"
                ),
                self.field_errors['semester'],
                css_id="semester-search-input",
                style="display: none;"
            ),
            Div(
                Field(
                    'section',
                    placeholder="Enter a section...",
                    id="section-search",
                    css_class="autocomplete",
                    wrapper_class="row justify-content-center mb-0 mt-3",
                    onChange="submitCourseSearch()"
                ),
                self.field_errors['section'],
                css_id="section-search-input",
                style="display: none;"
            )
        )

    def clean(self):
        super().clean()
        clean_course = self.cleaned_data.get('course', None)

        if clean_course:
            course = Course.objects.filter(name=clean_course).first()
            course_data = Grade.objects.filter(course=course).first()

            if not course:
                message = "We don't have record of that course"
                self.add_error('course', ValidationError(message, code="INVALID_COURSE"))
            elif not course_data:
                message = "No grade data available for that course"
                self.add_error('course', ValidationError(message, code="NO_DATA"))

        return self.cleaned_data

class HistoricProfessorGradeForm(Form):
    professor = CharField(required=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.field_errors = self.create_field_errors()

        self.helper = FormHelper()
        self.helper.form_class = 'justify-content-right'
        self.helper.field_class = 'col-sm-5'
        self.helper.label_class = 'col-form-label'
        self.helper.form_id = "professor-lookup-form"
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def create_field_errors(self):
        field_errors = {}

        for field in self.fields:
            if_condition = f'{{% if form.{field}.errors %}} '
            error_html = (
                f'<div id="{{{{ form.{field}.name }}}}_errors"'
                ' class="invalid-feedback lookup-error" style="font-size: 13px">'
                f' {{{{ form.{field}.errors|first|striptags }}}}</div>'
            )
            endif = ' {% endif %}'
            field_errors[field] = HTML(if_condition + error_html + endif)

        return field_errors

    def generate_layout(self):
        return Layout(
            Field(
                'professor',
                placeholder="Search for a professor...",
                id="professor-search",
                css_class="autocomplete",
                wrapper_class="row justify-content-center mb-0"
            )
        )

    def clean(self):
        clean_professor = self.cleaned_data.get('professor', None)

        if clean_professor:
            professor = Professor.objects.filter(name=clean_professor).first()
            professor_data = Grade.objects.filter(professor=professor).first()
            if not professor:
                message = "We don't have record of that professor"
                self.add_error('professor', ValidationError(message, code="INVALID_PROFESSOR"))
            elif not professor_data:
                message = "No grade data available for that professor"
                self.add_error('professor', ValidationError(message, code="NO_DATA"))

        return self.cleaned_data
