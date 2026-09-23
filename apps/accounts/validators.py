from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone

from apps.accounts.constants import MAX_USER_AGE


phone_number_validator = RegexValidator(
    regex=r"^\+[1-9]\d{7,14}$",
    message=(
        "Enter a valid phone number in international format. "
        "Example: +491701234567."
    ),
)


def validate_birth_date(value):
    if value is None:
        return

    today = timezone.localdate()

    if value > today:
        raise ValidationError(
            "Birth date cannot be in the future.",
            code="future_birth_date",
        )

    age = today.year - value.year - (
        (today.month, today.day) < (value.month, value.day)
    )

    if age > MAX_USER_AGE:
        raise ValidationError(
            "Age must not exceed %(max_age)s years.",
            code="max_age",
            params={"max_age": MAX_USER_AGE},
        )