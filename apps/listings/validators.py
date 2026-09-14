from django.core.exceptions import ValidationError

from .constants import (
    MAX_LISTING_AMENITIES,
    MAX_LISTING_IMAGES,
    MIN_LISTING_IMAGES,
)


def validate_max_images(current_count):
    if current_count >= MAX_LISTING_IMAGES:
        raise ValidationError(
            f"A listing cannot have more than "
            f"{MAX_LISTING_IMAGES} images."
        )


def validate_min_images(current_count):
    if current_count < MIN_LISTING_IMAGES:
        raise ValidationError(
            f"A listing must have at least "
            f"{MIN_LISTING_IMAGES} image."
        )


def validate_amenities_count(current_count, new_count):
    if current_count + new_count > MAX_LISTING_AMENITIES:
        raise ValidationError(
            f"A listing cannot have more than "
            f"{MAX_LISTING_AMENITIES} amenities."
        )