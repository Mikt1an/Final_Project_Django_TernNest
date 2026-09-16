from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.bookings.models import Booking
from apps.reviews.constants import MAX_REVIEW_IMAGES
from apps.reviews.models import Review, ReviewImage


class ReviewImageSerializer(serializers.ModelSerializer):
    review = serializers.PrimaryKeyRelatedField(queryset=Review.objects.all(), write_only=True,)

    class Meta:
        model = ReviewImage
        fields = (
            "id",
            "review",
            "image",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
        )

    def validate(self, attrs):
        request = self.context.get("request")

        review = attrs.get("review", getattr(self.instance, "review", None),)

        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError({"detail": "Authentication is required."})

        if review.booking.guest_id != request.user.id:
            raise serializers.ValidationError({"review": (
                        "You can only add images "
                        "to your own review."
                    )
                }
            )

        if self.instance is None and review.images.count() >= MAX_REVIEW_IMAGES:
            raise serializers.ValidationError(
                {
                    "image": (
                        f"A review can contain no more than "
                        f"{MAX_REVIEW_IMAGES} images."
                    )
                }
            )

        return attrs


class ReviewReadSerializer(serializers.ModelSerializer):
    guest = UserPublicSerializer(source="booking.guest", read_only=True,)
    listing_id = serializers.IntegerField(source="booking.listing_id", read_only=True,)
    images = ReviewImageSerializer(many=True, read_only=True,)

    class Meta:
        model = Review
        fields = (
            "id",
            "booking",
            "listing_id",
            "guest",
            "rating",
            "liked",
            "disliked",
            "images",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReviewCreateSerializer(serializers.ModelSerializer):
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all(),)

    class Meta:
        model = Review
        fields = (
            "id",
            "booking",
            "rating",
            "liked",
            "disliked",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
        )
        extra_kwargs = {
            "rating": {
                "required": False,
                "allow_null": True,
            },
        }

    def validate(self, attrs):
        request = self.context.get("request")
        booking = attrs["booking"]

        liked = (attrs.get("liked") or "").strip()
        disliked = (attrs.get("disliked") or "").strip()

        errors = {}

        if request is None or not request.user.is_authenticated:
            errors["detail"] = "Authentication is required."
        elif booking.guest_id != request.user.id:
            errors["booking"] = "You can only review your own booking."

        if booking.status != Booking.Status.COMPLETED:
            errors["booking"] = (
                "A review can only be created "
                "for a completed booking."
            )

        if booking.check_out > timezone.now():
            errors["booking"] = (
                "A review can only be created "
                "after the stay has ended."
            )

        if booking.guest_id == booking.listing.owner_id:
            errors["booking"] = (
                "A listing owner cannot review "
                "their own listing."
            )

        if Review.objects.filter(booking=booking).exists():
            errors["booking"] = "A review already exists for this booking."

        if not liked and not disliked:
            errors["non_field_errors"] = [
                "At least one review text field "
                "must be filled."
            ]

        if errors:
            raise serializers.ValidationError(errors)

        attrs["liked"] = liked
        attrs["disliked"] = disliked

        return attrs