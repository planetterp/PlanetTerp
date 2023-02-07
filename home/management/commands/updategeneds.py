import requests
from datetime import datetime

from django.core.management import BaseCommand
from argparse import RawTextHelpFormatter

from home.models import Course, Gened
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
        self.geneds = Gened.objects.all()
        self.courses = Course.unfiltered.all()

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument("semester")

    def handle(self, *args, **options):
        start = datetime.now()
        num_updated_geneds = 0
        num_updated_courses = 0
        num_courses_skipped = 0

        semester = Semester(options['semester'])
        print(f"Updating geneds for {semester.name()}...")
        kwargs = {"semester": semester.number(), "per_page": 100, "page": 1}
        umdio_courses = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

        if isinstance(umdio_courses, dict) and 'error_code' in umdio_courses.keys():
            print(f"umd.io doesn't have data for {semester.name()}!")
            return

        while umdio_courses:
            # for every course on `page` of umdio...
            for umdio_course in umdio_courses:
                pt_course = self.courses.filter(name=umdio_course['course_id'].strip("\n\t\r ")).first()

                # if we doesn't have record of this course, skip it.
                # if num_courses_skipped > 1 you should run the course update script then
                # run this script again.
                if not pt_course:
                    num_courses_skipped += 1
                    continue

                print(pt_course.name)

                umdio_gened_str = str(umdio_course['gen_ed'])

                # if umdio doesn't have any geneds for this course,
                # make sure our records indicate this too, but using NULL
                # instead of an empty list.
                if umdio_gened_str == '[]':
                    pt_course.geneds = None
                    pt_course.save()
                    num_updated_courses += 1
                    continue

                # if course.geneds isn't up to date with umdio, update it.
                if pt_course.geneds != umdio_gened_str:
                    pt_course.geneds = umdio_gened_str
                    pt_course.save()
                    num_updated_courses += 1

                # create a list of all the umdio geneds for this course.
                # This list is considered the "correct" geneds for this course.
                umdio_geneds = []
                for gened_lst in umdio_course['gen_ed']:
                    for gened in gened_lst:
                        # To account for cases that have a pipe |, take the first 4
                        # characters of the gened value because geneds only have 4
                        # characters in their name
                        umdio_geneds.append(gened[:4])

                # if we have a gened linked to a course but umdio doesn't agree,
                # assume our records are outdated and delete this link. The intention
                # here is to update our records if a course no longer satisfies a gened.
                for g in self.geneds.filter(course=pt_course):
                    if g.name not in umdio_geneds:
                        g.delete()
                        num_updated_geneds += 1

                # if we don't have a gened for this course that umdio does have,
                # add it to our records.
                for gened in umdio_geneds:
                    if not self.geneds.filter(name=gened, course=pt_course).exists():
                        Gened(name=gened, course=pt_course).save()
                        num_updated_geneds += 1

            kwargs["page"] += 1
            umdio_courses = requests.get("https://api.umd.io/v1/courses", params=kwargs).json()

        runtime = datetime.now() - start
        print(f"geneds updated: {num_updated_geneds}")
        print(f"courses updated: {num_updated_courses}")
        print(f"courses skipped: {num_courses_skipped}")
        print(f"total runtime: {round(runtime.seconds / 60, 2)} minutes")
