from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from blog.models import Comment, Post
from courses.models import Category, Course


@override_settings(SECURE_SSL_REDIRECT=False)
class BlogModelAndViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.author = user_model.objects.create_user(
            username="konrad",
            email="konrad@example.com",
            password="testpass123",
        )
        cls.published_post = Post.objects.create(
            title="Published Analytics Post",
            slug="published-analytics-post",
            author=cls.author,
            body="Useful published content for analytics leaders.",
            status=Post.Status.PUBLISHED,
            publish=timezone.now(),
        )
        cls.draft_post = Post.objects.create(
            title="Draft Analytics Post",
            slug="draft-analytics-post",
            author=cls.author,
            body="Draft content should stay private.",
            status=Post.Status.DRAFT,
            publish=timezone.now(),
        )
        cls.active_comment = Comment.objects.create(
            post=cls.published_post,
            name="Active Commenter",
            email="reader@example.com",
            body="First active comment",
            active=True,
        )
        cls.inactive_comment = Comment.objects.create(
            post=cls.published_post,
            name="Inactive Commenter",
            email="reader2@example.com",
            body="Second hidden comment",
            active=False,
        )
        cls.category = Category.objects.create(name="SQL", slug="sql")
        cls.available_course = Course.objects.create(
            category=cls.category,
            name="SQL for Analysts",
            slug="sql-for-analysts",
            description="Learn SQL in a practical way.",
            price=Decimal("49.00"),
            available=True,
        )
        cls.unavailable_course = Course.objects.create(
            category=cls.category,
            name="Archived SQL Course",
            slug="archived-sql-course",
            description="No longer available.",
            price=Decimal("49.00"),
            available=False,
        )

    def test_published_manager_only_returns_published_posts(self):
        self.assertQuerysetEqual(
            Post.published.values_list("slug", flat=True),
            ["published-analytics-post"],
            transform=lambda value: value,
        )

    def test_post_absolute_url_keeps_date_slug_shape(self):
        absolute_url = self.published_post.get_absolute_url()
        self.assertIn("/blog/", absolute_url)
        self.assertIn("/published-analytics-post/", absolute_url)

    def test_comment_ordering_and_active_visibility(self):
        comments = list(self.published_post.comments.order_by("created"))
        self.assertEqual(comments[0], self.active_comment)

        response = self.client.get(self.published_post.get_absolute_url())
        self.assertContains(response, "First active comment")
        self.assertNotContains(response, "Second hidden comment")

    def test_blog_list_gracefully_handles_invalid_pagination(self):
        response = self.client.get(reverse("blog:post_list"), {"page": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Analytics Post")

    def test_blog_detail_hides_draft_posts(self):
        response = self.client.get(
            reverse(
                "blog:post_detail",
                args=[
                    self.draft_post.publish.year,
                    self.draft_post.publish.month,
                    self.draft_post.publish.day,
                    self.draft_post.slug,
                ],
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_sitemap_only_lists_public_records(self):
        response = self.client.get(reverse("django.contrib.sitemaps.views.sitemap"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(self.published_post.get_absolute_url(), content)
        self.assertNotIn(self.draft_post.slug, content)
        self.assertIn(self.available_course.get_absolute_url(), content)
        self.assertNotIn(self.unavailable_course.slug, content)
