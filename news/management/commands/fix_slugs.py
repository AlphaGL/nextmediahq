from django.core.management.base import BaseCommand
from django.utils.text import slugify
from news.models import School, Category, News

class Command(BaseCommand):
    help = "Fix duplicate slugs safely (PostgreSQL-proof)"

    def fix_slugs(self, model, text_field):
        # Get all existing slugs from DB
        existing_slugs = set(
            model.objects.exclude(slug__isnull=True)
            .values_list("slug", flat=True)
        )

        for obj in model.objects.all():
            text = getattr(obj, text_field)
            base_slug = slugify(text, allow_unicode=True)
            slug = base_slug
            counter = 1

            # Remove its own slug temporarily
            existing_slugs.discard(obj.slug)

            while slug in existing_slugs:
                slug = f"{base_slug}-{counter}"
                counter += 1

            if obj.slug != slug:
                obj.slug = slug
                obj.save(update_fields=["slug"])

            existing_slugs.add(slug)

    def handle(self, *args, **kwargs):
        self.fix_slugs(School, "name")
        self.fix_slugs(Category, "name")
        self.fix_slugs(News, "title")

        self.stdout.write(self.style.SUCCESS("✅ All slugs fixed safely"))
