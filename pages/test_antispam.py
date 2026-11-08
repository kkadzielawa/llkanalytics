import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.db import close_old_connections
from django.test import Client, RequestFactory, TestCase, TransactionTestCase
from django.test import override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from .antispam import client_ip, consume_limit
from .forms import ContactForm
from .models import SubmissionThrottle


@override_settings(
    SECURE_SSL_REDIRECT=False,
    TRUST_PROXY_CLIENT_IP=False,
    CONTACT_FORM_MIN_SECONDS=0,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class ContactProtectionTests(TestCase):
    def payload(self, **changes):
        data = {
            "name": "Ada Analyst", "email": "ada@example.com",
            "message": "I would like help with a data project.",
            "website": "", "form_token": ContactForm().initial["form_token"],
        }
        data.update(changes)
        return data

    def test_spoofed_forwarded_headers_do_not_bypass_ip_limit(self):
        for attempt in range(4):
            response = self.client.post(
                reverse("pages:contact"),
                self.payload(email=f"reader{attempt}@example.com"),
                HTTP_X_FORWARDED_FOR=f"198.51.100.{attempt}",
                HTTP_X_LLK_CLIENT_IP=f"198.51.100.{attempt}",
            )
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response["Retry-After"]), 0)
        self.assertEqual(len(mail.outbox), 3)

    def test_sender_limit_survives_ip_rotation(self):
        for attempt in range(4):
            response = self.client.post(
                reverse("pages:contact"), self.payload(),
                REMOTE_ADDR=f"198.51.100.{attempt}",
            )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), 3)

    def test_invalid_attempts_are_limited(self):
        for _ in range(11):
            response = self.client.post(reverse("pages:contact"), {})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(len(mail.outbox), 0)

    def test_replaying_token_sends_only_once(self):
        payload = self.payload()
        self.assertEqual(self.client.post(reverse("pages:contact"), payload).status_code, 302)
        # Changing the message and source address cannot reuse the token.
        payload["message"] = "Another message using the same signed form."
        response = self.client.post(reverse("pages:contact"), payload, REMOTE_ADDR="198.51.100.2")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(mail.outbox), 1)

    def test_zero_send_result_is_failure_and_can_be_retried(self):
        payload = self.payload()
        with patch("pages.views.EmailMessage.send", return_value=0), self.assertLogs("pages.views", level="ERROR"):
            response = self.client.post(reverse("pages:contact"), payload)
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, payload["message"], status_code=503)
        response = self.client.post(reverse("pages:contact"), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_missing_or_tampered_token_is_recoverable(self):
        for token in ["", "not-signed"]:
            response = self.client.post(reverse("pages:contact"), self.payload(form_token=token))
            self.assertContains(response, "Please wait a moment and submit this form again")
            recovered_token = response.context["form"]["form_token"].value()
            self.assertNotEqual(recovered_token, token)
        self.assertEqual(len(mail.outbox), 0)

    def test_token_expiry_and_minimum_completion_time(self):
        payload = self.payload()
        with override_settings(CONTACT_FORM_MIN_SECONDS=3):
            self.assertFalse(ContactForm(payload).is_valid())
        with patch("time.time", return_value=time.time() + 86401):
            form = ContactForm(payload)
            self.assertFalse(form.is_valid())
            self.assertIn("form_token", form.errors)

    def test_signed_forms_are_not_cached_and_csrf_is_enforced(self):
        response = self.client.get(reverse("pages:contact"))
        self.assertIn("no-store", response["Cache-Control"])
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("pages:contact"), self.payload()).status_code, 403)

    def test_header_injection_is_validation_error(self):
        response = self.client.post(reverse("pages:contact"), self.payload(name="Ada\r\nBcc: bad@example.com"))
        self.assertContains(response, "single line")
        self.assertEqual(len(mail.outbox), 0)

    def test_legitimate_reference_links_are_allowed(self):
        response = self.client.post(reverse("pages:contact"), self.payload(message="Please review https://example.com and https://example.org for context."))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

    def test_proxy_header_is_opt_in_and_ip_is_normalized(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="192.0.2.1", HTTP_X_LLK_CLIENT_IP="2001:0db8::1",
        )
        self.assertEqual(client_ip(request), "192.0.2.1")
        with override_settings(TRUST_PROXY_CLIENT_IP=True):
            self.assertEqual(client_ip(request), "2001:db8::1")

    def test_expired_limits_reset_and_store_only_hashes(self):
        self.assertEqual(consume_limit("test", "ada@example.com", 1, 900), 0)
        self.assertGreater(consume_limit("test", "ada@example.com", 1, 900), 0)
        bucket = SubmissionThrottle.objects.get()
        self.assertEqual(len(bucket.key), 64)
        bucket.expires_at = timezone.now() - timedelta(seconds=1)
        bucket.save()
        self.assertEqual(consume_limit("test", "ada@example.com", 1, 900), 0)
        self.assertEqual(SubmissionThrottle.objects.get().count, 1)


class ConcurrentThrottleTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_workers_cannot_exceed_limit(self):
        def submit(_):
            close_old_connections()
            try:
                return consume_limit("concurrent", "192.0.2.1", 3, 900)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(submit, range(12)))
        self.assertEqual(results.count(0), 3)
        self.assertEqual(SubmissionThrottle.objects.get().count, 3)


@override_settings(SECURE_SSL_REDIRECT=False)
class UploadProtectionTests(TestCase):
    def test_anonymous_and_nonstaff_users_cannot_upload(self):
        endpoint = reverse("django_summernote-upload_attachment")
        self.assertEqual(self.client.post(endpoint).status_code, 302)
        user = get_user_model().objects.create_user(username="reader", password="test-password")
        self.client.force_login(user)
        self.assertEqual(self.client.post(endpoint).status_code, 403)

    def test_active_staff_can_reach_upload_validation(self):
        user = get_user_model().objects.create_user(username="editor", is_staff=True)
        self.client.force_login(user)
        response = self.client.post(reverse("django_summernote-upload_attachment"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "No files were requested")

    def test_current_admin_assets_take_precedence_over_old_copies(self):
        path = finders.find("admin/js/core.js")
        self.assertIn("django/contrib/admin/static", path)
