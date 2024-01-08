import re
from collections import defaultdict

from django.shortcuts import render, redirect
from django.http import Http404
from django.views import View
from django.db.models import Count, Q, Sum, FloatField, F

from home.models import Course as CourseModel, Review

class Course(View):
    template = "course.html"

    def get(self, request, name):

        if name != name.upper():
            return redirect("course", name=name.upper())
        course = CourseModel.unfiltered.filter(name=name).first()

        if not course:
            raise Http404()

        sister_courses = (
            CourseModel.recent
            .filter(department=course.department, course_number__startswith=course.course_number[:3])
            .order_by("name")
            .exclude(pk=course.id)
        )

        # calculate average rating for all professors as an optimization. Store
        # in `average_rating_` so we don't accidentaly access `average_rating`
        # and compute the average rating per professor. The template will need
        # to be careful of this as well
        professors = (
            course
            .professors.all()
            .annotate(
                num_reviews=Count(
                    "review",
                    filter=Q(review__status=Review.Status.VERIFIED),
                )
            )
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
            .annotate(
                semester_taught=F("professorcourse__semester_taught")
            )
        )

        grouped_professors = defaultdict(list)
        past_professors = []
        for professor in professors:
            semester_taught = professor.semester_taught

            if semester_taught and semester_taught.recent:
                grouped_professors[semester_taught].append(professor)
            else:
                past_professors.append(professor)

        course_description = course.description
        courses_replaced = []

        course_code_format = '[A-Za-z]{4}(?:[A-Za-z]|[0-9]){3,6}'
        matches = re.findall(course_code_format,course_description)

        for word in matches:
            if not word in courses_replaced and CourseModel.recent.filter(name=word).first():
                course_description = course_description.replace(word, '<a href="/course/{0}">{0}</a>'.format(word))
                courses_replaced.append(word)
        course.description = course_description

        def key(item):
            return item[0].number()

        # order by semester taught
        grouped_professors = {
            k.name(): v for k, v in sorted(grouped_professors.items(), key=key, reverse=True)
        }
        # then add "past semesters" at the end, but only if there are any
        # past professors to begin with - we don't want to display this block at
        # all otherwise
        if past_professors:
            grouped_professors["Past Semesters"] = past_professors

        context = {
            "course": course,
            "sister_courses": sister_courses,
            "grouped_professors": grouped_professors
        }
        return render(request, self.template, context)
