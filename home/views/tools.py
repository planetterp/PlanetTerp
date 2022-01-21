from django.http import HttpResponseBadRequest, JsonResponse
from django.views.generic import TemplateView
from django.db.models import Sum

from home.models import Grade, Course


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
            Grade.objects
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

        grades = Grade.objects.all()
        if len(search) == 4:
            grades = grades.filter(course__department=search)
        if len(search) > 4:
            if not Course.objects.filter(name=search).exists():
                return HttpResponseBadRequest("Course does not exist.")

            grades = grades.filter(course__name__istartswith=search)

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
