from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    # post views
    path("", views.course_list, name="course_list"),
    path("<slug:category_slug>", views.course_list, name="course_list_by_category"),
    path("<int:id>/<slug:slug>/", views.course_detail, name="course_detail"),
]
