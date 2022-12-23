from django.views import View
from django.http import JsonResponse

from home.forms.professor_forms import ProfessorFormAdd, EditReviewForm
from home.models import Professor, Review, Course
from home.utils import send_updates_webhook

class AddProfessorAndReview(View):
    def post(self, request):
        user = request.user
        form = ProfessorFormAdd(user, data=request.POST)

        if form.is_valid():
            cleaned_data = form.cleaned_data

            new_professor = Professor(
                name=cleaned_data['name'],
                slug=None,
                type=cleaned_data['type_']
            )
            new_professor.save()

            course = Course.unfiltered.filter(name=cleaned_data['course']).first()

            new_review = Review(
                professor=new_professor,
                course=course,
                user=user if user.is_authenticated else None,
                content=cleaned_data['content'],
                rating=cleaned_data['rating'],
                grade=cleaned_data['grade'],
                anonymous=cleaned_data['anonymous']
            )
            new_review.save()
            send_updates_webhook(request)

            form = ProfessorFormAdd(user)

            context = {
                "success": True
            }
        else:
            context = {
                "success": False,
                "errors": form.errors.as_json()
            }

        return JsonResponse(context)

class EditReview(View):
    def post(self, request):
        user = request.user
        form = EditReviewForm(user, data=request.POST)

        if form.is_valid():
            review_modified = form.cleaned_data
            review_orig = Review.unfiltered.filter(pk=review_modified['review_id']).select_related("course").first()

            if review_orig.content != review_modified['content']:
                review_orig.status = Review.Status.PENDING
                review_orig.content = review_modified['content']

            if review_modified["course"] and (review_orig.course.name != review_modified['course']):
                new_course = Course.unfiltered.filter(name=review_modified['course']).first()
                review_orig.course = new_course

            review_orig.rating = int(review_modified['rating'])
            review_orig.grade = review_modified['grade']
            review_orig.anonymous = review_modified['anonymous']

            review_orig.save()
            send_updates_webhook(request)

            context = {
                "success": True
            }
        else:
            context = {
                "success": False,
                "errors": form.errors.as_json()
            }

        return JsonResponse(context)
