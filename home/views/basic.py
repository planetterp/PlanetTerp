from django.http.response import JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView, RedirectView, ListView
from django.http import HttpResponse, Http404
from django.contrib.auth.mixins import UserPassesTestMixin

from home.models import Organization, Professor, Course, Review, Grade, User
from home.tables.reviews_table import VerifiedReviewsTable, ProfileReviewsTable
from home.forms.basic import ProfileForm
from home.utils import recompute_ttl_cache, ttl_cache

class About(View):
    def get(self, request):
        organizations = Organization.objects.all()

        context = {
            "organizations": organizations
        }
        return render(request, "about.html", context)

class Contact(RedirectView):
    permanent = True
    pattern_name = "about"

class PrivacyPolicy(TemplateView):
    template_name = "privacypolicy.html"

class TermsOfUse(TemplateView):
    template_name = "termsofuse.html"

class Courses(ListView):
    model = Course
    template_name = "course_list.html"

class Professors(ListView):
    queryset = Professor.verified.all()
    template_name = "professor_list.html"

class Documents(TemplateView):
    template_name = "documents.html"

class Ads(View):
    CONTENT = "google.com, pub-8981508768288124, DIRECT, f08c47fec0942fa0"
    def get(self, _request):
        return HttpResponse(self.CONTENT, content_type="text/plain")

class SetColorScheme(View):
    def post(self, request):
        request.session["color_scheme"] = request.POST["scheme"]
        return HttpResponse()

class Robots(TemplateView):
    content_type = "text/plain"
    template_name = "robots.html"

class CourseReviews(View):
    def get(self, request, name):
        if name != name.upper():
            return redirect("course-reviews", name=name.upper())
        course = Course.unfiltered.filter(name=name).first()

        if course is None:
            raise Http404()

        reviews = course.review_set(manager="verified").order_by("-created_at")

        context = {
            "course": course,
            "num_reviews": reviews.count(),
            "reviews_table": VerifiedReviewsTable(reviews, request)
        }
        return render(request, "course_reviews.html", context)

class Index(View):

    @staticmethod
    @ttl_cache(24 * 60 * 60 * 7)
    def get_counts():
        num_courses = Course.unfiltered.count()
        num_professors = Professor.verified.count()
        num_reviews = Review.verified.count()
        num_course_grades = Grade.unfiltered.count()
        return (num_courses, num_professors, num_reviews, num_course_grades)


    def get(self, request):
        counts = self.get_counts()
        num_courses, num_professors, num_reviews, num_course_grades = counts
        recent_reviews = (
            Review
            .verified
            .filter(professor__status=Professor.Status.VERIFIED)
            .order_by("-pk")[:3]
            .select_related()
        )
        random_organization = Organization.objects.order_by("?")
        random_organization = random_organization and random_organization[0]

        context = {
            "num_courses": num_courses,
            "num_professors": num_professors,
            "num_reviews": num_reviews,
            "num_course_grades": num_course_grades,
            "recent_reviews": recent_reviews,
            "random_organization": random_organization
        }
        return render(request, "index.html", context)

class SortReviewsTable(View):
    def post(self, request):
        data = request.POST
        obj_id = int(data["obj_id"])
        data_type = data["type"]
        dir_ = data["direction"]
        key =  "-rating" if dir_ == "desc" else ("rating" if dir_ == "asc" else "-created_at")
        if data_type == "professor":
            reviews = Review.verified.filter(professor__id=obj_id)
        elif data_type == "course":
            reviews = Review.verified.filter(course__id=obj_id)
        else:
            raise ValueError(f"Unknown type: {data_type}")

        reviews = reviews.order_by(key)

        context = {
            "reviews_table": VerifiedReviewsTable(reviews, request).as_html(request)
        }

        return JsonResponse(context)

class RecomputeTTLCache(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def post(self, _request):
        recompute_ttl_cache()
        return HttpResponse()

class UserProfile(UserPassesTestMixin, View):
    # as all accounts have the option to still leave anonymous reviews, only
    # allow admins to view individual user profiles for now.
    #
    # We may want to allow people to view a subset of other user's profiles
    # in the future, which would show only the public reviews of that user, and
    # definitely not their settings. We would probably want to move to an
    # entirely different template at that point instead of hijacking
    # profile.html.
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if not user:
            raise Http404()

        reviews = user.review_set.order_by("created_at")

        context = {
            "reviews_table": ProfileReviewsTable(reviews, request),
            "form": ProfileForm(instance=user, allow_edits=False)
        }

        return render(request, "profile.html", context)
