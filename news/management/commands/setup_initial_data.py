# news/management/commands/setup_initial_data.py
from django.core.management.base import BaseCommand
from news.models import Category, School
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Setup initial data for NextMedia'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial data...')
        
        # Create Categories
        categories = [
            {'name': 'School News', 'description': 'Latest news from educational institutions'},
            {'name': 'Global News', 'description': 'International news and updates'},
            {'name': 'Sports', 'description': 'Sports news and updates'},
            {'name': 'Technology', 'description': 'Technology and innovation news'},
            {'name': 'Education', 'description': 'Educational news and updates'},
            {'name': 'Politics', 'description': 'Political news and updates'},
            {'name': 'Health', 'description': 'Health and medical news'},
            {'name': 'Entertainment', 'description': 'Entertainment and celebrity news'},
        ]
        
        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                slug=slugify(cat_data['name']),
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description']
                }
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')
            else:
                self.stdout.write(f'Category already exists: {category.name}')
        
        # Create Sample Schools
        schools = [
            {'name': 'Federal University of Technology, Owerri', 'abbreviation': 'FUTO'},
            {'name': 'University of Nigeria, Nsukka', 'abbreviation': 'UNN'},
            {'name': 'University of Lagos', 'abbreviation': 'UNILAG'},
            {'name': 'Obafemi Awolowo University', 'abbreviation': 'OAU'},
            {'name': 'University of Ibadan', 'abbreviation': 'UI'},
            {'name': 'Ahmadu Bello University', 'abbreviation': 'ABU'},
            {'name': 'Federal University of Technology, Akure', 'abbreviation': 'FUTA'},
            {'name': 'Lagos State University', 'abbreviation': 'LASU'},
        ]
        
        for school_data in schools:
            school, created = School.objects.get_or_create(
                slug=slugify(school_data['name']),
                defaults={
                    'name': school_data['name'],
                    'abbreviation': school_data['abbreviation']
                }
            )
            if created:
                self.stdout.write(f'Created school: {school.name}')
            else:
                self.stdout.write(f'School already exists: {school.name}')
        
        self.stdout.write(self.style.SUCCESS('Initial data setup completed!'))