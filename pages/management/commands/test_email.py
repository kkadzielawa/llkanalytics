from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test email configuration"

    def handle(self, *args, **options):
        self.stdout.write("Testing email configuration...")
        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(
            f"CONTACT_FORM_RECIPIENTS: {', '.join(settings.CONTACT_FORM_RECIPIENTS)}"
        )

        try:
            send_mail(
                "Test Email from Django",
                "This is a test email to verify the email configuration is working.",
                settings.DEFAULT_FROM_EMAIL,
                settings.CONTACT_FORM_RECIPIENTS,
                fail_silently=False,
            )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Error: {exc}"))
            return

        self.stdout.write(self.style.SUCCESS("Email sent successfully!"))
