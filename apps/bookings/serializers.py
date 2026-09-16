from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.bookings.models import Booking, BlockedPeriod
from apps.listings.serializers import ListingReadSerializer


class BookingReadSerializer(serializers.ModelSerializer):
    guest = UserPublicSerializer(read_only=True)
    listing = ListingReadSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "guest",
            "listing",
            "check_in",
            "check_out",
            "book_days",
            "guests",
            "total_price",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BookingCreateSerializer(serializers.ModelSerializer):
    guest = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Booking
        fields = (
            "id",
            "guest",
            "listing",
            "check_in",
            "check_out",
            "book_days",
            "guests",
            "total_price",
            "status",
            "created_at",
        )
        read_only_fields = (
            "id",
            "book_days",
            "total_price",
            "status",
            "created_at",
        )

    def validate(self, attrs):
        guest = attrs["guest"]
        listing = attrs["listing"]
        check_in = attrs["check_in"]
        check_out = attrs["check_out"]
        guests = attrs["guests"]

        errors = {}

        if check_in < timezone.now():
            errors["check_in"] = "Check-in cannot be in the past."

        book_days = (check_out.date() - check_in.date()).days

        if check_out <= check_in:
            errors["check_out"] = "Check-out must be later than check-in."
        elif book_days < 1:
            errors["check_out"] = "A booking must include at least one night."

        if guest.pk == listing.owner_id:
            errors["listing"] = "You cannot book your own listing."
        elif not listing.is_active:
            errors["listing"] = "This listing is currently unavailable."

        if guests > listing.max_guests:
            errors["guests"] = (
                f"This listing allows a maximum of "
                f"{listing.max_guests} guests."
            )

        if check_in.time()< listing.earliest_check_in_time:
            errors["check_in"] = (
                f"Check-in cannot be earlier than "
                f"{listing.earliest_check_in_time.strftime('%H:%M')}."
            )

        if check_out.time()> listing.latest_check_out_time:
            errors["check_out"] = (
                f"Check-out cannot be later than "
                f"{listing.latest_check_out_time.strftime('%H:%M')}."
            )

        if errors:
            raise serializers.ValidationError(errors)

        overlapping_booking_exists = (
            Booking.objects
            .filter(
                listing=listing,
                check_in__lt=check_out,
                check_out__gt=check_in,
            )
            .exclude(status=Booking.Status.CANCELLED)
            .exists()
        )

        if overlapping_booking_exists:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "The listing is already booked "
                        "during the selected time."
                    ]
                }
            )

        blocked_period_exists = BlockedPeriod.objects.filter(
            listing=listing,
            start_at__lt=check_out,
            end_at__gt=check_in,
        ).exists()

        if blocked_period_exists:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "The listing is unavailable "
                        "during the selected time."
                    ]
                }
            )

        attrs["book_days"] = book_days
        attrs["total_price"] = listing.price_per_night * book_days

        return attrs


class BlockedPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedPeriod
        fields = (
            "id",
            "listing",
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context.get("request")

        listing = attrs.get("listing", getattr(self.instance, "listing", None),)
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None),)
        end_at = attrs.get("end_at", getattr(self.instance, "end_at", None),)

        errors = {}

        if request is None or not request.user.is_authenticated:
            errors["detail"] = "Authentication is required."
        elif listing.owner_id != request.user.id:
            errors["listing"] = "Only the listing owner can block time."

        if start_at < timezone.now():
            errors["start_at"] = (
                "The blocked period cannot start in the past."
            )

        if end_at <= start_at:
            errors["end_at"] = (
                "End time must be later than start time."
            )

        if errors:
            raise serializers.ValidationError(errors)

        blocked_periods = BlockedPeriod.objects.filter(
            listing=listing,
            start_at__lt=end_at,
            end_at__gt=start_at,
        )

        if self.instance is not None:
            blocked_periods = blocked_periods.exclude(pk=self.instance.pk)

        if blocked_periods.exists():
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "This period overlaps another "
                        "blocked period."
                    ]
                }
            )

        booking_exists = (
            Booking.objects
            .filter(
                listing=listing,
                check_in__lt=end_at,
                check_out__gt=start_at,
            )
            .exclude(status=Booking.Status.CANCELLED)
            .exists()
        )

        if booking_exists:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "This period contains an "
                        "existing booking."
                    ]
                }
            )

        return attrs