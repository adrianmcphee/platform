from decimal import Decimal
from django.core.management.base import BaseCommand
from django.apps import apps
import csv
from django.db import transaction, models, connection
from datetime import datetime
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import traceback

def debug_print(message):
    print(f"DEBUG: {message}")

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
            'bountybid': BountyBidParser(),
            'platformfee': PlatformFeeParser(),
            'salesorder': SalesOrderParser(),
        }
        return parsers.get(model._meta.model_name, ModelParser())

    def create_objects(self, model, data, parser):
        created_objects = []
        for row in data:
            try:
                with transaction.atomic():
                    obj, created = parser.create_object(model, row)
                    created_objects.append(obj)
                    action = "Created" if created else "Updated"
                    self.stdout.write(self.style.SUCCESS(f"{action} object: {obj}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating/updating object: {str(e)}"))
                self.stdout.write(self.style.ERROR(f"Row data: {row}"))
                self.stdout.write(self.style.ERROR(f"Traceback: {traceback.format_exc()}"))
        return created_objects

    def update_sequence(self, model):
        if model._meta.model_name != "producttree":
            table_name = model._meta.db_table
            sequence_name = f'{table_name}_id_seq'
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT setval('{sequence_name}', COALESCE((SELECT MAX(id) FROM {table_name}), 1));
                """)

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        model_name = options['model']

        try:
            model = apps.get_model(model_name)
        except LookupError:
            self.stdout.write(self.style.ERROR(f'Model {model_name} not found.'))
            return

        data = self.parse_csv(csv_file)
        parser = self.get_parser(model)
        objects = self.create_objects(model, data, parser)

        # Update the sequence after creating/updating objects
        self.update_sequence(model)

        self.stdout.write(self.style.SUCCESS(f'Successfully processed {len(objects)} objects from {csv_file} into {model_name}'))
        self.stdout.write(self.style.SUCCESS(f'Sequence for {model_name} has been updated.'))

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
                parsed_row[key] = timezone.make_aware(datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ"))
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

class BountyBidParser(ModelParser):
    def create_object(self, model, row):
        parsed = self.parse_row(row)
        
        try:
            #debug_print(f"Processing row: {parsed}")
            
            # Get the Bounty and Person models
            Bounty = apps.get_model('product_management.Bounty')
            Person = apps.get_model('talent.Person')
            #debug_print(f"Bounty model: {Bounty}")
            #debug_print(f"Person model: {Person}")
            
            # Ensure bounty_id and person_id are integers
            parsed['bounty_id'] = int(parsed['bounty_id'])
            parsed['person_id'] = int(parsed['person_id'])
            
            # Check if the bounty and person exist
            try:
                bounty = Bounty.objects.get(id=parsed['bounty_id'])
                person = Person.objects.get(id=parsed['person_id'])
                #debug_print(f"Found bounty: {bounty}")
                #debug_print(f"Found person: {person}")
            except ObjectDoesNotExist as e:
                #debug_print(f"Object does not exist: {str(e)}")
                raise ValueError(f"Bounty with id {parsed['bounty_id']} or Person with id {parsed['person_id']} does not exist")
            
            # Convert amount to integer
            parsed['amount'] = int(parsed['amount'])
            
            # Convert expected_finish_date to date object
            parsed['expected_finish_date'] = datetime.strptime(parsed['expected_finish_date'], "%d/%m/%Y").date()
            
            # Convert created_at and updated_at to timezone-aware datetime objects
            parsed['created_at'] = timezone.make_aware(datetime.strptime(parsed['created_at'], "%Y-%m-%dT%H:%M:%SZ"))
            parsed['updated_at'] = timezone.make_aware(datetime.strptime(parsed['updated_at'], "%Y-%m-%dT%H:%M:%SZ"))
            
            # Try to get existing object or create a new one
            obj, created = model.objects.update_or_create(
                id=int(parsed['id']),
                defaults={
                    'bounty': bounty,
                    'person': person,
                    'amount': parsed['amount'],
                    'expected_finish_date': parsed['expected_finish_date'],
                    'status': parsed['status'],
                    'message': parsed['message'],
                    'created_at': parsed['created_at'],
                    'updated_at': parsed['updated_at'],
                }
            )
            #debug_print(f"{'Created' if created else 'Updated'} object: {obj}")
            
            return obj, created
        
        except Exception as e:
            #debug_print(f"Error in BountyBidParser: {str(e)}")
            #debug_print(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Error processing row: {str(e)}")
        
class PlatformFeeParser(ModelParser):
    def parse_row(self, row):
        parsed_row = super().parse_row(row)
        
        # Convert amount_cents to integer
        if 'amount_cents' in parsed_row:
            parsed_row['amount_cents'] = int(parsed_row['amount_cents'])
        
        # Convert fee_rate to Decimal
        if 'fee_rate' in parsed_row:
            parsed_row['fee_rate'] = Decimal(parsed_row['fee_rate'])
        
        # Convert bounty_cart_id to integer
        if 'bounty_cart_id' in parsed_row:
            parsed_row['bounty_cart_id'] = int(parsed_row['bounty_cart_id'])
        
        return parsed_row

    def create_object(self, model, row):
        parsed = self.parse_row(row)
        obj, created = model.objects.update_or_create(
            id=int(parsed['id']),
            defaults=parsed
        )
        return obj, created
    
class SalesOrderParser(ModelParser):
    def parse_row(self, row):
        parsed_row = super().parse_row(row)
        
        # Convert numeric fields to appropriate types
        if 'bounty_cart_id' in parsed_row:
            parsed_row['bounty_cart_id'] = int(parsed_row['bounty_cart_id'])
        
        if 'total_usd_cents' in parsed_row:
            parsed_row['total_usd_cents'] = int(parsed_row['total_usd_cents'])
        
        if 'platform_fee_id' in parsed_row:
            parsed_row['platform_fee_id'] = int(parsed_row['platform_fee_id'])
        
        if 'tax_rate' in parsed_row:
            parsed_row['tax_rate'] = Decimal(parsed_row['tax_rate'])
        
        if 'tax_amount_cents' in parsed_row:
            parsed_row['tax_amount_cents'] = int(parsed_row['tax_amount_cents'])
        
        return parsed_row

    def create_object(self, model, row):
        parsed = self.parse_row(row)
        
        BountyCart = apps.get_model('commerce.BountyCart')
        PlatformFee = apps.get_model('commerce.PlatformFee')
        
        bounty_cart = BountyCart.objects.get(id=parsed['bounty_cart_id'])
        platform_fee = PlatformFee.objects.get(id=parsed['platform_fee_id'])
        
        obj, created = model.objects.update_or_create(
            id=int(parsed['id']),
            defaults={
                'bounty_cart': bounty_cart,
                'status': parsed['status'],
                'total_usd_cents': parsed['total_usd_cents'],
                'platform_fee': platform_fee,
                'tax_rate': parsed['tax_rate'],
                'tax_amount_cents': parsed['tax_amount_cents']
            }
        )
        return obj, created