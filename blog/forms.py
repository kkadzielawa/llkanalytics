import re

from django import forms
from pages.antispam import ProtectedFormMixin
from .models import Comment


class CommentForm(ProtectedFormMixin, forms.ModelForm):
    token_salt = "comment-form"
    minimum_seconds_setting = "COMMENT_FORM_MIN_SECONDS"
    form_token = forms.CharField(required=True, widget=forms.HiddenInput)
    company_website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "honeypot-field", "tabindex": "-1",
            "autocomplete": "off", "aria-hidden": "true",
        }),
    )
    name = forms.CharField(
        required=True,
        max_length=80,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "name",
                "placeholder": "Your name",
            }
        ),
    )
    email = forms.EmailField(
        required=True,
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "you@example.com",
            }
        ),
    )
    body = forms.CharField(
        required=True,
        min_length=10,
        max_length=3000,
        label="Comment",
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": "Share a thoughtful note or question...",
                "class": "comment-textarea",
            }
        ),
    )

    class Meta:
        model = Comment
        fields = ["name", "email", "body"]

    def clean_company_website(self):
        if self.cleaned_data["company_website"]:
            raise forms.ValidationError("Spam detected.")
        return ""

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        # A normal reader may include a useful reference link, but a comment
        # containing a large number of links is almost always SEO spam.
        link_count = len(
            re.findall(r"(?:https?://|www\.)", body, flags=re.IGNORECASE)
        )
        if link_count > 2:
            raise forms.ValidationError(
                "Please remove extra links from your comment before submitting."
            )
        return body
