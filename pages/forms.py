import re

from django import forms
from .antispam import ProtectedFormMixin


class ContactForm(ProtectedFormMixin, forms.Form):
    token_salt = "contact-form"
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
        max_length=254,
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

    def clean_website(self):
        value = self.cleaned_data["website"].strip()
        if value:
            raise forms.ValidationError("Spam detected.")
        return value

    def clean_name(self):
        name = self.cleaned_data["name"]
        if "\r" in name or "\n" in name:
            raise forms.ValidationError("Please enter your name on a single line.")
        return name

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
