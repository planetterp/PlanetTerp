from abc import abstractmethod

from django.forms.widgets import HiddenInput, RadioSelect, TextInput, Textarea, CheckboxInput
from django.forms import CharField, ChoiceField, BooleanField, IntegerField
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.urls import reverse
from django.forms import Form
from django.utils.html import format_html

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Fieldset, Layout, Div, Field, HTML, Button
from crispy_forms.bootstrap import FormActions, Alert, InlineRadios
from discord_webhook import DiscordWebhook
from discord_webhook.webhook import DiscordEmbed

from home.forms.layout_objects.bootstrap_modal import BootstrapModal
from home.models import Review, Professor, Course
from planetterp import config

# Base form that contains common form fields
class ProfessorForm(Form):
    grade = ChoiceField(
        choices=[('', 'Expected Grade')] + [(tup[0],tup[0]) for tup in Review.Grades.choices],
        error_messages={
            "invalid_choice": """Invalid grade entered.
                Please copy your review, refresh the page, and try again. If the error persists,
                please email us at admin@planetterp.com
                """
        },
        required=False,
        label=False
    )

    rating = IntegerField(
        required=True,
        widget=HiddenInput,
        min_value=1,
        max_value=5,
        error_messages={
            "required": "You must rate the instructor",
            "min_value": "The rating must be between 1 and 5",
            "max_value": "The rating must be between 1 and 5"
        },
        label=False
    )

    content = CharField(
        required=False,
        widget=Textarea,
        max_length=10000,
        label=False
    )

    anonymous = BooleanField(
        required=False,
        widget=CheckboxInput,
        label="Post Anonymously"
    )

    def __init__(self, user: QuerySet, form_type: Review.ReviewType, **kwargs):
        super().__init__(**kwargs)
        self.user = user
        self.form_type = form_type
        self.field_errors = self.create_field_errors()
        self.form_html_id = "professor-form-" + self.form_type.value

        self.helper = FormHelper()
        self.helper.form_id = self.form_html_id
        self.helper.layout = self.generate_layout()
        # we create custom form errors, don't let crispy handle errors
        self.helper.form_show_errors = False

    @abstractmethod
    def left_side_layout(self):
        pass

    @abstractmethod
    def get_content_styles(self):
        pass

    def generate_layout(self):
        # Ordering the fields/elements and assigning css styles
        # https://django-crispy-forms.readthedocs.io/en/latest/layouts.html#universal-layout-objects
        submit_button = Button(
            "Submit",
            "submit",
            id=f"submit-{self.form_type.value}-form",
            css_class="btn-warning w-100 mt-3",
            onClick=f'submitProfessorForm("#{self.form_html_id}")'
        )

        rateYo = HTML(f'<div id="div_id_rating"><div id="rateYo_{self.form_type.value}" class="rateYo" class="p-0"></div></div>')
        grade = Field('grade', id=f"id_grade_{self.form_type.value}")
        grade_errors = self.field_errors["grade"]
        rating = Field('rating', id=f"id_rating_{self.form_type.value}")
        rating_errors = self.field_errors["rating"]

        content = Field(
            'content',
            id=f"id_content_{self.form_type.value}",
            placeholder="Please keep the review relevant to the instructor's teaching...",
            wrapper_class="mb-0",
            style=self.get_content_styles()
        )
        content_errors = self.field_errors["content"]

        success_banner = Alert(
            "Review submitted successfully!",
            css_id=f"success-banner-{self.form_type.value}",
            css_class="alert-success text-center w-100 rounded-0 d-none position-absolute"
        )
        login_banner = None
        anonymous = None

        if self.user.is_authenticated:
            anonymous = Div(
                Field(
                    "anonymous",
                    id=f"id_anonymous_{self.form_type.value}"
                ),
                css_class="anonymous-checkbox"
            )
        else:
            banner_text = (
                '<strong>Note:</strong> <a href="{}" target="_blank">'
                'Register</a> to save your reviews to an account and to put a '
                'username next to your reviews'
            )
            login_banner = Alert(
                format_html(banner_text, reverse("login")),
                css_class="alert-primary text-center info-alert w-100 rounded-0"
            )

        layout = Layout(
            success_banner,
            login_banner,
            Fieldset(
                None,
                Div(
                    *self.left_side_layout(),
                    grade,
                    grade_errors,
                    rateYo,
                    rating_errors,
                    rating,
                    FormActions(submit_button),
                    css_id=f"review-left-wrapper-{self.form_type.value}",
                    css_class="no_select review-left-wrapper"
                ),
                Div(
                   content,
                    anonymous,
                    content_errors,
                    css_id=f"review-right-wrapper-{self.form_type.value}",
                    css_class="review-right-wrapper"
                ),
                css_class="p-2"
            )
        )
        return layout

    def create_field_errors(self):
        field_errors = {}

        for field in self.fields:
            error_html = f'<div id="{{{{ form.{field}.name }}}}_errors" class="invalid-feedback text-center mb-3" style="font-size: 15px"></div>'
            field_errors[field] = HTML(error_html)

        return field_errors

    def clean(self):
        cleaned_data = super().clean()
        grade = cleaned_data.get('grade')
        if grade == '':
            self.cleaned_data['grade'] = None

        content = cleaned_data.get('content')
        if content == '' or content.isspace():
            error_msg = "You must write a review"
            error = ValidationError(error_msg, code='Empty')
            self.add_error('content', error)

        return cleaned_data

    def send_webhook(self):
        channel_url = config.WEBHOOK_URL_UPDATE

        if channel_url is None:
            return

        webhook = DiscordWebhook(url=channel_url)

        if self.form_type is Review.ReviewType.REVIEW:
            num = Review.objects.pending.count()
        elif self.form_type is Review.ReviewType.ADD:
            num = Professor.objects.pending.count()
        else:
            raise ValueError("Invalid form type!")

        title = f"{num} new {'review' if num == 1 else 'reviews'}"
        embed = DiscordEmbed(title=title,
            url=self.request.build_absolute_uri(reverse("admin")))
        webhook.add_embed(embed)
        webhook.execute()

# The review form that contains fields specific to the review form
class ProfessorFormReview(ProfessorForm):
    course = ChoiceField(
        required=False,
        label=False
    )

    other_course = CharField(
        required=False,
        label=False
    )

    slug = CharField(
        required=True,
        widget=HiddenInput,
        label=False
    )

    def __init__(self, user, professor, **kwargs):
        super().__init__(user, Review.ReviewType.REVIEW, **kwargs)

        choices = [(course.name, course.name) for course in Course.objects.filter(professors__pk=professor.id)]
        choices.insert(0, ('', "Course"))
        choices.append(("other", "Other"))
        self.fields['course'].choices = choices
        self.fields['slug'].initial = professor.slug

    def get_content_styles(self):
        if self.user.is_authenticated:
            return "height: 10.5rem; margin: auto; border-bottom-left-radius: 0rem;"
        else:
            return "height: 12.9rem;"

    def left_side_layout(self):
        course = Field('course', onChange="courseChange(this)", id=f"div_course_{self.form_type.value}")
        course_errors = self.field_errors["course"]
        other_course = Field('other_course', placeholder="Enter a course...", style="display: none;")
        other_course_errors = self.field_errors["other_course"]
        other_course_container = Div(other_course, other_course_errors, css_class="mb-3")

        left_side = (course, course_errors, other_course_container, 'slug')
        return left_side

    def clean(self):
        super().clean()
        course = self.cleaned_data.get('course')
        other_course = self.cleaned_data.get('other_course')
        self.validate_course(course, other_course)

        return self.cleaned_data

    def validate_course(self, course, other_course):
        clean_course = None

        if course =='other':
            if other_course == '' or other_course.isspace():
                error_msg = "Please specify a course or select one from the dropdown above"
                error = ValidationError(error_msg, code='Empty')
                self.add_error("other_course", error)
            else:
                clean_course = other_course
        elif course == '':
            clean_course = None
        else:
            clean_course = course

        course_obj = Course.objects.filter(name=clean_course.replace(" ", ""))
        if clean_course and not course_obj.exists():
            error_msg = '''The course you specified is not in our database.
                If you think it should be, please email us at admin@planetterp.com.'''
            error = ValidationError(error_msg, code='Not Found')
            self.add_error("other_course", error)
        else:
            self.cleaned_data['course'] = clean_course

        return self.cleaned_data

# The add professor/TA form that contains fields specific to the add professor/TA form
class ProfessorFormAdd(ProfessorForm):
    name = CharField(
        required=False,
        widget=TextInput,
        label=False
    )

    type_ = ChoiceField(
        required=False,
        widget=RadioSelect,
        label=False
    )

    course = CharField(
        required=False,
        widget=TextInput,
        label=False
    )

    def __init__(self, user, **kwargs):
        super().__init__(user, Review.ReviewType.ADD, **kwargs)

        choices = [(tup[0],tup[0]) for tup in Professor.Type.choices]
        self.fields['type_'].choices = choices

    def error_message(self, field_name):
        return f"You must specify the instructor's {field_name}"

    def get_content_styles(self):
        if self.user.is_authenticated:
            return "height: 15.8rem; margin: auto; border-bottom-left-radius: 0rem;"
        else:
            return "height: 18rem;"

    def left_side_layout(self):
        name = Field('name', placeholder="Instructor Name")
        name_errors = self.field_errors["name"]

        type_ = InlineRadios('type_')
        type_errors = self.field_errors["type_"]

        course = Field(
            'course',
            placeholder="Course",
            id=f"id_course_{self.form_type.value}"
        )
        crispy_course_errors = self.field_errors["course"]

        left_side = (name, name_errors, type_,
            type_errors, course, crispy_course_errors)
        return left_side

    def generate_layout(self):
        layout = Layout(
            BootstrapModal(
                super().generate_layout(),
                css_id="add-professor-modal",
                title_id="add-professor-label",
                title="Add a new Professor/TA"
            )
        )
        return layout

    def clean(self):
        super().clean()

        name = self.cleaned_data.get('name')
        type_ = self.cleaned_data.get('type_')
        course = self.cleaned_data.get('course')

        if name == '' or name.isspace():
            error = ValidationError(self.error_message('name'), code='Empty')
            self.add_error("name", error)

        if type_ == '' or type_.isspace():
            error = ValidationError(self.error_message('type'), code='Empty')
            self.add_error("type_", error)

        if course and not Course.objects.filter(name=course).exists():
            error_msg = '''The course you specified is not in our database.
                If you think it should be, please email us at admin@planetterp.com.'''
            error = ValidationError(error_msg, code='Not Found')
            self.add_error("course", error)
        else:
            self.cleaned_data['course'] = course

        return self.cleaned_data
