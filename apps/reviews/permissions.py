from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)

from apps.bookings.models import Booking
from apps.reviews.models import Review


def _get_requested_booking(request):
    booking_id = request.data.get("booking")

    if booking_id in (None, ""):
        return None

    try:
        return Booking.objects.only("id", "guest_id",).get(pk=booking_id)
    except (
        Booking.DoesNotExist,
        DjangoValidationError,
        TypeError,
        ValueError,
    ):
        return None


def _get_requested_review(request):
    review_id = request.data.get("review")

    if review_id in (None, ""):
        return None

    try:
        return Review.objects.select_related("booking",).only("id", "booking__guest_id",).get(pk=review_id)
    except (
        Review.DoesNotExist,
        DjangoValidationError,
        TypeError,
        ValueError,
    ):
        return None


class CanCreateReview(BasePermission):
    message = (
        "A review can only be created by "
        "the guest who made the booking."
    )

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method != "POST":
            return True

        booking = _get_requested_booking(request)

        if booking is None:
            return True

        return booking.guest_id == request.user.id


class IsReviewAuthorOrReadOnly(BasePermission):
    message = "Only the review author can modify this review."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return obj.booking.guest_id == request.user.id


class IsReviewImageAuthorOrReadOnly(BasePermission):
    message = (
        "Only the review author can add, modify, "
        "or delete its images."
    )

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if not request.user.is_authenticated:
            return False

        if request.method == "POST":
            review = _get_requested_review(request)

            if review is None:
                return True

            return (
                review.booking.guest_id
                == request.user.id
            )

        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return (
            obj.review.booking.guest_id
            == request.user.id
        )