from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]
        verbose_name = "category"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("courses:course_list_by_category", args=[self.slug])


class Course(models.Model):
    category = models.ForeignKey(
        Category, related_name="courses", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    image = models.ImageField(upload_to="courses/%Y/%m/%d", blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["id", "slug"]),
            models.Index(fields=["name"]),
            models.Index(fields=["-created"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(price__gte=0),
                name="course_price_gte_zero",
            )
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("courses:course_detail", args=[self.slug])
