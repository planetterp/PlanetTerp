import re
import requests
from datetime import datetime

from django.core.management import BaseCommand
from argparse import RawTextHelpFormatter

from home.models import Course, Professor, ProfessorCourse, ProfessorAlias
from home.utils import Semester

class Command(BaseCommand):
    help = '''Updates the database with new courses and professors during the provided semester.
    The semester argument must be in the numerical form YEAR+SEASON (see ** for exception).
    The season codes are as follows:
        Spring -> 01
        Summer -> 05
         Fall  -> 08
        Winter -> 12
    EXAMPLE: Spring 2023 = 202301

    ** NOTE: Starting from Winter 2021, the values for winter semesters are off by one year. Winter 2021 is actually 202012, not 202112
   '''

    def __init__(self):
        super().__init__()
        self.total_num_new_courses = 0
        self.total_num_new_professors = 0
        self.courses = Course.unfiltered.all()
        self.verified_professors = Professor.verified.all()
        self.non_rejected_professors = Professor.unfiltered.exclude(status=Professor.Status.REJECTED)
        self.aliases = ProfessorAlias.objects.all()
        self.professor_courses = ProfessorCourse.objects.all()

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

            # if no courses were found during semester, skip.
            if "error_code" in course_data.keys():
                print(f"umd.io doesn't have data for {semester.name()}!")
                continue

            print(f"Working on courses for {semester.name()}...")

            while course_data:
                # for every course taught during `semester`...
                for umdio_course in course_data:
                    course = self.courses.filter(name=umdio_course['course_id'].strip("\n\t\r ")).first()

                    # if we don't have the course, create it.
                    if not course:
                        course = Course(
                            name=umdio_course['course_id'].strip("\n\t\r "),
                            department=umdio_course['dept_id'].strip("\n\t\r "),
                            course_number=umdio_course['course_id'].strip("\n\t\r ")[4:],
                            title=umdio_course['name'].strip("\n\t\r "),
                            credits=umdio_course['credits'].strip("\n\t\r "),
                            description=umdio_course["description"].strip("\n\t\r ")
                        )

                        course.save()
                        self.total_num_new_courses += 1

                    print(course)
                    # collect all the professors that taught this course during `semester`
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

        # if no professors were found for `course`, exit function.
        if isinstance(umdio_professors, dict) and 'error_code' in umdio_professors.keys():
            return

        # for every professor that taught `course`...
        for umdio_professor in umdio_professors:
            professor_name = umdio_professor['name'].strip("\n\t\r ")
            if re.search("instructor:?\s*tba", professor_name.lower()):
                continue

            professor = self.non_rejected_professors.filter(name=professor_name)
            alias = self.aliases.filter(alias=professor_name)

            # if there's only one matching professor, use that professor.
            if professor.count() == 1:
                professor = professor.first()

            # if there's more than one matching professor but
            # we have an alias that narrows the query down to one,
            # use the professor associated with that alias.
            elif professor.count() > 1 and alias.count() == 1:
                professor = alias.first()

            # Otherwise, we either don't have this professor or we couldn't
            # narrow down the query enough. So, create a new professor and
            # attempt to automatically verify it following a process similar
            # to that in admin.py.
            else:
                professor = Professor(name=professor_name, type=Professor.Type.PROFESSOR)
                similar_professors = Professor.find_similar(professor.name, 70)
                split_name = professor.name.strip().split()
                new_slug = split_name[-1].lower()
                valid_slug = True

                if self.verified_professors.filter(slug=new_slug).exists():
                    new_slug = f"{split_name[-1]}_{split_name[0]}".lower()
                    if self.verified_professors.filter(slug=new_slug).exists():
                        valid_slug = False

                # if there are no similarly named professors and there's no
                # issues with the auto generated slug, verify the professor.
                if len(similar_professors) == 0 and valid_slug:
                    professor.slug = new_slug
                    professor.status = Professor.Status.VERIFIED

                professor.save()
                self.total_num_new_professors += 1

            # for every course taught by `professor`...
            for entry in umdio_professor['taught']:
                # we only care about `course` taught during `semester`.
                if entry['course_id'] == course.name and Semester(entry['semester']) == semester:
                    professorcourse = self.professor_courses.filter(
                        course=course,
                        professor=professor
                    )

                    # if only one professorcourse record and it doesn't
                    # have a recent semester, update that one record.
                    if professorcourse.count() == 1 and not professorcourse.first().recent_semester:
                        professorcourse.update(recent_semester=semester)

                    # if there's no professorcourse entries at all that match
                    # the prof/course combo or if there are matching records but
                    # none of them have recent semester = `semester`, create a new
                    # professor course entry.
                    elif professorcourse.count() == 0 or not professorcourse.filter(recent_semester=semester).exists():
                        ProfessorCourse.objects.create(course=course, professor=professor, recent_semester=semester)
                    break
