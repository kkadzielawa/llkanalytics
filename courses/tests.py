from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Category, Course


@override_settings(SECURE_SSL_REDIRECT=False)
class CourseModelAndViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Python", slug="python")
        cls.available_course = Course.objects.create(
            category=cls.category,
            name="Python for Analytics",
            slug="python-for-analytics",
            description="A practical Python course for analytics teams.",
            price=Decimal("99.00"),
            available=True,
        )
        cls.unavailable_course = Course.objects.create(
            category=cls.category,
            name="Retired Python Course",
            slug="retired-python-course",
            description="This course should not be publicly visible.",
            price=Decimal("49.00"),
            available=False,
        )

    def test_category_absolute_url(self):
        self.assertEqual(self.category.get_absolute_url(), "/courses/python")

    def test_course_list_and_detail_routes_render(self):
        response = self.client.get(reverse("courses:course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Analytics")
        self.assertNotContains(response, "Retired Python Course")

        response = self.client.get(reverse("courses:course_list_by_category", args=[self.category.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for Analytics")

        response = self.client.get(self.available_course.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add to cart")

    def test_unavailable_course_detail_is_hidden(self):
        response = self.client.get(self.unavailable_course.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_price_constraint_rejects_negative_values(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Course.objects.create(
                    category=self.category,
                    name="Broken Price",
                    slug="broken-price",
                    description="Should fail.",
                    price=Decimal("-1.00"),
                    available=True,
                )

    def test_duplicate_slug_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Course.objects.create(
                    category=self.category,
                    name="Another Python Course",
                    slug="python-for-analytics",
                    description="Duplicate slug should fail.",
                    price=Decimal("79.00"),
                    available=True,
                )
