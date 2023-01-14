from django.db import migrations

def forwards_func(apps, schema_editor):
    ProfessorCourse = apps.get_model("home", "ProfessorCourse")
    db_alias = schema_editor.connection.alias
    professor_courses = ProfessorCourse.objects.using(db_alias).all()

    records_to_delete = []
    unique_professors = professor_courses.values_list("professor", flat=True).distinct()

    for pid in unique_professors:
        p_courses = professor_courses.filter(professor__pk=pid)
        unique_courses = p_courses.values_list("course", flat=True).distinct()

        for cid in unique_courses:
            # order by recent semester so all records where recent semester
            # is null are first.
            records = p_courses.filter(course__pk=cid).order_by("recent_semester")

            # there can't be any duplicates with just one record for this
            # professor/course combination, so skip this record. 
            if records.count() <= 1:
                continue

            # if there are any non-null recent semesters...
            if records.exclude(recent_semester=None).exists():
                # ...for every record...
                for record in records:
                    similar_records = records.filter(recent_semester=record.recent_semester)

                    # ...if recent semester is null, delete the record: a record
                    # with a non-null recent semester for this course/prof combination
                    # is gaurenteed to exist.
                    if not record.recent_semester:
                        records_to_delete.append(record.pk)

                    # ...otherwise, if there are any exact duplicates
                    # (semester + course + professor all match), delete all
                    # but the fist one.
                    elif similar_records.count() > 1:
                        records_to_delete += list(similar_records[1:].values_list("pk", flat=True))
            else:
                # if there are only null recent semesters, delete all but the
                # first one.
                records_to_delete += list(records[1:].values_list("pk", flat=True))

    professor_courses.filter(pk__in=records_to_delete).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('home', '0004_professoralias'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
