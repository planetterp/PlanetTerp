import re

from django.db import migrations

# https://docs.djangoproject.com/en/4.1/ref/migration-operations/#django.db.migrations.operations.RunPython

def forwards_func(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Course = apps.get_model("home", "Course")
    db_alias = schema_editor.connection.alias
    courses = Course.unfiltered.using(db_alias).all()
    regex = {
        "prereqs": "Prerequisite:(?:<\/b>)? ([^.]+\.)",
        "coreqs": "Corequisite:(?:<\/b>)? ([^.]+\.)",
        "reqs": "Recommended:(?:<\/b>)? ([^.]+\.)",
        "restrictions": "(?:Restricted to)|(?:Restriction:<\/b>) ([^.]+\.)(?:<\/i>)?",
        "cross_listed_with": "(?:Also offered as)|(?:Cross-listed with:?(?:<\/b>)?) ([^.]+\.) (?:<\/i>)?",
        "credit_granted_for": "Credit (?:(?:only )|(?:will be ))?granted for(?: one of the following)?:?(?:<\/b>)? ([^.]+\.) (?:<\/i>)?",
        "formerly": "Formerly:?(?:<\/b>)? ([^.]+\.) (?:<\/i>)?",
        "additional_info": "Additional information:(?:<\/b>)? ([^.]+\.)"
    }

    for course in courses:
        desc = str(course.description)
        desc = re.sub("(<i>)|(<\/i>)|(<b>)", '', desc)
        desc = re.sub("\\\\n", ' ', repr(desc))

        for column, pattern in regex.items():
            match_obj = re.search(pattern, desc)
            if match_obj:
                setattr(course, column, match_obj.group(1))
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
