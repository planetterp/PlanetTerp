from django.http.response import JsonResponse
from django.template.context_processors import csrf
from django.shortcuts import render
from django.views import View

from crispy_forms.utils import render_crispy_form

from home.forms.basic import HistoricCourseGradeForm, HistoricProfessorGradeForm
from home.views.data_sources import GradeData


class Grades(View):
    template_name = "grades.html"

    def get(self, request):
        context = {
            "course_form": HistoricCourseGradeForm(),
            "professor_form": HistoricProfessorGradeForm()
        }
        return render(request, self.template_name, context)

    def post(self, request):
        course = request.POST.get('course', None)
        semester = request.POST.get('semester', None)
        semester = semester if semester != '' else None
        pf_semesters = request.POST.get("pf_semesters", False) == "true"

        course_form = HistoricCourseGradeForm(course, semester, data=request.POST)
        professor_form = HistoricProfessorGradeForm(data=request.POST)

        ctx = {}
        ctx.update(csrf(request))
        context = {
            "course_search_success": False,
            "professor_search_success": False
        }

        if course is None and professor_form.is_valid():
            context["professor_search_success"] = True
            data = professor_form.cleaned_data
            professor = data.get("professor", None)
            context['professor_data'] = GradeData.compose_course_grade_data(professor, pf_semesters)

        if course is not None and course_form.is_valid():
            context["course_search_success"] = True
            data = course_form.cleaned_data
            professor = data.get("professor", None)
            course = data.get("course", None)
            semester = data.get("semester", None)
            section = data.get("section", None)
            context['course_data'] = GradeData.compose_grade_data(professor, course, semester, section, pf_semesters)

        context["professor_form"] = render_crispy_form(professor_form, professor_form.helper, context=ctx)
        context["course_form"] = render_crispy_form(course_form, course_form.helper, context=ctx)
        return JsonResponse(context)
