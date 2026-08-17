"""``python manage.py run_demo`` — seed, create a project, and run it to the end.

Uses the *inline* execution backend so the whole lifecycle (including the QA
fix loop) completes synchronously and the command can print the final state.
Great for a smoke test and for the ``docker compose`` demo entrypoint.
"""
from django.core.management.base import BaseCommand

from core.seed import create_demo_project, seed_demo
from core.workflow_engine import start_execution


class Command(BaseCommand):
    help = "Seed the demo and run one project end-to-end (inline)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scenario",
            default="fail_once",
            choices=["fail_once", "success", "always_fail"],
            help="Drives the deterministic FakeModelProvider.",
        )

    def handle(self, *args, **options):
        scenario = options["scenario"]
        org = seed_demo()
        project = create_demo_project(org, key=f"demo-{scenario}", scenario=scenario)
        self.stdout.write(f"Running project '{project.name}' (scenario={scenario})...")

        execution = start_execution(
            project, scenario=scenario, backend="inline"
        )
        execution.refresh_from_db()

        loops = execution.loop_states.first()
        self.stdout.write(
            self.style.SUCCESS(
                f"Execution finished: status={execution.status} "
                f"stop_reason={execution.stop_reason} "
                f"iterations={loops.iteration if loops else 0} "
                f"cost=${execution.total_cost} "
                f"node_runs={execution.node_runs.count()} "
                f"artifacts={project.artifacts.count()} "
                f"events={execution.events.count()}"
            )
        )
