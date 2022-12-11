# * Only CSV files are allowed!
#
# * Ensure that the grade data you're importing has the grade cutoffs listed as:
#   A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F, W, OTHER
#
# * Remove column headers and check data for invalid entires (bottom of data)
#
# UPDATE COURSES AND PROFESSORS BEFORE RUNNING THIS SCRIPT

import csv
from pathlib import Path

from django.db.models import Q
from django.core.management import BaseCommand, CommandError

from home.models import Professor, Course, Grade
from home.utils import Semester

class ValidationError(Exception):
    pass

class Command(BaseCommand):
    def __init__(self):
        super().__init__()

        self.grades = []
        self.reject_rows = []
        self.semester = None

    def add_arguments(self, parser):
        parser.add_argument("-s", "--semester")
        parser.add_argument("-f", "--file")

    def handle(self, *args, **options):
        self.semester = Semester(options["semester"])
        file_path = Path(options["file"])

        if file_path.suffix != ".csv":
            raise CommandError("File must be a .csv")

        with open(file_path, newline="") as file:
            reader = csv.reader(file, delimiter=',', quotechar="\"")

            self.stdout.write("Importing data...")
            for row in reader:
                self.add_grade(row)

        grades = Grade.unfiltered.bulk_create(self.grades)
        self.stdout.write(f"Done, added {len(grades)} grades")

        if self.reject_rows:
            print(f"Exporting {len(self.reject_rows)} rejected rows...")
            with open("rejected_imports.csv", "w+") as f:

                writer = csv.writer(f)
                for row in self.reject_rows:
                    writer.writerow(row)

            print("**** Some data could not be imported and was stored in "
                "rejected_imports.csv ****\n")


    def parse_course(self, name: str):
        if name is None:
            raise ValidationError("Missing course")

        name = name.strip()
        courses = Course.unfiltered.filter(name=name)
        if not courses.exists():
            raise ValidationError("Course doesn't exist")
        return courses.get()

    def parse_professor(self, name: str):
        if name is None or name == "":
            return None

        names = name.strip().split(",")
        lastname = names[0]
        firstname = names[-1].strip().split()[0]
        professors = Professor.verified.filter(
            Q(name__istartswith=firstname) & Q(name__iendswith=lastname)
        )
        if professors.exists():
            return professors.first()

        raise ValidationError("Professor doesn't exist")


    def add_grade(self, row):
        try:
            grade = Grade(
                semester=self.semester,
                course=self.parse_course(row[0]),
                section=row[1],
                professor=self.parse_professor(row[2]),
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
        except ValidationError as e:
            print(e)
            self.reject_rows.append(row)
        else:
            self.grades.append(grade)
