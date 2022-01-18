from django.http import HttpResponseBadRequest, JsonResponse
from django.views.generic import TemplateView
from django.db.models.functions import Concat
from django.db.models import Sum

from home.models import Grade


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
    SEMESTERS = ['199801', '199808', '199901', '199908', '200001', '200008',
        '200101', '200108', '200201', '200208', '200301', '200308', '200401',
        '200408', '200501', '200508', '200601', '200608', '200701', '200708',
        '200801', '200808', '200901', '200908', '201001', '201008', '201101',
        '201108', '201201', '201208', '201301', '201308', '201401', '201408',
        '201501', '201508', '201601', '201608', '201701', '201708', '201801',
        '201808', '201901', '201908', '202001', '202008', '202101'
    ]

    def post(self, request):
        data = request.POST
        if 'search' not in data:
            return HttpResponseBadRequest("Invalid search.")

        search = data["search"]

        if len(search) not in [0, 4, 5, 6, 7, 8]:
            return HttpResponseBadRequest("Invalid department or course.")

        dist = []
        for semester in self.SEMESTERS:
            grades = Grade.objects.filter(semester=semester)
            if len(search) == 4:
                grades = grades.filter(course__department=search)
            if len(search) > 4:
                grades.annotate(

                )
                grades = (
                    grades.annotate(
                        course_name=Concat("course__department", "course__course_number")
                    )
                    .filter(course_name=search)
                )

            gpa = grades.average_gpa()
            print(gpa, semester)
            dist.append(f"{gpa:.2f}" if gpa else None)

        return JsonResponse(dist, safe=False)


class ToolGeneds(TemplateView):
    template_name = "geneds.html"

class ToolCourseDifficulty(TemplateView):
    template_name = "coursedifficulty.html"
