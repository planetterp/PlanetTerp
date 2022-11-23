import requests
from datetime import datetime

from django.core.management import BaseCommand

from home.models import Course, Professor, ProfessorCourse
from home.utils import Semester

class Command(BaseCommand):
    def __init__(self):
        super().__init__()
        self.total_num_new_courses = 0
        self.total_num_new_professors = 0

    def add_arguments(self, parser):
        parser.add_argument("semesters", nargs='+')

    def handle(self, *args, **options):
        t_start = datetime.now()
        semesters = [Semester(s) for s in options['semesters']]
        print(f"Inputted Semesters: {', '.join(s.name() for s in semesters)}")

        for semester in semesters:
            kwargs = {"semester": semester, "per_page": 100, "page": 1}
            course_data = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

            if "error_code" in course_data[0].keys():
                print(f"umd.io doesn't have data for {semester.name()}!")
                continue

            print(f"Working on courses for {semester.name()}...")

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
                            description=umdio_course["description"]
                        )

                        course.save()
                        self.total_num_new_courses += 1

                    self._professors(course, semester)
                    print(course)

                kwargs["page"] += 1
                course_data = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

        print(f"\n** New Courses Created: {self.total_num_new_courses} **")
        print(f"** New Professors Created: {self.total_num_new_professors} **")

        runtime = datetime.now() - t_start
        print(f"Runtime: {round(runtime.seconds / 60, 2)} minutes")

    def _professors(self, course: Course, semester: Semester):
        kwargs = {"course_id": course.name}
        umdio_professors = requests.get("https://api.umd.io/v1/professors", params=kwargs).json()

        # if no professors were found for `course` during `semester`
        if isinstance(umdio_professors, dict) and 'error_code' in umdio_professors.keys():
            return

        for umdio_professor in umdio_professors:
            if umdio_professor['name'] == "Instructor: TBA":
                continue

            professor = Professor.verified.filter(name=umdio_professor['name']).first()

            if not professor:
                # To make our lives easier, attempt to automatically verify the professor
                # following the same criteria in admin.py
                split_name = umdio_professor['name'].strip().split()
                similar_professors = Professor.find_similar(professor.name, 70)
                split_name = str(professor.name).strip().split(" ")
                new_slug = "_".join(reversed(split_name)).lower()

                professor = Professor(name=umdio_professor['name'], type=Professor.Type.PROFESSOR)

                if len(similar_professors) == 0 and not Professor.verified.filter(slug=new_slug).exists():
                    professor.slug = "_".join(reversed(split_name)).lower()
                    professor.status = Professor.Status.VERIFIED

                professor.save()
                self.total_num_new_professors += 1

            for entry in umdio_professor['taught']:
                if entry['course_id'] == course.name and Semester(entry['semester']) == semester:
                    ProfessorCourse.objects.create(course=course, professor=professor, recent_semester=semester)
                    break
