from django import forms
#from honeypot.fields import HoneypotField

class EmailPostForm(forms.Form):
    name = forms.CharField(max_length=25)
    email = forms.EmailField()
    message = forms.CharField(required=False,
                                widget=forms.Textarea)
    #last_name = HoneypotField()