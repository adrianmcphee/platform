import uuid
import base58
from django.db import models
from django.conf import settings

class Base58UUIDv5Field(models.CharField):
    """
    A reusable custom Django field that generates a Base58 encoded UUIDv5
    based on a custom namespace (UUIDv4 from environment or settings)
    and a per-record UUIDv4.
    """
    description = "A Base58 encoded UUIDv5 field based on a custom namespace and per-record UUIDv4."

    def __init__(self, *args, **kwargs):
        # Set the max length for Base58 encoded UUIDs and ensure uniqueness
        kwargs['max_length'] = 22  # Base58-encoded UUID is 22 characters long
        kwargs['unique'] = True  # Ensure unique UUIDs
        kwargs['editable'] = False  # Set as non-editable
        if kwargs.get('primary_key', False):
            kwargs['primary_key'] = True  # Set as primary key if needed
        super().__init__(*args, **kwargs)

    def generate_id(self):
        custom_namespace = settings.PLATFORM_NAMESPACE
        record_uuid = uuid.uuid4()
        uuid_obj = uuid.uuid5(custom_namespace, str(record_uuid))
        return base58.b58encode(uuid_obj.bytes).decode('ascii')

    def pre_save(self, model_instance, add):
        if add and not getattr(model_instance, self.attname):
            value = self.generate_id()
            setattr(model_instance, self.attname, value)
        return super().pre_save(model_instance, add)

    def get_prep_value(self, value):
        if value is None:
            return self.generate_id()
        return value

    def from_db_value(self, value, expression, connection):
        return value

    def to_python(self, value):
        return value

    def deconstruct(self):
        """
        Ensure the field can be serialized by migrations.
        """
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop('max_length', None)
        kwargs.pop('unique', None)
        return name, path, args, kwargs
