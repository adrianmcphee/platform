import csv
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Load CSV data into the specified model.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file.')
        parser.add_argument('model_name', type=str, help='The app_label.ModelName (e.g., "auth.User")')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        model_name = kwargs['model_name']

        try:
            model = apps.get_model(model_name)
        except LookupError:
            self.stdout.write(self.style.ERROR(f'Model "{model_name}" not found.'))
            return

        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)

            for row in reader:
                # Convert boolean-like values
                for field, value in row.items():
                    if value.lower() == 'true':
                        row[field] = True
                    elif value.lower() == 'false':
                        row[field] = False

                # Create a dictionary for model instantiation
                data = {field: value for field, value in row.items() if field in [f.name for f in model._meta.fields]}

                obj, created = model.objects.get_or_create(**data)

                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created: {obj}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Already exists: {obj}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded data from {csv_file} into {model_name}'))