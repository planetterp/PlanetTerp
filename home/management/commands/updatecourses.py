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

    def handle(self, *args, **options):
        t_start = datetime.now()

        self.update_courses()
        self.update_and_link_professors()

        print(f"\n** New Courses Created: {self.total_num_new_courses} **")
        print(f"** New Professors Created: {self.total_num_new_professors} **")
        runtime = datetime.now() - t_start
        print(f"Runtime: {round(runtime.seconds / 60, 2)} minutes")

    def update_courses(self):
        print("Updating courses...")
        # progressively build a list of Courses we don't have then bulk create
        # them at the end.
        courses_to_create = []

        #TODO: use semester comparator when that gets fixed
        kwargs = {"per_page": 100, "page": 1}
        umdio_courses = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

        last_course = ""
        while umdio_courses:
            for umdio_course in umdio_courses:
                course_name = umdio_course['course_id'].strip("\n\t\r ")

                # print enough spaces to overwrite the last printed course
                print(" "*len(last_course), end='\r')
                print(course_name, end='\r')
                last_course = course_name

                # if we don't have the course, store it to create later
                if not Course.unfiltered.filter(name=course_name).exists():
                    courses_to_create.append(self.umdio_to_pt_course(umdio_course))

            kwargs["page"] += 1
            umdio_courses = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

        courses_created = Course.unfiltered.bulk_create(courses_to_create)
        self.total_num_new_courses += len(courses_created)

    def update_and_link_professors(self):
        print("Updating professors...")
        kwargs = {"per_page": 100, "page": 1}
        umdio_professors = requests.get("https://api.umd.io/v1/professors", params=kwargs).json()

        last_professor = ""
        while umdio_professors:
            for umdio_professor in umdio_professors:
                professor_name = self.clean_professor_name(umdio_professor['name'])

                if not professor_name:
                    continue

                # print enough spaces to overwrite the last printed name
                print(" "*len(last_professor), end='\r')
                print(professor_name, end='\r')
                last_professor = professor_name

                # all professors who are either pending or verified
                professor = (Professor.unfiltered
                            .exclude(status=Professor.Status.REJECTED)
                            .filter(name=professor_name))
                alias = ProfessorAlias.objects.filter(alias=professor_name)

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

                    verified_professors = Professor.verified.all()

                    # Try the lastname
                    if verified_professors.filter(slug=new_slug).exists():
                        # If that exists, try lastname_firstname
                        new_slug = f"{split_name[-1]}_{split_name[0]}".lower()
                        if verified_professors.filter(slug=new_slug).exists():
                            # If that exists, this professor will be waiting for us in the admin panel
                            valid_slug = False

                    # if there are no similarly named professors and there's no
                    # issues with the auto generated slug, verify the professor.
                    if len(similar_professors) == 0 and valid_slug:
                        professor.slug = new_slug
                        professor.status = Professor.Status.VERIFIED

                    professor.save()
                    self.total_num_new_professors += 1

                self.link_professor_to_courses(professor, umdio_professor['taught'])

            kwargs["page"] += 1
            umdio_professors = requests.get("https://api.umd.io/v1/professors", params=kwargs).json()

    def clean_professor_name(self, name):
        # get rid of unwanted characters anywhere in the name
        professor_name = (name.replace('/', '-')
                            .replace('\n', '')
                            .replace('\r', '')
                            .replace('\t', '')
                        )

        # skip placeholder professors
        if re.search("instructor:?\s*tba", professor_name):
            return None

        return professor_name

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

    def get_or_create_course(self, course_name, semester):
        try:
            # try to get the course
            course = Course.unfiltered.get(name=course_name)
        except Course.DoesNotExist:
            # if we don't have the course, create it using the info from umdio
            request_url = f"https://api.umd.io/v1/courses/{course_name}"
            umdio_course = requests.get(request_url, params={"semester": semester}).json()[0]

            course = self.umdio_to_pt_course(umdio_course)
            course.save()

            self.total_num_new_courses += 1

        return course

    def link_professor_to_courses(self, professor, courses):
        for course in courses:
            semester = course['semester'].strip("\n\t\r ")
            course_name = course['course_id'].strip("\n\t\r ")

            pt_course = self.get_or_create_course(course_name, semester)

            # get all professorcourse entries that match the professor and course
            professorcourse = ProfessorCourse.objects.filter(
                course=pt_course,
                professor=professor
            )

            semester_taught = Semester(semester)
            # if only one professorcourse record and it doesn't
            # have a recent semester, update that one record.
            if professorcourse.count() == 1 and not professorcourse.first().semester_taught:
                professorcourse.update(semester_taught=semester_taught)

            # if there's no professorcourse entries at all that match
            # the prof/course combo or if there are matching records but
            # none of them have recent semester = `semester`, create a new
            # professor course entry.
            elif professorcourse.count() == 0 or not professorcourse.filter(semester_taught=semester_taught).exists():
                ProfessorCourse.objects.create(
                    course=pt_course,
                    professor=professor,
                    semester_taught=semester_taught
                )
