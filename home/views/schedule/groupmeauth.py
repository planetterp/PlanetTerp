from home import model
import requests
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.views import View

class GroupMeAuth(View):
    template = "gropus.html"

    def get(self, request):
        data = request.POST

        if not request.session.get("logged_in", False):
            return HttpResponse("<html>Error: You must be logged in to authenticate with GroupMe. <a href='/login'>Log in or create an account</a>.</html>")

        if not 'access_token' in data:
            return redirect('https://oauth.groupme.com/oauth/authorize?client_id=DgS80vzpKvpVkKcYHFZ4d4meDObUCNJGHCVilHftlWIVvr9h')

        access_token = data["access_token"]

        if model.access_token_exists(access_token, request.session.get("id", None)):
            return HttpResponse("A user is already authenticated with that GroupMe account. Error? Please email us at admin@planetterp.com")

        username = requests.get("https://api.groupme.com/v3/users/me?token={}&omit=memberships&per_page=20".format(access_token)).json()['response']['name']

        if not model.user_already_authenticated(request.session.get("id", None)):
            model.insert_groupme_auth(request.session.get("id", None), username, access_token)

        groups = requests.get("https://api.groupme.com/v3/groups?token={}&omit=memberships&per_page=15".format(access_token)).json()['response']

        group_data = []

        for group in groups:
            group_id = group['group_id']
            group_name = group['name']

            group_data.append((group_id, group_name))

        context = {
            "groups": None,
            "group_users": None,
            "auth_group_data": group_data,
            "added_groups": None,
            "num_groups": None
        }

        if group_data:
            pass
            #TODO: figure out how to pass args to navbar
            #return render.groups(utils.navbar("groupme_auth"), render.footer(), None, None, group_data)
        else:
            pass
            #return render.groups(utils.navbar(), render.footer(), None, None, group_data)

        return render(request, self.template, context)

    def post(self, request):
        data = request.POST

        if not request.session.get("logged_in", False):
            return HttpResponse("Error: You must be logged in to authenticate with GroupMe.")

        access_token = model.get_access_token(request.session.get("id", None))

        groups = requests.get("https://api.groupme.com/v3/groups?token={}&omit=memberships&per_page=20".format(access_token)).json()['response']

        valid_groups = {}

        for group in groups:
            valid_groups[group['id']] = group['name']

        cnt = 0

        for group_id in data:
            if data[group_id] == 'on' and group_id in valid_groups:
                group_db_id = model.groupme_exists(group_id)

                if not group_db_id:
                    group_db_id = model.insert_groupme_group(group_id, valid_groups[group_id])

                if not model.user_is_in_group(request.session.get("id", None), group_db_id):
                    model.insert_groupme_user_group(request.session.get("id", None), group_db_id)

                    cnt += 1

        return redirect('/schedule/groups?groupme_auth_success=true&num_groups=' + str(cnt))
