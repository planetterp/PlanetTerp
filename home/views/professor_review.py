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
        review = Review.unfiltered.filter(pk=request.POST['review_id']).select_related("course").first()

        if form.is_valid():
                review.status = Review.Status.PENDING
                review.content = form.cleaned_data['content']

            unverify = False
            if review_orig.content != review_modified['content']:
                unverify = True

            updating_none_course = new_course and not review_orig.course
            updating_non_none_course = new_course and review_orig.course and (review_orig.course.name != new_course)

            if updating_none_course or updating_non_none_course:
                new_course = Course.unfiltered.filter(name=new_course).first()
                review.course = new_course

            review.rating = int(form.cleaned_data['rating'])
            review.grade = form.cleaned_data['grade']
            review.anonymous = form.cleaned_data['anonymous']

            review.save()
            send_updates_webhook(request)

            context = {
                "success": True,
                "unverify": unverify,
                "professor": review.professor.name,
                "rating": review.rating,
                "anonymous": review.anonymous,
                "course": {"id" : review.course.pk, "name": review.course.name} if review.course else None,
                "grade": review.grade,
                "id": review.pk,
                "content": review.content
            }
        else:
            context = {
                "success": False,
                "errors": form.errors.as_json()
            }

        return JsonResponse(context)
