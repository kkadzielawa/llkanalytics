from django import forms


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
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_website(self):
        value = self.cleaned_data["website"].strip()
        if value:
            raise forms.ValidationError("Spam detected.")
        return value
