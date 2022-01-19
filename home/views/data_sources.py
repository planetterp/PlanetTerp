from django.http import JsonResponse
from django.db.models import Sum, Q
from django.db.models.functions import Concat
from django.views import View
from django.urls import reverse

from home.models import Professor, Grade, Course, Gened
from home.utils import ttl_cache

SPRING_2020 = 202001
FALL_2020 = 202012
SPRING_2021 = 202101

class GradeData(View):
    def get(self, request):
        data = request.GET
        professor = data.get("professor", None)
        professor_courses = data.get("professor_courses", False)
        course = data.get("course", None)
        semester = data.get("semester", None)
        section = data.get("section", None)
        pf_semesters = data.get("pf_semesters", False) == "true"

        if professor_courses:
            grade_data = GradeData._course_grade_data(professor, pf_semesters)
            data = {
                "professor_slug": grade_data.pop("professor_slug"),
                "average_gpa": grade_data.pop("average_gpa"),
                "num_students": grade_data.pop("num_students"),
                "data": {}
            }

            for course_name, course_data in grade_data.items():
                (course_average_gpa, course_num_students, course_grades) = course_data

                if course_num_students and course_average_gpa:
                    data['data'][course_name] = GradeData._get_data(
                        course_average_gpa, course_num_students, course_grades)
        else:
            (average_gpa, num_students, grades) = GradeData._grade_data(professor,
                course, semester, section, pf_semesters)

            data = GradeData._get_data(average_gpa, num_students, grades)

        return JsonResponse(data)

    @staticmethod
    def _get_data(average_gpa, num_students, grades):
        def _statistic(name):
            if not num_students:
                return 0
            return round((grades[name] / num_students) * 100, 2)

        return {
            "average_gpa": average_gpa,
            "num_students": num_students,
            "data_plus": [
                _statistic("a_plus_total"),
                _statistic("b_plus_total"),
                _statistic("c_plus_total"),
                _statistic("d_plus_total")
            ],
            "data_flat": [
                _statistic("a_total"),
                _statistic("b_total"),
                _statistic("c_total"),
                _statistic("d_total"),
                _statistic("f_total"),
                _statistic("w_total"),
                _statistic("other_total")
            ],
            "data_minus": [
                _statistic("a_minus_total"),
                _statistic("b_minus_total"),
                _statistic("c_minus_total"),
                _statistic("d_minus_total")
            ]
        }

    @staticmethod
    def _course_grade_data(professor, pf_semesters):
        professor = Professor.objects.verified.filter(name=professor).first()
        courses = Course.objects.filter(professors=professor)
        grades = Grade.objects.filter(professor=professor)

        if not pf_semesters:
            grades = grades.exclude(
                Q(semester=SPRING_2020) |
                Q(semester=FALL_2020) |
                Q(semester=SPRING_2021)
            )

        grade_data = {
            "professor_slug": professor.slug,
            "average_gpa": grades.average_gpa(),
            "num_students": grades.num_students()
        }
        for course in courses:
            course_grades = grades
            course_grades = course_grades.filter(course=course)

            average_course_gpa = course_grades.average_gpa()
            num_course_students = course_grades.num_students()
            course_grades = course_grades.grade_totals_aggregate()

            grade_data[course.name] = (average_course_gpa, num_course_students, course_grades)

        return grade_data

    @staticmethod
    @ttl_cache(24 * 60 * 60)
    def _grade_data(professor, course, semester, section, pf_semesters):
        grades = Grade.objects.all()

        if professor:
            professor = Professor.objects.verified.filter(slug=professor).first()
            grades = grades.filter(professor=professor)
        if course:
            course = Course.objects.filter(name=course).first()
            grades = grades.filter(course=course)
        if semester:
            grades = grades.filter(semester=semester)
        if section:
            grades = grades.filter(section=section)
        if not pf_semesters:
            grades = grades.exclude(
                Q(semester=SPRING_2020) |
                Q(semester=FALL_2020) |
                Q(semester=SPRING_2021)
            )

        average_gpa = grades.average_gpa()
        num_students = grades.num_students()
        grades = grades.grade_totals_aggregate()

        return (average_gpa, num_students, grades)

    @staticmethod
    def compose_grade_data(professor, course, semester, section, pf_semesters):
        (average_gpa, num_students, grades) = GradeData._grade_data(professor,
        course, semester, section, pf_semesters)

        return GradeData._get_data(average_gpa, num_students, grades)

    @staticmethod
    def compose_course_grade_data(professor, pf_semesters):
        grade_data = GradeData._course_grade_data(professor, pf_semesters)
        data = {
            "professor_slug": grade_data.pop("professor_slug"),
            "average_gpa": grade_data.pop("average_gpa"),
            "num_students": grade_data.pop("num_students"),
            "data": {}
        }

        for course_name, course_data in grade_data.items():
            (course_average_gpa, course_num_students, course_grades) = course_data

            if course_num_students and course_average_gpa:
                data['data'][course_name] = GradeData._get_data(
                    course_average_gpa, course_num_students, course_grades)
        return data



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

        values = (
            Grade.objects
            .values("course__name", total_students=Sum("num_students"))
            .filter(total_students__gte=100)
            .average_gpa_annotate()
        )

        data = []
        for value in values:
            average_gpa = value["average_gpa"]
            # some courses with entirely "other" graded students have a gpa of
            # 0. Other courses with weirder circumstances (citation needed)
            # return an undefined gpa. Skip both of these; 0 gpa courses are
            # of no interest to users, and a gpa of `None` will error when we
            # try to round it.
            if average_gpa is None or average_gpa == 0:
                continue

            average_gpa = f"{average_gpa:.2f}"
            course_name = value["course__name"]
            # We're sacrificing access to the `course` object
            # itself for the sake of performance in the above query, so we have
            # to construct its location manually instead of with
            # `Course#get_absolute_url`. An acceptable, although unfortunate,
            # tradeoff.
            href = reverse("course", kwargs={"name": course_name})
            course_name = f"<a href='{href}' target='_blank'>{course_name}</a>"
            num_students = value["total_students"]

            entry = [course_name, average_gpa, num_students]
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

        if not geneds:
            return JsonResponse({"data": []})

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
