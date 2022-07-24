import datetime
import re

from django.shortcuts import redirect, render
from django.views import View
from django.http import HttpResponse

from home import model

class Schedule(View):
    template = "schedule_view.html"

    def get(self, request):
        data = request.GET

        if 'sections' in data:
            sections = data["sections"].split(",")

            if len(sections) > 8:
                return HttpResponse("Error: You can only select up to 8 courses.")

            user_sections = []
            for section in sections:
                if not section.isdigit():
                    return HttpResponse("Invalid section.")

                user_sections.append({'section_id': section})

        else:
            user_sections = model.get_user_schedule(request.session.get("id", None))
            if user_sections is None:
                return redirect('/schedule/new?no_saved_schedule=true')

        generated_schedules = []
        generated_schedule = []
        total_credits = 0
        index = 0

        for section in user_sections:
            section = section['section_id']
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

            schedule = {'schedule_index': 1, 'section_id': section, 'index': index,
                'title': temp_data[0]['title'], 'course': course, 'section': section_number,
                'meetings': meetings, 'professors': temp_data,
                'geneds': temp_data[0]['geneds'].replace(',', ', '), 'credits': temp_data[0]['credits'],
                'available_seats': temp_data[0]['available_seats'], 'seats': temp_data[0]['seats'],
                'waitlist': temp_data[0]['waitlist']}
            generated_schedule.append(schedule)
            index += 1

        generated_schedules.append(generated_schedule)

        schedule_sections = []
        for sched in generated_schedules:
            sections = [section['section_id'] for section in sched]
            schedule_sections.append(sections)

        request.session["generated_schedules"] = schedule_sections
        # HSL
        colors = [(203, 100, 50), (295, 100, 50), (30, 100, 50), (121, 35, 41),
            (348, 100, 63), (191, 100, 35), (249, 100, 78), (326, 100, 50)]

        context = {
            "schedules_html": render(request, "create_schedules.html", {"schedules": generated_schedule, "colors": colors}),
            "total_credits": total_credits,
            "saved_schedule": 'sections' not in data,
            "logged_in": request.session.get("logged_in", False)
        }

        return render(request, self.template, context)
