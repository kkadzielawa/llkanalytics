import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import ContactForm

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "HEAD"])
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /cart/",
        "",
        f"Sitemap: {settings.SITE_URL}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@require_http_methods(["GET", "HEAD", "POST"])
def contact(request):
    form = ContactForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        cleaned_data = form.cleaned_data
        service = cleaned_data.get("service") or "General inquiry"
        subject = f"LLK Analytics contact: {cleaned_data['name']} ({service})"
        message = (
            f"Name: {cleaned_data['name']}\n"
            f"Email: {cleaned_data['email']}\n"
            f"Service: {service}\n\n"
            f"Message:\n{cleaned_data['message']}"
        )

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=settings.CONTACT_FORM_RECIPIENTS,
            reply_to=[cleaned_data["email"]],
        )

        try:
            email.send(fail_silently=False)
        except Exception:
            logger.exception(
                "Contact form delivery failed for %s", cleaned_data["email"]
            )
            messages.error(
                request,
                "Your message could not be delivered right now. Please try again shortly.",
            )
        else:
            messages.success(
                request,
                "Message sent successfully. Thank you for reaching out.",
            )
            return redirect(f"{reverse('pages:contact')}#contact")

    return render(request, "contact.html", {"form": form})
