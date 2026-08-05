from django.shortcuts import get_object_or_404, render

from cart.forms import CartAddCourseForm

from .models import Category, Course


def course_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    courses = Course.objects.filter(available=True).select_related("category")

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        courses = courses.filter(category=category)

    return render(
        request,
        "courses/list.html",
        {"category": category, "categories": categories, "courses": courses},
    )


def course_detail(request, slug):
    course = get_object_or_404(
        Course.objects.select_related("category"),
        slug=slug,
        available=True,
    )
    cart_course_form = CartAddCourseForm()
    return render(
        request,
        "courses/detail.html",
        {"course": course, "cart_course_form": cart_course_form},
    )
