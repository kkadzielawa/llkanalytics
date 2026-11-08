from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from blog.models import Comment, Post
from blog.forms import CommentForm
from courses.models import Category, Course


@override_settings(SECURE_SSL_REDIRECT=False, COMMENT_FORM_MIN_SECONDS=0)
class BlogModelAndViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.author = user_model.objects.create_user(
            username="kkadzielawa",
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
        self.assertQuerySetEqual(
            Post.published.values_list("slug", flat=True),
            ["published-analytics-post"],
            transform=lambda value: value,
        )

    def test_post_absolute_url_keeps_date_slug_shape(self):
        absolute_url = self.published_post.get_absolute_url()
        self.assertIn("/blog/", absolute_url)
        self.assertIn("/published-analytics-post/", absolute_url)

    def test_public_author_display_uses_full_name_for_site_owner(self):
        self.assertEqual(self.published_post.author_display_name, "Konrad Kadzielawa")

        response = self.client.get(reverse("blog:post_list"))
        self.assertContains(response, "By Konrad Kadzielawa")
        self.assertNotContains(response, "By kkadzielawa")

        response = self.client.get(self.published_post.get_absolute_url())
        self.assertContains(response, "<span>Author</span>Konrad Kadzielawa")
        self.assertNotContains(response, "<span>Author</span>kkadzielawa")

    def test_comment_ordering_and_active_visibility(self):
        comments = list(self.published_post.comments.order_by("created"))
        self.assertEqual(comments[0], self.active_comment)

        response = self.client.get(self.published_post.get_absolute_url())
        self.assertContains(response, "First active comment")
        self.assertNotContains(response, "Second hidden comment")
        self.assertContains(response, 'class="comment-textarea"')
        self.assertContains(response, "Spam protection is enabled")

    def test_comment_requires_name_before_saving(self):
        comment_count = Comment.objects.count()

        response = self.client.post(
            reverse("blog:post_comment", args=[self.published_post.id]),
            data={
                "name": "",
                "email": "reader@example.com",
                "body": "This comment has no name.",
                "form_token": CommentForm().initial["form_token"],
                "company_website": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), comment_count)
        self.assertContains(response, "This field is required")

    def test_new_comments_are_pending_moderation(self):
        response = self.client.post(
            reverse("blog:post_comment", args=[self.published_post.id]),
            data={
                "name": "Thoughtful Reader",
                "email": "reader3@example.com",
                "body": "A useful question about this implementation.",
                "form_token": CommentForm().initial["form_token"],
                "company_website": "",
            },
        )

        self.assertRedirects(response, f"{self.published_post.get_absolute_url()}#comments", fetch_redirect_response=False)
        response = self.client.get(self.published_post.get_absolute_url())
        pending = Comment.objects.get(name="Thoughtful Reader")
        self.assertFalse(pending.active)
        self.assertContains(response, "submitted for review")
        self.assertNotContains(
            response,
            'class="card-copy">A useful question about this implementation.',
        )

    def test_comment_with_many_links_is_rejected(self):
        response = self.client.post(
            reverse("blog:post_comment", args=[self.published_post.id]),
            data={
                "name": "Promoter",
                "email": "promoter@example.com",
                "body": "Buy https://one.example https://two.example https://three.example",
                "form_token": CommentForm().initial["form_token"],
                "company_website": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please remove extra links")
        self.assertFalse(Comment.objects.filter(name="Promoter").exists())

    def test_comment_honeypot_blocks_spam_without_saving(self):
        comment_count = Comment.objects.count()

        response = self.client.post(
            reverse("blog:post_comment", args=[self.published_post.id]),
            data={
                "name": "Spam Bot",
                "email": "bot@example.com",
                "body": "Buy spam links now.",
                "form_token": CommentForm().initial["form_token"],
                "company_website": "https://spam.example.com",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), comment_count)

    def test_authenticated_user_without_email_can_comment_with_entered_email(self):
        self.author.email = ""
        self.author.save(update_fields=["email"])
        self.client.force_login(self.author)

        response = self.client.get(self.published_post.get_absolute_url())
        self.assertContains(response, 'name="email"')

        response = self.client.post(
            reverse("blog:post_comment", args=[self.published_post.id]),
            data={
                "email": "reader@example.com",
                "body": "This authenticated comment should appear.",
                "form_token": CommentForm().initial["form_token"],
                "company_website": "",
            },
        )

        self.assertRedirects(response, f"{self.published_post.get_absolute_url()}#comments", fetch_redirect_response=False)
        response = self.client.get(self.published_post.get_absolute_url())
        self.assertContains(response, "Your comment has been submitted for review")
        self.assertContains(response, "Konrad Kadzielawa")
        self.assertNotContains(response, 'class="card-copy">This authenticated comment should appear.')
        self.assertTrue(
            Comment.objects.filter(
                post=self.published_post,
                name="Konrad Kadzielawa",
                email="reader@example.com",
                body="This authenticated comment should appear.",
                active=False,
            ).exists()
        )

    def test_blog_list_gracefully_handles_invalid_pagination(self):
        response = self.client.get(reverse("blog:post_list"), {"page": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Analytics Post")

    def test_comments_require_their_own_signed_token(self):
        from pages.forms import ContactForm

        for token in ["", ContactForm().initial["form_token"]]:
            response = self.client.post(
                reverse("blog:post_comment", args=[self.published_post.id]),
                {"name": "Reader", "email": "reader@example.com", "body": "A thoughtful comment.", "form_token": token},
            )
            self.assertContains(response, "submit this form again")
        self.assertFalse(Comment.objects.filter(name="Reader").exists())

    def test_comment_length_is_bounded(self):
        response = self.client.post(
            reverse("blog:post_comment", args=[self.published_post.id]),
            {"name": "Reader", "email": "reader@example.com", "body": "x" * 3001, "form_token": CommentForm().initial["form_token"]},
        )
        self.assertContains(response, "at most 3000 characters")
        self.assertFalse(Comment.objects.filter(name="Reader").exists())

    def test_comment_replay_and_ip_spoofing_are_blocked(self):
        payload = {"name": "Reader", "email": "reader@example.com", "body": "A thoughtful comment.", "form_token": CommentForm().initial["form_token"]}
        endpoint = reverse("blog:post_comment", args=[self.published_post.id])
        self.assertEqual(self.client.post(endpoint, payload).status_code, 302)
        self.assertEqual(self.client.post(endpoint, payload).status_code, 409)
        for attempt in range(3):
            payload["form_token"] = CommentForm().initial["form_token"]
            payload["email"] = f"reader{attempt}@example.com"
            response = self.client.post(endpoint, payload, HTTP_X_FORWARDED_FOR=f"198.51.100.{attempt}")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Comment.objects.filter(name="Reader").count(), 2)

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
