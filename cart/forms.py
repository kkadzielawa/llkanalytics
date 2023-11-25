from django import forms


COURSE_QUANTITY_CHOICES = [(i, str(i)) for i in range(1, 21)]


class CartAddCourseForm(forms.Form):
    quantity = forms.TypedChoiceField(choices=COURSE_QUANTITY_CHOICES, coerce=int)
    override = forms.BooleanField(
        required=False, initial=False, widget=forms.HiddenInput
    )
