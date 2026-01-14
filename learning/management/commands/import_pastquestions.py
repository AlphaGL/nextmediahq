import json
import re
from difflib import SequenceMatcher
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from learning.models import (
    Subject, ExamYear, Question, Option, Explanation, Material
)
from django.db import transaction


class Command(BaseCommand):
    help = "Import past questions AND auto-create study materials from a JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            type=str,
            help="Path to the JSON file containing past questions"
        )
        parser.add_argument(
            "--skip-materials",
            action="store_true",
            help="Skip material creation and only import questions"
        )
        parser.add_argument(
            "--similarity-threshold",
            type=float,
            default=0.85,
            help="Content similarity threshold (0.0-1.0). Default: 0.85"
        )

    def normalize_topic(self, topic):
        """
        Normalize topic names to avoid duplicates.
        Examples:
        - "Electricity" -> "electricity"
        - "Electric Current (Electricity)" -> "electricity"
        - "  ELECTRIC CURRENT  " -> "electric current"
        """
        if not topic:
            return "general notes"
        
        # Convert to lowercase
        normalized = topic.lower().strip()
        
        # Remove content in parentheses
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        
        # Remove special characters except spaces and hyphens
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        
        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common redundant words
        redundant_words = ['topic', 'chapter', 'unit', 'lesson', 'notes on', 'introduction to']
        for word in redundant_words:
            normalized = normalized.replace(word, '')
        
        # Clean up again after removals
        normalized = normalized.strip()
        
        # If empty after normalization, return default
        if not normalized:
            return "general notes"
        
        return normalized

    def normalize_content(self, content):
        """
        Normalize content for similarity comparison.
        Remove extra whitespace, lowercase, remove punctuation.
        """
        if not content:
            return ""
        
        # Convert to lowercase
        normalized = content.lower()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common punctuation but keep meaningful characters
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return normalized.strip()

    def content_similarity(self, content1, content2):
        """
        Calculate similarity ratio between two content strings.
        Returns a value between 0.0 (completely different) and 1.0 (identical).
        """
        norm1 = self.normalize_content(content1)
        norm2 = self.normalize_content(content2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Use SequenceMatcher for similarity calculation
        return SequenceMatcher(None, norm1, norm2).ratio()

    def is_content_duplicate(self, new_content, existing_content, threshold=0.85):
        """
        Check if new content is a duplicate or very similar to existing content.
        """
        # Check if exact substring exists
        if new_content.strip() in existing_content:
            return True
        
        # Split existing content by separator to check individual sections
        sections = existing_content.split('='*60)
        
        for section in sections:
            similarity = self.content_similarity(new_content, section)
            if similarity >= threshold:
                return True
        
        return False

    def find_similar_material(self, subject, normalized_topic):
        """
        Find existing material with similar normalized topic name.
        """
        # Get all materials for this subject
        existing_materials = Material.objects.filter(subject=subject)
        
        for material in existing_materials:
            if self.normalize_topic(material.title) == normalized_topic:
                return material
        
        return None

    def handle(self, *args, **options):
        file_path = options["json_file"]
        skip_materials = options["skip_materials"]
        similarity_threshold = options["similarity_threshold"]

        # Read JSON file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise CommandError(f"Failed to read JSON file: {e}")

        # Validate required keys
        required_keys = [
            "subject_code", "subject_name",
            "year", "session", "questions"
        ]

        for key in required_keys:
            if key not in data:
                raise CommandError(f"Missing required key in JSON: '{key}'")

        if not isinstance(data["questions"], list) or len(data["questions"]) == 0:
            raise CommandError("JSON must contain at least one question in 'questions' array")

        # Start transaction
        with transaction.atomic():
            # Get or create subject
            subject, subject_created = Subject.objects.get_or_create(
                code=data["subject_code"],
                defaults={"name": data["subject_name"]}
            )

            if subject_created:
                self.stdout.write(self.style.SUCCESS(f"✓ Created subject: {subject.name}"))
            else:
                self.stdout.write(f"• Using existing subject: {subject.name}")

            # Get or create exam year
            exam_year, year_created = ExamYear.objects.get_or_create(
                subject=subject,
                year=data["year"],
                session=data["session"]
            )

            if year_created:
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Created exam year: {exam_year.year} {exam_year.session}"
                ))
            else:
                self.stdout.write(
                    f"• Using existing exam year: {exam_year.year} {exam_year.session}"
                )

            # Counters
            created_questions = 0
            skipped_questions = 0
            created_materials = 0
            updated_materials = 0
            skipped_duplicate_content = 0
            
            # Track materials by normalized topic to avoid redundant queries
            materials_cache = {}

            # Process each question
            for q in data["questions"]:
                try:
                    # Validate question structure
                    required_q_keys = ["number", "question", "options", "correct_option", "explanation"]
                    for key in required_q_keys:
                        if key not in q:
                            raise CommandError(
                                f"Question #{q.get('number', '?')} missing required field: '{key}'"
                            )

                    # Create or get question
                    question, created = Question.objects.get_or_create(
                        exam_year=exam_year,
                        question_number=q["number"],
                        defaults={
                            "question_text": q["question"],
                            "marks": q.get("marks", 1),
                            "question_type": q.get("question_type", "multiple")
                        }
                    )

                    if not created:
                        skipped_questions += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"⊗ Skipped duplicate Q{q['number']}"
                            )
                        )
                        continue

                    # Create options
                    if not isinstance(q["options"], dict):
                        raise CommandError(
                            f"Question #{q['number']}: 'options' must be a dictionary"
                        )

                    for label, text in q["options"].items():
                        Option.objects.create(
                            question=question,
                            option_label=label,
                            option_text=text,
                            is_correct=(label == q["correct_option"])
                        )

                    # Create explanation
                    Explanation.objects.create(
                        question=question,
                        explanation_text=q["explanation"],
                        additional_resources=q.get("additional_resources", "")
                    )

                    created_questions += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Created Q{q['number']}: {q['question'][:60]}...")
                    )

                    # Handle material creation (if not skipped and material_note exists)
                    if not skip_materials and "material_note" in q and q["material_note"]:
                        topic = q.get("topic", "General Notes")
                        normalized_topic = self.normalize_topic(topic)
                        material_content = q["material_note"]
                        
                        # Check cache first
                        if normalized_topic not in materials_cache:
                            # Try to find existing material with similar normalized name
                            existing_material = self.find_similar_material(subject, normalized_topic)
                            
                            if existing_material:
                                # Use existing material
                                material = existing_material
                                materials_cache[normalized_topic] = material
                                self.stdout.write(
                                    f"  • Found existing material: '{material.title}' (normalized: {normalized_topic})"
                                )
                            else:
                                # Create new material with proper title (capitalized)
                                proper_title = topic.strip().title()
                                material = Material.objects.create(
                                    subject=subject,
                                    title=proper_title,
                                    material_type="text",
                                    content=material_content,
                                    created_by=None  # System-generated
                                )
                                materials_cache[normalized_topic] = material
                                created_materials += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"  ✓ Created material: '{proper_title}' (normalized: {normalized_topic})")
                                )
                                continue  # Skip duplicate check for newly created material
                        else:
                            # Material already in cache
                            material = materials_cache[normalized_topic]
                        
                        # Check if content is duplicate or very similar
                        if self.is_content_duplicate(material_content, material.content, similarity_threshold):
                            skipped_duplicate_content += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  ⊗ Skipped duplicate/similar content for: '{material.title}'"
                                )
                            )
                        else:
                            # Add new unique content
                            material.content += f"\n\n{'='*60}\n\n{material_content}"
                            material.save()
                            updated_materials += 1
                            self.stdout.write(
                                f"  • Updated material: '{material.title}' (added new content)"
                            )

                except KeyError as e:
                    raise CommandError(
                        f"Question #{q.get('number', '?')}: Missing field {e}"
                    )
                except Exception as e:
                    raise CommandError(
                        f"Question #{q.get('number', '?')}: Error - {str(e)}"
                    )

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("✅ IMPORT COMPLETED SUCCESSFULLY"))
        self.stdout.write("="*60)
        self.stdout.write(f"Questions created:     {created_questions}")
        self.stdout.write(f"Questions skipped:     {skipped_questions}")
        
        if not skip_materials:
            self.stdout.write(f"Materials created:     {created_materials}")
            self.stdout.write(f"Materials updated:     {updated_materials}")
            self.stdout.write(f"Duplicate content skipped: {skipped_duplicate_content}")
            self.stdout.write(f"\n💡 Smart deduplication enabled:")
            self.stdout.write(f"   • Topic normalization (e.g., 'Electricity' = 'Electric Current')")
            self.stdout.write(f"   • Content similarity detection (threshold: {similarity_threshold:.0%})")
        
        self.stdout.write("="*60 + "\n")