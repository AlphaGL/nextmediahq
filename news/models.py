# news/models.py
from django.db import models
from django.utils import timezone
from django.urls import reverse
from cloudinary.models import CloudinaryField
from django.utils.text import slugify
from django.contrib.auth.models import User

class School(models.Model):
    name = models.CharField(max_length=200)
    abbreviation = models.CharField(max_length=10, blank=True)
    description = models.TextField(blank=True)
    logo = CloudinaryField('schools/', blank=True, null=True)
    established = models.DateField(blank=True, null=True)
    website = models.URLField(blank=True)
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Category(models.Model):
    name = models.CharField(max_length=100)
    # description = models.TextField(blank=True)
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

class News(models.Model):
    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(max_length=500, blank=True)
    featured_image = CloudinaryField('news/', blank=True, null=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    author = models.CharField(blank=True)
    published_by = models.ForeignKey(User, on_delete=models.CASCADE )
    published_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.excerpt and self.content:
            self.excerpt = self.content[:200] + "..."
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('news:news_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_date']
        verbose_name_plural = "News"


class PastQuestion(models.Model):
    title = models.CharField(max_length=200)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    cover_image = CloudinaryField('cover_image/', blank=True, null=True)
    start_year = models.IntegerField()
    end_year = models.IntegerField()
    link = models.URLField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.school.name} - {self.subject} ({self.year})"

    class Meta:
        ordering = ['-start_year', '-end_year', 'subject']
