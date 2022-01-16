from django.views.generic import TemplateView
from django.urls import reverse

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from home.models import Course as CourseModel, Professor as ProfessorModel
from home import queries
from api.serializers import (CourseSerializer, ProfessorSerializer,
    ProfessorWithReviewsSerializer, CourseWithReviewsSerializer,
    SearchResultSerializer, GradeSerializer)
from api.utils import param, param_int, param_bool, ValidationError


class Docs(TemplateView):
    template_name = "docs.html"


class Meta(APIView):
    def get(self, request):
        data = {
            "version": 1,
            "documentation": request.build_absolute_uri(reverse("api-docs"))
        }
        return Response(data)


class Course(APIView):
    def get(self, request):
        name = param(request, "name")
        reviews = param_bool(request, "reviews", default=False)

        course = CourseModel.objects.filter(name=name).first()
        if not course:
            raise ValidationError("course not found")

        Serializer = (CourseWithReviewsSerializer if reviews else
            CourseSerializer)
        serializer = Serializer(course)
        return Response(serializer.data)


class Courses(ListAPIView):
    serializer_class = CourseSerializer

    def get_queryset(self):
        request = self.request
        department = param(request, "department", default=None)
        reviews = param_bool(request, "reviews", default=False)
        limit = param_int(request, "limit", default=100, min_=0, max_=100)
        offset = param_int(request, "offset", default=0, min_=0)

        if department and len(department) != 4:
            raise ValidationError("department parameter must be 4 characters")

        courses = CourseModel.objects.all()
        if department:
            courses = courses.filter(department=department)

        if reviews:
            self.serializer_class = CourseWithReviewsSerializer

        courses = courses[offset:offset + limit]
        return courses


class Professor(APIView):
    def get(self, request):
        name = param(request, "name")
        reviews = param_bool(request, "reviews", default=False)

        professor = ProfessorModel.objects.verified.filter(name=name).first()
        if not professor:
            raise ValidationError("professor not found")

        Serializer = (ProfessorWithReviewsSerializer if reviews else
            ProfessorSerializer)
        serializer = Serializer(professor)
        return Response(serializer.data)

class Professors(ListAPIView):
    serializer_class = ProfessorSerializer

    def get_queryset(self):
        request = self.request
        type_ = param(request, "type", default=None,
            options=["professor", "ta"])
        reviews = param_bool(request, "reviews", default=False)
        limit = param_int(request, "limit", default=100, min_=0, max_=100)
        offset = param_int(request, "offset", default=0, min_=0)
        # keep backwards compatability
        if type_ == "ta":
            type_ = "TA"

        professors = ProfessorModel.objects.all()
        if type_:
            professors = professors.filter(type=type_)

        if reviews:
            self.serializer_class = ProfessorWithReviewsSerializer

        professors = professors[offset:offset + limit]
        return professors

class Grades(APIView):
    def get(self, request):
        course_name = param(request, "course", default=None)
        professor_name = param(request, "professor", default=None)
        semester = param(request, "semester", default=None)
        section = param(request, "section", default=None)

        if not course_name and not professor_name:
            raise ValidationError("parameters must include at least one of: "
                "\"course\", \"professor\"")

        if course_name:
            course = CourseModel.objects.filter(name=course_name).first()
            if not course:
                raise ValidationError("course not found")
            grades = course.grade_set

        if professor_name:
            professor = (
                ProfessorModel.objects.filter(name=professor_name).first()
            )
            if not professor:
                raise ValidationError("professor not found")
            grades = professor.grade_set

        if semester:
            grades = grades.filter(semester=semester)
        if section:
            grades = grades.filter(section=section)

        serializer = GradeSerializer(grades, many=True)
        return Response(serializer.data)


class Search(APIView):
    def get(self, request):
        query = param(request, "query")
        limit = param_int(request, "limit", default=30, min_=0, max_=100)
        offset = param_int(request, "offset", default=0, min_=0)

        results = queries.search(query, limit, offset=offset, professors=True,
            courses=True)

        serializer = SearchResultSerializer(results, many=True)
        return Response(serializer.data)
