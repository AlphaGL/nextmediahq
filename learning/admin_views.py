# learning/admin_views.py - Enhanced with complete CRUD functionality
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.http import JsonResponse, HttpResponse
from .models import (
    Subject, Material, ExamYear, Question, Option, 
    Explanation, Exam, Answer, StudentProgress, StudentProfile
)
from .forms import (
    MaterialUploadForm, ExamYearForm, QuestionForm, 
    OptionFormSet, ExplanationForm
)
import json
from django.db import transaction
import csv
from datetime import datetime
import cloudinary.uploader


@staff_member_required
def custom_admin_dashboard(request):
    """Custom admin dashboard with statistics"""
    context = {
        'total_students': StudentProfile.objects.count(),
        'total_subjects': Subject.objects.count(),
        'total_materials': Material.objects.count(),
        'total_questions': Question.objects.count(),
        'total_exams': Exam.objects.filter(is_completed=True).count(),
        'recent_students': StudentProfile.objects.order_by('-created_at')[:5],
        'recent_exams': Exam.objects.filter(is_completed=True).order_by('-submitted_at')[:10],
        'popular_materials': Material.objects.order_by('-views')[:5],
        'subjects_with_stats': Subject.objects.annotate(
            material_count=Count('materials'),
            question_count=Count('exam_years__questions')
        ),
    }
    return render(request, 'learning/admin/dashboard.html', context)


# ==================== SUBJECT CRUD ====================
@staff_member_required
def subject_list(request):
    """List all subjects with search"""
    query = request.GET.get('q', '')
    subjects = Subject.objects.annotate(
        material_count=Count('materials'),
        exam_count=Count('exam_years')
    )
    
    if query:
        subjects = subjects.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )
    
    subjects = subjects.order_by('name')
    
    context = {
        'subjects': subjects,
        'query': query,
    }
    return render(request, 'learning/admin/subject_list.html', context)


@staff_member_required
def subject_create(request):
    """Create new subject"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        
        if Subject.objects.filter(code=code).exists():
            messages.error(request, f'Subject with code {code} already exists!')
        else:
            Subject.objects.create(name=name, code=code, description=description)
            messages.success(request, f'Subject "{name}" created successfully!')
            return redirect('custom_subject_list')
    
    return render(request, 'learning/admin/subject_form.html', {'action': 'Create'})


@staff_member_required
def subject_edit(request, subject_id):
    """Edit existing subject"""
    subject = get_object_or_404(Subject, id=subject_id)
    
    if request.method == 'POST':
        subject.name = request.POST.get('name')
        subject.code = request.POST.get('code')
        subject.description = request.POST.get('description', '')
        subject.save()
        messages.success(request, f'Subject "{subject.name}" updated successfully!')
        return redirect('custom_subject_list')
    
    context = {
        'subject': subject,
        'action': 'Edit',
    }
    return render(request, 'learning/admin/subject_form.html', context)


@staff_member_required
def subject_delete(request, subject_id):
    """Delete subject with confirmation"""
    subject = get_object_or_404(Subject, id=subject_id)
    
    if request.method == 'POST':
        name = subject.name
        subject.delete()
        messages.success(request, f'Subject "{name}" deleted successfully!')
        return redirect('custom_subject_list')
    
    context = {
        'subject': subject,
        'material_count': subject.materials.count(),
        'exam_count': subject.exam_years.count(),
    }
    return render(request, 'learning/admin/subject_delete.html', context)


# ==================== EXAM YEAR CRUD ====================
@staff_member_required
def exam_year_list(request):
    """List all exam years with filtering"""
    subject_id = request.GET.get('subject')
    query = request.GET.get('q', '')
    
    exam_years = ExamYear.objects.select_related('subject').annotate(
        question_count=Count('questions')
    )
    
    if subject_id:
        exam_years = exam_years.filter(subject_id=subject_id)
    
    if query:
        exam_years = exam_years.filter(
            Q(year__icontains=query) | 
            Q(session__icontains=query) |
            Q(subject__name__icontains=query)
        )
    
    exam_years = exam_years.order_by('-year', 'subject__name')
    subjects = Subject.objects.all()
    
    context = {
        'exam_years': exam_years,
        'subjects': subjects,
        'selected_subject': subject_id,
        'query': query,
    }
    return render(request, 'learning/admin/exam_year_list.html', context)


@staff_member_required
def exam_year_create(request):
    """Create new exam year"""
    if request.method == 'POST':
        form = ExamYearForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam year created successfully!')
            return redirect('custom_exam_year_list')
    else:
        form = ExamYearForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'learning/admin/exam_year_form.html', context)


@staff_member_required
def exam_year_edit(request, exam_year_id):
    """Edit existing exam year"""
    exam_year = get_object_or_404(ExamYear, id=exam_year_id)
    
    if request.method == 'POST':
        form = ExamYearForm(request.POST, instance=exam_year)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exam year updated successfully!')
            return redirect('custom_exam_year_list')
    else:
        form = ExamYearForm(instance=exam_year)
    
    context = {
        'form': form,
        'exam_year': exam_year,
        'action': 'Edit',
    }
    return render(request, 'learning/admin/exam_year_form.html', context)


@staff_member_required
def exam_year_delete(request, exam_year_id):
    """Delete exam year with cascade warning"""
    exam_year = get_object_or_404(ExamYear, id=exam_year_id)
    
    if request.method == 'POST':
        name = str(exam_year)
        exam_year.delete()
        messages.success(request, f'Exam year "{name}" deleted successfully!')
        return redirect('custom_exam_year_list')
    
    context = {
        'exam_year': exam_year,
        'question_count': exam_year.questions.count(),
    }
    return render(request, 'learning/admin/exam_year_delete.html', context)


# ==================== QUESTION CRUD ====================
@staff_member_required
def question_list(request):
    """List all questions with filtering"""
    exam_year_id = request.GET.get('exam_year')
    query = request.GET.get('q', '')
    
    questions = Question.objects.select_related('exam_year__subject').prefetch_related('options')
    
    if exam_year_id:
        questions = questions.filter(exam_year_id=exam_year_id)
    
    if query:
        questions = questions.filter(
            Q(question_text__icontains=query) |
            Q(question_number__icontains=query)
        )
    
    questions = questions.order_by('exam_year', 'question_number')
    exam_years = ExamYear.objects.select_related('subject').all()
    
    context = {
        'questions': questions,
        'exam_years': exam_years,
        'selected_exam_year': exam_year_id,
        'query': query,
    }
    return render(request, 'learning/admin/question_list.html', context)


@staff_member_required
def question_create(request):
    """Create new question with options"""
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save()
            
            # Create options
            option_count = int(request.POST.get('option_count', 4))
            for i in range(option_count):
                label = request.POST.get(f'option_label_{i}')
                text = request.POST.get(f'option_text_{i}')
                is_correct = request.POST.get(f'is_correct_{i}') == 'on'
                
                if label and text:
                    Option.objects.create(
                        question=question,
                        option_label=label,
                        option_text=text,
                        is_correct=is_correct
                    )
            
            # Create explanation if provided
            explanation_text = request.POST.get('explanation_text', '').strip()
            if explanation_text:
                Explanation.objects.create(
                    question=question,
                    explanation_text=explanation_text,
                    additional_resources=request.POST.get('additional_resources', '')
                )
            
            messages.success(request, f'Question {question.question_number} created successfully!')
            return redirect('custom_question_list')
    else:
        form = QuestionForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'learning/admin/question_form.html', context)


@staff_member_required
def question_edit(request, question_id):
    """Edit existing question"""
    question = get_object_or_404(Question, id=question_id)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            question = form.save()
            
            # Delete existing options and recreate
            question.options.all().delete()
            
            option_count = int(request.POST.get('option_count', 4))
            for i in range(option_count):
                label = request.POST.get(f'option_label_{i}')
                text = request.POST.get(f'option_text_{i}')
                is_correct = request.POST.get(f'is_correct_{i}') == 'on'
                
                if label and text:
                    Option.objects.create(
                        question=question,
                        option_label=label,
                        option_text=text,
                        is_correct=is_correct
                    )
            
            # Update or create explanation
            explanation_text = request.POST.get('explanation_text', '').strip()
            if explanation_text:
                Explanation.objects.update_or_create(
                    question=question,
                    defaults={
                        'explanation_text': explanation_text,
                        'additional_resources': request.POST.get('additional_resources', '')
                    }
                )
            
            messages.success(request, f'Question {question.question_number} updated successfully!')
            return redirect('custom_question_list')
    else:
        form = QuestionForm(instance=question)
    
    try:
        explanation = question.explanation
    except Explanation.DoesNotExist:
        explanation = None
    
    context = {
        'form': form,
        'question': question,
        'options': question.options.all().order_by('option_label'),
        'explanation': explanation,
        'action': 'Edit',
    }
    return render(request, 'learning/admin/question_form.html', context)


@staff_member_required
def question_delete(request, question_id):
    """Delete question"""
    question = get_object_or_404(Question, id=question_id)
    
    if request.method == 'POST':
        number = question.question_number
        question.delete()
        messages.success(request, f'Question {number} deleted successfully!')
        return redirect('custom_question_list')
    
    context = {
        'question': question,
    }
    return render(request, 'learning/admin/question_delete.html', context)


# ==================== MATERIAL CRUD ====================
@staff_member_required
def material_list(request):
    """List all materials with filtering"""
    subject_id = request.GET.get('subject')
    material_type = request.GET.get('type')
    query = request.GET.get('q', '')
    
    materials = Material.objects.select_related('subject', 'created_by')
    
    if subject_id:
        materials = materials.filter(subject_id=subject_id)
    
    if material_type:
        materials = materials.filter(material_type=material_type)
    
    if query:
        materials = materials.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )
    
    materials = materials.order_by('-created_at')
    subjects = Subject.objects.all()
    
    context = {
        'materials': materials,
        'subjects': subjects,
        'selected_subject': subject_id,
        'selected_type': material_type,
        'query': query,
        'material_types': Material.MATERIAL_TYPES,
    }
    return render(request, 'learning/admin/material_list.html', context)


@staff_member_required
def material_create(request):
    """Create new material"""
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        title = request.POST.get('title')
        content = request.POST.get('content')
        video_url = request.POST.get('video_url', '')
        
        # Validate required fields
        if not all([subject_id, title, content]):
            messages.error(request, 'Please fill in all required fields (Subject, Title, Content).')
            context = {
                'subjects': Subject.objects.all(),
                'action': 'Create',
                'material': None,
                'post_data': request.POST
            }
            return render(request, 'learning/admin/material_form.html', context)
        
        try:
            subject = Subject.objects.get(id=subject_id)
            
            # Create material
            material = Material.objects.create(
                subject=subject,
                title=title,
                content=content,
                video_url=video_url,
                created_by=request.user
            )
            
            # Handle file upload if provided
            if request.FILES.get('file'):
                uploaded_file = request.FILES['file']
                
                # Upload to cloudinary
                upload_result = cloudinary.uploader.upload(
                    uploaded_file,
                    folder="learning_materials",
                    resource_type="auto"
                )
                
                material.file_url = upload_result['secure_url']
                material.cloudinary_public_id = upload_result['public_id']
                
                # Detect material type from file
                file_extension = uploaded_file.name.split('.')[-1].lower()
                if file_extension == 'pdf':
                    material.material_type = 'pdf'
                elif file_extension in ['jpg', 'jpeg', 'png']:
                    material.material_type = 'image'
                else:
                    material.material_type = 'text'
                
                material.save()
            
            messages.success(request, f'Material "{title}" created successfully!')
            return redirect('custom_material_list')
            
        except Subject.DoesNotExist:
            messages.error(request, 'Selected subject does not exist.')
        except Exception as e:
            messages.error(request, f'Error creating material: {str(e)}')
    
    context = {
        'subjects': Subject.objects.all(),
        'action': 'Create',
        'material': None,
    }
    return render(request, 'learning/admin/material_form.html', context)


@staff_member_required
def material_edit(request, material_id):
    """Edit existing material"""
    material = get_object_or_404(Material, id=material_id)
    
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        title = request.POST.get('title')
        content = request.POST.get('content')
        video_url = request.POST.get('video_url', '')
        
        # Validate required fields
        if not all([subject_id, title, content]):
            messages.error(request, 'Please fill in all required fields (Subject, Title, Content).')
            context = {
                'material': material,
                'subjects': Subject.objects.all(),
                'action': 'Edit',
                'post_data': request.POST
            }
            return render(request, 'learning/admin/material_form.html', context)
        
        try:
            subject = Subject.objects.get(id=subject_id)
            
            # Update material
            material.subject = subject
            material.title = title
            material.content = content
            material.video_url = video_url
            
            # Handle file upload if provided
            if request.FILES.get('file'):
                # Delete old file from cloudinary
                if material.cloudinary_public_id:
                    try:
                        cloudinary.uploader.destroy(material.cloudinary_public_id)
                    except:
                        pass
                
                # Upload new file
                uploaded_file = request.FILES['file']
                upload_result = cloudinary.uploader.upload(
                    uploaded_file,
                    folder="learning_materials",
                    resource_type="auto"
                )
                
                material.file_url = upload_result['secure_url']
                material.cloudinary_public_id = upload_result['public_id']
                
                # Update material type from file
                file_extension = uploaded_file.name.split('.')[-1].lower()
                if file_extension == 'pdf':
                    material.material_type = 'pdf'
                elif file_extension in ['jpg', 'jpeg', 'png']:
                    material.material_type = 'image'
                else:
                    material.material_type = 'text'
            
            material.save()
            messages.success(request, f'Material "{material.title}" updated successfully!')
            return redirect('custom_material_list')
            
        except Subject.DoesNotExist:
            messages.error(request, 'Selected subject does not exist.')
        except Exception as e:
            messages.error(request, f'Error updating material: {str(e)}')
    
    context = {
        'material': material,
        'subjects': Subject.objects.all(),
        'action': 'Edit',
    }
    return render(request, 'learning/admin/material_form.html', context)


@staff_member_required
def material_delete(request, material_id):
    """Delete material"""
    material = get_object_or_404(Material, id=material_id)
    
    if request.method == 'POST':
        title = material.title
        
        # Delete from cloudinary if exists
        if material.cloudinary_public_id:
            try:
                cloudinary.uploader.destroy(material.cloudinary_public_id)
            except:
                pass
        
        material.delete()
        messages.success(request, f'Material "{title}" deleted successfully!')
        return redirect('custom_material_list')
    
    context = {
        'material': material,
    }
    return render(request, 'learning/admin/material_delete.html', context)

# ==================== JSON UPLOAD ====================
@staff_member_required
def json_upload(request):
    """Upload questions from JSON"""
    if request.method == 'POST':
        try:
            if request.FILES.get('json_file'):
                json_data = json.load(request.FILES['json_file'])
            else:
                json_data = json.loads(request.POST.get('json_text'))
            
            with transaction.atomic():
                result = process_json_upload(json_data)
            
            messages.success(
                request, 
                f'Successfully uploaded {result["questions_created"]} questions for {result["exam_year"]}!'
            )
            return redirect('custom_exam_year_list')
            
        except json.JSONDecodeError as e:
            messages.error(request, f'Invalid JSON format: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'learning/admin/json_upload.html')


def process_json_upload(json_data):
    """Process JSON data and create questions"""
    subject, _ = Subject.objects.get_or_create(
        code=json_data['subject_code'],
        defaults={
            'name': json_data['subject_name'],
            'description': f"Subject for {json_data['subject_name']}"
        }
    )
    
    exam_year, _ = ExamYear.objects.get_or_create(
        subject=subject,
        year=json_data['year'],
        session=json_data['session'],
        defaults={
            'description': f"{json_data['subject_name']} - {json_data['year']} {json_data['session']}"
        }
    )
    
    questions_created = 0
    
    for q_data in json_data['questions']:
        question, _ = Question.objects.update_or_create(
            exam_year=exam_year,
            question_number=q_data['number'],
            defaults={
                'question_text': q_data['question'],
                'question_type': q_data['question_type'],
                'marks': q_data['marks']
            }
        )
        
        question.options.all().delete()
        
        if 'options' in q_data:
            for label, text in q_data['options'].items():
                Option.objects.create(
                    question=question,
                    option_label=label,
                    option_text=text,
                    is_correct=(label == q_data['correct_option'])
                )
        
        if 'explanation' in q_data:
            explanation_text = q_data['explanation']
            
            if 'option_analysis' in q_data:
                explanation_text += "\n\n--- Option Analysis ---\n"
                for label, analysis in q_data['option_analysis'].items():
                    explanation_text += f"\n{label}: {analysis}"
            
            additional = ""
            if 'cbt_tip' in q_data:
                additional = f"💡 CBT Tip: {q_data['cbt_tip']}"
            
            Explanation.objects.update_or_create(
                question=question,
                defaults={
                    'explanation_text': explanation_text,
                    'additional_resources': additional
                }
            )
        
        questions_created += 1
    
    return {
        'questions_created': questions_created,
        'exam_year': exam_year
    }


# ==================== STUDENT MANAGEMENT ====================
@staff_member_required
def student_list(request):
    """List all students"""
    query = request.GET.get('q', '')
    
    students = StudentProfile.objects.select_related('user')
    
    if query:
        students = students.filter(
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query) |
            Q(registration_number__icontains=query) |
            Q(phone_number__icontains=query)
        )
    
    students = students.order_by('-created_at')
    
    context = {
        'students': students,
        'query': query,
    }
    return render(request, 'learning/admin/student_list.html', context)


@staff_member_required
def student_detail(request, student_id):
    """View student details and performance"""
    student = get_object_or_404(StudentProfile, id=student_id)
    
    exams = Exam.objects.filter(
        student=student.user,
        is_completed=True
    ).select_related('exam_year__subject').order_by('-submitted_at')
    
    progress = StudentProgress.objects.filter(student=student.user)
    
    context = {
        'student': student,
        'exams': exams,
        'progress': progress,
        'total_exams': exams.count(),
        'avg_score': exams.aggregate(Avg('score'))['score__avg'] or 0,
    }
    return render(request, 'learning/admin/student_detail.html', context)


@staff_member_required
def student_delete(request, student_id):
    """Delete student profile"""
    student = get_object_or_404(StudentProfile, id=student_id)
    
    if request.method == 'POST':
        user = student.user
        username = user.username
        user.delete()  # This will cascade delete the profile
        messages.success(request, f'Student "{username}" deleted successfully!')
        return redirect('custom_student_list')
    
    context = {
        'student': student,
        'exam_count': Exam.objects.filter(student=student.user).count(),
    }
    return render(request, 'learning/admin/student_delete.html', context)


# ==================== EXAM MANAGEMENT ====================
@staff_member_required
def exam_list(request):
    """List all exam submissions"""
    student_id = request.GET.get('student')
    subject_id = request.GET.get('subject')
    query = request.GET.get('q', '')
    
    exams = Exam.objects.filter(is_completed=True).select_related(
        'student', 'exam_year__subject'
    )
    
    if student_id:
        exams = exams.filter(student_id=student_id)
    
    if subject_id:
        exams = exams.filter(exam_year__subject_id=subject_id)
    
    if query:
        exams = exams.filter(
            Q(student__username__icontains=query) |
            Q(student__email__icontains=query)
        )
    
    exams = exams.order_by('-submitted_at')
    students = StudentProfile.objects.select_related('user').all()
    subjects = Subject.objects.all()
    
    context = {
        'exams': exams,
        'students': students,
        'subjects': subjects,
        'selected_student': student_id,
        'selected_subject': subject_id,
        'query': query,
    }
    return render(request, 'learning/admin/exam_list.html', context)


@staff_member_required
def exam_detail(request, exam_id):
    """View detailed exam results"""
    exam = get_object_or_404(
        Exam.objects.select_related('student', 'exam_year__subject'),
        exam_id=exam_id
    )
    
    answers = exam.answers.select_related(
        'question', 'selected_option'
    ).prefetch_related('question__options').order_by('question__question_number')
    
    context = {
        'exam': exam,
        'answers': answers,
    }
    return render(request, 'learning/admin/exam_detail.html', context)


@staff_member_required
def exam_delete(request, exam_id):
    """Delete exam submission"""
    exam = get_object_or_404(Exam, exam_id=exam_id)
    
    if request.method == 'POST':
        student_name = exam.student.username
        exam.delete()
        messages.success(request, f'Exam submission for {student_name} deleted successfully!')
        return redirect('custom_exam_list')
    
    context = {
        'exam': exam,
    }
    return render(request, 'learning/admin/exam_delete.html', context)


# ==================== REPORTS & ANALYTICS ====================
@staff_member_required
def analytics_dashboard(request):
    """Analytics and reports dashboard"""
    subject_stats = Subject.objects.annotate(
        total_exams=Count('exam_years__exams', filter=Q(exam_years__exams__is_completed=True)),
        avg_score=Avg('exam_years__exams__score', filter=Q(exam_years__exams__is_completed=True))
    ).order_by('-total_exams')
    
    recent_exams = Exam.objects.filter(
        is_completed=True
    ).select_related('student', 'exam_year__subject').order_by('-submitted_at')[:20]
    
    top_students = StudentProfile.objects.filter(
        user__exams__is_completed=True
    ).annotate(
        avg_score=Avg('user__exams__score'),
        total_exams=Count('user__exams')
    ).order_by('-avg_score')[:10]
    
    context = {
        'subject_stats': subject_stats,
        'recent_exams': recent_exams,
        'top_students': top_students,
    }
    return render(request, 'learning/admin/analytics.html', context)


@staff_member_required
def export_data(request):
    """Export data to CSV"""
    data_type = request.GET.get('type', 'students')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{data_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    if data_type == 'students':
        writer.writerow(['Username', 'Email', 'Registration Number', 'Phone', 'Joined Date'])
        for student in StudentProfile.objects.select_related('user'):
            writer.writerow([
                student.user.username,
                student.user.email,
                student.registration_number,
                student.phone_number,
                student.created_at.strftime('%Y-%m-%d')
            ])
    
    elif data_type == 'exams':
        writer.writerow(['Student', 'Subject', 'Exam Year', 'Score', 'Date'])
        for exam in Exam.objects.filter(is_completed=True).select_related('student', 'exam_year__subject'):
            writer.writerow([
                exam.student.username,
                exam.exam_year.subject.name,
                str(exam.exam_year),
                f'{exam.score:.2f}%',
                exam.submitted_at.strftime('%Y-%m-%d %H:%M')
            ])
    
    return response