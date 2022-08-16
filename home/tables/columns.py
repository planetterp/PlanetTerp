from datetime import date
from abc import abstractmethod

from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.template.context_processors import csrf
from django.urls import reverse

from crispy_forms.utils import render_crispy_form
import django_tables2 as tables

from planetterp.settings import DATE_FORMAT
from home.models import Review, Grade
from home.forms.admin_forms import ReviewUnverifyForm

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

        # wrap long usernames to avoid increasing the information column width
        column_html += '<span style="white-space: normal; word-break: break-all;">'
        if is_staff and review.user:
            if review.anonymous:
                column_html += '''
                     <span class="noselect" data-toggle="tooltip" data-placement="right" title="This reviewer posted anonymously">
                        <i class="fa fa-eye-slash"></i>
                    </span>
                '''
            else:
                column_html += '''
                     <span class="noselect" data-toggle="tooltip" data-placement="right" title="This reviewer posted publicly">
                        <i class="fa fa-eye"></i>
                    </span>
                '''
            profile_link = reverse("user-profile", kwargs={"user_id": review.user.id})
            column_html += f"<a href='{profile_link}'>{{username}}</a>"
        else:
            column_html += "{username}"

        column_html += '''
            </span>
            <br />
            {created_at}
        '''

        if review.from_ourumd:
            column_html += ' <i class="fas fa-info-circle" data-toggle="tooltip" data-placement="right" title="This review was automatically imported from OurUMD. It was not manually verified and may not follow our review standards."></i>'

        if review.created_at.date() >= date(2020, 3, 10) and review.created_at.date() <= date(2021, 8, 30):
            column_html += ' <i class="fas fa-head-side-mask" data-toggle="tooltip" data-placement="right" title="This review was submitted while most classes were online during the COVID-19 pandemic. It may not be indicative of a regular semester."></i>'

        if not review.user or (review.anonymous and not is_staff):
            username = "Anonymous"
        else:
            username = review.user.username

        kwargs = {
            "professor_slug": review.professor.slug,
            "professor_name": review.professor.name,
            "course_name": review.course.name if review.course else None,
            "username": username,
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
        return value.pop("review").content

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

        column_html = '''
            <div class="unverified_review_{professor_id} container" style="white-space: nowrap;">
                <div class="row">
                    <div class="col">
                        <button class="btn btn-success w-100" onClick="verifyReview('{review_id}', 'verified')" style="border-bottom-left-radius: 0; border-bottom-right-radius: 0;">Verify</button>
                    </div>
                </div>
                <div class="row">
                    <div class="col btn-group">
                        <button class="btn btn-danger" onClick="verifyReview('{review_id}', 'rejected')" style="border-top-left-radius: 0;">Reject</button>
                        <button class="btn btn-warning" onClick="verifyReview('{review_id}', 'review_help')" style="border-top-right-radius: 0;">Help</button>
                    </div>
                </div>
            </div>
        '''
        kwargs = {
            "professor_id": model_obj.professor_id,
            "review_id": model_obj.pk
        }
        return format_html(column_html, **kwargs)

# Admin actions for unverified professors
class UnverifiedProfessorsActionColumn(ActionColumn):
    def render(self, value: dict):
        request = value.pop("request")
        model_obj = value.pop("model_obj")

        csrf_token = csrf(request)
        ctx = {}
        ctx.update(csrf_token)

        column_html = '''
            <div class="unverified_professor_{id} container" style="white-space: nowrap;">
                <div class="row">
                    <div class="col">
                        <button class="btn btn-success w-100" onClick="verifyProfessor('{id}', 'verified')" style="border-bottom-left-radius: 0; border-bottom-right-radius: 0;">Verify</button>
                    </div>
                </div>
                <div class="row">
                    <div class="col btn-group">
                        <button class="btn btn-danger w-50" onClick="verifyProfessor('{id}', 'rejected')" style="border-top-left-radius: 0;">Reject</button>
                        <button class="btn btn-primary rounded-0" onclick="mergeProfessor('{name}', '{id}')">Merge</button>
                        <button class="btn btn-dark" onClick="verifyProfessor('{id}', 'professor_delete')" style="border-top-right-radius: 0;">Delete</button>
                    </div>
                </div>
        '''
        kwargs = {
            "id": model_obj.pk,
            "name": model_obj.name,
            "csrf": csrf_token['csrf_token']
        }
        return format_html(column_html, **kwargs)
