from django.views import View
from django.shortcuts import render
from django.http import Http404, JsonResponse

from home.utils import send_updates_webhook
from home.forms.professor_forms import ProfessorFormReview
from home.models import Professor as ProfessorModel, Review, Course
from home.tables.reviews_table import VerifiedReviewsTable
from home.forms.admin_forms import ProfessorUpdateForm, ProfessorUnverifyForm, ProfessorMergeForm, ReviewUnverifyForm


class Professor(View):
    template = "professor.html"

    def get(self, request, slug):
        professor = ProfessorModel.verified.filter(slug=slug).first()
        if not professor:
            raise Http404()

        user = request.user

        review_form = ProfessorFormReview(user, professor)

        reviews = (
            professor.review_set(manager="verified")
            .select_related("course")
            .order_by("-created_at")
        )

        reviews_table = VerifiedReviewsTable(reviews, request)

        courses_taught = (
            Course.recent
            .filter(professors__pk=professor.pk)
            .order_by("name")
            .distinct()
        )

        courses_reviewed = []
        values = (
            reviews
            .order_by("course__name")
            .values("course__name")
            .distinct()
        )
        for value in values:
            # filter out None values
            if not value["course__name"]:
                continue
            courses_reviewed.append(value["course__name"])

        values = (
            professor.grade_set(manager="recent")
            .order_by("course__name")
            .values("course__name")
            .distinct()
        )
        courses_graded = [value["course__name"] for value in values]

        context = {
            "user": user,
            "professor": professor,
            "review_form": review_form,
            "courses_taught": courses_taught,
            "courses_reviewed": courses_reviewed,
            "courses_graded": courses_graded,
            "reviews_table": reviews_table,
            "num_reviews": reviews.count()
        }

        if request.user.is_staff:
            edit_professor_form = ProfessorUpdateForm(professor, instance=professor)
            unverify_professor_form = ProfessorUnverifyForm(professor.pk)
            merge_professor_form = ProfessorMergeForm(request)
            review_unverify_form = ReviewUnverifyForm()
            context["edit_professor_form"] = edit_professor_form
            context['unverify_professor_form'] = unverify_professor_form
            context['merge_professor_form'] = merge_professor_form
            context['review_unverify_form'] = review_unverify_form

        return render(request, self.template, context)

    def post(self, request, slug):
        data = request.POST
        slug = data['slug']
        professor = ProfessorModel.verified.filter(slug=slug).first()
        user = request.user

        form = ProfessorFormReview(user, professor, data=request.POST)

        if form.is_valid():
            cleaned_data = form.cleaned_data
            course = Course.unfiltered.filter(name=cleaned_data['course']).first()
            review_data = {
                "professor": professor,
                "course": course,
                "user": user if user.is_authenticated else None,
                "content": cleaned_data['content'],
                "rating": cleaned_data['rating'],
                "grade": cleaned_data['grade'],
                "anonymous": cleaned_data['anonymous']
            }

            new_review = Review(**review_data)
            new_review.save()

            send_updates_webhook(request)

            form = ProfessorFormReview(user, professor)
            context = {
                "success": True
            }
        else:
            context = {
                "success": False,
                "errors": form.errors.as_json()
            }

        return JsonResponse(context)
