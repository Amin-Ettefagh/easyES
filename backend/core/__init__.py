"""Shared engine primitives that are independent of Django apps.

`core` holds the parts of the platform that other subsystems build on but
which must not depend on any single app: the model gateway, the tool
abstraction, the event emitter, rule resolution and the workflow engine.
"""
