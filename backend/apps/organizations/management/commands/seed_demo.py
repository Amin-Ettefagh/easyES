"""``python manage.py seed_demo`` — build the demo software company.

Idempotent: safe to run repeatedly. Honors ``EASYES_ALLOW_DEMO_SEED`` so a
production config never auto-creates the demo login.
"""
from django.core.management.base import BaseCommand

from core.seed import DEMO_ORG_SLUG, seed_demo


class Command(BaseCommand):
    help = "Seed the demo 'amin' software company (org, roles, agents, workflow)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-user",
            action="store_true",
            help="Skip creating the demo login user.",
        )

    def handle(self, *args, **options):
        org = seed_demo(create_user=not options["no_user"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded organization '{org.name}' (slug={DEMO_ORG_SLUG}). "
                f"Roles={org.roles.count()} Agents={org.agents.count()} "
                f"Workflows={org.workflows.count()}"
            )
        )
