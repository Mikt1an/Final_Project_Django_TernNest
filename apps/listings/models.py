from datetime import time
from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.listings.constants import (
    MAX_BATHROOMS,
    MAX_BEDROOMS,
    MAX_BEDS,
    MAX_GUESTS,
    MAX_PRICE_PER_NIGHT,
    MIN_GUESTS,
    MIN_PRICE_PER_NIGHT,
)
from apps.listings.validators import validate_max_images


# Create your models here.
class Amenity(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True,)

    class Meta:
        ordering = ("name",)
        verbose_name = "Amenity"
        verbose_name_plural = "Amenities"

    def __str__(self):
        return self.name


class Listing(TimeStampedModel):
    class ListingType(models.TextChoices):
        APARTMENT = "apartment", "Apartment"
        HOUSE = "house", "House"
        STUDIO = "studio", "Studio"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="listings",)

    title = models.CharField(max_length=200,)

    description = models.TextField()

    listing_type = models.CharField(max_length=20, choices=ListingType.choices, default=ListingType.APARTMENT,)

    country = models.CharField(max_length=100,)

    city = models.CharField(max_length=100,)

    address = models.CharField(max_length=255,)

    earliest_check_in_time = models.TimeField(default=time(15, 0),)

    latest_check_out_time = models.TimeField(default=time(11, 0),)

    price_per_night = models.DecimalField(max_digits=10, decimal_places=2,
        validators=[
            MinValueValidator(
                Decimal(
                    str(MIN_PRICE_PER_NIGHT)
                )
            ),
            MaxValueValidator(
                Decimal(
                    str(MAX_PRICE_PER_NIGHT)
                )
            ),
        ],
    )

    max_guests = models.PositiveIntegerField(default=1,
        validators=[
            MinValueValidator(
                MIN_GUESTS
            ),
            MaxValueValidator(
                MAX_GUESTS
            ),
        ],
    )

    bedrooms = models.PositiveIntegerField(default=1,
        validators=[
            MaxValueValidator(
                MAX_BEDROOMS
            ),
        ],
    )

    beds = models.PositiveIntegerField(default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(
                MAX_BEDS
            ),
        ],
    )

    bathrooms = models.PositiveIntegerField(default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(
                MAX_BATHROOMS
            ),
        ],
    )

    amenities = models.ManyToManyField(Amenity, related_name="listings",blank=True,)

    is_active = models.BooleanField(default=True,)

    def save(self, *args, **kwargs):
        if self.listing_type == self.ListingType.STUDIO:
            self.bedrooms = 0

        super().save(*args, **kwargs,)

    class Meta:
        ordering = ("-created_at",)

        verbose_name = "Listing"
        verbose_name_plural = "Listings"

        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        listing_type="studio",
                        bedrooms=0,
                    )
                    |
                    models.Q(
                        ~models.Q(
                            listing_type="studio"
                        ),
                        bedrooms__gte=1,
                    )
                ),
                name=(
                    "valid_bedrooms_for_"
                    "listing_type"
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(
                    price_per_night__gte=(
                        MIN_PRICE_PER_NIGHT
                    )
                ),
                name=(
                    "listing_price_per_"
                    "night_gte_1"
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(
                    max_guests__gte=(
                        MIN_GUESTS
                    )
                ),
                name=(
                    "listing_max_guests_"
                    "gte_1"
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(
                    beds__gte=1
                ),
                name="listing_beds_gte_1",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    bathrooms__gte=1
                ),
                name=(
                    "listing_bathrooms_"
                    "gte_1"
                ),
            ),
        ]

    def __str__(self):
        return self.title


class ListingImage(TimeStampedModel):
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT,related_name="images",)

    image = models.ImageField(upload_to="apartments/photos/",)

    is_main = models.BooleanField(default=False,)

    def clean(self):
        super().clean()

        if self._state.adding:
            validate_max_images(self.listing.images.count())

    def save(self, *args, **kwargs):
        self.full_clean()

        super().save(*args, **kwargs,)

    class Meta:
        ordering = ("-is_main", "created_at",)

        verbose_name = "Listing image"
        verbose_name_plural = ("Listing images")

    def __str__(self):
        return (
            f"{self.listing.title} "
            f"- Image {self.pk}"
        )


class Favorite(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="favorites",)

    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="favorites",)

    class Meta:
        ordering = ("-created_at",)

        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "user",
                    "listing",
                ),
                name=(
                    "unique_user_listing_"
                    "favorite"
                ),
            ),
        ]

    def __str__(self):
        return (
            f"{self.user.email} "
            f"- {self.listing.title}"
        )


class ListingView(TimeStampedModel):
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="views",)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="listing_views",
        null=True,
        blank=True,
    )

    viewer_key = models.CharField(max_length=80, editable=False,)

    viewed_on = models.DateField(default=timezone.localdate, editable=False,)

    class Meta:
        ordering = ("-updated_at", "-created_at",)

        verbose_name = "Listing view"
        verbose_name_plural = "Listing views"

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "listing",
                    "viewer_key",
                    "viewed_on",
                ),
                name=(
                    "unique_daily_listing_"
                    "view"
                ),
            ),
        ]

        indexes = [
            models.Index(
                fields=(
                    "user",
                    "viewed_on",
                ),
                name=(
                    "listing_view_user_"
                    "date_idx"
                ),
            ),
        ]

    def __str__(self):
        viewer = (self.user.email if self.user_id else "Anonymous")

        return (
            f"{viewer} viewed "
            f"{self.listing.title} "
            f"on {self.viewed_on}"
        )


class SearchHistory(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="search_history",
        null=True,
        blank=True,
    )

    searcher_key = models.CharField(max_length=80, editable=False,)

    query = models.CharField(max_length=200,)

    normalized_query = models.CharField(max_length=200, editable=False,)

    searched_on = models.DateField(default=timezone.localdate, editable=False,
)

    @staticmethod
    def normalize_query(value):
        cleaned_query = " ".join(str(value or "").split())

        return cleaned_query.casefold()

    def save(self, *args, **kwargs):
        self.query = " ".join(str(self.query or "").split())

        self.normalized_query = (self.normalize_query(self.query))

        super().save(*args, **kwargs,)

    class Meta:
        ordering = ("-created_at",)

        verbose_name = "Search history"
        verbose_name_plural = ("Search history")

        constraints = [
            models.CheckConstraint(
                condition=(
                    ~models.Q(
                        searcher_key=""
                    )
                ),
                name=(
                    "search_history_key_"
                    "not_empty"
                ),
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(
                        normalized_query=""
                    )
                ),
                name=(
                    "search_history_query_"
                    "not_empty"
                ),
            ),
        ]

        indexes = [
            models.Index(
                fields=(
                    "normalized_query",
                    "-created_at",
                ),
                name=(
                    "search_history_query_"
                    "idx"
                ),
            ),
            models.Index(
                fields=(
                    "user",
                    "-created_at",
                ),
                name=(
                    "search_history_user_"
                    "idx"
                ),
            ),
            models.Index(
                fields=(
                    "searcher_key",
                    "-created_at",
                ),
                name=(
                    "search_history_key_"
                    "idx"
                ),
            ),
        ]

    def __str__(self):
        searcher = (self.user.email if self.user_id else "Anonymous")

        return (
            f"{searcher} searched "
            f"for {self.query}"
        )