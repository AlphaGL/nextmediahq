# learning/admin_urls.py - Updated with material create route
from django.urls import path
from . import admin_views

urlpatterns = [
    # Dashboard
    path('', admin_views.custom_admin_dashboard, name='custom_admin_dashboard'),
    
    # Subjects CRUD
    path('subjects/', admin_views.subject_list, name='custom_subject_list'),
    path('subjects/create/', admin_views.subject_create, name='custom_subject_create'),
    path('subjects/<int:subject_id>/edit/', admin_views.subject_edit, name='custom_subject_edit'),
    path('subjects/<int:subject_id>/delete/', admin_views.subject_delete, name='custom_subject_delete'),
    
    # Exam Years CRUD
    path('exam-years/', admin_views.exam_year_list, name='custom_exam_year_list'),
    path('exam-years/create/', admin_views.exam_year_create, name='custom_exam_year_create'),
    path('exam-years/<int:exam_year_id>/edit/', admin_views.exam_year_edit, name='custom_exam_year_edit'),
    path('exam-years/<int:exam_year_id>/delete/', admin_views.exam_year_delete, name='custom_exam_year_delete'),
    
    # Questions CRUD
    path('questions/', admin_views.question_list, name='custom_question_list'),
    path('questions/create/', admin_views.question_create, name='custom_question_create'),
    path('questions/<int:question_id>/edit/', admin_views.question_edit, name='custom_question_edit'),
    path('questions/<int:question_id>/delete/', admin_views.question_delete, name='custom_question_delete'),
    
    # Materials CRUD
    path('materials/', admin_views.material_list, name='custom_material_list'),
    path('materials/create/', admin_views.material_create, name='custom_material_create'),
    path('materials/<int:material_id>/edit/', admin_views.material_edit, name='custom_material_edit'),
    path('materials/<int:material_id>/delete/', admin_views.material_delete, name='custom_material_delete'),
    
    # JSON Upload
    path('upload-json/', admin_views.json_upload, name='custom_json_upload'),
    
    # Students Management
    path('students/', admin_views.student_list, name='custom_student_list'),
    path('students/<int:student_id>/', admin_views.student_detail, name='custom_student_detail'),
    path('students/<int:student_id>/delete/', admin_views.student_delete, name='custom_student_delete'),
    
    # Exams Management
    path('exams/', admin_views.exam_list, name='custom_exam_list'),
    path('exams/<uuid:exam_id>/', admin_views.exam_detail, name='custom_exam_detail'),
    path('exams/<uuid:exam_id>/delete/', admin_views.exam_delete, name='custom_exam_delete'),
    
    # Analytics & Export
    path('analytics/', admin_views.analytics_dashboard, name='custom_analytics'),
    path('export/', admin_views.export_data, name='custom_export_data'),
]