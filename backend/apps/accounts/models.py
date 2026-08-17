from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Platform user.

    A human's identity. A Human :class:`~apps.actors.models.Actor` links to a
    User; the two are kept separate because "who can log in" and "who can do
    work in the domain" are different concerns (Actor also covers AI agents).
    """

    display_name = models.CharField(max_length=150, blank=True)
    is_demo = models.BooleanField(default=False)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.get_username()
