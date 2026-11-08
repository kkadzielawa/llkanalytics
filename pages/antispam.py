import math
import time
from datetime import timedelta
from ipaddress import ip_address
from uuid import uuid4

from django import forms
from django.conf import settings
from django.core.signing import BadSignature, TimestampSigner
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import SubmissionThrottle


def client_ip(request):
    # Caddy overwrites this dedicated header. Enable it only when the application
    # is reachable exclusively through that proxy; never trust arbitrary XFF.
    value = request.META.get("REMOTE_ADDR", "")
    if settings.TRUST_PROXY_CLIENT_IP:
        value = request.META.get("HTTP_X_LLK_CLIENT_IP", value)
    try:
        return str(ip_address(value.strip()))
    except ValueError:
        return "unknown"


def private_key(scope, identifier):
    return salted_hmac(scope, identifier, algorithm="sha256").hexdigest()


def consume_limit(scope, identifier, limit, seconds):
    """Return retry seconds, or zero after atomically reserving a slot.

    PostgreSQL row locks and the primary-key constraint serialize workers,
    including simultaneous first submissions. Rejected requests do not extend
    the window. No IP addresses, email addresses, or message bodies are stored.
    """
    now = timezone.now()
    key = private_key(scope, identifier)
    # Bounded housekeeping keeps expired one-use tokens from accumulating.
    expired = list(
        SubmissionThrottle.objects.filter(expires_at__lte=now)
        .values_list("key", flat=True)[:100]
    )
    SubmissionThrottle.objects.filter(key__in=expired, expires_at__lte=now).delete()
    with transaction.atomic():
        bucket, _ = SubmissionThrottle.objects.select_for_update().get_or_create(
            key=key,
            defaults={"expires_at": now + timedelta(seconds=seconds)},
        )
        if bucket.expires_at <= now:
            bucket.count = 0
            bucket.expires_at = now + timedelta(seconds=seconds)
        if bucket.count >= limit:
            return max(1, math.ceil((bucket.expires_at - now).total_seconds()))
        bucket.count += 1
        bucket.save(update_fields=["count", "expires_at"])
    return 0


def submission_limit(request, channel, email=None):
    window = settings.FORM_RATE_WINDOW_SECONDS
    if email is None:
        return consume_limit(
            f"{channel}:attempt", client_ip(request),
            settings.FORM_ATTEMPT_LIMIT, window,
        )
    for scope, identifier in [
        (f"{channel}:ip", client_ip(request)),
        (f"{channel}:email", email.casefold()),
    ]:
        retry = consume_limit(scope, identifier, settings.FORM_SUBMISSION_LIMIT, window)
        if retry:
            return retry
    return 0


def reserve_token(form):
    return consume_limit(
        f"{form.token_salt}:token", form.cleaned_data["form_token"], 1,
        settings.FORM_TOKEN_MAX_AGE,
    )


def release_token(form):
    SubmissionThrottle.objects.filter(
        key=private_key(f"{form.token_salt}:token", form.cleaned_data["form_token"])
    ).delete()


class ProtectedFormMixin:
    token_salt = "public-form"
    minimum_seconds_setting = "CONTACT_FORM_MIN_SECONDS"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["form_token"] = self.new_token()

    def new_token(self):
        return TimestampSigner(salt=self.token_salt).sign(f"{time.time()}:{uuid4().hex}")

    def clean_form_token(self):
        value = self.cleaned_data["form_token"]
        try:
            issued = TimestampSigner(salt=self.token_salt).unsign(
                value, max_age=settings.FORM_TOKEN_MAX_AGE,
            )
            issued_at = float(issued.split(":", 1)[0])
        except (BadSignature, ValueError):
            raise forms.ValidationError("This form has expired. Please submit it again.")
        minimum_seconds = getattr(settings, self.minimum_seconds_setting)
        if time.time() - issued_at < minimum_seconds:
            raise forms.ValidationError("Please take a moment to complete the form, then try again.")
        return value

    def full_clean(self):
        super().full_clean()
        # Make hidden-field failures actionable and allow recovery without
        # discarding the visitor's message or requiring a page reload.
        if self.is_bound and "form_token" in self.errors:
            self.add_error(None, "Please wait a moment and submit this form again.")
            self.data = self.data.copy()
            self.data[self.add_prefix("form_token")] = self.new_token()
        for name, field in self.fields.items():
            if name in self.errors:
                field.widget.attrs["aria-invalid"] = "true"
                field.widget.attrs["aria-describedby"] = f"id_{name}_errors"
