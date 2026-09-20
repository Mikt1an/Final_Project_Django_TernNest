from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.bookings.models import Booking, BlockedPeriod
from apps.listings.models import Listing
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
    listing = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(),
    )

    class Meta:
        model = Booking
        fields = (
            "id",
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
        listing = attrs["listing"]
        check_in = attrs["check_in"]
        check_out = attrs["check_out"]
        guests = attrs["guests"]

        if check_in <= timezone.now():
            raise serializers.ValidationError(
                {
                    "check_in": (
                        "Check-in must be in the future."
                    )
                }
            )

        if check_out <= check_in:
            raise serializers.ValidationError(
                {
                    "check_out": (
                        "Check-out must be later than check-in."
                    )
                }
            )

        book_days = (check_out.date() - check_in.date()).days

        if book_days < 1:
            raise serializers.ValidationError(
                {
                    "check_out": (
                        "A booking must contain at least one night."
                    )
                }
            )

        if not listing.is_active:
            raise serializers.ValidationError(
                {
                    "listing": (
                        "This listing is not available for booking."
                    )
                }
            )

        if guests > listing.max_guests:
            raise serializers.ValidationError(
                {
                    "guests": (
                        f"This listing allows no more than "
                        f"{listing.max_guests} guests."
                    )
                }
            )

        check_in_time = check_in.time()
        check_out_time = check_out.time()

        if check_in_time< listing.earliest_check_in_time:
            earliest_check_in = listing.earliest_check_in_time.strftime("%H:%M")

            raise serializers.ValidationError(
                {
                    "check_in": (
                        f"Check-in is available from "
                        f"{earliest_check_in}."
                    )
                }
            )

        if check_out_time> listing.latest_check_out_time:
            latest_check_out = listing.latest_check_out_time.strftime("%H:%M")

            raise serializers.ValidationError(
                {
                    "check_out": (
                        f"Check-out must be no later than "
                        f"{latest_check_out}."
                    )
                }
            )

        booking_conflict_exists = (
            Booking.objects.filter(
                listing=listing,
                check_in__lt=check_out,
                check_out__gt=check_in,
            )
            .exclude(
                status__in=(
                    Booking.Status.CANCELLED,
                    Booking.Status.REJECTED,
                ),
            )
            .exists()
        )

        if booking_conflict_exists:
            raise serializers.ValidationError(
                {
                    "non_field_errors": (
                        "This listing is already booked "
                        "for the selected period."
                    )
                }
            )

        blocked_period_exists = (
            BlockedPeriod.objects.filter(
                listing=listing,
                start_at__lt=check_out,
                end_at__gt=check_in,
            ).exists()
        )

        if blocked_period_exists:
            raise serializers.ValidationError(
                {
                    "non_field_errors": (
                        "This listing is unavailable "
                        "for the selected period."
                    )
                }
            )

        attrs["book_days"] = book_days
        attrs["total_price"] = listing.price_per_night * book_days

        return attrs


class BlockedPeriodSerializer(serializers.ModelSerializer):
    listing = serializers.PrimaryKeyRelatedField(
        queryset=Listing.objects.all(),
    )

    class Meta:
        model = BlockedPeriod
        fields = (
            "id",
            "listing",
            "start_at",
            "end_at",
            "reason",
            "note",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        current_listing = (
            self.instance.listing
            if self.instance is not None
            else None
        )
        current_start_at = (
            self.instance.start_at
            if self.instance is not None
            else None
        )
        current_end_at = (
            self.instance.end_at
            if self.instance is not None
            else None
        )

        listing = attrs.get(
            "listing",
            current_listing,
        )
        start_at = attrs.get(
            "start_at",
            current_start_at,
        )
        end_at = attrs.get(
            "end_at",
            current_end_at,
        )

        if start_at < timezone.now():
            raise serializers.ValidationError(
                {
                    "start_at": (
                        "The blocked period cannot start "
                        "in the past."
                    )
                }
            )

        if end_at <= start_at:
            raise serializers.ValidationError(
                {
                    "end_at": (
                        "The end of the blocked period must "
                        "be later than its start."
                    )
                }
            )

        overlapping_periods = BlockedPeriod.objects.filter(
            listing=listing,
            start_at__lt=end_at,
            end_at__gt=start_at,
        )

        if self.instance is not None:
            overlapping_periods = overlapping_periods.exclude(
                pk=self.instance.pk,
            )

        if overlapping_periods.exists():
            raise serializers.ValidationError(
                {
                    "non_field_errors": (
                        "This blocked period overlaps with "
                        "another blocked period."
                    )
                }
            )

        booking_conflict_exists = (
            Booking.objects.filter(
                listing=listing,
                check_in__lt=end_at,
                check_out__gt=start_at,
            )
            .exclude(
                status__in=(
                    Booking.Status.CANCELLED,
                    Booking.Status.REJECTED,
                ),
            )
            .exists()
        )

        if booking_conflict_exists:
            raise serializers.ValidationError(
                {
                    "non_field_errors": (
                        "Existing bookings must be cancelled "
                        "or rescheduled before blocking "
                        "this period."
                    )
                }
            )

        return attrs