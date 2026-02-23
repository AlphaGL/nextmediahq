# models.py - Updated with video_url field + CGPA Calculator models
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import re


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    registration_number = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.registration_number}"
    
    class Meta:
        ordering = ['-created_at']

        
class Subject(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Material(models.Model):
    MATERIAL_TYPES = [
        ('pdf', 'PDF Document'),
        ('text', 'Text Content'),
        ('image', 'Image'),
    ]
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=300)
    material_type = models.CharField(max_length=10, choices=MATERIAL_TYPES, null=True, blank=True)
    content = models.TextField()
    file_url = models.URLField(max_length=500, blank=True, null=True)
    cloudinary_public_id = models.CharField(max_length=255, blank=True, null=True)
    video_url = models.URLField(max_length=500, blank=True, null=True, help_text="YouTube video URL for tutorial")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title
    
    def get_youtube_embed_url(self):
        """Convert YouTube URL to embed format"""
        if not self.video_url:
            return None
        
        patterns = [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.video_url)
            if match:
                video_id = match.group(1)
                video_id = video_id.split('&')[0].split('?')[0]
                return f"https://www.youtube.com/embed/{video_id}"
        
        return None
    
    def get_youtube_video_id(self):
        """Extract YouTube video ID from URL"""
        if not self.video_url:
            return None
        
        patterns = [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]+)',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.video_url)
            if match:
                video_id = match.group(1)
                return video_id.split('&')[0].split('?')[0]
        
        return None
    
    class Meta:
        ordering = ['-created_at']


class ExamYear(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exam_years')
    year = models.IntegerField()
    session = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.subject.name} - {self.year} {self.session}"
    
    class Meta:
        ordering = ['-year', 'subject']
        unique_together = ['subject', 'year', 'session']


class Question(models.Model):
    QUESTION_TYPES = [
        ('multiple', 'Multiple Choice'),
        ('true_false', 'True/False'),
    ]
    
    exam_year = models.ForeignKey(ExamYear, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple')
    question_number = models.IntegerField()
    marks = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Q{self.question_number} - {self.exam_year}"
    
    class Meta:
        ordering = ['exam_year', 'question_number']
        unique_together = ['exam_year', 'question_number']


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    option_label = models.CharField(max_length=5)
    
    def __str__(self):
        return f"{self.option_label}: {self.option_text[:50]}"
    
    class Meta:
        ordering = ['option_label']
        unique_together = ['question', 'option_label']


class Explanation(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='explanation')
    explanation_text = models.TextField()
    additional_resources = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Explanation for {self.question}"


class Exam(models.Model):
    MODE_CHOICES = [
        ('exam', 'Exam Mode'),
        ('test', 'Test Mode'),
    ]
    
    exam_year = models.ForeignKey(ExamYear, on_delete=models.CASCADE, related_name='exams')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exams')
    mode = models.CharField(max_length=10, choices=MODE_CHOICES)
    exam_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)
    is_completed = models.BooleanField(default=False)
    score = models.FloatField(null=True, blank=True)
    total_marks = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.student.username} - {self.exam_year} ({self.mode})"
    
    class Meta:
        ordering = ['-started_at']
    
    def calculate_score(self):
        correct = self.answers.filter(is_correct=True).count()
        total = self.answers.count()
        if total > 0:
            self.score = (correct / total) * 100
            self.total_marks = sum([ans.question.marks for ans in self.answers.filter(is_correct=True)])
        else:
            self.score = 0
            self.total_marks = 0
        self.save()
        return self.score


class Answer(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    time_taken_seconds = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        self.is_correct = self.selected_option.is_correct
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.exam.student.username} - Q{self.question.question_number}"
    
    class Meta:
        unique_together = ['exam', 'question']


class StudentProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    materials_read = models.ManyToManyField(Material, blank=True)
    total_exams_taken = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student.username} - {self.subject.name}"
    
    class Meta:
        unique_together = ['student', 'subject']
        verbose_name_plural = "Student Progress"


# ══════════════════════════════════════════════════════════════
#  CGPA CALCULATOR MODELS
# ══════════════════════════════════════════════════════════════

class Semester(models.Model):
    """Represents an academic semester / level for a student"""
    LEVEL_CHOICES = [
        (100, '100 Level'),
        (200, '200 Level'),
        (300, '300 Level'),
        (400, '400 Level'),
        (500, '500 Level'),
        (600, '600 Level'),
        (700, '700 Level'),
    ]
    SEMESTER_CHOICES = [
        ('first', 'First Semester'),
        ('second', 'Second Semester'),
    ]

    student   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='semesters')
    level     = models.IntegerField(choices=LEVEL_CHOICES)
    semester  = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    session   = models.CharField(max_length=20, help_text='e.g. 2023/2024', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['level', 'semester']
        unique_together = ['student', 'level', 'semester']

    def __str__(self):
        return f"{self.get_level_display()} – {self.get_semester_display()} ({self.session})"

    def gpa(self):
        """Return GPA for this semester (0.00 – 5.00)."""
        courses = self.courses.all()
        if not courses:
            return 0.0
        total_points = sum(c.credit_units * c.grade_point for c in courses)
        total_units  = sum(c.credit_units for c in courses)
        return round(total_points / total_units, 2) if total_units else 0.0

    def total_units(self):
        return sum(c.credit_units for c in self.courses.all())

    def total_points(self):
        return sum(c.credit_units * c.grade_point for c in self.courses.all())


class CourseResult(models.Model):
    """A single course result within a semester"""
    GRADE_CHOICES = [
        ('A', 'A  (70 – 100)'),
        ('B', 'B  (60 – 69)'),
        ('C', 'C  (50 – 59)'),
        ('D', 'D  (45 – 49)'),
        ('E', 'E  (40 – 44)'),
        ('F', 'F  (0  – 39)'),
    ]

    # 5-point scale (standard Nigerian universities)
    GRADE_POINT_MAP = {
        'A': 5.0,
        'B': 4.0,
        'C': 3.0,
        'D': 2.0,
        'E': 1.0,
        'F': 0.0,
    }

    semester     = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='courses')
    course_code  = models.CharField(max_length=20)
    course_title = models.CharField(max_length=200)
    credit_units = models.PositiveSmallIntegerField(default=2)
    grade        = models.CharField(max_length=2, choices=GRADE_CHOICES)
    score        = models.FloatField(null=True, blank=True, help_text='Raw score out of 100 (optional)')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['course_code']

    def __str__(self):
        return f"{self.course_code} – {self.grade}"

    @property
    def grade_point(self):
        return self.GRADE_POINT_MAP.get(self.grade, 0.0)

    @property
    def weighted_point(self):
        return self.credit_units * self.grade_point