from django.http import JsonResponse
from django.views import View

from home import queries

class Autocomplete(View):
    def get(self, request):
        data = request.GET
        query = data["query"]
        types = data.getlist("types[]")
        professors = "professor" in types
        courses = "course" in types
        return_attrs = data.getlist("return_attrs[]")
        search_results = queries.search(query, 10, professors=professors,
            courses=courses)
        results = []

        for result in search_results:
            value_dict = {}
            if "url" in return_attrs:
                value_dict['url'] = result.get_absolute_url()
            if "pk" in return_attrs:
                value_dict["pk"] = result.pk
            if "name" in return_attrs:
                value_dict['name'] = result.name

            data = {
                "label": f"{result}" if request.user.is_staff else f"{result.name}",
                "result": value_dict
            }

            results.append(data)

        return JsonResponse(results, safe=False)
