# Generated by Django 3.2.4 on 2022-08-31 18:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_rename_recent_course_is_recent'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='additional_info',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='coreqs',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='credit_granted_for',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='cross_listed_with',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='formerly',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='prereqs',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='recs',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='restrictions',
            field=models.TextField(null=True),
        ),
    ]