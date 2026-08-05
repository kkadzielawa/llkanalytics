from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from honeypot.decorators import check_honeypot

from .forms import CommentForm
from .models import Post


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
    form = CommentForm(data=request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post_obj
        if getattr(request.user, "is_authenticated", False):
            full_name = request.user.get_full_name() or getattr(
                request.user, "username", ""
            )
            comment.name = full_name
            user_email = getattr(request.user, "email", "")
            if user_email:
                comment.email = user_email
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
