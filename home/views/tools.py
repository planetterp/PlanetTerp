from django.http import HttpResponseBadRequest, JsonResponse
from django.views.generic import TemplateView
from django.db.models.functions import Concat
from django.db.models import Sum

from home.models import Grade
from home import model

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
            return HttpResponseBadRequest("Your search must be 3 or more "
                "characters.")

        grades = (
            Grade.objects
            .annotate(
                course_name=Concat("course__department", "course__course_number")
            )
            .filter(course_name__icontains=query)
        )

        if not grades:
            return HttpResponseBadRequest("No results.")

        courses = (
            grades
            .values("course_name")
            .annotate(num_students=Sum("num_students"))
            .order_by("-num_students")
        )
        data = [[], []]
        for course in courses:
            data[0].append(course["num_students"])
            data[1].append(course["course_name"])

        return JsonResponse(data, safe=False)

class ToolGradeInflation(TemplateView):
    template_name = "gradeinflation.html"

    def post(self, request):
        data = request.POST

        if 'search' not in data:
            return HttpResponseBadRequest("Invalid search.")

        # TODO rewrite this

        if len(data["search"]) != 0 and len(data["search"]) != 4 and len(data["search"]) != 7 and len(data["search"]) != 8:
            return HttpResponseBadRequest("Invalid department or course.")

        distribution = list(model.get_distribution(data["search"]))

        if len(distribution) == 0:
            return HttpResponseBadRequest("No results.")

        new_distribution = []
        semesters = ['199801', '199808', '199901', '199908', '200001', '200008', '200101', '200108', '200201', '200208',
            '200301', '200308', '200401', '200408', '200501', '200508', '200601', '200608', '200701', '200708', '200801',
            '200808', '200901', '200908', '201001', '201008', '201101', '201108', '201201', '201208', '201301', '201308',
            '201401', '201408', '201501', '201508', '201601', '201608', '201701', '201708', '201801', '201808',
            '201901', '201908', '202001', '202008']

        for semester in semesters:
            if not any(semester in s.semester for s in distribution):
                new_distribution.append('null')
            else:
                for s in distribution:
                    if s.semester == semester:
                        new_distribution.append("{0:.2f}".format(s.avg_gpa))

        return JsonResponse(new_distribution, safe=False)


class ToolGeneds(TemplateView):
    template_name = "geneds.html"

class ToolCourseDifficulty(TemplateView):
    template_name = "coursedifficulty.html"
