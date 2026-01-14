# urls.py - Updated without custom_material_create route
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'learning'

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='learning/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='learning/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Home and Dashboard
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Materials (Student View Only)
    path('materials/', views.materials_list, name='materials_list'),
    path('materials/subject/<int:subject_id>/', views.materials_list, name='materials_by_subject'),
    path('material/<int:material_id>/', views.material_detail, name='material_detail'),
    
    # Exam Years
    path('subject/<int:subject_id>/exams/', views.exam_years_list, name='exam_years_list'),
    
    # Exam Taking
    path('exam/start/<int:exam_year_id>/<str:mode>/', views.start_exam, name='start_exam'),
    path('exam/take/<uuid:exam_id>/', views.take_exam, name='take_exam'),
    path('exam/submit-answer/<uuid:exam_id>/', views.submit_answer, name='submit_answer'),
    path('exam/submit/<uuid:exam_id>/', views.submit_exam, name='submit_exam'),
    path('exam/results/<uuid:exam_id>/', views.exam_results, name='exam_results'),
    
    # Custom Admin Panel (All CRUD operations including materials)
    path('custom-admin/', include('learning.admin_urls')),
]