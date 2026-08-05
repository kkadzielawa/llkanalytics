from django.conf import settings


def site_settings(request):
    return {
        "site_url": settings.SITE_URL,
        "contact_recipients": settings.CONTACT_FORM_RECIPIENTS,
    }
