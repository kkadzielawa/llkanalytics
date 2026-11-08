from django_summernote.apps import DjangoSummernoteConfig


class SummernoteConfig(DjangoSummernoteConfig):
    # Match the third-party app's existing migrations when using Django 5.2.
    default_auto_field = "django.db.models.AutoField"
