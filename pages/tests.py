from unittest.mock import patch

from django.contrib.messages import get_messages
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CONTACT_FORM_RECIPIENTS=["owner@example.com", "team@example.com"],
    DEFAULT_FROM_EMAIL="hello@llkanalytics.com",
    SECURE_SSL_REDIRECT=False,
)
class ContactViewTests(TestCase):
    def test_public_pages_render(self):
        response = self.client.get(reverse("pages:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Engineering and Classical Machine Learning")

        response = self.client.get(reverse("pages:services"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Applied analytics support")

        response = self.client.get(reverse("pages:contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shoot me a message")

    def test_valid_contact_submission_sends_email(self):
        response = self.client.post(
            reverse("pages:contact"),
            data={
                "name": "Ada Analyst",
                "email": "ada@example.com",
                "service": "analytics-consulting",
                "message": "I would like help scoping an analytics roadmap.",
                "website": "",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('pages:contact')}#contact",
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com", "team@example.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["ada@example.com"])
        self.assertIn("analytics-consulting", mail.outbox[0].subject)

    def test_invalid_contact_submission_sends_no_email(self):
        response = self.client.post(
            reverse("pages:contact"),
            data={
                "name": "Ada Analyst",
                "email": "ada@example.com",
                "service": "",
                "message": "Too short",
                "website": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please review the highlighted fields")
        self.assertEqual(len(mail.outbox), 0)

    def test_honeypot_submission_sends_no_email(self):
        response = self.client.post(
            reverse("pages:contact"),
            data={
                "name": "Spam Bot",
                "email": "bot@example.com",
                "service": "",
                "message": "This looks like spam content but should not send.",
                "website": "https://spam.example.com",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_delivery_failure_renders_error(self):
        with patch("pages.views.EmailMessage.send", side_effect=RuntimeError("smtp down")):
            response = self.client.post(
                reverse("pages:contact"),
                data={
                    "name": "Ada Analyst",
                    "email": "ada@example.com",
                    "service": "training-course",
                    "message": "I want to discuss a private training session for our team.",
                    "website": "",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not be delivered")
        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertTrue(any("could not be delivered" in message for message in messages))
