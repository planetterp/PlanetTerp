from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0010_initial_data'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'permissions': [('admin', 'Can take any planetterp admin actions')]},
        ),
    ]
