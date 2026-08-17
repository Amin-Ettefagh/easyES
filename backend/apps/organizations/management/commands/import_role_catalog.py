from django.core.management.base import BaseCommand, CommandError

from apps.organizations.models import Organization
from core.taxonomy_import import import_role_agents


class Command(BaseCommand):
    help = "Import roll.md + SoftwareEngineerCompanySamples.html and create one agent per unique role."

    def add_arguments(self, parser):
        parser.add_argument("--organization", default="amin")

    def handle(self, *args, **options):
        try:
            organization = Organization.objects.get(slug=options["organization"])
        except Organization.DoesNotExist as exc:
            raise CommandError(f"Organization '{options['organization']}' does not exist") from exc
        result = import_role_agents(organization)
        self.stdout.write(self.style.SUCCESS("Role catalogue imported: " + ", ".join(f"{key}={value}" for key, value in result.items())))
