from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.bookings.models import Booking
from apps.reviews.constants import MAX_REVIEW_IMAGES
from apps.reviews.models import Review, ReviewImage


class ReviewImageSerializer(serializers.ModelSerializer):
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
        review = attrs.get("review")

        if review is None and self.instance is not None:
            review = self.instance.review

        if review is None:
            return attrs

        images = review.images.all()

        if self.instance is not None:
            images = images.exclude(pk=self.instance.pk)

        if images.count() >= MAX_REVIEW_IMAGES:
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
    guest = UserPublicSerializer(
        source="booking.guest",
        read_only=True,
    )
    listing_id = serializers.IntegerField(
        source="booking.listing_id",
        read_only=True,
    )
    images = ReviewImageSerializer(
        many=True,
        read_only=True,
    )

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
    booking = serializers.PrimaryKeyRelatedField(
        queryset=Booking.objects.select_related(
            "guest",
            "listing",
            "listing__owner",
        ),
    )

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

    def validate(self, attrs):
        booking = attrs["booking"]

        liked = (attrs.get("liked") or "").strip()
        disliked = (attrs.get("disliked") or "").strip()

        attrs["liked"] = liked
        attrs["disliked"] = disliked

        if not liked and not disliked:
            raise serializers.ValidationError(
                {
                    "non_field_errors": (
                        "At least one review text field must be filled."
                    )
                }
            )

        if booking.status != Booking.Status.COMPLETED:
            raise serializers.ValidationError(
                {
                    "booking": (
                        "A review can only be created "
                        "for a completed booking."
                    )
                }
            )

        if booking.check_out > timezone.now():
            raise serializers.ValidationError(
                {
                    "booking": (
                        "A review can only be created "
                        "after the stay has ended."
                    )
                }
            )

        if booking.guest_id == booking.listing.owner_id:
            raise serializers.ValidationError(
                {
                    "booking": (
                        "A listing owner cannot review "
                        "their own listing."
                    )
                }
            )

        if Review.objects.filter(booking=booking).exists():
            raise serializers.ValidationError(
                {
                    "booking": (
                        "A review already exists for this booking."
                    )
                }
            )

        return attrs