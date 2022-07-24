import re
from collections import defaultdict

from home import utils
from home.models import ProfessorCourse, Course as CourseModel
from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse

class Course(View):
    template = "course.html"

    def get(self, request, name):

        if name != name.upper():
            return redirect("course", name=name.upper())
        course = CourseModel.objects.filter(name=name).first()

        if not course:
            return HttpResponse("Error: Course not found.")

        sister_courses = (
            CourseModel.objects
            .filter(department=course.department, course_number__startswith=course.course_number[:3])
            .order_by("name")
            .exclude(pk=course.id)
        )

        professors = course.professors.all()
        grouped_professors = defaultdict(list)

        for professor in professors:
            professor_course = ProfessorCourse.objects.get(
                professor_id=professor.id, course_id=course.id)
            professor.recent_semester = professor_course.recent_semester
            if professor.recent_semester in utils.RECENT_SEMESTERS:
                grouped_professors[professor.recent_semester].append(professor)
            else:
                grouped_professors["Past Semesters"].append(professor)

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

        # https://code.djangoproject.com/ticket/16335
        grouped_professors = dict(grouped_professors)

        context = {
            "course": course,
            "sister_courses": sister_courses,
            "grouped_professors": grouped_professors
        }
        return render(request, self.template, context)
