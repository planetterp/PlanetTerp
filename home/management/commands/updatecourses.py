import requests

from django.core.management import BaseCommand
from django.db.models import Q

from home.models import Course, Professor
from home.utils import Semester

class Command(BaseCommand):
    def __init__(self):
        super().__init__()
        self.num_new_courses = 0
        self.num_new_professors = 0

    def add_arguments(self, parser):
        parser.add_argument("semesters", nargs='+')

    def handle(self, *args, **options):
        for semester in options['semesters']:
            s = Semester(semester)
            if Semester.current() < s:
                print(f"{s.name()} hasn't happened yet! Skipping...")
                continue

            print(f"Working on data for {s.name()}...")
            kwargs = {"semester": semester, "per_page": 100, "page": 1}
            course_data = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()
            while course_data:
                for item in course_data:
                    course = Course.unfiltered.filter(name=item['course_id']).first()
                    if not course:
                        course = Course(
                            name=item['course_id'],
                            department=item['dept_id'],
                            course_number=item['course_id'][4:],
                            title=item['name'],
                            credits=item['credits'],
                            description=self._description(item["relationships"])
                        )

                        course.save()
                        self.num_new_courses += 1
                        print(f"Created course {course.name}")

                    professors = self._professors(course)
                    course.professors.add(*professors)

                kwargs["page"] += 1
                course_data = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

        print(f"\nNew Courses Created: {self.num_new_courses}")
        print(f"New Professors Created: {self.num_new_professors}")

    def _professors(self, course):
        ret = []
        kwargs = {"course_id": course.name}
        professor_data = requests.get("https://api.umd.io/v1/professors", params=kwargs).json()

        for item in professor_data:
            try:
                professor = Professor.unfiltered.filter(name=item['name']).first()
            except Exception:
                continue

            if item['name'] == "Instructor: TBA":
                continue

            if not professor:
                # To make our lives easier, attempt to automatically verify the professor
                # following the same criteria in admin.py
                split_name = item['name'].strip().split(" ")
                first_name = split_name[0].lower().strip()
                last_name = split_name[-1].lower().strip()
                query = Professor.verified.filter(
                    (
                        Q(name__istartswith=first_name) &
                        Q(name__iendswith=last_name)
                    ) |
                    Q(slug="_".join(reversed(split_name)).lower())
                )

                professor = Professor(name=item['name'], type=Professor.Type.PROFESSOR)

                if not query.exists() and len(split_name) < 2:
                    professor.slug = "_".join(reversed(split_name)).lower()
                    professor.verified = Professor.Status.VERIFIED

                professor.save()
                self.num_new_professors += 1
                print(f"Created professor {professor.name} for {course.name}")

            ret.append(professor)

        return ret

    def _description(self, relationships):
        mappings = {
            "prereqs": "\n<b>Prerequisite:</b> ",
            "coreqs": "\n<b>Corequisite:</b> ",
            "restrictions": "\n<b>Restriction:</b> ",
            "formerly": "\n<b>Formerly:</b> ",
            "credit_granted_for": "\n<b>Credit only granted for:</b> ",
            "additional_info": "\n<b>Additional information:</b> "
        }
        description = "".join([mappings[key] + relationships[key] for key in mappings.keys() if relationships[key]])
        return description
