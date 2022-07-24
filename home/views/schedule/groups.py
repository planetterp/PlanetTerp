from home import model
from django.shortcuts import redirect, render
from django.views import View

class Groups(View):
    template = "groups.html"

    def get(self, request):
        data = request.GET

        if not model.get_access_token(request.session.get("id", None)):
            return redirect('/schedule/groups/auth')

        groups = list(model.get_user_groups(request.session.get("id", None)))

        group_users = {}

        for group in groups:
            group_users[group.id] = model.get_group_users(group.id, request.session.get("id", None))

        context = {
            "groups": groups,
            "group_users": group_users,
            "auth_group_data": None,
            "added_groups": None,
            "num_groups": None
        }

        if 'groupme_auth_success' in data and data.groupme_auth_success == "true" and 'num_groups' in data and data["num_groups"].isdigit():
            context["added_groups"] = "added_groups"
            context["num_groups"] = data["num_groups"]

        return render(request, self.template, context)
