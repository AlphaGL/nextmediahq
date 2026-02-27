# views.py - Updated with fixes for exam submission + CGPA Calculator views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Avg, Count, Q
from .models import (
    Subject, Material, ExamYear, Question,
    Option, Explanation, Exam, Answer, StudentProgress,
    Semester, CourseResult
)
from .forms import (
    MaterialUploadForm, QuestionForm, StudentRegistrationForm,
    StudentLoginForm, CustomPasswordResetForm,
    SemesterForm, CourseResultForm
)
from django.views.decorators.http import require_http_methods
import json
import cloudinary
import cloudinary.uploader
from io import BytesIO

# PDF processing (works on Vercel)
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# Image processing (basic support only - no OCR on Vercel)
try:
    from PIL import Image
    IMAGE_SUPPORT = True
except ImportError:
    IMAGE_SUPPORT = False


# ══════════════════════════════════════════════════════════════
#  HOME & AUTH VIEWS
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════

@login_required
def dashboard(request):
    user_progress = StudentProgress.objects.filter(student=request.user)
    recent_exams  = Exam.objects.filter(student=request.user, is_completed=True).order_by('-submitted_at')[:5]
    subjects      = Subject.objects.all()

    # CGPA summary for dashboard widget
    semesters    = Semester.objects.filter(student=request.user).prefetch_related('courses')
    total_points = sum(s.total_points() for s in semesters)
    total_units  = sum(s.total_units()  for s in semesters)
    cgpa         = round(total_points / total_units, 2) if total_units else None

    context = {
        'progress':     user_progress,
        'recent_exams': recent_exams,
        'subjects':     subjects,
        'cgpa':         cgpa,
        'cgpa_class':   _cgpa_class(cgpa or 0),
    }
    return render(request, 'learning/dashboard.html', context)


# ══════════════════════════════════════════════════════════════
#  MATERIAL VIEWS
# ══════════════════════════════════════════════════════════════

@login_required
def materials_list(request, subject_id=None):
    if subject_id:
        subject   = get_object_or_404(Subject, id=subject_id)
        materials = Material.objects.filter(subject=subject)
    else:
        materials = Material.objects.all()
        subject   = None
    
    subjects = Subject.objects.all()
    
    context = {
        'materials':       materials,
        'subjects':        subjects,
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


# ══════════════════════════════════════════════════════════════
#  EXAM YEAR & QUESTION VIEWS
# ══════════════════════════════════════════════════════════════

@login_required
def exam_years_list(request, subject_id):
    subject    = get_object_or_404(Subject, id=subject_id)
    exam_years = ExamYear.objects.filter(subject=subject).annotate(
        question_count=Count('questions')
    )
    
    context = {
        'subject':    subject,
        'exam_years': exam_years,
    }
    return render(request, 'learning/exam_years_list.html', context)


@login_required
def start_exam(request, exam_year_id, mode):
    if mode not in ['exam', 'test']:
        messages.error(request, 'Invalid exam mode.')
        return redirect('learning:home')
    
    exam_year = get_object_or_404(ExamYear, id=exam_year_id)
    
    if exam_year.questions.count() == 0:
        messages.error(request, 'This exam has no questions yet.')
        return redirect('learning:exam_years_list', subject_id=exam_year.subject.id)
    
    exam = Exam.objects.create(
        exam_year=exam_year,
        student=request.user,
        mode=mode,
        duration_minutes=40 if mode == 'exam' else 45
    )
    
    return redirect('learning:take_exam', exam_id=exam.exam_id)


@login_required
def take_exam(request, exam_id):
    exam = get_object_or_404(Exam, exam_id=exam_id, student=request.user)
    
    if exam.is_completed:
        return redirect('learning:exam_results', exam_id=exam.exam_id)
    
    questions = exam.exam_year.questions.prefetch_related('options').order_by('question_number')
    
    answered_dict = {}
    for answer in exam.answers.select_related('selected_option'):
        answered_dict[answer.question_id] = {
            'option_id':  answer.selected_option_id,
            'is_correct': answer.is_correct
        }
    
    answered_question_ids = list(answered_dict.keys())
    
    questions_with_explanations = []
    if exam.mode == 'test':
        for question in questions:
            try:
                explanation = question.explanation
            except Explanation.DoesNotExist:
                explanation = None
            
            answer_info = answered_dict.get(question.id)
            
            questions_with_explanations.append({
                'question':          question,
                'explanation':       explanation,
                'answered':          answer_info is not None,
                'selected_option_id': answer_info['option_id'] if answer_info else None,
                'is_correct':        answer_info['is_correct'] if answer_info else None
            })
    
    context = {
        'exam':                        exam,
        'questions':                   questions,
        'answered':                    answered_question_ids,
        'answered_dict_json':          json.dumps(answered_dict),
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
        option_id   = data.get('option_id')
        time_taken  = data.get('time_taken', 0)
        
        question = get_object_or_404(Question, id=question_id, exam_year=exam.exam_year)
        option   = get_object_or_404(Option, id=option_id, question=question)
        
        answer, created = Answer.objects.update_or_create(
            exam=exam,
            question=question,
            defaults={
                'selected_option':   option,
                'time_taken_seconds': time_taken
            }
        )
        
        response_data = {
            'success':         True,
            'is_correct':      answer.is_correct,
            'answered_count':  exam.answers.count(),
            'total_questions': exam.exam_year.questions.count()
        }
        
        if exam.mode == 'test':
            correct_option = question.options.filter(is_correct=True).values('id').first()
            response_data['correct_option_id'] = correct_option['id'] if correct_option else None
            
            try:
                explanation = Explanation.objects.filter(question=question).values(
                    'explanation_text', 'additional_resources'
                ).first()
                
                if explanation:
                    response_data['explanation'] = {
                        'text':      explanation['explanation_text'],
                        'resources': explanation['additional_resources'] or ''
                    }
                else:
                    response_data['explanation'] = None
            except Exception:
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
        
        exam.is_completed = True
        exam.submitted_at = timezone.now()
        exam.calculate_score()
        
        progress, created = StudentProgress.objects.get_or_create(
            student=request.user,
            subject=exam.exam_year.subject
        )
        progress.total_exams_taken += 1
        
        avg_score = Exam.objects.filter(
            student=request.user,
            exam_year__subject=exam.exam_year.subject,
            is_completed=True
        ).aggregate(Avg('score'))['score__avg']
        
        progress.average_score = avg_score or 0
        progress.save()
        
        return JsonResponse({
            'success':      True,
            'redirect_url': reverse('learning:exam_results', kwargs={'exam_id': str(exam.exam_id)})
        })
    except Exception as e:
        import traceback
        print(f"Error in submit_exam: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


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
    
    questions_data = []
    for answer in answers:
        correct_option = answer.question.options.filter(is_correct=True).first()
        
        try:
            explanation = answer.question.explanation
        except Explanation.DoesNotExist:
            explanation = None
        
        questions_data.append({
            'question':        answer.question,
            'selected_option': answer.selected_option,
            'is_correct':      answer.is_correct,
            'correct_option':  correct_option,
            'explanation':     explanation,
            'all_options':     answer.question.options.all().order_by('option_label')
        })
    
    total_questions  = answers.count()
    correct_answers  = answers.filter(is_correct=True).count()
    incorrect_answers = total_questions - correct_answers
    
    context = {
        'exam':              exam,
        'questions_data':    questions_data,
        'show_explanations': True,
        'total_questions':   total_questions,
        'correct_answers':   correct_answers,
        'incorrect_answers': incorrect_answers,
    }
    return render(request, 'learning/exam_results.html', context)


# ══════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_file   = BytesIO(file.read())
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
        text  = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        return f"Error extracting text from image: {str(e)}"


# ══════════════════════════════════════════════════════════════
#  CGPA CALCULATOR VIEWS
# ══════════════════════════════════════════════════════════════

def _cgpa_class(cgpa):
    """Return human-readable degree classification (5-point scale)."""
    if cgpa >= 4.50:
        return ('First Class', 'success')
    elif cgpa >= 3.50:
        return ('Second Class Upper', 'primary')
    elif cgpa >= 2.40:
        return ('Second Class Lower', 'info')
    elif cgpa >= 1.50:
        return ('Third Class', 'warning')
    elif cgpa > 0:
        return ('Pass', 'danger')
    else:
        return ('No Results Yet', 'secondary')


@login_required
def cgpa_dashboard(request):
    """Main CGPA page: shows all semesters + cumulative CGPA."""
    semesters = (
        Semester.objects
        .filter(student=request.user)
        .prefetch_related('courses')
        .order_by('level', 'semester')
    )

    total_points = sum(s.total_points() for s in semesters)
    total_units  = sum(s.total_units()  for s in semesters)
    cgpa = round(total_points / total_units, 2) if total_units else 0.0

    semester_stats = [
        {
            'obj':          s,
            'gpa':          s.gpa(),
            'total_units':  s.total_units(),
            'course_count': s.courses.count(),
        }
        for s in semesters
    ]

    context = {
        'semesters':      semesters,
        'semester_stats': semester_stats,
        'cgpa':           cgpa,
        'total_units':    total_units,
        'total_points':   total_points,
        'cgpa_class':     _cgpa_class(cgpa),
    }
    return render(request, 'learning/cgpa/dashboard.html', context)


@login_required
def semester_create(request):
    if request.method == 'POST':
        form = SemesterForm(request.POST)
        if form.is_valid():
            semester = form.save(commit=False)
            semester.student = request.user
            try:
                semester.save()
                messages.success(request, 'Semester added successfully.')
                return redirect('learning:semester_detail', pk=semester.pk)
            except Exception:
                messages.error(request, 'This semester already exists in your record.')
    else:
        form = SemesterForm()

    return render(request, 'learning/cgpa/semester_form.html', {
        'form':   form,
        'action': 'Add Semester',
    })


@login_required
def semester_detail(request, pk):
    semester = get_object_or_404(Semester, pk=pk, student=request.user)
    courses  = semester.courses.all().order_by('course_code')

    context = {
        'semester': semester,
        'courses':  courses,
        'gpa':      semester.gpa(),
    }
    return render(request, 'learning/cgpa/semester_detail.html', context)


@login_required
def semester_edit(request, pk):
    semester = get_object_or_404(Semester, pk=pk, student=request.user)

    if request.method == 'POST':
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            form.save()
            messages.success(request, 'Semester updated.')
            return redirect('learning:semester_detail', pk=semester.pk)
    else:
        form = SemesterForm(instance=semester)

    return render(request, 'learning/cgpa/semester_form.html', {
        'form':     form,
        'semester': semester,
        'action':   'Edit Semester',
    })


@login_required
def semester_delete(request, pk):
    semester = get_object_or_404(Semester, pk=pk, student=request.user)

    if request.method == 'POST':
        semester.delete()
        messages.success(request, 'Semester deleted.')
        return redirect('learning:cgpa_dashboard')

    return render(request, 'learning/cgpa/semester_confirm_delete.html', {
        'semester': semester,
    })


@login_required
def course_create(request, semester_pk):
    semester = get_object_or_404(Semester, pk=semester_pk, student=request.user)

    if request.method == 'POST':
        form = CourseResultForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.semester = semester
            course.save()
            messages.success(request, f'{course.course_code} added.')
            return redirect('learning:semester_detail', pk=semester.pk)
    else:
        form = CourseResultForm()

    return render(request, 'learning/cgpa/course_form.html', {
        'form':     form,
        'semester': semester,
        'action':   'Add Course',
    })


@login_required
def course_edit(request, pk):
    course   = get_object_or_404(CourseResult, pk=pk, semester__student=request.user)
    semester = course.semester

    if request.method == 'POST':
        form = CourseResultForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated.')
            return redirect('learning:semester_detail', pk=semester.pk)
    else:
        form = CourseResultForm(instance=course)

    return render(request, 'learning/cgpa/course_form.html', {
        'form':     form,
        'course':   course,
        'semester': semester,
        'action':   'Edit Course',
    })


@login_required
def course_delete(request, pk):
    course   = get_object_or_404(CourseResult, pk=pk, semester__student=request.user)
    semester = course.semester

    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Course removed.')
        return redirect('learning:semester_detail', pk=semester.pk)

    return render(request, 'learning/cgpa/course_confirm_delete.html', {
        'course':   course,
        'semester': semester,
    })  