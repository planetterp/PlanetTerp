import datetime
import itertools
import random
import re
import time

from home import model
from home.models import Course


all_meetings = list(model.get_all_meetings())
meetings = {}
am_pm = ["am", "pm"]
times = {}

for h in am_pm:
    for hour in range(1, 13):
        for minute in range (0, 60):
            if minute < 10:
                minute = "0" + str(minute)
            times[str(hour) + ":" + str(minute) + str(h)] = datetime.datetime.strptime(str(hour) + ":" + str(minute) + str(h), "%I:%M%p")

def conflict_exists (sections, restrictions):
    monday_times = []
    tuesday_times = []
    wednesday_times = []
    thursday_times = []
    friday_times = []

    for time in restrictions:
        days = time['days']

        for day in re.findall("M|Tu|W|Th|F", days):
            if day == "M":
                monday_times.append({'start_time': time['start_time'], 'end_time': time['end_time'], 'section': 0})
            if day == "Tu":
                tuesday_times.append({'start_time': time['start_time'], 'end_time': time['end_time'], 'section': 0})
            if day == "W":
                wednesday_times.append({'start_time': time['start_time'], 'end_time': time['end_time'], 'section': 0})
            if day == "Th":
                thursday_times.append({'start_time': time['start_time'], 'end_time': time['end_time'], 'section': 0})
            if day == "F":
                friday_times.append({'start_time': time['start_time'], 'end_time': time['end_time'], 'section': 0})


    for section in sections:
        if not section in meetings:
            meetings[section] = []
            for meeting in all_meetings:
                if meeting['section_id'] == section:
                    meetings[section].append(meeting)

        for meeting in meetings[section]:
            days = re.findall("M|Tu|W|Th|F", meeting['days'])

            if meeting['start_time'] == "" or meeting['end_time'] == "":
                break

            start_time = times[meeting['start_time']]
            end_time = times[meeting['end_time']]

            start_and_end_time = {'section': section, 'start_time': start_time, 'end_time': end_time}

            for day in days:
                if day == "M":
                    for time in monday_times:
                        if section != time['section'] and ((start_time == time['start_time']) or (end_time == time['end_time']) or (start_time <= time['start_time'] and end_time >= time['start_time']) or (start_time >= time['start_time'] and start_time <= time['end_time'])):
                            return [section, time['section']]

                    monday_times.append(start_and_end_time)

                if day == "Tu":
                    for time in tuesday_times:
                        if section != time['section'] and ((start_time == time['start_time']) or (end_time == time['end_time']) or (start_time <= time['start_time'] and end_time >= time['start_time']) or (start_time >= time['start_time'] and start_time <= time['end_time'])):
                            return [section, time['section']]

                    tuesday_times.append(start_and_end_time)

                if day == "W":
                    for time in wednesday_times:
                        if section != time['section'] and ((start_time == time['start_time']) or (end_time == time['end_time']) or (start_time <= time['start_time'] and end_time >= time['start_time']) or (start_time >= time['start_time'] and start_time <= time['end_time'])):
                            return [section, time['section']]

                    wednesday_times.append(start_and_end_time)

                if day == "Th":
                    for time in thursday_times:
                        if section != time['section'] and ((start_time == time['start_time']) or (end_time == time['end_time']) or (start_time <= time['start_time'] and end_time >= time['start_time']) or (start_time >= time['start_time'] and start_time <= time['end_time'])):
                            return [section, time['section']]

                    thursday_times.append(start_and_end_time)

                if day == "F":
                    for time in friday_times:
                        if section != time['section'] and ((start_time == time['start_time']) or (end_time == time['end_time']) or (start_time <= time['start_time'] and end_time >= time['start_time']) or (start_time >= time['start_time'] and start_time <= time['end_time'])):
                            return [section, time['section']]

                    friday_times.append(start_and_end_time)

    return False


def generate_schedule(courses, restrictions, generated_schedules, maxwaitlist):
    t = time.time()
    data = {}

    all_sections = []

    geneds = ["FSAW", "FSAR", "FSMA", "FSOC", "FSPW", "DSHS", "DSHU", "DSNS", "DSNL", "DSSP", "DVCC", "DVUP", "SCIS"]

    course_ids = []

    for course in courses:
        is_gened = course in geneds

        if is_gened:
            course_data = {}
            course_data['id'] = model.get_random_gened_course(course)

            course_ids.append(course)
        else:
            course_no_parentheses = re.sub(r"\(.*\)", "", course)
            course_data = Course.objects.filter(name=course_no_parentheses).first()

            if course_data is None:
                return -1

            course_ids.append(course_data['id'])

        data[course] = {}
        data[course]['id'] = course_data['id']
        data[course]['sections'] = []

        course_sections = list(model.get_sections(course_data['id'], maxwaitlist))

        if len(course_sections) == 0:
            if len(model.get_sections(course_data['id'], -1)) == 0:
                return -5

            return -4

        if "(" in course and ")" in course:
            sections = course[course.find("(")+1:course.find(")")]

            for section in sections.split("|"):
                if bool(re.search('^[A-Z0-9]{4}$', section)):
                    found = False
                    for course_section in course_sections:
                        if section == course_section.section_number:
                            data[course]['sections'].append(course_section.id)
                            found = True
                            break

                    if not found:
                        return -3
                else:
                    return -1

            if len(data[course]['sections']) == 0:
                return -1
        else:
            for section in course_sections:
                data[course]['sections'].append(section.id)

        sections = data[course]['sections']

        if len(sections) > 0: # If course has at least one section this semester
            random.shuffle(sections)
            all_sections.append(sections)

    # all_sections.sort(key=len)
    possible_schedules = []

    conflicts = set()

    for possible_schedule in itertools.product(*all_sections):
        if any(c[0] in possible_schedule and c[1] in possible_schedule for c in conflicts):
            if time.time() - t > 15: # If it takes longer than 15 seconds to attempt to find a schedule, timeout
                if len(possible_schedules) != 0:
                    break

                total_time = time.time() - t
                if len(generated_schedules) == 0:
                    model.insert_created_schedule(total_time, course_ids, 3)

                return -2
            continue

        conflict = conflict_exists(possible_schedule, restrictions)
        if conflict is not False:
            if not any(sorted(conflict) == sorted(c) for c in conflicts): # Don't allow duplicates, regardless of order
                conflicts.add(tuple(conflict))

        if time.time() - t > 15: # If it takes longer than 15 seconds to attempt to find a schedule, timeout
            if len(possible_schedules) != 0:
                break

            total_time = time.time() - t
            if len(generated_schedules) == 0:
                model.insert_created_schedule(total_time, course_ids, 3)

            return -2

        if conflict is False and not any(set(schedule) == set(possible_schedule) for schedule in generated_schedules):
            possible_schedules.append(possible_schedule)
            if len(possible_schedules) == 10:
                total_time = time.time() - t

                if len(generated_schedules) == 0:
                    model.insert_created_schedule(total_time, course_ids, 1)

                return possible_schedules

    total_time = time.time() - t
    # Only insert generated schedule if it's from a new search
    # (i.e., not loading more results from a previous search)
    if len(generated_schedules) == 0:
        if len(possible_schedules) == 0:
            model.insert_created_schedule(total_time, course_ids, 2)
        else:
            model.insert_created_schedule(total_time, course_ids, 1)

    return possible_schedules
