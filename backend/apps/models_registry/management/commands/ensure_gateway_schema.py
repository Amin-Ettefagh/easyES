"""Bridge legacy demo databases whose initial migrations were generated at runtime.

The original project does not commit migration files.  Existing databases therefore
have an ``0001_initial`` migration recorded even when a newer image generates a
different initial migration.  This command makes additive gateway changes safe
without deleting or faking any existing data.
"""

from django.core.management.base import BaseCommand
from django.db import connection

from apps.models_registry.models import Model


class Command(BaseCommand):
    help = "Apply additive provider-gateway columns missing from a legacy database."

    def handle(self, *args, **options):
        table = Model._meta.db_table
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table)
            }

        field = Model._meta.get_field("remote_id")
        if field.column in columns:
            self.stdout.write("Provider gateway schema is already current.")
            return

        with connection.schema_editor() as editor:
            editor.add_field(Model, field)
        self.stdout.write(self.style.SUCCESS("Added models_registry_model.remote_id."))
