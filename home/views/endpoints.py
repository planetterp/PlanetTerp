from django.http import JsonResponse
from django.views import View
from django.http import Http404

from home import queries
from home.models import Professor, ProfessorCourse

class Autocomplete(View):
    def get(self, request):
        data = request.GET
        
        if "query" not in data:
            raise Http404()
        
        query = data["query"]
        types = data.getlist("types[]")
        professors = "professor" in types
        courses = "course" in types
        return_attrs = data.getlist("return_attrs[]")
        search_results = queries.search(query, 10, professors=professors,
            courses=courses)
        results = []

        departments = {}
        if "departments" in return_attrs:
            professor_ids = [result.pk for result in search_results if isinstance(result, Professor)]
            rows = (
                ProfessorCourse.objects
                .filter(professor_id__in=professor_ids)
                .values_list("professor_id", "course__department")
                .order_by("course__department")
                .distinct()
            )
            for professor_id, department in rows:
                departments.setdefault(professor_id, []).append(department)

        for result in search_results:
            value_dict = {}
            if "url" in return_attrs:
                value_dict['url'] = result.get_absolute_url()
            if "pk" in return_attrs:
                value_dict["pk"] = result.pk
            if "name" in return_attrs:
                value_dict['name'] = result.name
            if "departments" in return_attrs and isinstance(result, Professor):
                value_dict['departments'] = departments.get(result.pk, [])

            data = {
                "label": f"{result}" if request.user.has_perm("home.mod") else f"{result.name}",
                "result": value_dict
            }

            results.append(data)

        return JsonResponse(results, safe=False)
