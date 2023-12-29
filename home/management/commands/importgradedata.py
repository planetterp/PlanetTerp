# Expected input is a csv file of grade data from umd.
#
# Before running:
# * run updatecourses for the corresponding semester
# * ensure the spreadsheet has only the following grades listed, in this order:
#   `A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F, W, OTHER`
# * remove the header row at the top of the spreadsheet and check the data for
#   invalid entries (at the bottom of the spreadsheet).
#
# After running:
# * go through /admin and deal with any new pending professors. These professors
#   may be created when the spreadsheet has courses which are not on umdio,
#   perhaps because they were added late (after umdio scraped), or they were never
#   put on SOC at all (such as some administrative or graduate courses).

import csv
from pathlib import Path
from requests import get

from django.core.management import BaseCommand, CommandError

from home.models import Professor, Course, Grade, ProfessorAlias
from home.utils import Semester

class ValidationError(Exception):
    pass

class Command(BaseCommand):
    def __init__(self):
        super().__init__()

        self.grades = []
        self.reject_rows = []
        self.semester = None
        self.section_prof_lookup = {}

    def add_arguments(self, parser):
        parser.add_argument("-s", "--semester", required=True)
        parser.add_argument("-f", "--file", required=True)

    def handle(self, *args, **options):
        self.semester = Semester(options["semester"])
        self.debug = options["verbosity"] > 1
        file_path = Path(options["file"])
        if file_path.suffix != ".csv":
            raise CommandError("Input file must be a .csv")

        self.get_instructor_data()

        with open(file_path, newline="") as file:
            reader = csv.reader(file, delimiter=',', quotechar="\"")

            self.stdout.write("Importing data...")
            for row in reader:
                self.add_grade(row)

        self.stdout.write(f"Adding {len(self.grades)} grades to database...")
        grades = Grade.unfiltered.bulk_create(self.grades)
        self.stdout.write(f"Done, added {len(grades)} grades")

        if self.reject_rows:
            self.stdout.write(f"Exporting {len(self.reject_rows)} rejected rows...")
            with open("rejected_imports.csv", "w+") as f:

                writer = csv.writer(f)
                for row in self.reject_rows:
                    writer.writerow(row)

            self.stderr.write("Some data could not be imported and was stored in "
                "rejected_imports.csv")

    def get_instructor_data(self):
        # umdio goes up to 50, but can take a while per request and we want to
        # ensure we don't time out.
        next_url = f"https://api.umd.io/v1/courses/sections?semester={self.semester}&per_page=30"

        while next_url is not None:
            page_data = get(next_url)
            page_dict = {section["section_id"]: section["instructors"] for section in page_data.json()}
            self.section_prof_lookup.update(page_dict)
            self.stdout.write(f"Requesting {next_url}")
            next_url = page_data.headers.get("X-Next-Page")

    def parse_course(self, name: str):
        if name is None:
            raise ValidationError("Missing course")

        name = name.strip()
        courses = Course.unfiltered.filter(name=name)
        if not courses.exists():
            raise ValidationError(f"Unknown course {name}")
        return courses.get()

    def parse_professor(self, course:str, section:str, existing_name:str):
        key = f"{course}-{section:0>4}"
        names = self.section_prof_lookup.get(key)
        if names:
            # we don't handle courses with multiple profs right now. assign
            # these grades to the first listed professor.
            name = names[0]
        elif existing_name not in {None, ""}:
            self.stdout.write(f"Could not find section {key} on umdio. "
                f"Using professor {existing_name} from umd's spreadsheet")
            # pray we don't encounter a prof without a last name.
            assert "," in existing_name
            name = existing_name.strip()
            lastname, firstname = name.split(", ")
            name = f"{firstname.strip()} {lastname.strip()}"
        else:
            # this case may be hit because we don't properly propagate professor
            # names downward in the csvs umd provides us.
            raise ValidationError(f"Could not find section {key} on umdio, and "
                "umd did not provide a professor in the spreadsheet.")

        # respect any aliases for this professor name.
        # .first() is ok here because at most one record will be returned
        alias = ProfessorAlias.objects.filter(alias=name).first()
        if alias:
            return alias.professor

        professors = Professor.unfiltered.exclude(status=Professor.Status.REJECTED).filter(name=name)
        if professors.count() == 1:
            return professors.first()

        # if we still don't recognize this professor, submit it as a new pending
        # professor. It may just need an alias created via merging in the admin
        # panel.
        self.stdout.write(f"Unknown professor {name}. Creating corresponding "
            "pending professor")
        new_professor = Professor(
            name=name,
            type=Professor.Type.PROFESSOR
        )
        new_professor.save()
        return new_professor


    def add_grade(self, row):
        try:
            grade = Grade(
                semester=self.semester,
                course=self.parse_course(row[0]),
                section=row[1],
                professor=self.parse_professor(row[0], row[1], row[2]),
                num_students=row[3],
                a_plus=row[4],
                a=row[5],
                a_minus=row[6],
                b_plus=row[7],
                b=row[8],
                b_minus=row[9],
                c_plus=row[10],
                c=row[11],
                c_minus=row[12],
                d_plus=row[13],
                d=row[14],
                d_minus=row[15],
                f=row[16],
                w=row[17],
                other=row[18]
            )
            if self.debug:
                self.stdout.write(f"processed {grade.course}-{grade.section} by {grade.professor} ({grade})")
        except ValidationError as e:
            self.stderr.write(str(e))
            self.reject_rows.append(row)
        else:
            self.grades.append(grade)
