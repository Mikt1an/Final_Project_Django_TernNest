from decimal import Decimal

from django.db.models import (
    Exists,
    F,
    OuterRef,
    Q,
)
from django.utils import timezone
from rest_framework import serializers

from apps.bookings.models import (
    BlockedPeriod,
    Booking,
)
from apps.listings.constants import (
    MAX_BATHROOMS,
    MAX_BEDROOMS,
    MAX_BEDS,
    MAX_GUESTS,
    MAX_PRICE_PER_NIGHT,
    MIN_GUESTS,
    MIN_PRICE_PER_NIGHT,
)
from apps.listings.models import Listing


LISTING_ORDERING_CHOICES = (
    ("-created_at", "Newest first"),
    ("created_at", "Oldest first"),
    ("price_per_night", "Price: low to high"),
    ("-price_per_night", "Price: high to low"),
    ("-rating", "Rating: high to low"),
    ("rating", "Rating: low to high"),
)


class ListingFilterSerializer(serializers.Serializer):
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        trim_whitespace=True,
    )

    city = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        trim_whitespace=True,
    )

    country = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        trim_whitespace=True,
    )

    listing_type = serializers.ChoiceField(
        required=False,
        choices=Listing.ListingType.choices,
    )

    min_price = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal(
            str(MIN_PRICE_PER_NIGHT)
        ),
        max_value=Decimal(
            str(MAX_PRICE_PER_NIGHT)
        ),
    )

    max_price = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal(
            str(MIN_PRICE_PER_NIGHT)
        ),
        max_value=Decimal(
            str(MAX_PRICE_PER_NIGHT)
        ),
    )

    bedrooms = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=MAX_BEDROOMS,
    )

    beds = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=MAX_BEDS,
    )

    bathrooms = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=MAX_BATHROOMS,
    )

    guests = serializers.IntegerField(
        required=False,
        min_value=MIN_GUESTS,
        max_value=MAX_GUESTS,
    )

    amenities = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )

    check_in = serializers.DateField(
        required=False,
    )

    check_out = serializers.DateField(
        required=False,
    )

    ordering = serializers.ChoiceField(
        required=False,
        choices=LISTING_ORDERING_CHOICES,
        default="-created_at",
    )

    def validate_amenities(self, value):
        if not value.strip():
            return []

        raw_ids = [
            item.strip()
            for item in value.split(",")
        ]

        try:
            amenity_ids = [
                int(item)
                for item in raw_ids
            ]
        except (TypeError, ValueError) as error:
            raise serializers.ValidationError(
                "Amenities must be comma-separated integer IDs."
            ) from error

        if any(
            amenity_id < 1
            for amenity_id in amenity_ids
        ):
            raise serializers.ValidationError(
                "Amenity IDs must be positive integers."
            )

        return list(
            dict.fromkeys(amenity_ids)
        )

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")

        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            raise serializers.ValidationError(
                {
                    "max_price": (
                        "Maximum price must be greater "
                        "than or equal to minimum price."
                    )
                }
            )

        check_in = attrs.get("check_in")
        check_out = attrs.get("check_out")

        if check_in is not None and check_out is None:
            raise serializers.ValidationError(
                {
                    "check_out": (
                        "Check-out is required when "
                        "check-in is provided."
                    )
                }
            )

        if check_out is not None and check_in is None:
            raise serializers.ValidationError(
                {
                    "check_in": (
                        "Check-in is required when "
                        "check-out is provided."
                    )
                }
            )

        if (
            check_in is not None
            and check_in < timezone.localdate()
        ):
            raise serializers.ValidationError(
                {
                    "check_in": (
                        "Check-in cannot be in the past."
                    )
                }
            )

        if (
            check_in is not None
            and check_out is not None
            and check_out <= check_in
        ):
            raise serializers.ValidationError(
                {
                    "check_out": (
                        "Check-out must be later "
                        "than check-in."
                    )
                }
            )

        return attrs


def filter_listings(queryset, query_params):
    serializer = ListingFilterSerializer(
        data=query_params
    )
    serializer.is_valid(
        raise_exception=True
    )

    filters = serializer.validated_data

    search = filters.get("search")

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
        )

    city = filters.get("city")

    if city:
        queryset = queryset.filter(
            city__icontains=city
        )

    country = filters.get("country")

    if country:
        queryset = queryset.filter(
            country__icontains=country
        )

    listing_type = filters.get(
        "listing_type"
    )

    if listing_type:
        queryset = queryset.filter(
            listing_type=listing_type
        )

    min_price = filters.get("min_price")

    if min_price is not None:
        queryset = queryset.filter(
            price_per_night__gte=min_price
        )

    max_price = filters.get("max_price")

    if max_price is not None:
        queryset = queryset.filter(
            price_per_night__lte=max_price
        )

    bedrooms = filters.get("bedrooms")

    if bedrooms is not None:
        queryset = queryset.filter(
            bedrooms=bedrooms
        )

    beds = filters.get("beds")

    if beds is not None:
        queryset = queryset.filter(
            beds=beds
        )

    bathrooms = filters.get("bathrooms")

    if bathrooms is not None:
        queryset = queryset.filter(
            bathrooms=bathrooms
        )

    guests = filters.get("guests")

    if guests is not None:
        queryset = queryset.filter(
            max_guests__gte=guests
        )

    for amenity_id in filters.get(
        "amenities",
        [],
    ):
        queryset = queryset.filter(
            amenities__id=amenity_id
        )

    check_in = filters.get("check_in")
    check_out = filters.get("check_out")

    if (
        check_in is not None
        and check_out is not None
    ):
        booking_conflicts = (
            Booking.objects
            .filter(
                listing_id=OuterRef("pk"),
                check_in__date__lt=check_out,
                check_out__date__gt=check_in,
            )
            .exclude(
                status__in=(
                    Booking.Status.CANCELLED,
                    Booking.Status.REJECTED,
                )
            )
        )

        blocked_period_conflicts = (
            BlockedPeriod.objects
            .filter(
                listing_id=OuterRef("pk"),
                start_at__date__lt=check_out,
                end_at__date__gt=check_in,
            )
        )

        queryset = (
            queryset
            .annotate(
                has_booking_conflict=Exists(
                    booking_conflicts
                ),
                has_blocked_period_conflict=Exists(
                    blocked_period_conflicts
                ),
            )
            .filter(
                has_booking_conflict=False,
                has_blocked_period_conflict=False,
            )
        )

    queryset = queryset.distinct()

    ordering = filters["ordering"]

    if ordering == "-rating":
        return queryset.order_by(
            F("average_rating").desc(
                nulls_last=True
            ),
            "-created_at",
            "pk",
        )

    if ordering == "rating":
        return queryset.order_by(
            F("average_rating").asc(
                nulls_last=True
            ),
            "-created_at",
            "pk",
        )

    return queryset.order_by(
        ordering,
        "pk",
    )