import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache

from .forms import ContactForm
from .antispam import release_token, reserve_token, submission_limit

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


@never_cache
@require_http_methods(["GET", "HEAD", "POST"])
def contact(request):
    form = ContactForm(request.POST if request.method == "POST" else None)
    status = 200
    retry = submission_limit(request, "contact") if request.method == "POST" else 0

    if retry:
        form.add_error(None, "Too many attempts. Please try again in 15 minutes.")
        status = 429
    elif request.method == "POST" and form.is_valid():
        retry = submission_limit(request, "contact", form.cleaned_data["email"])
        if retry:
            form.add_error(
                None,
                "Too many messages were submitted recently. Please wait a few minutes before trying again.",
            )
            response = render(request, "contact.html", {"form": form}, status=429)
            response["Retry-After"] = str(retry)
            return response

        if reserve_token(form):
            form.add_error(None, "This message was already submitted. Please reload the form before sending another.")
            return render(request, "contact.html", {"form": form}, status=409)

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
            if email.send(fail_silently=False) != 1:
                raise RuntimeError("Email backend did not accept the contact message")
        except Exception:
            release_token(form)
            status = 503
            logger.exception("Contact form delivery failed")
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

    response = render(request, "contact.html", {"form": form}, status=status)
    if retry:
        response["Retry-After"] = str(retry)
    return response
