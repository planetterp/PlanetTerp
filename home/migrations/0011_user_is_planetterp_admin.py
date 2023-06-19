from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0010_initial_data'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'permissions': [('mod', 'Can take any planetterp site moderator actions')]},
        ),
    ]
