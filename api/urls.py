from django.urls import path

from api.views import (Docs, Meta, Course, Courses, Professor, Professors,
    Grades, Search)

urlpatterns = [
    path("", Docs.as_view(), name="api-docs"),
    path("v1", Meta.as_view(), name="api-meta"),
    path("v1/course", Course.as_view(), name="api-course"),
    path("v1/courses", Courses.as_view(), name="api-courses"),
    path("v1/professor", Professor.as_view(), name="api-professor"),
    path("v1/professors", Professors.as_view(), name="api-professors"),
    path("v1/grades", Grades.as_view(), name="api-grades"),
    path("v1/search", Search.as_view(), name="api-search")
]
