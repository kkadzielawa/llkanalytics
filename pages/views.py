from django.shortcuts import render
from django.shortcuts import get_object_or_404

from .forms import EmailPostForm
from blog.models import Post

def contact(request):

    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # ... send email
    else:
        form = EmailPostForm()

    return render(request, 'contact.html', {'form': form})