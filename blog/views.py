from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from pages.antispam import client_ip, private_key, reserve_token, submission_limit

from .forms import CommentForm
from .models import Comment, Post


def post_list(request):
    post_queryset = Post.published.select_related("author")
    paginator = Paginator(post_queryset, 2)
    page_number = request.GET.get("page", 1)
    posts = paginator.get_page(page_number)
    return render(request, "blog/post/list.html", {"posts": posts})


@never_cache
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


@never_cache
@require_POST
def post_comment(request, post_id):
    post_obj = get_object_or_404(Post.published, id=post_id)
    status = 200
    retry = submission_limit(request, "comment")
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
    if retry:
        form.add_error(None, "Too many attempts. Please try again in 15 minutes.")
        status = 429
    elif form.is_valid():
        retry = submission_limit(request, "comment", form.cleaned_data["email"])
        if retry:
            form.add_error(None, "You have submitted several comments recently. Please try again in 15 minutes.")
            status = 429
        elif reserve_token(form):
            form.add_error(None, "This comment was already submitted. Please reload the form before adding another.")
            status = 409
        else:
            comment = form.save(commit=False)
            comment.post = post_obj
            comment.active = False
            comment.submitter_hash = private_key("comment:ip", client_ip(request))
            comment.save()
            messages.success(request, "Your comment has been submitted for review.")
            return redirect(f"{post_obj.get_absolute_url()}#comments")
    comments = post_obj.comments.filter(active=True)
    response = render(
        request,
        "blog/post/detail.html",
        {
            "post": post_obj,
            "form": form,
            "comments": comments,
        },
        status=status,
    )
    if retry:
        response["Retry-After"] = str(retry)
    return response
