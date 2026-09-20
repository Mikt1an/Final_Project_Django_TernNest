from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from django.db.models import Avg

from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.listings.models import (
    Amenity,
    Favorite,
    Listing,
    ListingImage,
)
from apps.listings.validators import (
    validate_amenities_count,
    validate_max_images,
    validate_min_images,
)


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = (
            "id",
            "name",
        )
        read_only_fields = ("id",)


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = (
            "id",
            "image",
            "is_main",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
        )

    def create(self, validated_data):
        listing = validated_data.get("listing")

        if listing is not None:
            try:
                validate_max_images(
                    listing.images.count()
                )
            except DjangoValidationError as error:
                raise serializers.ValidationError(
                    {
                        "image": list(
                            error.messages
                        )
                    }
                ) from error

        return super().create(validated_data)


class ListingReadSerializer(serializers.ModelSerializer):
    owner = UserPublicSerializer(
        read_only=True,
    )

    amenities = AmenitySerializer(
        many=True,
        read_only=True,
    )

    images = ListingImageSerializer(
        many=True,
        read_only=True,
    )

    rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()

    is_favorite = serializers.SerializerMethodField()
    favorite_id = serializers.SerializerMethodField()

    class Meta:
        model = Listing

        fields = (
            "id",
            "owner",
            "title",
            "description",
            "listing_type",
            "country",
            "city",
            "address",
            "earliest_check_in_time",
            "latest_check_out_time",
            "price_per_night",
            "max_guests",
            "bedrooms",
            "beds",
            "bathrooms",
            "amenities",
            "images",

            # Reviews
            "rating",
            "reviews_count",

            # Favorites
            "is_favorite",
            "favorite_id",

            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = fields

    def get_rating(self, obj):
        value = getattr(
            obj,
            "average_rating",
            None,
        )

        if value is None:
            value = (
                obj.bookings
                .filter(
                    review__rating__isnull=False
                )
                .aggregate(
                    average=Avg(
                        "review__rating"
                    )
                )
                .get("average")
            )

        if value is None:
            return None

        return round(
            float(value),
            1,
        )

    def get_reviews_count(self, obj):
        value = getattr(
            obj,
            "reviews_count_value",
            None,
        )

        if value is not None:
            return value

        return (
            obj.bookings
            .filter(
                review__isnull=False
            )
            .count()
        )

    def _get_favorite(self, obj):
        request = self.context.get("request")

        if (
            request is None
            or not request.user.is_authenticated
        ):
            return None

        cache_name = (
            f"_favorite_for_user_"
            f"{request.user.pk}"
        )

        if hasattr(obj, cache_name):
            return getattr(
                obj,
                cache_name,
            )

        favorite = (
            Favorite.objects
            .filter(
                user=request.user,
                listing=obj,
            )
            .only("id")
            .first()
        )

        setattr(
            obj,
            cache_name,
            favorite,
        )

        return favorite

    def get_is_favorite(self, obj):
        return (
            self._get_favorite(obj)
            is not None
        )

    def get_favorite_id(self, obj):
        favorite = self._get_favorite(obj)

        if favorite is None:
            return None

        return favorite.id


class ListingWriteSerializer(serializers.ModelSerializer):
    amenities = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(),
        many=True,
        required=False,
    )

    earliest_check_in_time = serializers.TimeField(
        required=True,
    )

    latest_check_out_time = serializers.TimeField(
        required=True,
    )

    class Meta:
        model = Listing

        fields = (
            "id",
            "title",
            "description",
            "listing_type",
            "country",
            "city",
            "address",
            "earliest_check_in_time",
            "latest_check_out_time",
            "price_per_night",
            "max_guests",
            "bedrooms",
            "beds",
            "bathrooms",
            "amenities",
            "is_active",
        )

        read_only_fields = ("id",)

    def validate_amenities(self, amenities):
        try:
            validate_amenities_count(
                current_count=0,
                new_count=len(amenities),
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                list(error.messages)
            ) from error

        return amenities

    def validate(self, attrs):
        if self.instance is not None:
            current_listing_type = (
                self.instance.listing_type
            )

            current_bedrooms = (
                self.instance.bedrooms
            )

            current_check_in_time = (
                self.instance
                .earliest_check_in_time
            )

            current_check_out_time = (
                self.instance
                .latest_check_out_time
            )

        else:
            current_listing_type = (
                Listing.ListingType.APARTMENT
            )

            current_bedrooms = 1

            current_check_in_time = None
            current_check_out_time = None

        listing_type = attrs.get(
            "listing_type",
            current_listing_type,
        )

        bedrooms = attrs.get(
            "bedrooms",
            current_bedrooms,
        )

        earliest_check_in_time = attrs.get(
            "earliest_check_in_time",
            current_check_in_time,
        )

        latest_check_out_time = attrs.get(
            "latest_check_out_time",
            current_check_out_time,
        )

        if (
            listing_type
            == Listing.ListingType.STUDIO
        ):
            attrs["bedrooms"] = 0

        elif bedrooms < 1:
            raise serializers.ValidationError(
                {
                    "bedrooms": (
                        "Apartments and houses must "
                        "have at least one bedroom."
                    )
                }
            )

        if (
            earliest_check_in_time is not None
            and latest_check_out_time is not None
            and earliest_check_in_time
            <= latest_check_out_time
        ):
            raise serializers.ValidationError(
                {
                    "earliest_check_in_time": (
                        "Check-in time must be later "
                        "than check-out time to allow "
                        "property turnover."
                    )
                }
            )

        target_is_active = attrs.get(
            "is_active",
            (
                self.instance.is_active
                if self.instance is not None
                else False
            ),
        )

        if (
            self.instance is not None
            and target_is_active
        ):
            try:
                validate_min_images(
                    self.instance.images.count()
                )
            except DjangoValidationError as error:
                raise serializers.ValidationError(
                    {
                        "is_active": list(
                            error.messages
                        )
                    }
                ) from error

        return attrs

    def create(self, validated_data):
        validated_data["is_active"] = False

        return super().create(
            validated_data
        )


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite

        fields = (
            "id",
            "listing",
            "created_at",
        )

        read_only_fields = (
            "id",
            "created_at",
        )