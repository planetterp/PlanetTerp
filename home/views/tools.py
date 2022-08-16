import math

from django.http import HttpResponseBadRequest, JsonResponse
from django.db.models import Count, Sum, Q, FloatField
from django.views.generic import TemplateView
from django.shortcuts import render
from django.views import View

from home.models import Grade, Course, Review, Professor
from home.utils import ttl_cache

class Tools(TemplateView):
    template_name = "tools.html"

class ToolDemographics(TemplateView):
    template_name = "demographics.html"

class ToolPopularCourses(TemplateView):
    template_name = "popularcourses.html"

    def post(self, request):
        data = request.POST

        if 'department' not in data:
            return HttpResponseBadRequest("Invalid search.")

        query = data["department"]
        if len(query) < 3:
            return HttpResponseBadRequest("Your search must be at least 3 "
                "characters.")

        values = (
            Grade.recent
            .filter(course__name__icontains=query)
            .values("course__name")
            .annotate(num_students=Sum("num_students"))
            .order_by("-num_students")
        )

        if not values:
            return HttpResponseBadRequest("No results.")

        data = [[], []]
        for value in values:
            data[0].append(value["num_students"])
            data[1].append(value["course__name"])

        return JsonResponse(data, safe=False)

class ToolGradeInflation(TemplateView):
    template_name = "gradeinflation.html"

    def post(self, request):
        data = request.POST
        if 'search' not in data:
            return HttpResponseBadRequest("Invalid search.")

        search = data["search"]

        if len(search) not in [0, 4, 5, 6, 7, 8]:
            return HttpResponseBadRequest("Invalid department or course.")

        grades = Grade.unfiltered.all()
        if len(search) == 4:
            grades = grades.filter(course__department=search)
        if len(search) > 4:
            course = Course.recent.filter(name=search).first()
            if not course:
                return HttpResponseBadRequest("Course does not exist.")

            grades = course.grade_set.all()

        values = (
            grades
            .values("semester")
            .average_gpa_annotate()
            .order_by("semester")
        )
        # [labels, data]
        dist = [[], []]
        for value in values:
            semester = value["semester"].name(short=True, year_first=True)
            dist[0].append(semester)
            average_gpa = value["average_gpa"]
            dist[1].append(f"{average_gpa:0.2f}")
        return JsonResponse(dist, safe=False)


class ToolGeneds(TemplateView):
    template_name = "geneds.html"

class ToolCourseDifficulty(TemplateView):
    template_name = "coursedifficulty.html"

class ToolStatistics(View):
    def get(self, request):
        (review_ratings, review_dates, professor_ratings) = self.graph_data()
        context = {
            "review_ratings": review_ratings,
            "review_dates": review_dates,
            "professor_ratings": professor_ratings
        }
        return render(request, "statistics.html", context)

    @staticmethod
    @ttl_cache(24 * 60 * 60)
    def graph_data():
        reviews = Review.verified.all()
        professors = (
            Professor.verified
            .annotate(
                # TODO consolidate this with the Professor#average_rating
                # method, will likely require a new Professors queryset
                average_rating_= (
                    Sum(
                        "review__rating",
                        output_field=FloatField(),
                        filter=Q(review__status=Review.Status.VERIFIED)
                    )
                    /
                    Count(
                        "review",
                        filter=Q(review__status=Review.Status.VERIFIED)
                    )
                )
            )
        )

        review_ratings = [0] * 5
        # not a typo - there are actually 53 weeks in an isocalendar year.
        review_dates = [0] * 53
        # we'll divide each of the 4 intervals (1-2, 2-3, 3-4, 4-5) into 10
        # segments each. So bucket 1.0 - 1.1 together, 1.1 - 1.2 together, etc.
        # We need one additional bucket to deal with inclusivity on both ends.
        professor_ratings = [0] * (10 * 4 + 1)

        for review in reviews:
            review_ratings[review.rating - 1] += 1
            week = review.created_at.isocalendar()[1]
            review_dates[week - 1] += 1

        for professor in professors:
            rating = professor.average_rating_
            if rating is None:
                continue
            # careful: due to floating point errors, (rating - 1) // 0.1 is
            # incorrect. Try evaluating `5.0 // 0.1` in a terminal yourself if
            # you don't believe me!
            bucket = math.floor((rating - 1) / 0.1)
            professor_ratings[bucket] += 1

        return (review_ratings, review_dates, professor_ratings)
