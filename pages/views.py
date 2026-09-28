import logging
from hashlib import sha256

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import ContactForm

logger = logging.getLogger(__name__)

CONTACT_RATE_LIMIT = 3
CONTACT_RATE_WINDOW = 15 * 60


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "").strip()


def _contact_rate_limited(request):
    client_ip = _client_ip(request)
    if not client_ip:
        return False
    key = "contact-submit:" + sha256(
        f"{settings.SECRET_KEY}:{client_ip}".encode("utf-8")
    ).hexdigest()
    try:
        attempts = cache.incr(key)
    except ValueError:
        cache.add(key, 1, timeout=CONTACT_RATE_WINDOW)
        attempts = 1
    return attempts > CONTACT_RATE_LIMIT


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
        if _contact_rate_limited(request):
            form.add_error(
                None,
                "Too many messages were submitted recently. Please wait a few minutes before trying again.",
            )
            return render(request, "contact.html", {"form": form})

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
