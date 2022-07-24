from datetime import date
from abc import abstractmethod

from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.template.context_processors import csrf

import django_tables2 as tables

from crispy_forms.utils import render_crispy_form

from home.models import Review, Grade
from home.forms.admin_forms import ReviewUnverifyForm, ReviewVerifyForm, ProfessorVerifyForm, ReviewRejectForm, ReviewHelpForm, ProfessorRejectForm, ProfessorDeleteForm
from planetterp.settings import DATE_FORMAT

class InformationColumn(tables.Column):
    def __init__(self, *args, **kwargs):
        attrs = {
            "th": {"class": "information"},
            "td": {
                "class": "information",
                "style": "white-space: nowrap; width: 11%;"
            }
        }
        super().__init__(verbose_name="Information", orderable=False, attrs=attrs, *args, **kwargs)

    def rating_to_element(self, rating: int):
        rating_html = '<span class="rating">'

        for _ in range(rating): # filled stars
            rating_html += '<i style="margin-top:4px;" class="fas fa-star"></i>\n'
            rating_html += '<i class="far fa-star"></i>\n'

        for _ in range(rating, 5): # unfilled stars
            rating_html += '<i class="far fa-star"></i>\n'

        rating_html += '</span> <br />'
        return mark_safe(rating_html)

    def grade_to_element(self, grade):
        a_str = "an" if grade in Grade.VOWEL_GRADES else "a"
        kwargs = {
            "a_str": a_str,
            "grade": grade
        }
        return format_html('<span class="grade">Expecting {a_str} {grade}</span> <br />', **kwargs)

    def render(self, value: dict):
        review = value.pop("review")
        is_staff = value.pop("is_staff")

        column_html = ""
        if review.professor.slug:
            column_html += '''
                <span>
                    <a href="/professor/{professor_slug}">
                        <strong>{professor_name}</strong>
                    </a>
                </span>
                <br />
            '''
        else:
            column_html += '''
                <span>
                    <strong>{professor_name}</strong>
                </span>
                <br />
            '''

        if review.course:
            column_html += '''
                <span class="course">
                    <a href="/course/{course_name}">{course_name}</a>
                </span>
                <br />
            '''

        column_html += self.rating_to_element(review.rating)

        if review.grade:
            column_html += self.grade_to_element(review.grade)

        if is_staff:
            if review.anonymous and review.user:
                column_html += '''
                     <span class="noselect" data-toggle="tooltip" data-placement="right" title="This reviewer posted anonymously">
                        <i class="fa fa-eye-slash"></i>
                    </span>
                '''
            elif not review.anonymous and review.user:
                column_html += '''
                     <span class="noselect" data-toggle="tooltip" data-placement="right" title="This reviewer posted publicly">
                        <i class="fa fa-eye"></i>
                    </span>
                '''

        column_html += '''
            {anonymous}
            <br />
            {created_at}
        '''

        if review.from_ourumd:
            column_html += ' <i class="fas fa-info-circle" data-toggle="tooltip" data-placement="right" title="This review was automatically imported from OurUMD. It was not verified by our review checkers. It may not follow our review standards."></i>'


        if review.created_at.date() >= date(2020, 3, 10) and review.created_at.date() <= date(2021, 8, 30):
            column_html += ' <i class="fas fa-head-side-mask" data-toggle="tooltip" data-placement="right" title="This review was submitted while most classes were online during the COVID-19 pandemic. The review may not be indicative of a regular semester."></i>'

        kwargs = {
            "professor_slug": review.professor.slug,
            "professor_name": review.professor.name,
            "course_name": review.course.name if review.course else None,
            "anonymous": "Anonymous" if not review.user or (review.anonymous and not is_staff) else review.user.username,
            "created_at": review.created_at.date().strftime(DATE_FORMAT)
        }

        return format_html(column_html, **kwargs)

class ReviewColumn(tables.Column):
    def __init__(self, *args, **kwargs):
        attrs = {
            "th": {"class": "review"},
            "td": {
                "class": "review",
                "style": "white-space: pre-line; width: 75%;"
            }
        }

        super().__init__(verbose_name="Review", orderable=False, attrs=attrs, *args, **kwargs)

    def render(self, value: dict):
        review = value.pop("review")
        return mark_safe(review.content)

class StatusColumn(tables.Column):
    def __init__(self, *args, **kwargs):
        attrs = {
            "th": {"class": "status"},
            "td": {"class": "status"}
        }
        super().__init__(verbose_name="Status", orderable=False, attrs=attrs, *args, **kwargs)

    def render(self, value: dict):
        review = value.pop("review")
        review_status = Review.Status(review.status)
        column_html = ''

        if review_status is Review.Status.PENDING:
            column_html += '<p style="color: darkgoldenrod;">Under Review</p>'
        elif review_status is Review.Status.REJECTED:
            column_html += '''
                <p style="color: red; display: inline;">Rejected</p>
                <i class="fas fa-info-circle" data-toggle="tooltip" data-placement="right" title="Check the about page to see our standards for accepting reviews."></i>
            '''
        elif review_status is Review.Status.VERIFIED:
            column_html += '<p style="color: green;">Accepted</p>'
        else:
            # For testing only; Will be removed after testing
            raise ValueError("Invalid status!")

        return mark_safe(column_html)

class ActionColumn(tables.Column):
    def __init__(self, *args, **kwargs):

        attrs = {
            "th": {"class": "action"},
            "td": {"class": "action"}
        }
        super().__init__(verbose_name="Action", orderable=False, attrs=attrs, *args, **kwargs)

    @abstractmethod
    def render(self, value: dict):
        pass

# Admin actions for verified reviews
class VerifiedReviewsActionColumn(ActionColumn):
    def render(self, value: dict):
        request = value.pop("request")
        model_obj = value.pop("model_obj")

        ctx = {}
        ctx.update(csrf(request))

        form = ReviewUnverifyForm(model_obj.pk)
        column_html = render_crispy_form(form, form.helper, context=ctx)
        return mark_safe(column_html)

# Admin actions for unverified reviews
class UnverifiedReviewsActionColumn(ActionColumn):
    def render(self, value: dict):
        request = value.pop("request")
        model_obj = value.pop("model_obj")

        ctx = {}
        ctx.update(csrf(request))

        verify_form = ReviewVerifyForm(model_obj.pk)
        reject_form = ReviewRejectForm(model_obj.pk)
        help_form = ReviewHelpForm(model_obj.pk)

        column_html = '''
            <div class="unverified_review_{professor_id}" style="white-space: nowrap;">
                <div class="btn-group">
                    {verify_form}
                    {reject_form}
                </div>
                <div class="btn-group">
                    {help_form}
                </div>
            </div>
        '''
        kwargs = {
            "professor_id": model_obj.professor_id,
            "verify_form": render_crispy_form(verify_form, verify_form.helper, context=ctx),
            "reject_form": render_crispy_form(reject_form, reject_form.helper, context=ctx),
            "help_form": render_crispy_form(help_form, help_form.helper, context=ctx)
        }
        return format_html(column_html, **kwargs)

# Admin actions for unverified professors
class UnverifiedProfessorsActionColumn(ActionColumn):
    def render(self, value: dict):
        request = value.pop("request")
        model_obj = value.pop("model_obj")

        ctx = {}
        ctx.update(csrf(request))

        verify_form = ProfessorVerifyForm(model_obj.pk)
        reject_form = ProfessorRejectForm(model_obj.pk)
        delete_form = ProfessorDeleteForm(model_obj)

        column_html = '''
            <div style="white-space: nowrap;">
                <div class="btn-group">
                    {verify_form}
                    {reject_form}
                </div>
                <div class="btn-group">
                    {delete_form}
                </div>
            </div>
        '''
        kwargs = {
            "verify_form": render_crispy_form(verify_form, verify_form.helper, context=ctx),
            "reject_form": render_crispy_form(reject_form, reject_form.helper, context=ctx),
            "delete_form": render_crispy_form(delete_form, delete_form.helper, context=ctx)
        }
        return format_html(column_html, **kwargs)
