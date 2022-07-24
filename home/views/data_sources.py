from django.http import JsonResponse
from django.views import View
from django.db.models import Sum

from home.utils import ttl_cache
from home.models import Professor, Grade, Course, Gened


class GradeData(View):
    def get(self, request):
        data = request.GET
        professor = data.get("professor", None)
        course = data.get("course", None)
        spring_2020 = data.get("spring_2020", True) == "true"

        (average_gpa, num_students, grades) = self._grade_data(professor,
            course, spring_2020)

        def _statistic(name):
            if not num_students:
                return 0
            return round((grades[name] / num_students) * 100, 2)

        data = {
            "average_gpa": average_gpa,
            "num_students": num_students,
            "data_plus": [
                _statistic("a_plus_total"), _statistic("b_plus_total"),
                _statistic("c_plus_total"), _statistic("d_plus_total")
            ],
            "data_flat": [
                _statistic("a_total"), _statistic("b_total"), _statistic("c_total"),
                _statistic("d_total"), _statistic("f_total"), _statistic("w_total"),
                _statistic("other_total")
            ],
            "data_minus": [
                _statistic("a_minus_total"), _statistic("b_minus_total"),
                _statistic("c_minus_total"), _statistic("d_minus_total")
            ]
        }
        return JsonResponse(data)

    @staticmethod
    @ttl_cache(24 * 60 * 60)
    def _grade_data(professor, course, spring_2020):
        grades = Grade.objects.all()

        if professor:
            professor = Professor.objects.verified.filter(slug=professor).first()
            grades = grades.filter(professor=professor)
        if course:
            course = Course.objects.filter(name=course).first()
            grades = grades.filter(course=course)

        if not spring_2020:
            grades = grades.exclude(semester=202001)

        average_gpa = grades.average_gpa()
        num_students = grades.num_students()
        grades = grades.grade_totals_aggregate()

        return (average_gpa, num_students, grades)


class CourseDifficultyData(View):
    def get(self, _request, type_):
        if type_ == "courses":
            data = self._course_data()
        if type_ == "departments":
            data = self._departments_data()

        return JsonResponse({"data": data})

    @staticmethod
    @ttl_cache(24 * 60 * 60)
    def _course_data():
        data = []
        for course in Course.objects.all():
            num_students = course.grade_set.all().num_students() or 0
            if num_students < 100:
                continue

            average_gpa = round(course.average_gpa(), 2)
            entry = [course.name, average_gpa, num_students]
            data.append(entry)

        return data

    @staticmethod
    @ttl_cache(24 * 60 * 60)
    def _departments_data():
        departments = (
            Grade.objects
            .values("course__department").distinct()
            .annotate(num_students=Sum("num_students"))
            .filter(num_students__gte=100)
        )

        data = []
        for department in departments:
            department_name = department["course__department"]
            average_gpa = (
                Grade.objects
                .filter(course__department=department_name)
                .average_gpa()
            )
            entry = [department_name, round(average_gpa, 2), department["num_students"]]
            data.append(entry)
        return data


class GenedData(View):
    def get(self, request):
        geneds = request.GET["geneds"].replace("&", "").split("=on")
        geneds = set(gened for gened in geneds if gened in Gened.GENEDS)
        geneds = tuple(geneds)
        courses = Course.objects.raw("""
            SELECT GROUP_CONCAT(name) AS geneds, course_id AS id
            FROM home_gened
            GROUP BY course_id
            HAVING SUM(name IN %s) = %s
            """, [geneds, len(geneds)])

        data = []
        for course in courses:
            geneds = course.geneds.replace(",", ", ")
            average_gpa = course.average_gpa()
            average_gpa = round(average_gpa, 2) if average_gpa else "No grade data available"
            entry = [course.name, course.title, course.credits, average_gpa,
                geneds]
            data.append(entry)

        return JsonResponse({"data": data})
