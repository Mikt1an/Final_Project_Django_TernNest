from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.serializers import UserPublicSerializer
from apps.listings.models import (
    Amenity,
    Favorite,
    Listing,
    ListingImage,
)
from apps.listings.validators import validate_max_images


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
                validate_max_images(listing.images.count())
            except DjangoValidationError as error:
                raise serializers.ValidationError({"image": list(error.messages)}) from error

        return super().create(validated_data)


class ListingReadSerializer(serializers.ModelSerializer):
    owner = UserPublicSerializer(read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True,)
    images = ListingImageSerializer(many=True, read_only=True,)

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
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ListingWriteSerializer(serializers.ModelSerializer):
    amenities = serializers.PrimaryKeyRelatedField(queryset=Amenity.objects.all(),many=True, required=False,)
    earliest_check_in_time = serializers.TimeField(required=True,)
    latest_check_out_time = serializers.TimeField(required=True,)

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


    def validate(self, attrs):
        if self.instance is not None:
            current_listing_type = self.instance.listing_type
            current_bedrooms = self.instance.bedrooms
            current_check_in_time = self.instance.earliest_check_in_time
            current_check_out_time = self.instance.latest_check_out_time
        else:
            current_listing_type = Listing.ListingType.APARTMENT
            current_bedrooms = 1
            current_check_in_time = None
            current_check_out_time = None

        listing_type = attrs.get("listing_type", current_listing_type,)
        bedrooms = attrs.get("bedrooms", current_bedrooms,)
        earliest_check_in_time = attrs.get("earliest_check_in_time", current_check_in_time,)
        latest_check_out_time = attrs.get("latest_check_out_time", current_check_out_time,)

        if listing_type == Listing.ListingType.STUDIO:
            attrs["bedrooms"] = 0
        elif bedrooms < 1:
            raise serializers.ValidationError(
                {
                    "bedrooms": (
                        "Apartments and houses must have "
                        "at least one bedroom."
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
                        "Check-in time must be later than "
                        "check-out time to allow property "
                        "turnover."
                    )
                }
            )

        return attrs


class FavoriteSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Favorite
        fields = (
            "id",
            "user",
            "listing",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
        )