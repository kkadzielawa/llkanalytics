from django.shortcuts import render, get_object_or_404


from .models import Category
from .models import Course


def course_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    courses = Course.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(
            Category,
            slug=category_slug,
        )
        courses = Course.objects.filter(category=category)
    return render(
        request,
        "courses/list.html",
        {"category": category, "categories": categories, "courses": courses},
    )


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, available=True)

    return render(request, "courses/detail.html", {"course": course})
