from django.db import migrations

def forwards_func(apps, schema_editor):
    ProfessorCourse = apps.get_model("home", "ProfessorCourse")
    db_alias = schema_editor.connection.alias
    professor_courses = ProfessorCourse.objects.using(db_alias).all()
    for record in professor_courses:
        dup_records = professor_courses.filter(
            professor=record.professor,
            course=record.course
        ).exclude(pk=record.pk)

        if dup_records.count() <= 1:
            continue

        for dup in dup_records:
            if dup.recent_semester and record.recent_semester and dup.recent_semester != record.recent_semester:
                dup_records = dup_records.exclude(pk=dup.pk)

        dup_records.delete()
        professor_courses = ProfessorCourse.objects.using(db_alias).all()

class Migration(migrations.Migration):
    dependencies = [
        ('home', '0004_professoralias'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
