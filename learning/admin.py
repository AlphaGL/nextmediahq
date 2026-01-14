# admin.py - Updated with JSON upload functionality
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages
from django import forms
from .models import (
    Subject, Material, ExamYear, Question, 
    Option, Explanation, Exam, Answer, StudentProgress, StudentProfile
)
import json


# JSON Upload Form
class JSONUploadForm(forms.Form):
    json_file = forms.FileField(
        label='Upload JSON File',
        help_text='Upload a JSON file containing questions in the specified format',
        widget=forms.FileInput(attrs={'accept': '.json'})
    )
    json_text = forms.CharField(
        label='Or Paste JSON Content',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 15,
            'placeholder': 'Paste your JSON content here...'
        }),
        help_text='Alternatively, paste the JSON content directly'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        json_file = cleaned_data.get('json_file')
        json_text = cleaned_data.get('json_text')
        
        if not json_file and not json_text:
            raise forms.ValidationError("Please provide either a JSON file or paste JSON content.")
        
        return cleaned_data


# Register StudentProfile
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'registration_number', 'phone_number', 'created_at']
    search_fields = ['user__username', 'registration_number', 'user__email', 'phone_number']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Student Details', {
            'fields': ('registration_number', 'phone_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']
    list_filter = ['created_at']


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'material_type', 'created_by', 'has_video', 'views', 'created_at']
    list_filter = ['material_type', 'subject', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['views', 'created_at', 'updated_at', 'get_embed_preview']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('subject', 'title', 'material_type')
        }),
        ('Content', {
            'fields': ('content', 'file_url', 'cloudinary_public_id')
        }),
        ('Video Tutorial', {
            'fields': ('video_url', 'get_embed_preview'),
            'description': 'Add YouTube video URL for tutorial content'
        }),
        ('Metadata', {
            'fields': ('created_by', 'views', 'created_at', 'updated_at')
        }),
    )
    
    def has_video(self, obj):
        return bool(obj.video_url)
    has_video.boolean = True
    has_video.short_description = 'Has Video'
    
    def get_embed_preview(self, obj):
        if obj.video_url:
            embed_url = obj.get_youtube_embed_url()
            if embed_url:
                return f'<iframe width="560" height="315" src="{embed_url}" frameborder="0" allowfullscreen></iframe>'
            return 'Invalid YouTube URL'
        return 'No video URL provided'
    get_embed_preview.short_description = 'Video Preview'
    get_embed_preview.allow_tags = True


class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    fields = ['option_label', 'option_text', 'is_correct']


class ExplanationInline(admin.StackedInline):
    model = Explanation
    extra = 1
    fields = ['explanation_text', 'additional_resources']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_number', 'exam_year', 'question_type', 'marks', 'get_subject']
    list_filter = ['question_type', 'exam_year__subject', 'exam_year__year']
    search_fields = ['question_text']
    inlines = [OptionInline, ExplanationInline]
    
    def get_subject(self, obj):
        return obj.exam_year.subject.name
    get_subject.short_description = 'Subject'


@admin.register(ExamYear)
class ExamYearAdmin(admin.ModelAdmin):
    list_display = ['subject', 'year', 'session', 'question_count']
    list_filter = ['subject', 'year']
    search_fields = ['subject__name', 'year', 'session']
    actions = ['upload_questions_json']
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('upload-json/', self.admin_site.admin_view(self.upload_json_view), name='examyear_upload_json'),
        ]
        return custom_urls + urls
    
    def upload_json_view(self, request):
        if request.method == 'POST':
            form = JSONUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    # Get JSON data from file or text
                    if form.cleaned_data.get('json_file'):
                        json_data = json.load(form.cleaned_data['json_file'])
                    else:
                        json_data = json.loads(form.cleaned_data['json_text'])
                    
                    # Process the JSON data
                    result = self.process_json_upload(json_data, request.user)
                    
                    messages.success(request, f"Successfully uploaded {result['questions_created']} questions!")
                    return redirect('..')
                    
                except json.JSONDecodeError as e:
                    messages.error(request, f"Invalid JSON format: {str(e)}")
                except Exception as e:
                    messages.error(request, f"Error processing upload: {str(e)}")
        else:
            form = JSONUploadForm()
        
        context = {
            'form': form,
            'title': 'Upload Questions from JSON',
            'site_title': 'Django Admin',
            'site_header': 'Administration',
            'opts': self.model._meta,
        }
        return render(request, 'admin/upload_json.html', context)
    
    def process_json_upload(self, json_data, user):
        """Process the uploaded JSON and create questions"""
        # Get or create subject
        subject, created = Subject.objects.get_or_create(
            code=json_data['subject_code'],
            defaults={
                'name': json_data['subject_name'],
                'description': f"Subject for {json_data['subject_name']}"
            }
        )
        
        # Get or create exam year
        exam_year, created = ExamYear.objects.get_or_create(
            subject=subject,
            year=json_data['year'],
            session=json_data['session'],
            defaults={
                'description': f"{json_data['subject_name']} - {json_data['year']} {json_data['session']}"
            }
        )
        
        questions_created = 0
        
        # Create questions
        for q_data in json_data['questions']:
            # Create or update question
            question, created = Question.objects.update_or_create(
                exam_year=exam_year,
                question_number=q_data['number'],
                defaults={
                    'question_text': q_data['question'],
                    'question_type': q_data['question_type'],
                    'marks': q_data['marks']
                }
            )
            
            # Delete existing options if updating
            if not created:
                question.options.all().delete()
            
            # Create options
            if 'options' in q_data and q_data['options']:
                for label, text in q_data['options'].items():
                    is_correct = (label == q_data['correct_option'])
                    Option.objects.create(
                        question=question,
                        option_label=label,
                        option_text=text,
                        is_correct=is_correct
                    )
            
            # Create or update explanation
            if 'explanation' in q_data and q_data['explanation']:
                explanation_text = q_data['explanation']
                
                # Add option analysis to explanation if available
                if 'option_analysis' in q_data and q_data['option_analysis']:
                    explanation_text += "\n\nOption Analysis:\n"
                    for label, analysis in q_data['option_analysis'].items():
                        explanation_text += f"\n{label}: {analysis}"
                
                # Add CBT tip if available
                additional_resources = ""
                if 'cbt_tip' in q_data and q_data['cbt_tip']:
                    additional_resources = f"CBT Tip: {q_data['cbt_tip']}"
                
                Explanation.objects.update_or_create(
                    question=question,
                    defaults={
                        'explanation_text': explanation_text,
                        'additional_resources': additional_resources
                    }
                )
            
            questions_created += 1
        
        return {
            'questions_created': questions_created,
            'subject': subject,
            'exam_year': exam_year
        }
    
    def upload_questions_json(self, request, queryset):
        """Admin action to upload questions"""
        return redirect('admin:examyear_upload_json')
    upload_questions_json.short_description = "Upload questions from JSON"


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['question', 'selected_option', 'is_correct', 'answered_at', 'time_taken_seconds']
    can_delete = False


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['student', 'exam_year', 'mode', 'score', 'is_completed', 'started_at']
    list_filter = ['mode', 'is_completed', 'exam_year__subject', 'started_at']
    search_fields = ['student__username', 'exam_year__subject__name']
    readonly_fields = ['exam_id', 'started_at', 'score', 'total_marks']
    inlines = [AnswerInline]
    
    fieldsets = (
        ('Exam Details', {
            'fields': ('exam_year', 'student', 'mode', 'exam_id')
        }),
        ('Timing', {
            'fields': ('started_at', 'submitted_at', 'duration_minutes', 'is_completed')
        }),
        ('Results', {
            'fields': ('score', 'total_marks')
        }),
    )


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['exam', 'question', 'selected_option', 'is_correct', 'answered_at']
    list_filter = ['is_correct', 'answered_at']
    search_fields = ['exam__student__username', 'question__question_text']
    readonly_fields = ['is_correct', 'answered_at']


@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'total_exams_taken', 'average_score', 'last_activity']
    list_filter = ['subject', 'last_activity']
    search_fields = ['student__username', 'subject__name']
    readonly_fields = ['last_activity']
    filter_horizontal = ['materials_read']