from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.bookings.models import Booking
from apps.core.models import TimeStampedModel

from .constants import (
    ALLOWED_REVIEW_IMAGE_EXTENSIONS,
    MAX_REVIEW_CHARACTERS,
    MAX_REVIEW_IMAGES,
)
from .validators import (
    validate_review_image_size,
    validate_review_words,
)


# Create your models here.
class Review(TimeStampedModel):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="reviews",)

    rating = models.PositiveSmallIntegerField(validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )

    liked = models.TextField(max_length=MAX_REVIEW_CHARACTERS, blank=True, validators=[
            validate_review_words,
        ],
    )

    disliked = models.TextField(max_length=MAX_REVIEW_CHARACTERS, blank=True, validators=[
            validate_review_words,
        ],
    )

    class Meta:
        ordering = ("-created_at",)

        constraints = [
            models.CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
        ]

    def clean(self):
        super().clean()

        self.liked = (self.liked or "").strip()
        self.disliked = (self.disliked or "").strip()

        if not self.liked and not self.disliked:
            raise ValidationError(
                "At least one reviews text field must be filled."
            )

        if not self.booking_id:
            return

        if self.booking.status != Booking.Status.COMPLETED:
            raise ValidationError(
                {
                    "booking": (
                        "A reviews can only be created "
                        "for a completed booking."
                    )
                }
            )

        if self.booking.check_out > timezone.localdate():
            raise ValidationError(
                {
                    "booking": (
                        "A reviews can only be created "
                        "after the stay has ended."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.booking.guest} - "
            f"{self.booking.listing} - "
            f"{self.rating}/5"
        )


class ReviewImage(TimeStampedModel):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="images",)

    image = models.ImageField(upload_to="users/reviews/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=ALLOWED_REVIEW_IMAGE_EXTENSIONS,
            ),
            validate_review_image_size,
        ],
    )

    def clean(self):
        super().clean()

        if not self.review_id:
            return

        images_count = (self.review.images.exclude(pk=self.pk).count())

        if images_count >= MAX_REVIEW_IMAGES:
            raise ValidationError(
                {
                    "image": (
                        f"A reviews can contain no more than "
                        f"{MAX_REVIEW_IMAGES} images."
                    )
                }
            )

    def __str__(self):
        return f"Image for reviews #{self.review_id}"