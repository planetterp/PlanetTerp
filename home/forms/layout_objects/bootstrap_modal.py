from django.template.loader import render_to_string

from crispy_forms.layout import LayoutObject
from crispy_forms.utils import flatatt, TEMPLATE_PACK


class BootstrapModal(LayoutObject):
    """
    Boostrap layout object for rendering crispy forms objects inside a bootstrap modal.

    The following attributes can be set:
        - `css_id`: modal's DOM id
        - `css_class`: modal's DOM classes
            - NOTE: "modal" and "fade" are applied by default
        - `title`: text to display in the modal's header
            - NOTE: text will be wrapped in a <h5> tag
        - `title_id`: title's DOM id
        - `title_class`: titles's DOM classes
            - NOTE: "modal-title" is applied by default

    Example::

        Modal(
            'field1',
            Div('field2'),
            css_id="modal-id-ex",
            css_class="modal-class-ex,
            title="This is my modal"
        )
    """

    template = "bootstrap_modal.html"

    def __init__(self, *fields, **kwargs):
        self.fields = list(fields)
        self.template = kwargs.pop("template", self.template)

        self.css_id = kwargs.pop("css_id", "modal_id")
        self.title = kwargs.pop("title", "Modal Title")
        self.title_id = kwargs.pop("title_id", "modal_title_id")

        self.css_class = "modal fade"
        if "css_class" in kwargs:
            self.css_class += " %s" % kwargs.pop("css_class")

        self.title_class = "modal-title"
        if "title_class" in kwargs:
            self.title_class += " %s" % kwargs.pop("title_class")

        kwargs = {**kwargs, "tabindex": "-1", "role": "dialog", "aria-labelledby": "%s-label" % self.css_id}

        self.flat_attrs = flatatt(kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        fields = self.get_rendered_fields(form, form_style, context, template_pack, **kwargs)
        template = self.get_template_name(template_pack)

        return render_to_string(template, {"modal": self, "fields": fields})
