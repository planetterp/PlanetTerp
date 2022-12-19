import re

from django.db import migrations

# TODO: Investigate why regex doesn't catch this query:
#   SELECT * FROM planetterp.home_course WHERE description LIKE "Or permission of %.";

# https://docs.djangoproject.com/en/4.1/ref/migration-operations/#django.db.migrations.operations.RunPython

def forwards_func(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Course = apps.get_model("home", "Course")
    db_alias = schema_editor.connection.alias
    courses = Course.unfiltered.using(db_alias).all()
    regex = [
        ("prereqs", "Prerequisite: ([^.]+\. (Or permission of [^.]+\.)?)", 1),
        ("coreqs", "Corequisite: ([^.]+\.)", 1),
        ("reqs", "Recommended: ([^.]+\.)", 1),
        ("restrictions", "(Restricted to ([^.]+\.))|(Restriction: ([^.]+\.))", 2),
        ("cross_listed_with", "(Also offered as: ([^.]+\.))|(Cross-listed with: ([^.]+\.))", 2),
        ("credit_granted_for", "(Credit only granted for: ([^.]+\.)) | (Credit will be granted for: ([^.]+\.)) | (Credit only granted for one of the following ([^.]+\.)) | (Credit will be granted for one of the following: ([^.]+\.))", 2),
        ("formerly", "Formerly: ([^.]+\.)", 1),
        ("additional_info", "Additional information: ([^.]+\.)", 1)
    ]

    for course in courses:
        desc = str(course.description)
        desc = re.sub("(<i>)|(<\/i>)|(<b>)|(<\/b>)", '', desc)
        desc = re.sub("\\\\n", ' ', repr(desc))

        for column, pattern, group in regex:
            match_obj = re.search(pattern, desc)
            if match_obj:
                setattr(course, column, match_obj.group(group))
                desc = re.sub(pattern, '', desc)

        desc = desc.strip('\'').strip('\"').strip()
        if desc in ['', 'None']:
            course.description = None
        else:
            # Some descriptions on testduo have links to different pages.
            # Since we don't link to those pages, remove that part of the description.
            # Why? Because we can and it's easy to do so.
            desc = re.sub("(Please)? (C|c)lick here (.*)(/.)?", '', desc)
            course.description = desc

        course.save()


class Migration(migrations.Migration):
    dependencies = [
        ('home', '0004_auto_20220831_1805'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
