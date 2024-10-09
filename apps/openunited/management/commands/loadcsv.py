
from django.core.management.base import BaseCommand
from django.apps import apps
import csv
from django.db import transaction, models
from datetime import datetime
from django.utils.timezone import make_aware

class Command(BaseCommand):
    help = 'Load data from a CSV file into the specified model.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The CSV file to load')
        parser.add_argument('--model', type=str, help='The model to use for the CSV file', required=True)

    def parse_csv(self, file_path):
        with open(file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            return list(reader)

    def get_parser(self, model):
        parsers = {
            'personskill': PersonSkillParser(),
            'person': PersonParser(),
            'skill': SkillParser(),
            'expertise': ExpertiseParser(),
            'bounty': BountyParser(),
        }
        return parsers.get(model._meta.model_name, ModelParser())

    def create_objects(self, model, data, parser):
        created_objects = []
        for row in data:
            try:
                obj, created = parser.create_object(model, row)
                created_objects.append(obj)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating/updating object: {e}. Row: {row}"))
        return created_objects

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        model_name = options['model']

        try:
            # Load the specified model
            model = apps.get_model(model_name)
        except LookupError:
            self.stdout.write(self.style.ERROR(f'Model {model_name} not found.'))
            return

        # Parse the CSV file
        data = self.parse_csv(csv_file)

        # Create objects
        parser = self.get_parser(model)
        objects = self.create_objects(model, data, parser)

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded data from {csv_file} into {model_name}'))

class ModelParser:
    def create_object(self, model, row):
        parsed = self.parse_row(row)
        
        # Check if the 'id' field is a UUID or integer
        if isinstance(model._meta.get_field('id'), models.UUIDField):
            obj, created = model.objects.update_or_create(
                id=parsed['id'],  # Don't cast to int if it's a UUID
                defaults=parsed
            )
        else:
            obj, created = model.objects.update_or_create(
                id=int(parsed['id']),
                defaults=parsed
            )
        return obj, created

    def parse_row(self, row):
        parsed_row = {}
        for key, value in row.items():
            if value.lower() in ['true', 'false']:
                parsed_row[key] = value.lower() == 'true'
            elif 'deadline' in key.lower() and value:  # Check if the field is a deadline
                # Convert string to aware datetime object
                parsed_row[key] = make_aware(datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ"))
            else:
                parsed_row[key] = value
        return parsed_row

class PersonParser(ModelParser):
    pass

class SkillParser(ModelParser):
    pass

class ExpertiseParser(ModelParser):
    pass

class PersonSkillParser(ModelParser):
    def create_object(self, model, row):
        parsed = self.parse_row(row)

        # Extract expertise IDs and remove them from parsed data
        expertise_ids = parsed.pop('expertise_ids', '')
        if isinstance(expertise_ids, str):
            expertise_ids = [int(x.strip()) for x in expertise_ids.split(',') if x]

        # Create or update the PersonSkill object
        obj, created = model.objects.update_or_create(
            id=int(parsed['id']),
            defaults={
                'person_id': parsed['person_id'],
                'skill_id': parsed['skill_id']
            }
        )

        # Set the expertise M2M relationship
        if expertise_ids:
            Expertise = apps.get_model('talent.Expertise')
            obj.expertise.set(Expertise.objects.filter(id__in=expertise_ids))

        return obj, created

class BountyParser(ModelParser):
    def parse_row(self, row):
        parsed_row = super().parse_row(row)
        
        # Convert string 'null' to None for specific fields
        for field in ['claimed_by_id', 'competition_id']:
            if parsed_row.get(field) == 'null':
                parsed_row[field] = None
        
        # Ensure numeric fields are properly typed
        for field in ['reward_amount', 'skill_id', 'challenge_id']:
            if parsed_row.get(field):
                parsed_row[field] = int(parsed_row[field])
        
        return parsed_row

    def create_object(self, model, row):
        parsed = self.parse_row(row)
        obj, created = model.objects.update_or_create(
            id=int(parsed['id']),
            defaults=parsed
        )
        return obj, created