from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from learning.models import (
    Subject, Material,
    ExamYear, Question, Option, Explanation
)
from django.db import transaction


class Command(BaseCommand):
    help = "Transfer subjects, materials, exam years, questions and options from old DB to new DB"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Starting data transfer..."))

        with transaction.atomic():
            self.transfer_subjects()
            self.transfer_materials()
            self.transfer_exam_data()

        self.stdout.write(self.style.SUCCESS("✅ Data transfer completed successfully"))

    def transfer_subjects(self):
        old_subjects = Subject.objects.using('old').all()

        for subject in old_subjects:
            Subject.objects.get_or_create(
                code=subject.code,
                defaults={
                    'name': subject.name,
                    'description': subject.description,
                    'created_at': subject.created_at,
                }
            )

        self.stdout.write("✔ Subjects transferred")

    def transfer_materials(self):
        old_materials = Material.objects.using('old').select_related('subject', 'created_by')

        for material in old_materials:
            subject = Subject.objects.get(code=material.subject.code)

            created_by = None
            if material.created_by:
                created_by, _ = User.objects.get_or_create(
                    username=material.created_by.username,
                    defaults={
                        'email': material.created_by.email,
                        'first_name': material.created_by.first_name,
                        'last_name': material.created_by.last_name,
                    }
                )

            Material.objects.get_or_create(
                title=material.title,
                subject=subject,
                defaults={
                    'material_type': material.material_type,
                    'content': material.content,
                    'file_url': material.file_url,
                    'cloudinary_public_id': material.cloudinary_public_id,
                    'video_url': material.video_url,
                    'created_by': created_by,
                    'created_at': material.created_at,
                    'views': material.views,
                }
            )

        self.stdout.write("✔ Materials transferred")

    def transfer_exam_data(self):
        old_exam_years = ExamYear.objects.using('old').select_related('subject')

        for old_exam_year in old_exam_years:
            subject = Subject.objects.get(code=old_exam_year.subject.code)

            exam_year, _ = ExamYear.objects.get_or_create(
                subject=subject,
                year=old_exam_year.year,
                session=old_exam_year.session,
                defaults={
                    'description': old_exam_year.description,
                }
            )

            old_questions = Question.objects.using('old').filter(exam_year=old_exam_year)

            for old_question in old_questions:
                question, _ = Question.objects.get_or_create(
                    exam_year=exam_year,
                    question_number=old_question.question_number,
                    defaults={
                        'question_text': old_question.question_text,
                        'question_type': old_question.question_type,
                        'marks': old_question.marks,
                    }
                )

                old_options = Option.objects.using('old').filter(question=old_question)

                for option in old_options:
                    Option.objects.get_or_create(
                        question=question,
                        option_label=option.option_label,
                        defaults={
                            'option_text': option.option_text,
                            'is_correct': option.is_correct,
                        }
                    )

                try:
                    old_explanation = Explanation.objects.using('old').get(question=old_question)
                    Explanation.objects.get_or_create(
                        question=question,
                        defaults={
                            'explanation_text': old_explanation.explanation_text,
                            'additional_resources': old_explanation.additional_resources,
                        }
                    )
                except Explanation.DoesNotExist:
                    pass

        self.stdout.write("✔ Exam questions transferred")
