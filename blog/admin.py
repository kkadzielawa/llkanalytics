from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from .models import Comment, Post


@admin.register(Post)
class PostAdmin(SummernoteModelAdmin):
    list_display = ["title", "slug", "author", "publish", "status"]
    list_filter = ["status", "created", "publish", "author"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ["author"]
    date_hierarchy = "publish"
    ordering = ["status", "-publish"]
    summernote_fields = ("body",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "post", "created", "active"]
    list_filter = ["active", "created", "updated"]
    search_fields = ["name", "email", "body"]
    list_select_related = ["post"]
    ordering = ["created"]
