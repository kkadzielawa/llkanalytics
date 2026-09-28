from datetime import timedelta
from hashlib import sha256

from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from honeypot.decorators import check_honeypot

from .forms import CommentForm
from .models import Comment, Post


COMMENT_RATE_WINDOW = timedelta(minutes=10)
COMMENT_RATE_LIMIT = 3


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR", "").strip()


def _submitter_hash(request):
    client_ip = _client_ip(request)
    if not client_ip:
        return ""
    return sha256(f"{settings.SECRET_KEY}:{client_ip}".encode("utf-8")).hexdigest()


def post_list(request):
    post_queryset = Post.published.select_related("author")
    paginator = Paginator(post_queryset, 2)
    page_number = request.GET.get("page", 1)
    posts = paginator.get_page(page_number)
    return render(request, "blog/post/list.html", {"posts": posts})


def post_detail(request, year, month, day, post):
    post_obj = get_object_or_404(
        Post.published.select_related("author"),
        slug=post,
        publish__year=year,
        publish__month=month,
        publish__day=day,
    )
    comments = post_obj.comments.filter(active=True)
    form = CommentForm()
    return render(
        request,
        "blog/post/detail.html",
        {"post": post_obj, "comments": comments, "form": form},
    )


@require_POST
@check_honeypot
def post_comment(request, post_id):
    post_obj = get_object_or_404(Post.published, id=post_id)
    comment = None
    form_data = request.POST.copy()
    if getattr(request.user, "is_authenticated", False):
        full_name = request.user.get_full_name().strip() or getattr(
            request.user, "username", ""
        )
        if full_name.lower() in {"kkadzielawa", "konrad"}:
            full_name = "Konrad Kadzielawa"
        form_data["name"] = full_name

        user_email = getattr(request.user, "email", "")
        if user_email:
            form_data["email"] = user_email

    form = CommentForm(data=form_data)
    submitter_hash = _submitter_hash(request)
    recent_comments = 0
    if submitter_hash:
        recent_comments = Comment.objects.filter(
            submitter_hash=submitter_hash,
            created__gte=timezone.now() - COMMENT_RATE_WINDOW,
        ).count()

    if recent_comments >= COMMENT_RATE_LIMIT:
        form.add_error(
            None,
            "You have submitted several comments recently. Please wait a few minutes before trying again.",
        )
    elif form.is_valid():
        comment = form.save(commit=False)
        comment.post = post_obj
        comment.active = False
        comment.submitter_hash = submitter_hash
        comment.save()
    comments = post_obj.comments.filter(active=True)
    return render(
        request,
        "blog/post/detail.html",
        {
            "post": post_obj,
            "form": form,
            "comment": comment,
            "comments": comments,
        },
    )
