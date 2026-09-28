import re
import time

from django import forms
from django.conf import settings
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner


class ContactForm(forms.Form):
    SERVICE_CHOICES = [
        ("", "Select a focus area"),
        ("analytics-consulting", "Analytics consulting"),
        ("data-bi-project", "Data/BI project"),
        ("training-course", "Training/course"),
        ("speaking-other", "Speaking/other"),
    ]

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "name",
                "placeholder": "Your name",
            }
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "you@example.com",
            }
        )
    )
    service = forms.ChoiceField(
        choices=SERVICE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"autocomplete": "off"}),
    )
    message = forms.CharField(
        min_length=10,
        max_length=3000,
        widget=forms.Textarea(
            attrs={
                "rows": 10,
                "autocomplete": "off",
                "placeholder": "Tell me a little about the problem, project, or idea.",
            }
        ),
    )
    # This field is visually hidden with CSS, but deliberately remains a text
    # input so simple bots that fill every field trigger the trap.
    website = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={
                "class": "honeypot-field",
                "tabindex": "-1",
                "autocomplete": "off",
                "aria-hidden": "true",
            }
        ),
    )
    form_token = forms.CharField(required=True, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["form_token"] = TimestampSigner(
                salt="contact-form"
            ).sign(str(time.time()))

    def clean_website(self):
        value = self.cleaned_data["website"].strip()
        if value:
            raise forms.ValidationError("Spam detected.")
        return value

    def clean_form_token(self):
        value = self.cleaned_data["form_token"]
        try:
            issued_at = float(
                TimestampSigner(salt="contact-form").unsign(value, max_age=60 * 60 * 24)
            )
        except (BadSignature, SignatureExpired, ValueError):
            raise forms.ValidationError("Please reload the form and try again.")
        minimum_seconds = float(getattr(settings, "CONTACT_FORM_MIN_SECONDS", 3))
        if time.time() - issued_at < minimum_seconds:
            raise forms.ValidationError("Please take a moment to complete the form.")
        return value

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        link_count = len(
            re.findall(r"(?:https?://|www\.)", message, flags=re.IGNORECASE)
        )
        if link_count > 2:
            raise forms.ValidationError(
                "Please remove extra links from your message before submitting."
            )
        return message
