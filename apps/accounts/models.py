from django.db import models
from django.contrib.auth.models import AbstractUser

from apps.core.models import TimeStampedModel
from apps.accounts.managers import UserManager
from apps.accounts.validators import (
    phone_number_validator,
    validate_birth_date,
)


# Create your models here.
class User(AbstractUser, TimeStampedModel):
    username = None

    first_name = models.CharField(max_length=150,)
    last_name = models.CharField(max_length=150,)
    email = models.EmailField(unique=True,)
    phone_number = models.CharField(max_length=16, unique=True, validators=[phone_number_validator],)
    birth_date = models.DateField(
        null=True,
        blank=True,
        validators=[validate_birth_date],
    )

    avatar = models.ImageField(upload_to="users/avatars/", null=True, blank=True,)

    is_verified = models.BooleanField(default=False,)

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "phone_number",
    ]

    objects = UserManager()

    deleted_at = models.DateTimeField(null=True, blank=True,)

    class Meta(AbstractUser.Meta):
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"