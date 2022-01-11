from django.urls import path

from api.views import (Docs, Meta, Course, Courses, Professor, Professors,
    Grades, Search)

urlpatterns = [
    path("", Docs.as_view()),
    path("v1", Meta.as_view()),
    path("v1/course", Course.as_view()),
    path("v1/courses", Courses.as_view()),
    path("v1/professor", Professor.as_view()),
    path("v1/professors", Professors.as_view()),
    path("v1/grades", Grades.as_view()),
    path("v1/search", Search.as_view())
]
