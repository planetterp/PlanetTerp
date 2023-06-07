import re
import requests
from datetime import datetime

from django.core.management import BaseCommand

from home.models import Course, Professor, ProfessorCourse, ProfessorAlias
from home.utils import Semester

class Command(BaseCommand):
    help = (
        "Updates the database with any new professors, courses, and "
        "ProfessorCourse relations."
    )

    def __init__(self):
        super().__init__()
        self.total_num_new_courses = 0
        self.total_num_new_professors = 0
        self.verified_professors = Professor.verified.all()
        self.non_rejected_professors = Professor.unfiltered.exclude(status=Professor.Status.REJECTED)
        self.aliases = ProfessorAlias.objects.all()
        self.professor_courses = ProfessorCourse.objects.all()

    def handle(self, *args, **options):
        t_start = datetime.now()
        self.update_and_link_professors()

        print(f"\n** New Courses Created: {self.total_num_new_courses} **")
        print(f"** New Professors Created: {self.total_num_new_professors} **")
        runtime = datetime.now() - t_start
        print(f"Runtime: {round(runtime.seconds / 60, 2)} minutes")

    def update_and_link_professors(self):
        kwargs = {"per_page": 100, "page": 1}
        umdio_professors = requests.get("https://api.umd.io/v1/professors", params=kwargs).json()

        last_professor = ""
        while umdio_professors:
            for umdio_professor in umdio_professors:
                professor_name = umdio_professor['name'].strip("\n\t\r ")

                # skip placeholder professors
                if re.search("instructor:?\s*tba", professor_name.lower()):
                    continue

                print(" "*len(last_professor), end='\r')
                print(professor_name, end='\r')
                last_professor = professor_name

                professor = self.non_rejected_professors.filter(name=professor_name)
                alias = self.aliases.filter(alias=professor_name)

                # if there's only one matching professor, use that professor.
                if professor.count() == 1:
                    professor = professor.first()

                # if there are no matching professors but we have an alias
                # for this name, use the professor associated with that alias.
                elif professor.count() == 0 and alias.exists():
                    professor = alias.first().professor

                # Otherwise, we either don't recognize this professor or there is
                # more than one professor with this exact same name. So we create a
                # new professor and attempt to automatically verify it following
                # a process similar to that in views/admin.py.
                else:
                    professor = Professor(name=professor_name, type=Professor.Type.PROFESSOR)
                    similar_professors = Professor.find_similar(professor.name, 70)
                    split_name = professor.name.strip().split()
                    new_slug = split_name[-1].lower()
                    valid_slug = True

                    # Try the lastname
                    if self.verified_professors.filter(slug=new_slug).exists():
                        # If that exists, try lastname_firstname
                        new_slug = f"{split_name[-1]}_{split_name[0]}".lower()
                        if self.verified_professors.filter(slug=new_slug).exists():
                            # If that exists, this professor will be waiting for us in the admin panel
                            valid_slug = False

                    # if there are no similarly named professors and there's no
                    # issues with the auto generated slug, verify the professor.
                    if len(similar_professors) == 0 and valid_slug:
                        professor.slug = new_slug
                        professor.status = Professor.Status.VERIFIED

                    professor.save()
                    self.total_num_new_professors += 1

                # for every course taught by `professor`...
                for course in umdio_professor['taught']:
                    clean_semester = course['semester'].strip("\n\t\r ")
                    clean_course_name = course['course_id'].strip("\n\t\r ")
                    pt_course = self.get_or_create_course(clean_course_name, clean_semester)

                    # get all professorcourse entries that match the professor and course
                    professorcourse = self.professor_courses.filter(
                        course=pt_course,
                        professor=professor
                    )

                    semester_taught = Semester(clean_semester)
                    # if only one professorcourse record and it doesn't
                    # have a recent semester, update that one record.
                    if professorcourse.count() == 1 and not professorcourse.first().semester_taught:
                        professorcourse.update(semester_taught=semester_taught)

                    # if there's no professorcourse entries at all that match
                    # the prof/course combo or if there are matching records but
                    # none of them have recent semester = `semester`, create a new
                    # professor course entry.
                    elif professorcourse.count() == 0 or not professorcourse.filter(semester_taught=semester_taught).exists():
                        ProfessorCourse.objects.create(course=pt_course, professor=professor, semester_taught=semester_taught)

            kwargs["page"] += 1
            umdio_professors = requests.get("https://api.umd.io/v1/professors", params=kwargs).json()

    def get_or_create_course(self, course_name, semester):
        # get the course if we have the course
        course = Course.unfiltered.filter(name=course_name).first()
    def umdio_to_pt_course(self, umdio_course):
        course_name = umdio_course['course_id'].strip("\n\t\r ")

        return Course(
            name=course_name,
            department=umdio_course['dept_id'].strip("\n\t\r "),
            course_number=course_name[4:],
            title=umdio_course['name'].strip("\n\t\r "),
            credits=umdio_course['credits'].strip("\n\t\r "),
            description=umdio_course["description"].strip("\n\t\r ")
        )

        # if we don't have the course...
        if not course:
            # create a new course using the course info from umdio
            request_url = f"https://api.umd.io/v1/courses/{course_name}"
            umdio_course = requests.get(request_url, params={"semester": semester}).json()[0]

            course = self.umdio_to_pt_course(umdio_course)
            course.save()

            self.total_num_new_courses += 1

        return course
