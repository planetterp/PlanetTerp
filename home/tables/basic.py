from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe

import django_tables2 as tables

from home.models import Professor
from home.tables.columns import UnverifiedProfessorsActionColumn

class ProfessorsTable(tables.Table):
    name = tables.Column(orderable=False)
    type_ = tables.Column(orderable=False)
    professor_id = tables.Column(visible=False, orderable=False)
    action = UnverifiedProfessorsActionColumn()

    def __init__(self, professors: QuerySet[Professor], request, *args, **kwargs):
        self.professors = professors
        self.request = request
        kwargs = {
            "attrs": {"class": "table table-striped professors-table"},
            "empty_text": mark_safe('<h4 class="text-center">No professors/TAs to verify!</h4>'),
            "show_header": False
        }
        self.data = self.get_data(self.professors)

        self.row_attrs = {
            "id": lambda record: f"professor-{record['professor_id']}"
        }

        super().__init__(self.data, row_attrs=self.row_attrs, *args, **kwargs)

    def get_data(self, professors: QuerySet[Professor]):
        data = []
        for professor in professors:
            formatted_data = {
                "name": f"{professor.name} ({professor.pk})",
                "type_": professor.type,
                "professor_id": professor.pk,
                "action": {
                    "request": self.request,
                    "model_obj": professor
                }
            }
            data.append(formatted_data)
        return data
