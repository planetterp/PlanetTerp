import re
import requests
from datetime import datetime

from django.core.management import BaseCommand
from argparse import RawTextHelpFormatter

from home.models import Course, Professor, ProfessorCourse, ProfessorAlias
from home.utils import Semester

class Command(BaseCommand):
    help = '''* NOTE: Updates the database with new courses and professors during the provided semester. The semester argument must be in the numerical form YEAR+SEASON.
        See below for the season codes:
            Spring -> 01
            Summer -> 05
            Fall -> 08
            Winter -> 12
        EXAMPLE: Spring 2023 = 202301
   '''

    def __init__(self):
        super().__init__()
        self.total_num_new_courses = 0
        self.total_num_new_professors = 0

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

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

                    print(course)
                    self._professors(course, semester)

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
            if re.search("instructor:?\s*tba", umdio_professor['name'].lower()):
                continue

            professors = Professor.verified.all()
            professor = Professor.unfiltered.exclude(status=Professor.Status.REJECTED).filter(name=umdio_professor['name'])

            if professor.count() == 1:
                professor = professor.first()
            else:
                aliases = ProfessorAlias.objects.filter(alias=umdio_professor['name'])
                if professor.count() > 1 and aliases.count() == 1:
                    professor = aliases.first()
                else:
                    # To make our lives easier, attempt to automatically verify the professor
                    # following a similar process to that in admin.py
                    professor = Professor(name=umdio_professor['name'], type=Professor.Type.PROFESSOR)
                    similar_professors = Professor.find_similar(professor.name, 70)
                    split_name = professor.name.strip().split()
                    new_slug = split_name[-1].lower()
                    valid_slug = True

                    if professors.filter(slug=new_slug).exists():
                        new_slug = f"{split_name[-1]}_{split_name[0]}".lower()
                        if professors.filter(slug=new_slug).exists():
                            valid_slug = False

                    if len(similar_professors) == 0 and valid_slug:
                        professor.slug = new_slug
                        professor.status = Professor.Status.VERIFIED

                    professor.save()
                    self.total_num_new_professors += 1

            for entry in umdio_professor['taught']:
                if entry['course_id'] == course.name and Semester(entry['semester']) == semester:
                    professorcourse = ProfessorCourse.objects.filter(
                        course=course,
                        professor=professor,
                        recent_semester=semester
                    ).first()

                    if not professorcourse:
                        ProfessorCourse.objects.create(course=course, professor=professor, recent_semester=semester)
                    elif professorcourse and not professorcourse.recent_semester:
                        professorcourse.recent_semester = semester
                    break
