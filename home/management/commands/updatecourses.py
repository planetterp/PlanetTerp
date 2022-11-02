import requests

from django.core.management import BaseCommand
from django.db.models import Q

from home.models import Course, Professor
from home.utils import Semester

class Command(BaseCommand):
    def __init__(self):
        super().__init__()
        self.total_num_new_courses = 0
        self.total_num_new_professors = 0

    def add_arguments(self, parser):
        parser.add_argument("semesters", nargs='+')

    def handle(self, *args, **options):
        inputted_semesters = [Semester(s).name() for s in options['semesters']]
        print(f"Inputted Semesters: {', '.join(inputted_semesters)}")

        for semester in options['semesters']:
            s = Semester(semester)
            kwargs = {"semester": semester, "per_page": 100, "page": 1}
            course_data = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

            if course_data["error_code"]:
                print(f"{s.name()} hasn't happened yet! Skipping...")
                continue

            print(f"Working on courses for {s.name()}...")

            while course_data:
                for umdio_course in course_data:
                    course = Course.unfiltered.filter(name=umdio_course['course_id']).first()

                    if not course:
                        course = Course(
                            name=umdio_course['course_id'],
                            department=umdio_course['dept_id'],
                            course_number=umdio_course['course_id'][4:],
                            title=umdio_course['name'],
                            credits=umdio_course['credits'],
                            additional_info=umdio_course['relationships']['additional_info'],
                            cross_listed_with=umdio_course['relationships']['also_offered_as'],
                            credit_granted_for=umdio_course['relationships']['credit_granted_for'],
                            formerly=umdio_course['relationships']['formerly'],
                            prereqs=umdio_course['relationships']['prereqs'],
                            #recs=umdio_course['relationships']['recs'], # TODO: check name after umdio gets updated
                            coreqs=umdio_course['relationships']['coreqs'],
                            restrictions=umdio_course['relationships']['restrictions'],
                            # TODO: Add new field when umdio gets updated
                            description=umdio_course["description"]
                        )

                        course.save()
                        self.total_num_new_courses += 1
                        print(f"Created course {course.name}")

                    self._professors(course)

                kwargs["page"] += 1
                course_data = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

        print(f"\n** New Courses Created: {self.total_num_new_courses} **")
        print(f"** New Professors Created: {self.total_num_new_professors} **")

    def _professors(self, course: Course):
        new_professors = set()
        kwargs = {"course_id": course.name}
        umdio_professors = requests.get("https://api.umd.io/v1/professors", params=kwargs).json()
        course_professors = course.professors.all()

        for umdio_professor in umdio_professors:
            try:
                professor = Professor.unfiltered.filter(name=umdio_professor['name']).first()
            except TypeError:
                continue

            if umdio_professor['name'] == "Instructor: TBA":
                continue

            if not professor:
                # To make our lives easier, attempt to automatically verify the professor
                # following the same criteria in admin.py
                split_name = umdio_professor['name'].strip().split()
                first_name = split_name[0].lower().strip()
                last_name = split_name[-1].lower().strip()
                query = Professor.verified.filter(
                    (
                        Q(name__istartswith=first_name) &
                        Q(name__iendswith=last_name)
                    ) |
                    Q(slug="_".join(reversed(split_name)).lower())
                )

                prof_name = " ".join([name.capitalize() for name in umdio_professor['name'].split()])
                professor = Professor(name=prof_name, type=Professor.Type.PROFESSOR)

                if (not query.exists()) and len(split_name) <= 2:
                    professor.slug = "_".join(reversed(split_name)).lower()
                    professor.status = Professor.Status.VERIFIED

                professor.save()
                self.total_num_new_professors += 1
                print(f"Created professor {professor.name} for {course.name}")

            if professor not in course_professors:
                new_professors.add(professor)

        num_new_professors = len(new_professors)
        if num_new_professors > 0:
            print(f"Updated course {course.name} with {num_new_professors} new {'professors' if num_new_professors > 0 else 'professor'}")
            course.professors.add(*new_professors)
