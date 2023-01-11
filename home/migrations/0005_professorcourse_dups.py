from django.db import migrations

def forwards_func(apps, schema_editor):
    ProfessorCourse = apps.get_model("home", "ProfessorCourse")
    db_alias = schema_editor.connection.alias
    professor_courses = ProfessorCourse.objects.using(db_alias).all()
    unique_professors = professor_courses.values_list("professor", flat=True).distinct()
    records_to_delete = []

    for pid in unique_professors:
        courses = professor_courses.filter(professor__pk=pid)
        unique_courses = courses.values_list("course", flat=True).distinct()
        for cid in unique_courses:
            records = courses.filter(course__pk=cid).order_by("recent_semester")

            if records.count() <= 1:
                continue

            if records.exclude(recent_semester=None).exists():
                for record in records:
                    similar_records = records.filter(recent_semester=record.recent_semester)
                    if not record.recent_semester:
                        records_to_delete.append(record.pk)
                    elif similar_records.count() > 1:
                        records_to_delete += list(similar_records[1:].values_list("pk", flat=True))
            else:
                records_to_delete += list(records[1:].values_list("pk", flat=True))

    professor_courses.filter(pk__in=records_to_delete).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('home', '0004_professoralias'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
