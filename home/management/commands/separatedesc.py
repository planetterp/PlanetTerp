import re

from django.core.management import BaseCommand

from home.models import Course

class Command(BaseCommand):
    def handle(self, *args, **options):
        courses = Course.unfiltered.all()
        regex = {
            "prereqs": "Prerequisite:(?:<\/b>)? ([^.]+\.)",
            "coreqs": "Corequisite:(?:<\/b>)? ([^.]+\.)",
            "reqs": "Recommended:(?:<\/b>)? ([^.]+\.)",
            "restrictions": "(?:Restricted to)|(?:Restriction: <\/b>) ([^.]+\.) (?:<\/i>)?",
            "credit_granted_for": "Credit (?:(?:only )|(?:will be ))?granted for(?: one of the following)?:?(?:<\/b>)? ([^.]+\.) (?:<\/i>)?",
            "cross_listed_with": "(?:Also offered as)|(?:Cross-listed with) (?:<\/b>)? ([^.]+\.) (?:<\/i>)?",
            "formerly": "Formerly:?(?:<\/b>)? ([^.]+\.) (?:<\/i>)?",
            "additional_info": "Additional information:(?:<\/b>)? ([^.]+\.)"
        }

        for course in courses:
            desc = str(course.description)
            desc = re.sub("(<i>)|(<\/i>)|(<b>)", '', desc)

            for column, pattern in regex.items():
                match_obj = re.search(pattern, desc)

                if match_obj:
                    setattr(course, column, match_obj.group(1))
                    desc = re.sub(pattern, '', desc)

            desc = desc.strip()

            if desc.isspace() or desc in ['', 'None', None]:
                course.description = None
            else:
                course.description = desc

            course.save()
