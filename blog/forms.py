import re

from django import forms
from .models import Comment


class CommentForm(forms.ModelForm):
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
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "you@example.com",
            }
        ),
    )
    body = forms.CharField(
        required=True,
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
