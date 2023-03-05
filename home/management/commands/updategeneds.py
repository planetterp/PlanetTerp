import requests
from datetime import datetime

from django.core.management import BaseCommand
from argparse import RawTextHelpFormatter

from home.models import Course, Gened

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

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.num_geneds_updated = 0

    def create_parser(self, *args, **kwargs):
        # to format the help text that gets displayed with the -h option
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def handle(self, *args, **options):
        start = datetime.now()
        pt_courses = Course.unfiltered.all()

        # for each of our courses...
        for pt_course in pt_courses:
            # see if umdio has this course
            umdio_course = requests.get(f"https://api.umd.io/v1/courses/{pt_course.name}").json()

            # if umdio does not have this course continue to the next course
            if isinstance(umdio_course, dict) and 'error_code' in umdio_course.keys():
                print(f"umd.io doesn't have {pt_course.name}")
                continue

            print(pt_course.name)
            self.update_course_table(pt_course, umdio_course)
            self.update_geneds_table(pt_course, umdio_course)

        runtime = datetime.now() - start
        print(f"number of geneds updated: {self.num_geneds_updated}")
        print(f"total runtime: {round(runtime.seconds / 60, 2)} minutes")

    def update_course_table(self, pt_course, umdio_course):
        # umdio uses an empty list if a course has no geneds but
        # we want to use null because that's what our schema is expecting.
        if not umdio_course['gen_ed']:
            pt_course.geneds = None
        else:
            pt_course.geneds = umdio_course['gen_ed']

        pt_course.save()

    def update_geneds_table(self, pt_course, umdio_course):
        pt_geneds = Gened.objects.all()

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
        # assume our records are outdated and delete this link.
        for gened in pt_geneds.filter(course=pt_course):
            if gened.name not in umdio_geneds:
                self.num_geneds_updated += 1
                gened.delete()

        # if we don't have a gened for this course that umdio does have,
        # add it to our records.
        for gened in umdio_geneds:
            if not pt_geneds.filter(name=gened, course=pt_course).exists():
                self.num_geneds_updated += 1
                Gened(name=gened, course=pt_course).save()
