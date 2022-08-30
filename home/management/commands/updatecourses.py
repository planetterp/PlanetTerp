import requests
import json

from django.core.management import BaseCommand, CommandError

from home.models import Course, Professor

class Command(BaseCommand):
    def __init__(self):
        super().__init__()
        self.num_new_courses = 0
        self.num_new_professors = 0

    def add_arguments(self, parser):
        parser.add_argument("semesters", nargs='+')

    def handle(self, *args, **options):
        for semester in options['semesters']:
            response = requests.get("https://api.umd.io/v1/courses", params={"semester": semester})
            course_data = json.loads(response.content)
            for item in course_data:
                course = Course.unfiltered.filter(name=item['course_id']).first()
                if not course:
                    course = Course(
                        name=item['course_id'],
                        department=item['dept_id'],
                        course_number=item['course_id'][-3:],
                        title=item['name'],
                        credits=item['credits'],
                        description=self._description(item["relationships"])
                    )

                    course.save()
                    self.num_new_courses += 1
                    print(f"Created course {course.name}")

                professors = self._professors(course)
                course.professors.add(*professors)


        print(f"New Courses Added: {self.num_new_courses}")
        print(f"New Professors Added: {self.num_new_professors}")

    def _professors(self, course):
        ret = []
        response = requests.get("https://api.umd.io/v1/professors", params={"course_id":course.name})
        professor_data = json.loads(response.content)

        for item in professor_data:
            print(item)
            professor = Professor.unfiltered.filter(name=item['name']).first()
            if not professor:
                professor = Professor(name=item['name'], type=Professor.Type.PROFESSOR)
                professor.save()
                self.num_new_professors += 1
                print(f"  Created professor {professor.name}")


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
