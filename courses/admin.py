from django.contrib import admin

from .models import Category, Course


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "slug", "price", "available", "created", "updated"]
    list_filter = ["available", "category", "created", "updated"]
    list_editable = ["price", "available"]
    search_fields = ["name", "description"]
    list_select_related = ["category"]
    prepopulated_fields = {"slug": ("name",)}
