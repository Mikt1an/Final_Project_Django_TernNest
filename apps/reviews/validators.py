from django.core.exceptions import ValidationError

from .constants import (
    MAX_REVIEW_WORDS,
    MAX_REVIEW_IMAGE_SIZE,
)


def validate_review_words(value):
    if not value:
        return

    words_count = len(value.split())

    if words_count > MAX_REVIEW_WORDS:
        raise ValidationError(
            f"Review text cannot exceed {MAX_REVIEW_WORDS} words."
        )


def validate_review_image_size(image):
    if image.size > MAX_REVIEW_IMAGE_SIZE:
        raise ValidationError(
            "Image size cannot exceed 5 MB."
        )