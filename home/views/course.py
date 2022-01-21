import re
from collections import defaultdict

from django.shortcuts import render, redirect
from django.http import Http404
from django.views import View

from home.models import ProfessorCourse, Course as CourseModel

class Course(View):
    template = "course.html"

    def get(self, request, name):

        if name != name.upper():
            return redirect("course", name=name.upper())
        course = CourseModel.objects.filter(name=name).first()

        if not course:
            raise Http404()

        sister_courses = (
            CourseModel.objects
            .filter(department=course.department, course_number__startswith=course.course_number[:3])
            .order_by("name")
            .exclude(pk=course.id)
        )

        professors = course.professors.all()
        grouped_professors = defaultdict(list)
        past_professors = []
        for professor in professors:
            professor_course = ProfessorCourse.objects.get(
                professor_id=professor.id, course_id=course.id)
            recent_semester = professor_course.recent_semester

            if recent_semester and recent_semester.recent:
                grouped_professors[recent_semester].append(professor)
            else:
                past_professors.append(professor)


        course_description = course.description
        courses_replaced = []

        if course_description is not None:
            for word in re.split(r' |\.', course_description):
                # remove any character that is not a letter or number
                word = re.sub(r'[\W_]+', '', word)
                if not word in courses_replaced and re.match(r'^([A-Z]{4}(?:[A-Z]|[0-9]){3,6})$', word) and CourseModel.objects.filter(name=word).first():
                    course_description = course_description.replace(word, '<a href="/course/{0}">{0}</a>'.format(word))
                    courses_replaced.append(word)
        course.description = course_description

        def key(item):
            return item[0].number()

        # order by semester taught
        grouped_professors = {
            k.name(): v for k, v in sorted(grouped_professors.items(), key=key, reverse=True)
        }
        # then add "past semesters" at the end
        grouped_professors["Past Semesters"] = past_professors

        context = {
            "course": course,
            "sister_courses": sister_courses,
            "grouped_professors": grouped_professors
        }
        return render(request, self.template, context)
