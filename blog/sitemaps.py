from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Post
from courses.models import Course


class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Post.published.all()

    def lastmod(self, obj):
        return obj.updated


class CourseSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Course.objects.filter(available=True)

    def lastmod(self, obj):
        return obj.updated


class StaticSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return ["pages:home", "pages:services", "pages:contact", "blog:post_list", "courses:course_list"]

    def location(self, item):
        return reverse(item)
