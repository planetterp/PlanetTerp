from django.template.loader import render_to_string

from crispy_forms.layout import LayoutObject
from crispy_forms.utils import flatatt, TEMPLATE_PACK


class BootstrapModal(LayoutObject):
    '''
    Custom crispy_forms layout object that displays forms fields
    inside a bootstrap4 modal. This layout object works like all other
    crispy_forms layout objects:
    - Initialize the object with the desired form fields
    - Add any html attribute to the modal via kwargs using the following keys:
        - css_id: The modal id, or the id of the outermost <div>
        - css_class: The modal class name(s), or the class(es) of the outermost <div>
            - The "modal" and "fade" classes are applied by default
        - title_id: The id attribute of the title tag
        - title: The text to display in the modal header. The text will be wrapped in
                 a <h5> tag
    '''
    css_class = "modal fade"

    def __init__(self, *fields, **kwargs):
        self.fields = list(fields)
        self.template = "bootstrap_modal.html"

        if hasattr(self, "css_class") and "css_class" in kwargs:
            self.css_class += " %s" % kwargs.pop("css_class")
        if not hasattr(self, "css_class"):
            self.css_class = kwargs.pop("css_class", None)

        self.css_id = kwargs.pop("css_id", "")
        self.title_id = kwargs.pop("title_id", "modal_title_id")
        self.title = kwargs.pop("title", "Modal Title")

        kwargs = {
            **kwargs,
            "tabindex": "-1",
            "role": "dialog",
            "aria-labelledby": "%s-label" % self.css_id
        }

        self.flat_attrs = flatatt(kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        fields = self.get_rendered_fields(form, form_style, context, template_pack, **kwargs)

        return render_to_string(self.template, {"modal": self, "fields": fields})
