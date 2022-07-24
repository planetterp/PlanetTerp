import datetime
import json
import re

from django.shortcuts import redirect, render
from django.views import View
from django.http.response import HttpResponse

from home.models import Gened
from home import model
from home.views.schedule import schedule_helper
from home import queries


class NewSchedule(View):
    template = "schedule_new.html"

    def get(self, request):
        data = request.GET
        request.session["generated_schedules"] = []
        restrictions = []

        for restriction in request.session.get("restrictions", []):
            restrictions.append({'days': restriction['days'], 'start_time': datetime.datetime.strftime(restriction['start_time'], '%-I:%M %p'), 'end_time': datetime.datetime.strftime(restriction['end_time'], '%-I:%M %p')})
        if 'maxwaitlist' not in request.session:
            request.session['maxwaitlist'] = -1

        context = {
            "message": "",
            "saved_courses": request.session.get("courses", []),
            "saved_restrictions": restrictions,
            "saved_maxwaitlist": request.session.get("maxwaitlist", [])
        }

        if 'no_saved_schedule' in data and data["no_saved_schedule"] == "true":
            context["message"] = "no_saved_schedule"
            return render(request, self.template, context)

        if 'edit' in data and data["edit"] == 'true':
            context["message"] = "edit"
            return render(request, self.template, context)

        if 'sections' in data:
            sections = data["sections"].split(",")

            if not request.session.get("logged_in", False):
                return HttpResponse("<html>You must be logged in to save your schedule. <a href=\"/login\">Log in or create an account</a>.</html>")

            all_sections = list(model.get_all_sections())

            for section in sections:
                if not section.isdigit():
                    return HttpResponse("Error: Invalid section")

                found = False
                for s in all_sections:
                    if str(s['id']) == section:
                        found = True
                        break

                if not found:
                    return HttpResponse("Error: Invalid section")

            model.insert_user_sections(request.session.get("id", None), sections, True, "202101")
            return redirect('/schedule')

        if request.session.get("logged_in", False) and model.get_user_schedule(request.session.get("id", None)) is not None:
            context["message"] = "saved_schedule"
            return render(request, self.template, context)

        return render(request, self.template, context)

    def post(self, request):
        data = request.POST
        restrictions = []

        for restriction in request.session.get("restrictions", []):
            restrictions.append({'days': restriction['days'], 'start_time': datetime.datetime.strftime(restriction['start_time'], '%-I:%M %p'), 'end_time': datetime.datetime.strftime(restriction['end_time'], '%-I:%M %p')})

        if 'query' in data:
            results = []

            for gened in Gened.GENEDS:
                if data["query"].upper() in gened:
                    results.append({'label': gened, 'value': gened})

                    if len(results) == 3:
                        break

            num_results = 3 - len(results)
            search_results = queries.search(data["query"], num_results, courses=True)

            for result in search_results:
                results.append({'label': result['course'], 'value': result['course']})

            return json.dumps(results)

        if 'courses' not in data and not request.session.get("courses", []):
            return HttpResponse("Error: No courses inputted.")

        if 'courses' not in data:
            courses = request.session.get("courses", [])
        else:
            courses = data["courses"].split(",")
            request.session["courses"] = courses

        restrictions = []

        if 'restrictions' in data:
            restrictions_temp = data["restrictions"].split('<span class="time-wrapper">')

            restrictions_temp_error = []

            for restriction in restrictions_temp:
                restriction = restriction.replace('<span class="remove-time"><i class="fas fa-times-circle"></i></span></span></span>', "")
                restriction = restriction.split("<br>")[-1] # Remove '<span id="time-x"><br>'

                if restriction == "":
                    continue

                days = restriction.split(" ")[0]

                if not re.compile('^(M)?(Tu)?(W)?(Th)?(F)?$').match(days):
                    return HttpResponse("Error: Invalid restriction input.")

                restriction_data = ''.join(restriction.split(" ")[1:]).split("-")

                if len(restriction_data) > 2:
                    return HttpResponse("Error: Invalid restriction input.")

                start_time = restriction_data[0]
                end_time = restriction_data[1]

                restrictions_temp_error.append({'days': days, 'start_time': start_time, 'end_time': end_time})

                try:
                    start_time = datetime.datetime.strptime(start_time, "%I:%M%p")
                    end_time = datetime.datetime.strptime(end_time, "%I:%M%p")
                except ValueError:
                    return HttpResponse("Error: Invalid restriction input.")

                restrictions.append({'days': days, 'start_time': start_time, 'end_time': end_time})

            request.session["restrictions"] = restrictions


        if 'max-waitlist' in data:
            if data['max-waitlist'] == "":
                maxwaitlist = -1
            elif not data['max-waitlist'].isdigit() and data['max-waitlist'] != "-1":
                return HttpResponse("Error: Number not inputted for maximum waitlist size.")
            else:
                maxwaitlist = int(data['max-waitlist'])
        elif 'load_more' in data and data["load_more"] == 'true':
            maxwaitlist = request.session.get("maxwaitlist", [])
        else:
            maxwaitlist = -1

        request.session["maxwaitlist"] = maxwaitlist

        if len(courses) > 8:
            return HttpResponse("Error: You can only select up to 8 courses.")

        if 'load_more' not in data or data["load_more"] != 'true':
            request.session["generated_schedules"] = []

        schedule_sections = schedule_helper.generate_schedule(courses, request.session.get("restrictions", []), request.session.get("generated_schedules", []), request.session.get("maxwaitlist", []))
        context = {
            "message": None,
            "saved_courses": request.session.get("courses", []),
            "saved_restrictions": restrictions_temp_error,
            "saved_maxwaitlist": request.session.get("maxwaitlist", [])
        }

        if schedule_sections == -1 and 'load_more' in data and data["load_more"] == "true":
            return HttpResponse("<div class='alert alert-danger text-center error-alert'><strong>Error: </strong> No schedule found for those courses.</div>")
        elif schedule_sections == -1:
            context["message"] = "invalid_course"
            return render(request, self.template, context)
        elif schedule_sections == -2 and 'load_more' in data and data["load_more"] == "true":
            return HttpResponse("<div class='alert alert-danger text-center error-alert'><strong>Error: </strong> It took too long to find a valid schedule. Sorry. You can try again, or you can try using <a href='https://www.sis.umd.edu/bin/venus'>Venus</a>. Please also consider <a href='mailto:admin@planetterp.com'>contacting us</a> and letting us know which courses you're trying to search for.</div>")
        elif schedule_sections == -2:
            context["message"] = "timeout"
            return render(request, self.template, context)
        elif schedule_sections == -3:
            context["message"] = "invalid_section"
            return render(request, self.template, context)
        elif schedule_sections == -4:
            context["message"] = "waitlist"
            return render(request, self.template, context)
        elif schedule_sections == -5:
            context["message"] = "semester"
            return render(request, self.template, context)
        elif len(schedule_sections) == 0 and 'load_more' in data and data["load_more"] == "true":
            return HttpResponse("")
        elif len(schedule_sections) == 0:
            if any(course in Gened.GENEDS for course in courses):
                context["message"] = "no_schedules_gened"
                return render(request, self.template, context)
            else:
                context["message"] = "no_schedules"
                return render(request, self.template, context)

        generated_schedules = []
        schedule_index = len(request.session.get("generated_schedules", []))

        for sched in schedule_sections:
            generated_schedule = []

            index = 0
            total_credits = 0
            schedule_index += 1
            request.session.get("generated_schedules", []).append(sched)

            for section in sched:
                meetings_temp = list(model.get_meetings(section))
                meetings = []

                for meeting in meetings_temp:
                    if meeting['start_time'] == "" or meeting['end_time'] == "":
                        break

                    start_time = datetime.datetime.strptime(meeting['start_time'], "%I:%M%p")
                    end_time = datetime.datetime.strptime(meeting['end_time'], "%I:%M%p")
                    num_minutes = (end_time - start_time).total_seconds() / 60
                    num_minutes_since_8 = (start_time - datetime.datetime.strptime("08:00am", "%I:%M%p")).total_seconds() / 60

                    if not meeting['room']:
                        meeting['room'] = ""

                    meeting = {'start_time': meeting['start_time'],
                                'end_time': meeting['end_time'],
                                'num_minutes': num_minutes,
                                'num_minutes_since_8': num_minutes_since_8,
                                'location': meeting['building'] + meeting['room'],
                                'days': re.findall("M|Tu|W|Th|F", meeting['days']),
                                'type': meeting['type']}
                    meetings.append(meeting)

                temp_data = list(model.get_data_from_section(section))

                if len(temp_data) == 0:
                    return HttpResponse("Invalid section.")

                course = temp_data[0]['course']
                section_number = temp_data[0]['section_number']

                if not temp_data[0]['geneds']:
                    temp_data[0]['geneds'] = ""

                if temp_data[0]['credits']:
                    total_credits += temp_data[0]['credits']

                schedule = {'schedule_index': schedule_index, 'section_id': section, 'index': index,
                    'title': temp_data[0]['title'], 'course': course, 'section': section_number,
                    'meetings': meetings, 'professors': temp_data,
                    'geneds': temp_data[0]['geneds'].replace(',', ', '), 'credits':
                    temp_data[0]['credits'], 'available_seats': temp_data[0]['available_seats'],
                    'seats': temp_data[0]['seats'], 'waitlist': temp_data[0]['waitlist']}
                generated_schedule.append(schedule)
                index += 1

            generated_schedules.append(generated_schedule)

            schedule_sections = []
            for sched in generated_schedules:
                sections = []
                for section in sched:
                    sections.append(section['section_id'])

                schedule_sections.append(sections)

        colors = [(203, 100, 50), (295, 100, 50), (30, 100, 50), (121, 35, 41), (348, 100, 63), (191, 100, 35), (249, 100, 78), (326, 100, 50)] # HSL

        load_more_context = {
            "generated_schedules": generated_schedules,
            "colors": colors
        }
        if 'load_more' in data and data["load_more"] == "true":
            return render(request, "create_schedule.html", load_more_context)

        alt_context = {
            "schedules_html": render(request, "create_schedule.html", load_more_context),
            "total_credits": total_credits,
            "saved_schedule": False,
            "logged_in": request.session.get("logged_in", False)
        }
        return render(request, "schedule_view.html", alt_context)
