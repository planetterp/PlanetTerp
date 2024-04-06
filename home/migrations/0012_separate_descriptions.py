import re

from django.db import migrations

# TODO: Investigate why regex doesn't catch this query:
#   SELECT * FROM planetterp.home_course WHERE description LIKE "Or permission of %.";

# https://docs.djangoproject.com/en/4.1/ref/migration-operations/#django.db.migrations.operations.RunPython


# All the course information is currently contained within a course's
# description. This is gross. The goal here is to go through each of our courses
# and progressively extract everything from the "description" except the actual
# description and put them in their own columns in the Course model.
def forwards_func(apps, schema_editor):
    # Get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Course = apps.get_model("home", "Course")
    db_alias = schema_editor.connection.alias
    courses = Course.unfiltered.using(db_alias).all()

    # A list of 3-tuples, each of which contains the name for a particular Course
    # column [0], the regex to extract what we want from that column [1], and
    # the regex group index to obtain the piece of the matched expression we're
    # interested in [2].
    regex = [
        ("prereqs", "Pre-?requisites?:? ([^.]+\.\s?(((\s?Or)|(\s?And)) [^.]+\.)*)", 1),
        ("coreqs", "Co-?requisites?:? ([^.]+\.)", 1),
        ("recs", "Recommended:? ([^.]+\.)", 1),
        ("restrictions", "(Restricted to:? ([^.]+\.))|(Restrictions?:* ([^.]+\.))", 2),
        ("cross_listed_with", "(Also offered as:? ([^.]+\.))|(Cross-?listed with:? ([^.]+\.))", 2),
        ("formerly", "Formerly:? ([^.]+\.)", 1),
        ("additional_info", "Additional information:? ([^.]+\.)", 1),
        ("additional_info", "Jointly offered w\s?it\s?h:? [^.]+\.", 0),
        ("credit_granted_for", "(Credit only granted for:? ([^.]+\.))|(Credit will be granted for:? ([^.]+\.))|(Credit only granted for one of the following ([^.]+\.))|(Credit will be granted for one of the following:? ([^.]+\.))|(Credit granted for:? ([^.]+\.))", 2),
    ]

    # for each of our courses...
    for course in courses:
        # the state of this course's columns as the description gets parsed
        column_values = {
            "prereqs": None,
            "coreqs": None,
            "recs": None,
            "restrictions": None,
            "cross_listed_with": None,
            "formerly": None,
            "additional_info": None,
            "credit_granted_for": None
        }

        # shallow copy the description so we can progressively modify it
        desc = str(course.description)

        # remove the italics and/or bold font from the description
        desc = re.sub("(<i>)|(<\/i>)|(<b>)|(<\/b>)", '', desc)

        # remove edge case that appears in some of the descriptions
        desc = re.sub("\\\\n", ' ', repr(desc))

        # ensure words are single-spaced
        desc = re.sub("\s{2,}", ' ', desc)

        # for each tuple in the regex list...
        for column, pattern, group in regex:
            # search for the associated pattern
            match_obj = re.search(pattern, desc)

            # if there is no match, skip to the next column/pattern
            if not match_obj:
                continue

            # if there is a match, set the column accordingly and remove the
            # matched piece from the description
            piece = match_obj.group(group)
            if column_values[column]:
                column_values[column] += ' ' + piece
            else:
                column_values[column] = piece

            desc = re.sub(pattern, '', desc)

        # Remove quote chars
        desc = desc.strip('\'\"')

        # Some descriptions on testduo have links to different pages.
        # Since we don't link to those pages, remove that part of the description.
        desc = re.sub("(Please )?(C|c)lick here.*\.?", '', desc)

        # Remove leading/trailing whitespace
        desc = desc.strip()

        # If there's nothing left of desc, then there must not be any actual
        # description for this course, so set the description to None.
        # Otherwise, set the description to whatever is left.
        if desc in ['', 'None']:
            course.description = None
        else:
            course.description = desc

        for col, val in column_values.items():
            setattr(course, col, val)

        course.save()


class Migration(migrations.Migration):
    dependencies = [
        ('home', '0011_auto_20230525_1634'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]