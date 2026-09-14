from django.core.validators import RegexValidator


phone_number_validator = RegexValidator(
    regex=r"^\+[1-9]\d{7,14}$",
    message=(
        "Enter a valid phone number in international format. "
        "Example: +491701234567."
    ),
)