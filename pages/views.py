from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from honeypot.decorators import check_honeypot
import logging
import re

from .forms import EmailPostForm

logger = logging.getLogger(__name__)

def is_suspicious_content(text):
    """Check for common spam patterns"""
    if not text:
        return False
    
    # URLs in message (common spam indicator)
    url_pattern = r'https?://|www\.|\.com|\.net|\.org'
    if re.search(url_pattern, text, re.IGNORECASE):
        return True
    
    # Excessive repetition
    if len(text) > 500 and len(set(text)) < len(text) * 0.2:
        return True
    
    # Suspicious keywords
    spam_keywords = ['viagra', 'casino', 'lottery', 'click here', 'buy now', 'limited offer']
    if any(keyword in text.lower() for keyword in spam_keywords):
        return True
    
    return False

@require_http_methods(["GET", "POST"])
@check_honeypot
def contact(request):
    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            
            # Additional spam checks
            if is_suspicious_content(cd.get('message', '')):
                logger.warning(f"Suspicious content detected from {cd['email']}")
                # Still show success to not reveal to spammers
                return redirect(reverse('pages:contact') + '?sent=1')
            
            # Basic email validation
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', cd['email']):
                form.add_error('email', 'Invalid email format')
            else:
                subject = f"New Contact Message from {cd['name']}"
                message = f"Name: {cd['name']}\nEmail: {cd['email']}\n\nMessage:\n{cd['message']}"
                
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        ['kkadzi25@gmail.com'],
                        fail_silently=False,
                    )
                    logger.info(f"Contact form submitted by {cd['email']}")
                except Exception as e:
                    logger.error(f"Error sending contact email: {e}")
                
                # Redirect to avoid re-submission on page refresh
                return redirect(reverse('pages:contact') + '?sent=1')
    else:
        form = EmailPostForm()

    sent = request.GET.get('sent') == '1'
    return render(request, 'contact.html', {'form': form, 'sent': sent})