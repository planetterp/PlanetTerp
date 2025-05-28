import re

from django.shortcuts import redirect, render
from django.views import View
from django.http import HttpResponse

from home.models import Course
from home import queries

class Search(View):
    def get(self, request):
        data = request.GET

        if 'query' not in data:
            return HttpResponse("Invalid search query.")

        query = data["query"]

        if query == "":
            context = {"results": []}
            return render(request, "search.html", context)

        if any(character.isdigit() for character in query):
            query = query.replace(" ", "")

        query = re.sub(r"\s+", " ", query).strip()

        results = queries.search(query, 30, courses=True, professors=True)

        if len(results) == 1:
            result = results[0]
            return redirect(result)

        # send searches directly to a course's page instead of a disambiguation
        # page if the search matches exactly
        if results:
            result = results[0]
            if isinstance(result, Course) and result.name.upper() == query.upper():
                return redirect(result)

        context = {
            "results": results
        }
        return render(request, "search.html", context)
