from django.core.exceptions import ValidationError
from django.forms import CharField, IntegerField, DateField, ChoiceField, BooleanField
from django.forms.widgets import DateInput, HiddenInput, TextInput
from django.utils.html import format_html
from django.forms import Form, ModelForm
from django.utils.safestring import mark_safe

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Button, HTML
from crispy_forms.bootstrap import FormActions, Modal

from home.utils import AdminAction
from home.models import Course, Grade, Review, Professor
from planetterp.settings import DATE_FORMAT

def slug_in_use_err(slug: str, name: str):
    return (f"Slug '{slug}' is already in use by '{name}'. Please merge these "
        "professors together if they are the same person.")

# For verifying, rejecting, and asking for help on unverified reviews
# and verifying/rejecting unverified professors
class ActionForm(Form):
    id_ = IntegerField(required=True, widget=HiddenInput)
    verified = CharField(required=True, widget=HiddenInput)
    action_type = CharField(required=True, widget=HiddenInput)
    override = BooleanField(required=True, widget=HiddenInput)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.helper = FormHelper()
        self.helper.form_id = "action_form"
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def generate_layout(self):
        return Layout(
            Field('id_', id="id_"),
            Field('verified', id="verified"),
            Field('action_type', id="action_type"),
            Field('override', id="override")
        )

# For unverifying a verified review. Currently used on /professor
class ReviewUnverifyForm(Form):
    id_ = IntegerField(required=True, widget=HiddenInput)
    verified = CharField(required=True, widget=HiddenInput, initial=Review.Status.PENDING.value)
    action_type = CharField(required=True, widget=HiddenInput, initial=AdminAction.REVIEW_VERIFY.value)

    def __init__(self, review_id, **kwargs):
        super().__init__(**kwargs)
        self.fields['id_'].initial = review_id

        self.helper = FormHelper()
        self.helper.form_id = f"unverify_review_{review_id}"
        self.helper.form_class = "unverify_review"
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def generate_layout(self):
        submit_button = Button(
            "unverify",
            "Unverify",
            css_class="btn-danger btn-lg",
            onClick=f"unverifyReview('#{self.helper.form_id}')"
        )
        return Layout(
            'id_',
            'verified',
            'action_type',
            FormActions(submit_button)
        )

# For deleting unverified professors. This action cannot be undone.
# Use carefully: Once a professor is deleted, all their data is lost
# and cannot be retrived!
class ProfessorDeleteForm(ActionForm):
    professor_type = CharField(required=True, widget=HiddenInput)

    def __init__(self, professor: Professor, **kwargs):
        self.fields['professor_type'].initial = professor.type
        super().__init__(**kwargs)

    def generate_layout(self):
        return Layout(
            super().generate_layout(),
            'professor_type'
        )

# For manually entering a professor's slug when
# the system couldn't automatically generate one
class ProfessorSlugForm(Form):
    slug = CharField(required=False, widget=TextInput, label=False)
    professor_id = IntegerField(required=True, widget=HiddenInput)
    action_type = CharField(required=True, widget=HiddenInput, initial=AdminAction.PROFESSOR_SLUG.value)

    def __init__(self, professor: Professor, modal_title="", **kwargs):
        super().__init__(**kwargs)
        self.professor = professor
        self.modal_title = modal_title
        self.fields['professor_id'].initial = self.professor.pk

        self.helper = FormHelper()
        self.helper.form_id = "slug-form"
        self.helper.form_class = "slug-form"
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def generate_layout(self):
        slug_errors = HTML(
            '''
            <div id="slug_errors" class="invalid-feedback" style="font-size: 15px">
            </div>
            '''
        )
        return Layout(
            Modal(
                Field(
                    'slug',
                    id="slug-form-slug",
                    placeholder="EX: Andres De Los Reyes = reyes_los_de_andres"
                ),
                slug_errors,
                Field(
                    'professor_id',
                    id="slug-form-id"
                ),
                'action_type',
                FormActions(
                    Button(
                        "done",
                        "Done",
                        id="submit-slug-form",
                        css_class="btn-primary float-right mt-3",
                        onClick="verifySlug('#slug-form')"
                    )
                ),
                css_id="slug-modal",
                title_id="slug-modal-label",
                title=self.modal_title
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        slug = str(cleaned_data.get("slug"))

        slug = slug.lower().strip().replace(" ", "_")
        professor = Professor.unfiltered.filter(slug=slug).first()

        if slug == '' or slug.isspace():
            error_msg = "You must enter a slug"
            error = ValidationError(error_msg, code='Empty')
            self.add_error('slug', error)

        if professor:
            error_msg = slug_in_use_err(slug, professor.name)
            error = ValidationError(error_msg, code='Exists')
            self.add_error('slug', error)

        return cleaned_data

# For editing a professor via the professor
# feature on /professor
class ProfessorUpdateForm(ModelForm):
    # Only reason I explicitly declare name, slug, and type
    #   as form fields is to remove the form_suffix. Doing
    #   this overrides the model field so I need to explicitly
    #   state the choices for the type field.
    name = CharField(
        required=False,
        label_suffix=None
    )

    slug = CharField(
        required=False,
        label_suffix=None
    )

    type = ChoiceField(
        required=False,
        label_suffix=None,
        choices=Professor.Type.choices
    )

    created_at = DateField(
        required=False,
        label_suffix=None,
        label="Date Created",
        disabled=True,
        widget=DateInput(format=DATE_FORMAT)
    )

    professor_id = CharField(
        required=False,
        label_suffix=None,
        label="ID",
        disabled=True
    )

    action_type = CharField(
        required=True,
        widget=HiddenInput,
        initial=AdminAction.PROFESSOR_EDIT.value
    )

    hidden_professor_id = IntegerField(
        required=True,
        widget=HiddenInput
    )

    class Meta:
        model = Professor
        exclude = ['status']

    def __init__(self, professor: Professor, **kwargs):
        super().__init__(**kwargs)
        self.professor = professor
        self.helper = FormHelper()
        self.helper.form_id = "edit-professor-form"
        self.helper.form_show_errors = False
        self.field_responses = self.create_field_responses()

        self.fields['created_at'].initial = self.professor.created_at
        self.fields['professor_id'].initial = self.professor.pk
        self.fields['hidden_professor_id'].initial = self.professor.pk

        self.helper.layout = self.generate_layout()

    def create_field_responses(self):
        field_response = {}
        for field in self.fields.keys():
            response_html = f'<div id="{field}_response" class="invalid-feedback text-center" style="font-size: 12px">{{{{ form.{field}.errors|striptags }}}}</div>'
            field_response[field] = HTML(response_html)

        return field_response

    def generate_layout(self):
        layout = Layout(
            Modal(
                'action_type',
                'hidden_professor_id',
                Div(
                    Div(
                        Field('name', id="edit_name"),
                        self.field_responses['name'],
                        css_class="form-group col-md-8"
                    ),
                    Div(
                        Field('slug', id="edit_slug"),
                        self.field_responses['slug'],
                        css_class="form-group col-md-4"
                    ),
                    css_class="form-row"
                ),
                Div(
                    Div(
                        Field('type', id="edit_type"),
                        self.field_responses['type'],
                        css_class="form-group col-md-4"
                    ),
                    Div(
                        'created_at',
                        css_class="form-group col-md-4"
                    ),
                    Div(
                        'professor_id',
                        css_class="form-group col-md-4"
                    ),
                    css_class="form-row"
                ),
                Div(
                    Button(
                        'update',
                        'Update',
                        css_id="update-professor",
                        css_class="btn-success",
                        onClick='sendResponse($("#edit-professor-form").serialize(), "professor_edit");'
                    ),
                    Button(
                        'merge',
                        'Merge',
                        css_id="merge-professor",
                        css_class="btn-primary",
                        onclick=format_html("mergeProfessor({args})", args={"merge_subject": self.professor.name, "subject_id": self.professor.pk})
                    ),
                    Button(
                        'unverify',
                        'Unverify',
                        css_class="btn-danger",
                        onClick='sendResponse($("#unverify-professor-form").serialize(), "professor_verify");'
                    ),
                    css_class="btn-group mt-3 float-right"
                ),
                css_id="edit-professor-modal",
                title_id="edit-professor-label",
                title=format_html('Viewing info for <b>{}</b>. Click a field to edit its contents then click update to save your changes.', (self.professor.name))
            )
        )
        return layout

    def clean(self):
        cleaned_data = self.cleaned_data
        professor_id = int(cleaned_data.get("hidden_professor_id"))
        name = str(cleaned_data.get("name"))
        slug = str(cleaned_data.get("slug"))

        professor = Professor.unfiltered.get(pk=professor_id)

        if not (name.strip() == "" or name == professor.name):
            professor_obj = Professor.unfiltered.filter(name=name).exclude(pk=professor_id)

            if professor_obj.exists():
                error_msg = "A professor with this name already exists"
                error = ValidationError(error_msg, code='Exists')
                self.add_error('name', error)
            else:
                cleaned_data['name'] = name.strip()
        else:
            cleaned_data['name'] = professor.name.strip().lower().replace(" ", "_")


        if not (slug.strip() == "" or slug == professor.slug):
            professor_obj = Professor.unfiltered.filter(slug=slug).exclude(pk=professor_id)

            if professor_obj.exists():
                error_msg = slug_in_use_err(slug, professor_obj.first().name)
                error = ValidationError(error_msg, code='Exists')
                self.add_error('slug', error)
            else:
                cleaned_data['slug'] = slug.strip().lower().replace(" ", "_")
        else:
            cleaned_data['slug'] = professor.slug.strip().lower().replace(" ", "_")


        return cleaned_data

# For unverifying a professor in the edit professor modal
# on /professor
class ProfessorUnverifyForm(Form):
    id_ = IntegerField(required=True, widget=HiddenInput)
    action_type = CharField(required=True, widget=HiddenInput, initial=AdminAction.PROFESSOR_VERIFY.value)
    verified = CharField(required=True, widget=HiddenInput, initial=Professor.Status.PENDING.value)

    def __init__(self, professor_id, **kwargs):
        super().__init__(**kwargs)
        self.fields['id_'].initial = professor_id
        self.helper = FormHelper()
        self.helper.form_id = "unverify-professor-form"
        self.helper.form_show_errors = False
        self.helper.layout = self.generate_layout()

    def generate_layout(self):
        return Layout(
            'id_',
            'action_type',
            'verified'
        )

# For merging two professors together. The optional merge_subject
# param is used on /professor to pre-fill the merge_subject
# field on the form.
# merge_subject = Professor being merged. Will be deleted afterwards.
# merge_target = Professor that will contain all the subject's data. Will remain afterwards.
class ProfessorMergeForm(Form):
    action_type = CharField(
        required=True,
        widget=HiddenInput,
        initial=AdminAction.PROFESSOR_MERGE.value
    )

    merge_subject = CharField(
        required=False,
        disabled=True
    )

    subject_id = IntegerField(
        required=True,
        widget=HiddenInput
    )

    merge_target = CharField(
        required=False
    )

    target_id = IntegerField(
        required=True,
        widget=HiddenInput
    )

    source_page = CharField(
        required=False,
        widget=HiddenInput
    )

    def __init__(self, request, **kwargs):
        super().__init__(**kwargs)

        self.helper = FormHelper()
        self.helper.form_id = "merge-form"
        self.helper.form_show_errors = False
        self.helper.form_show_labels = False
        self.helper.layout = self.generate_layout()

        if request:
            self.fields['source_page'].initial = request.path
            if "admin" in request.path:
                self.helper.form_class = "unverified_professor_form"

        # subject_id and/or target_id have hard-coded negative values to determine if the input belongs to a real professor.
        # If it does, the value will be replaced with that professor's id. These values must be different or the validation
        # will think the inputs are the same and return an error. These values must also be negative because a professor
        # could have an id of any non-negative number.
        self.fields['target_id'].initial = "-1"

    def generate_layout(self):
        fields = Layout(
            Div(
                'source_page',
                'action_type',
                Div(
                    HTML('''
                        {% if form.merge_target.errors %}
                            {{ form.merge_target.errors|striptags }}
                        {% else %}
                            {{ form.merge_subject.errors|striptags }}
                        {% endif %}
                    '''),
                    css_id="merge-errors",
                    css_class="row justify-content-center merge-errors invalid-feedback mb-1",
                    style="display: none;"
                ),
                Div(
                    Div(
                        Div(
                            # font-awesome icons don't render with the crispy_forms Button()
                            # element so this was my work around.
                            HTML(
                                '''
                                <button class="btn btn-outline-secondary fas fa-question-circle"
                                data-toggle="tooltip" data-placement="left"
                                title="All data for the instructor on the left will be merged into the
                                instructor on the right. The instructor on the left will be
                                deleted after the merge." type="button" onClick="null"></button>
                                '''
                            ),
                            css_class="input-group-prepend"
                        ),
                        Field(
                            'merge_subject',
                            css_class="rounded-0",
                            wrapper_class="mb-0"
                        ),
                        'subject_id',
                        Div(
                            HTML('<button class="input-group-text fas fa-arrow-right" disabled></button>'),
                            css_class="input-group-prepend"
                        ),
                        Field(
                            'merge_target',
                            id="id_merge_target",
                            css_class="rounded-right",
                            wrapper_class="mb-0",
                            placeholder="Merge Target",
                            type="search",
                            style="border-top-left-radius: 0; border-bottom-left-radius: 0;",
                        ),
                        Field(
                            'target_id',
                            id="id_target_id"
                        ),
                        css_class="input-group justify-content-center mb-1"
                    ),
                    css_class="row"
                ),
                Div(
                    Button(
                        'merge',
                        'Merge',
                        css_class="btn-primary mt-3 w-100",
                        onClick=f'sendResponse($("#{self.helper.form_id}").serialize(), "professor_merge")'
                    ),
                    css_class="row"
                ),
                css_class="container",
                style="width: fit-content",
                css_id="merge-form-container"
            )
        )
        layout = Modal(
            fields,
            css_id="merge-modal",
            title_id="merge-professor-label",
            title='Search for a professor/TA to merge with'
        )
        return layout

    def clean(self):
        cleaned_data = super().clean()
        merge_subject_id = cleaned_data['subject_id']
        merge_target_id = cleaned_data['target_id']

        merge_subject = merge_subject_id >= 0
        merge_target = merge_target_id >= 0
        if not (merge_subject and merge_target):
            if not merge_subject:
                error_msg = "This field cannot be empty"
                error = ValidationError(error_msg, code='Empty')
                self.add_error('merge_subject', error)
            if not merge_target:
                error_msg = "You must enter a professor to merge with"
                error = ValidationError(error_msg, code='Empty')
                self.add_error('merge_target', error)
        else:
            if merge_subject_id == merge_target_id:
                error_msg = "You can't merge someone with themselves"
                error = ValidationError(error_msg, code='Self-Merge')
                self.add_error('merge_target', error)
            else:
                subject = Professor.unfiltered.filter(pk=merge_subject_id).first()
                target = Professor.unfiltered.filter(pk=merge_target_id).first()
                error_msg = f'''The highlighted {"names don't" if not (subject or target) else "name doesn't"} exist'''
                error = ValidationError(error_msg, code='DNE')
                if not subject:
                    self.add_error('merge_subject', error)
                if not target:
                    self.add_error('merge_target', error)

        return cleaned_data


# Used on /admin when verifying professors that might be duplicates of already
# verified professors.
class ProfessorInfoModal(Form):
    def __init__(self, professor_in_question, similar_professors):
        super().__init__()
        self.professor_in_question = professor_in_question
        self.similar_professors = similar_professors
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = self.generate_layout()

    def generate_layout(self):
        def get_courses(professor: Professor):
            courses = set()

            reviews = Review.unfiltered.filter(professor__id=professor.pk).exclude(course=None).select_related("course")
            if reviews.exists():
                courses |= {review.course for review in reviews}

            courses_from_courses = Course.unfiltered.filter(professors__id=professor.pk)
            if courses_from_courses.exists():
                courses |= {course for course in courses_from_courses}

            grades = Grade.unfiltered.filter(professor__id=professor.pk).select_related("course")
            if grades.exists():
                courses |= {grade.course for grade in grades}

            def url_html(course):
                return f'<a href="{course.get_absolute_url()}" target="_blank">{course.name}</a>'

            return "No Courses" if len(courses) == 0 else mark_safe(', '.join(url_html(course) for course in courses))

        def create_row(professor: Professor):
            row = '''
                <tr class="row">
                    <td class="col-3 text-center"><a href="{absolute_url}" target="_blank">{similar_name}</a><br> (ID: {pid})</td>
                    <td class="col-6 text-center">{similar_courses}</td>
                    <td class="col-3 text-center"><button class="btn btn-primary" onclick="mergeProfessor({merge_args})">Merge</button></td>
                </tr>
            '''

            merge_data = {
                "merge_subject": self.professor_in_question.name,
                "subject_id": self.professor_in_question.pk,
                "merge_target": professor.name,
                "target_id": professor.pk
            }

            kwargs = {
                "absolute_url": professor.get_absolute_url(),
                "similar_name": professor.name,
                "pid": professor.pk,
                "similar_courses": get_courses(professor),
                "merge_args": merge_data
            }
            return format_html(row, **kwargs)

        table_str = '''
            <table class="table">
                <tbody>
        '''
        for professor in self.similar_professors:
            table_str += create_row(professor)

        table_str += '''
                </tbody>
            </table>
        '''

        modal_title = (
            f'This {self.professor_in_question.type} might be a duplicate of one of the professors below. <br>'
            f'<i>{self.professor_in_question.name}</i> ({self.professor_in_question.pk}) has taught: {get_courses(self.professor_in_question)}'
        )

        verify_data = {
            "professor_id": self.professor_in_question.pk,
            "action": "verified",
            "override": "true"
        }

        return Layout(
            Modal(
                HTML(table_str),
                Button("verify", "Verify", css_class="btn btn-success w-100", onclick=format_html("verifyProfessor({args})", args=verify_data)),
                css_id="info-modal",
                title=format_html(modal_title),
                title_class="col-11 text-center"
            )
        )
