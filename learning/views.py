# views.py - Updated with improved exam modes and navigation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Count, Q
from .models import (
    Subject, Material, ExamYear, Question, 
    Option, Explanation, Exam, Answer, StudentProgress
)
from .forms import MaterialUploadForm, QuestionForm, StudentRegistrationForm, StudentLoginForm, CustomPasswordResetForm
import PyPDF2
from PIL import Image
import pytesseract
import io
from django.views.decorators.http import require_http_methods
import json
import cloudinary
import cloudinary.uploader
from io import BytesIO

# Home and Dashboard Views
def home(request):
    subjects = Subject.objects.all()
    context = {
        'subjects': subjects,
    }
    return render(request, 'learning/home.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('learning:dashboard')
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Registration successful! You can now login with your registration number.')
            return redirect('learning:login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = StudentRegistrationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'learning/register.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('learning:dashboard')
    
    if request.method == 'POST':
        form = StudentLoginForm(request.POST)
        if form.is_valid():
            registration_number = form.cleaned_data['registration_number']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=registration_number, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                next_url = request.GET.get('next')

                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('learning:dashboard')

            else:
                messages.error(request, 'Invalid registration number or password.')
    else:
        form = StudentLoginForm()
    
    context = {
        'form': form,
    }
    return render(request, 'learning/login.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('learning:home')


class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'learning/password_reset.html'
    email_template_name = 'learning/password_reset_email.html'
    subject_template_name = 'learning/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    
    def form_valid(self, form):
        messages.success(self.request, 'Password reset email has been sent to your email address.')
        return super().form_valid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'learning/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your password has been reset successfully. You can now login with your new password.')
        return super().form_valid(form)


@login_required
def dashboard(request):
    user_progress = StudentProgress.objects.filter(student=request.user)
    recent_exams = Exam.objects.filter(student=request.user, is_completed=True).order_by('-submitted_at')[:5]
    subjects = Subject.objects.all()
    
    context = {
        'progress': user_progress,
        'recent_exams': recent_exams,
        'subjects': subjects,
    }
    return render(request, 'learning/dashboard.html', context)


# Material Views
@login_required
def materials_list(request, subject_id=None):
    if subject_id:
        subject = get_object_or_404(Subject, id=subject_id)
        materials = Material.objects.filter(subject=subject)
    else:
        materials = Material.objects.all()
        subject = None
    
    subjects = Subject.objects.all()
    
    context = {
        'materials': materials,
        'subjects': subjects,
        'current_subject': subject,
    }
    return render(request, 'learning/materials_list.html', context)


@login_required
def material_detail(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    material.views += 1
    material.save()
    
    progress, created = StudentProgress.objects.get_or_create(
        student=request.user,
        subject=material.subject
    )
    progress.materials_read.add(material)
    
    context = {
        'material': material,
    }
    return render(request, 'learning/material_detail.html', context)

# Exam Year and Question Views
@login_required
def exam_years_list(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    exam_years = ExamYear.objects.filter(subject=subject).annotate(
        question_count=Count('questions')
    )
    
    context = {
        'subject': subject,
        'exam_years': exam_years,
    }
    return render(request, 'learning/exam_years_list.html', context)


@login_required
def start_exam(request, exam_year_id, mode):
    if mode not in ['exam', 'test']:
        messages.error(request, 'Invalid exam mode.')
        return redirect('learning:home')
    
    exam_year = get_object_or_404(ExamYear, id=exam_year_id)
    
    # Check if exam year has questions
    if exam_year.questions.count() == 0:
        messages.error(request, 'This exam has no questions yet.')
        return redirect('learning:exam_years_list', subject_id=exam_year.subject.id)
    
    exam = Exam.objects.create(
        exam_year=exam_year,
        student=request.user,
        mode=mode,
        duration_minutes=60 if mode == 'exam' else 30
    )
    
    return redirect('learning:take_exam', exam_id=exam.exam_id)


@login_required
def take_exam(request, exam_id):
    exam = get_object_or_404(Exam, exam_id=exam_id, student=request.user)
    
    if exam.is_completed:
        return redirect('learning:exam_results', exam_id=exam.exam_id)
    
    questions = exam.exam_year.questions.prefetch_related('options').order_by('question_number')
    answered = exam.answers.values_list('question_id', flat=True)
    
    # For test mode, get explanations
    questions_with_explanations = []
    if exam.mode == 'test':
        for question in questions:
            try:
                explanation = question.explanation
            except Explanation.DoesNotExist:
                explanation = None
            questions_with_explanations.append({
                'question': question,
                'explanation': explanation
            })
    
    context = {
        'exam': exam,
        'questions': questions,
        'answered': list(answered),
        'questions_with_explanations': questions_with_explanations if exam.mode == 'test' else None,
    }
    return render(request, 'learning/take_exam.html', context)


@login_required
@require_http_methods(["POST"])
def submit_answer(request, exam_id):
    try:
        data = json.loads(request.body)
        exam = get_object_or_404(Exam, exam_id=exam_id, student=request.user)
        
        if exam.is_completed:
            return JsonResponse({'error': 'Exam already completed'}, status=400)
        
        question_id = data.get('question_id')
        option_id = data.get('option_id')
        time_taken = data.get('time_taken', 0)
        
        question = get_object_or_404(Question, id=question_id, exam_year=exam.exam_year)
        option = get_object_or_404(Option, id=option_id, question=question)
        
        # Save or update answer
        answer, created = Answer.objects.update_or_create(
            exam=exam,
            question=question,
            defaults={
                'selected_option': option,
                'time_taken_seconds': time_taken
            }
        )
        
        # For test mode, return correct answer and explanation
        response_data = {
            'success': True,
            'is_correct': answer.is_correct,
            'answered_count': exam.answers.count(),
            'total_questions': exam.exam_year.questions.count()
        }
        
        if exam.mode == 'test':
            correct_option = question.options.filter(is_correct=True).first()
            response_data['correct_option_id'] = correct_option.id if correct_option else None
            
            try:
                explanation = question.explanation
                response_data['explanation'] = {
                    'text': explanation.explanation_text,
                    'resources': explanation.additional_resources
                }
            except Explanation.DoesNotExist:
                response_data['explanation'] = None
        
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def submit_exam(request, exam_id):
    try:
        exam = get_object_or_404(Exam, exam_id=exam_id, student=request.user)
        
        if exam.is_completed:
            return JsonResponse({'error': 'Exam already completed'}, status=400)
        
        # Check if all questions are answered
        total_questions = exam.exam_year.questions.count()
        answered_questions = exam.answers.count()
        
        if answered_questions < total_questions:
            return JsonResponse({
                'error': f'You have only answered {answered_questions} out of {total_questions} questions. Please answer all questions before submitting.',
                'confirm_needed': True
            }, status=400)
        
        exam.is_completed = True
        exam.submitted_at = timezone.now()
        exam.calculate_score()
        
        # Update student progress
        progress, created = StudentProgress.objects.get_or_create(
            student=request.user,
            subject=exam.exam_year.subject
        )
        progress.total_exams_taken += 1
        
        # Calculate average score for this subject
        avg_score = Exam.objects.filter(
            student=request.user,
            exam_year__subject=exam.exam_year.subject,
            is_completed=True
        ).aggregate(Avg('score'))['score__avg']
        
        progress.average_score = avg_score or 0
        progress.save()
        
        return JsonResponse({
            'success': True,
            'redirect_url': f'/exam/results/{exam.exam_id}/'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def exam_results(request, exam_id):
    exam = get_object_or_404(Exam, exam_id=exam_id, student=request.user)
    
    if not exam.is_completed:
        return redirect('learning:take_exam', exam_id=exam.exam_id)
    
    answers = exam.answers.select_related(
        'question', 
        'selected_option',
        'question__explanation'
    ).prefetch_related('question__options').order_by('question__question_number')
    
    # Prepare questions data with correct answers
    questions_data = []
    for answer in answers:
        correct_option = answer.question.options.filter(is_correct=True).first()
        
        try:
            explanation = answer.question.explanation
        except Explanation.DoesNotExist:
            explanation = None
        
        questions_data.append({
            'question': answer.question,
            'selected_option': answer.selected_option,
            'is_correct': answer.is_correct,
            'correct_option': correct_option,
            'explanation': explanation,
            'all_options': answer.question.options.all().order_by('option_label')
        })
    
    # Calculate statistics
    total_questions = answers.count()
    correct_answers = answers.filter(is_correct=True).count()
    incorrect_answers = total_questions - correct_answers
    
    context = {
        'exam': exam,
        'questions_data': questions_data,
        'show_explanations': True,  # Always show explanations in results
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
    }
    return render(request, 'learning/exam_results.html', context)


# Utility functions
def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_file = BytesIO(file.read())
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def extract_text_from_image(file):
    """Extract text from image using OCR"""
    try:
        image = Image.open(file)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        return f"Error extracting text from image: {str(e)}"