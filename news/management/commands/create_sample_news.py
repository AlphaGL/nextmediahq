# news/management/commands/create_sample_news.py
from django.core.management.base import BaseCommand
from news.models import News, Category, School
from django.utils import timezone
import random

class Command(BaseCommand):
    help = 'Create sample news articles'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=20, help='Number of news articles to create')

    def handle(self, *args, **options):
        count = options['count']
        
        # Sample news data
        sample_titles = [
            "New Academic Session Begins with Record Enrollment",
            "University Launches Innovative Research Program",
            "Students Excel in International Competition",
            "Campus Infrastructure Gets Major Upgrade",
            "Professor Wins Prestigious Research Award",
            "New Partnership with Industry Leaders Announced",
            "Student Union Elections Conclude Successfully",
            "University Ranks High in Latest Assessment",
            "Technology Center Opens to Students",
            "Graduation Ceremony Celebrates Achievements",
            "Global Climate Summit Addresses Environmental Concerns",
            "Technology Giant Announces Breakthrough Innovation",
            "Economic Indicators Show Positive Growth Trends",
            "Healthcare Advances Promise Better Treatment Options",
            "Space Mission Achieves Historic Milestone",
            "Sports Championship Delivers Thrilling Matches",
            "Cultural Festival Showcases Diverse Traditions",
            "Educational Reform Initiative Gains Support",
            "Renewable Energy Project Shows Promising Results",
            "International Cooperation Agreement Signed",
        ]
        
        sample_contents = [
            "This is a comprehensive news article about recent developments in education and research. The initiative aims to improve academic standards and foster innovation among students and faculty members.",
            "Recent developments have shown significant progress in various academic and research areas. The university community has responded positively to these changes and improvements.",
            "The latest announcement brings exciting opportunities for students and faculty to engage in cutting-edge research and academic pursuits that will benefit the broader community.",
            "Officials have confirmed that the new program will provide enhanced learning opportunities and resources for students across different departments and faculties.",
            "The development represents a major step forward in academic excellence and research capabilities, positioning the institution for continued growth and success.",
        ]
        
        categories = list(Category.objects.all())
        schools = list(School.objects.all())
        
        if not categories:
            self.stdout.write(self.style.ERROR('No categories found. Please run setup_initial_data first.'))
            return
        
        created_count = 0
        
        for i in range(count):
            title = random.choice(sample_titles)
            content = random.choice(sample_contents)
            category = random.choice(categories)
            
            # Some news articles will have schools, others won't
            school = random.choice(schools + [None, None])  # Higher chance of no school
            
            # Create the news article
            news = News.objects.create(
                title=f"{title} - {i+1}",
                content=content * 3,  # Make content longer
                excerpt=content[:200] + "...",
                category=category,
                school=school,
                is_featured=random.choice([True, False, False, False]),  # 25% chance of being featured
                published_date=timezone.now() - timezone.timedelta(days=random.randint(0, 30))
            )
            
            created_count += 1
            self.stdout.write(f'Created news: {news.title}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} news articles!')
        )