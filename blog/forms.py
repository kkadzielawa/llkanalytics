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
