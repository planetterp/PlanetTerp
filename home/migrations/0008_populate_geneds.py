from django.db import migrations

def forwards_func(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    ProfessorCourse = apps.get_model("home", "ProfessorCourse")
    professor_courses = ProfessorCourse.objects.using(db_alias).all()


class Migration(migrations.Migration):
    dependencies = [
        ('home', '0007_course_geneds'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
