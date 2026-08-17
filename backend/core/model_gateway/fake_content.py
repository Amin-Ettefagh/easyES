"""Deterministic canned content for the FakeModelProvider.

Each software-workflow stage maps to a builder that returns a structured dict.
The dict shape the agent runner understands:

    {
        "summary": str,              # short decision/action summary (shown in UI)
        "messages": [                # optional inter-agent messages to emit
            {"to_role": str, "type": str, "content": str}, ...
        ],
        "artifacts": [               # optional artifacts to persist
            {"type": str, "name": str, "content": str}, ...
        ],
        "evaluation": {              # optional; QA/evaluation stages only
            "tests_passed": bool,
            "requirement_coverage": float,   # 0..1
            "critical_errors": int,
            "score": float,                  # 0..100
            "feedback": str,
        },
    }

QA is scenario-aware: with the default ``fail_once`` scenario, iteration 0
fails (an intentional API-contract mismatch) and any later iteration passes,
which drives the visible fix→retest loop that is central to the demo.
"""
from __future__ import annotations


def _idea(iteration, scenario):
    return {
        "summary": "Analyzed the idea and framed it as a small, well-scoped SaaS.",
        "artifacts": [
            {
                "type": "idea_analysis",
                "name": "Idea Analysis",
                "content": (
                    "# Idea Analysis\n\n"
                    "**Problem:** Small teams lack a lightweight, focused task manager.\n"
                    "**Target users:** Teams of 2–10 people.\n"
                    "**Value:** Fast task capture, clear ownership, minimal setup.\n"
                    "**Feasibility:** High — CRUD + auth + a simple board.\n"
                    "**Risks:** Scope creep; keep the MVP tiny.\n"
                ),
            }
        ],
        "messages": [
            {
                "to_role": "Market Researcher",
                "type": "delegation",
                "content": "Idea validated at a high level. Please assess the market.",
            }
        ],
    }


def _market(iteration, scenario):
    return {
        "summary": "Compiled a concise market scan with positioning and competitors.",
        "artifacts": [
            {
                "type": "market_research",
                "name": "Market Research Report",
                "content": (
                    "# Market Research\n\n"
                    "**Competitors:** Trello, Todoist, Linear (heavier), sticky notes.\n"
                    "**Gap:** A no-frills board for very small teams.\n"
                    "**Positioning:** 'Task management that fits on one screen.'\n"
                    "**Pricing hint:** Freemium; $4/user/mo for teams.\n"
                ),
            }
        ],
        "messages": [
            {
                "to_role": "Product Manager",
                "type": "report",
                "content": "Market looks favorable for a minimal team task board.",
            }
        ],
    }


def _product(iteration, scenario):
    return {
        "summary": "Turned research into a prioritized feature list and product spec.",
        "artifacts": [
            {
                "type": "feature_list",
                "name": "Feature List",
                "content": (
                    "# Features (MVP)\n\n"
                    "1. Email/password auth\n"
                    "2. Projects\n"
                    "3. Tasks with status (todo/doing/done)\n"
                    "4. Assign task to a member\n"
                    "5. Board view\n"
                ),
            },
            {
                "type": "product_spec",
                "name": "Product Specification",
                "content": (
                    "# Product Spec\n\n"
                    "## User stories\n"
                    "- As a user I can create a project.\n"
                    "- As a user I can add tasks and move them across statuses.\n"
                    "- As a user I can assign a task to a teammate.\n\n"
                    "## Acceptance criteria\n"
                    "- Tasks persist and reload correctly.\n"
                    "- API returns correct status codes.\n"
                ),
            },
        ],
        "messages": [
            {
                "to_role": "Software Architect",
                "type": "delegation",
                "content": "Spec finalized. Please design the architecture and API contract.",
            }
        ],
    }


def _architecture(iteration, scenario):
    return {
        "summary": "Designed a simple REST architecture and a versioned API contract.",
        "artifacts": [
            {
                "type": "architecture",
                "name": "Architecture Document",
                "content": (
                    "# Architecture\n\n"
                    "- Backend: REST API (Python).\n"
                    "- DB: PostgreSQL.\n"
                    "- Frontend: SPA calling the API.\n\n"
                    "## Entities\n"
                    "Project(id, name) — Task(id, project_id, title, status, assignee)\n"
                ),
            },
            {
                "type": "api_spec",
                "name": "API Specification",
                "content": (
                    "# API Contract v1\n\n"
                    "GET  /api/tasks -> 200 [Task]\n"
                    "POST /api/tasks {title, project_id} -> 201 Task\n"
                    "PATCH /api/tasks/{id} {status|assignee} -> 200 Task\n\n"
                    "Task.status in [todo, doing, done]\n"
                ),
            },
        ],
        "messages": [
            {
                "to_role": "Backend Engineer",
                "type": "delegation",
                "content": "Implement the API per the v1 contract (note: status field is required).",
            },
            {
                "to_role": "Frontend Engineer",
                "type": "delegation",
                "content": "Build the board UI against the v1 API contract.",
            },
        ],
    }


def _backend(iteration, scenario):
    # On the first attempt the backend omits the required `status` field,
    # which is the defect QA catches. Later iterations ship the fix.
    fixed = iteration > 0 or scenario == "success"
    if fixed:
        code = (
            "def create_task(payload):\n"
            "    return {\n"
            "        'id': new_id(),\n"
            "        'title': payload['title'],\n"
            "        'project_id': payload['project_id'],\n"
            "        'status': payload.get('status', 'todo'),  # contract-compliant\n"
            "        'assignee': payload.get('assignee'),\n"
            "    }\n"
        )
        summary = "Implemented the task API, including the required `status` field."
    else:
        code = (
            "def create_task(payload):\n"
            "    return {\n"
            "        'id': new_id(),\n"
            "        'title': payload['title'],\n"
            "        'project_id': payload['project_id'],\n"
            "        # BUG: missing required 'status' field (contract mismatch)\n"
            "        'assignee': payload.get('assignee'),\n"
            "    }\n"
        )
        summary = "Implemented the task API (first pass)."
    return {
        "summary": summary,
        "artifacts": [
            {"type": "backend_code", "name": "tasks_api.py", "content": code}
        ],
        "messages": [
            {
                "to_role": "QA Engineer",
                "type": "report",
                "content": "Backend build ready for testing.",
            }
        ],
    }


def _frontend(iteration, scenario):
    return {
        "summary": "Implemented the board UI that consumes the task API.",
        "artifacts": [
            {
                "type": "frontend_code",
                "name": "Board.jsx",
                "content": (
                    "export function Board({tasks}) {\n"
                    "  return tasks.map(t => <Card key={t.id} title={t.title} "
                    "status={t.status} />);\n"
                    "}\n"
                ),
            }
        ],
        "messages": [
            {
                "to_role": "QA Engineer",
                "type": "report",
                "content": "Frontend build ready for testing.",
            }
        ],
    }


def _integration(iteration, scenario):
    return {
        "summary": "Integrated backend and frontend; wired the board to the API.",
        "artifacts": [
            {
                "type": "integration_notes",
                "name": "Integration Notes",
                "content": "Board fetches GET /api/tasks and renders status columns.",
            }
        ],
    }


def _qa(iteration, scenario):
    fixed = iteration > 0 or scenario == "success"
    if scenario == "always_fail":
        fixed = False
    if fixed:
        return {
            "summary": "All tests passed; API contract satisfied.",
            "evaluation": {
                "tests_passed": True,
                "requirement_coverage": 0.95,
                "critical_errors": 0,
                "score": 92.0,
                "feedback": "Contract mismatch resolved. 12/12 tests green.",
            },
            "artifacts": [
                {
                    "type": "test_report",
                    "name": "Test Report",
                    "content": "12 passed, 0 failed. Coverage 95%.",
                }
            ],
            "messages": [
                {
                    "to_role": "Code Reviewer",
                    "type": "report",
                    "content": "QA passed. Ready for review.",
                }
            ],
        }
    return {
        "summary": "QA failed: create_task response is missing the required 'status' field.",
        "evaluation": {
            "tests_passed": False,
            "requirement_coverage": 0.75,
            "critical_errors": 1,
            "score": 61.0,
            "feedback": "API contract mismatch: POST /api/tasks omits 'status'. 9/12 tests passed.",
        },
        "artifacts": [
            {
                "type": "test_report",
                "name": "Test Report",
                "content": "9 passed, 3 failed. Failure: response.status is undefined.",
            }
        ],
        "messages": [
            {
                "to_role": "Backend Engineer",
                "type": "feedback",
                "content": "3 tests failed — 'status' missing from create_task response. Please fix.",
            }
        ],
    }


def _failure_analysis(iteration, scenario):
    return {
        "summary": "Diagnosed the QA failure and produced a targeted fix plan.",
        "artifacts": [
            {
                "type": "fix_plan",
                "name": "Fix Plan",
                "content": (
                    "Root cause: create_task omits 'status'.\n"
                    "Fix: default status to 'todo' and include it in the response.\n"
                    "Owner: Backend Engineer."
                ),
            }
        ],
        "messages": [
            {
                "to_role": "Backend Engineer",
                "type": "delegation",
                "content": "Apply the fix: include 'status' (default 'todo') in create_task.",
            }
        ],
    }


def _review(iteration, scenario):
    return {
        "summary": "Reviewed the code and approved it against the checklist.",
        "artifacts": [
            {
                "type": "review_report",
                "name": "Review Report",
                "content": "Code readable, contract satisfied, tests present. Approved.",
            }
        ],
        "evaluation": {
            "tests_passed": True,
            "requirement_coverage": 0.95,
            "critical_errors": 0,
            "score": 90.0,
            "feedback": "Approved with minor nits.",
        },
    }


def _product_analysis(iteration, scenario):
    return {
        "summary": "Confirmed the delivered product meets the specified requirements.",
        "artifacts": [
            {
                "type": "product_analysis",
                "name": "Product Analysis",
                "content": "All MVP features present. Requirement coverage 95%.",
            }
        ],
        "evaluation": {
            "tests_passed": True,
            "requirement_coverage": 0.95,
            "critical_errors": 0,
            "score": 93.0,
            "feedback": "Meets acceptance criteria.",
        },
    }


def _final(iteration, scenario):
    return {
        "summary": "Compiled the final report; project meets completion criteria.",
        "artifacts": [
            {
                "type": "final_report",
                "name": "Final Report",
                "content": (
                    "# Final Report\n\n"
                    "Delivered a minimal team task management SaaS: auth, projects, "
                    "tasks with status, assignment and a board view. QA green after "
                    "one fix loop. Requirement coverage 95%.\n"
                ),
            }
        ],
    }


_BUILDERS = {
    "idea_analysis": _idea,
    "market_research": _market,
    "product_spec": _product,
    "architecture": _architecture,
    "backend_implementation": _backend,
    "frontend_implementation": _frontend,
    "integration": _integration,
    "qa": _qa,
    "evaluation": _qa,
    "failure_analysis": _failure_analysis,
    "fix_planning": _failure_analysis,
    "review": _review,
    "product_analysis": _product_analysis,
    "final_evaluation": _final,
}


def build(stage: str, iteration: int = 0, scenario: str = "fail_once") -> dict:
    builder = _BUILDERS.get(stage)
    if builder is None:
        return {
            "summary": f"Completed stage '{stage}'.",
            "artifacts": [
                {"type": "note", "name": f"{stage} output", "content": f"Stage {stage} done."}
            ],
        }
    return builder(iteration, scenario)
