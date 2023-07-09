from django.db import migrations
from django.core.serializers import base, python
from django.core.management import call_command

# Loads the initial fixture data as a fixed point in our migration chain. See
# https://github.com/planetterp/PlanetTerp/pull/114 for why this cannot be a
# normal loaddata call.

# ugly monkey patching to make loaddata use models at the time of migration,
# instead of the model schema defined by the current source files.
# This code has remained unchanged since django 1.8, so I think it's safe to
# consider it stable, although it is absolutely not part of the public django
# api.
# https://stackoverflow.com/a/39743581
def load_fixture(apps, _schema_editor):
    old_get_model = python._get_model

    def _get_model(model_identifier):
        try:
            return apps.get_model(model_identifier)
        except (LookupError, TypeError):
            raise base.DeserializationError("Invalid model identifier: "
                f"'{model_identifier}'")

    python._get_model = _get_model

    try:
        call_command('loaddata', 'home/fixtures/initial.json.gz')
    finally:
        python._get_model = old_get_model


class Migration(migrations.Migration):
    dependencies = [
        ('home', '0009_auto_20230310_0939')
    ]

    operations = [
        migrations.RunPython(load_fixture)
    ]
