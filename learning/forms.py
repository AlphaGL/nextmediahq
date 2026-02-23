# forms.py - Updated with video_url field + CGPA Calculator forms
from django import forms
from .models import (
    Material, Question, Option, Explanation, ExamYear, Subject,
    StudentProfile, Semester, CourseResult
)
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm


class StudentRegistrationForm(UserCreationForm):
    name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number'
        })
    )
    registration_number = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registration number'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a strong password',
            'id': 'password1'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )
    
    class Meta:
        model = User
        fields = ['name', 'phone_number', 'registration_number', 'email', 'password1', 'password2']
    
    def clean_registration_number(self):
        reg_number = self.cleaned_data.get('registration_number')
        if StudentProfile.objects.filter(registration_number=reg_number).exists():
            raise forms.ValidationError("This registration number is already registered.")
        return reg_number
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['registration_number']
        name_parts = self.cleaned_data['name'].split(' ', 1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                registration_number=self.cleaned_data['registration_number'],
                phone_number=self.cleaned_data['phone_number']
            )
        return user


class StudentLoginForm(forms.Form):
    registration_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registration number'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email'
        })
    )


class MaterialUploadForm(forms.ModelForm):
    file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png'})
    )
    
    class Meta:
        model = Material
        fields = ['subject', 'title', 'material_type', 'content', 'video_url']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 10,
                'class': 'form-control',
                'placeholder': 'Enter material content manually or leave blank to extract from file'
            }),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Material Title'}),
            'material_type': forms.Select(attrs={'class': 'form-select'}),
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'YouTube video URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID)'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        file = cleaned_data.get('file')
        
        if not content and not file:
            raise forms.ValidationError("Please provide either content or upload a file.")
        
        return cleaned_data


class ExamYearForm(forms.ModelForm):
    class Meta:
        model = ExamYear
        fields = ['subject', 'year', 'session', 'description']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2024'}),
            'session': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Semester'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['exam_year', 'question_text', 'question_type', 'question_number', 'marks']
        widgets = {
            'exam_year': forms.Select(attrs={'class': 'form-select'}),
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'question_type': forms.Select(attrs={'class': 'form-select'}),
            'question_number': forms.NumberInput(attrs={'class': 'form-control'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control', 'value': 1}),
        }


class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ['option_label', 'option_text', 'is_correct']
        widgets = {
            'option_label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'A'}),
            'option_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExplanationForm(forms.ModelForm):
    class Meta:
        model = Explanation
        fields = ['explanation_text', 'additional_resources']
        widgets = {
            'explanation_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'additional_resources': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Formset for creating multiple options at once
from django.forms import inlineformset_factory

OptionFormSet = inlineformset_factory(
    Question,
    Option,
    form=OptionForm,
    extra=4,
    max_num=6,
    can_delete=True
)


# ══════════════════════════════════════════════════════════════
#  CGPA CALCULATOR FORMS
# ══════════════════════════════════════════════════════════════

class SemesterForm(forms.ModelForm):
    class Meta:
        model  = Semester
        fields = ['level', 'semester', 'session']
        widgets = {
            'level': forms.Select(attrs={'class': 'form-select'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'session': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2023/2024',
            }),
        }


class CourseResultForm(forms.ModelForm):
    class Meta:
        model  = CourseResult
        fields = ['course_code', 'course_title', 'credit_units', 'grade', 'score']
        widgets = {
            'course_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. MTH 101',
            }),
            'course_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Course title',
            }),
            'credit_units': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1, 'max': 6,
            }),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'score': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional raw score',
                'min': 0, 'max': 100, 'step': '0.01',
            }),
        }