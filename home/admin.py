from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.apps import apps

class HomeModelAdmin(ModelAdmin):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields]
        super().__init__(model, admin_site)

models = apps.get_models()
for model in models:
    try:
        admin.site.register(model, HomeModelAdmin)
    except admin.sites.AlreadyRegistered:
        pass
