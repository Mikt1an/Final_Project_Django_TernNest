from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.listings.validators import validate_max_images
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

    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, validators=[
            MinValueValidator(Decimal(str(MIN_PRICE_PER_NIGHT))),
            MaxValueValidator(Decimal(str(MAX_PRICE_PER_NIGHT))),
        ],
                                          )

    max_guests = models.PositiveIntegerField(default=1, validators=[
            MinValueValidator(MIN_GUESTS),
            MaxValueValidator(MAX_GUESTS),
        ],
                                             )
    bedrooms = models.PositiveIntegerField(default=1, validators=[
            MaxValueValidator(MAX_BEDROOMS),
        ],
                                           )
    beds = models.PositiveIntegerField(default=1, validators=[
            MinValueValidator(1),
            MaxValueValidator(MAX_BEDS),
        ],
                                       )
    bathrooms = models.PositiveIntegerField(default=1, validators=[
            MinValueValidator(1),
            MaxValueValidator(MAX_BATHROOMS),
        ],
                                            )

    amenities = models.ManyToManyField(Amenity, related_name="listings", blank=True,)

    is_active = models.BooleanField(default=True,)

    def save(self, *args, **kwargs):
        if self.listing_type == self.ListingType.STUDIO:
            self.bedrooms = 0

        super().save(*args, **kwargs)


    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Listing"
        verbose_name_plural = "Listings"

        constraints = [
            models.CheckConstraint(
                condition=(models.Q(listing_type="studio", bedrooms=0,)
                        |
                        models.Q(~models.Q(listing_type="studio"),bedrooms__gte=1,)
                ),
                name="valid_bedrooms_for_listing_type",
            ),
            models.CheckConstraint(condition=models.Q(price_per_night__gte=1), name="listing_price_per_night_gte_1",),
            models.CheckConstraint(condition=models.Q(max_guests__gte=1), name="listing_max_guests_gte_1",),
            models.CheckConstraint(condition=models.Q(bedrooms__gte=1), name="listing_bedrooms_gte_1",),
            models.CheckConstraint(condition=models.Q(beds__gte=1), name="listing_beds_gte_1",),
            models.CheckConstraint(condition=models.Q(bathrooms__gte=1), name="listing_bathrooms_gte_1",),
        ]


    def __str__(self):
        return self.title


class ListingImage(TimeStampedModel):
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="images",)

    image = models.ImageField(upload_to="apartments/photos/",)

    is_main = models.BooleanField(default=False,)

    def clean(self):
        super().clean()

        if self._state.adding:
            validate_max_images(self.listing.images.count())

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ("-is_main", "created_at")
        verbose_name = "Listing image"
        verbose_name_plural = "Listing images"

    def __str__(self):
        return f"{self.listing.title} - Image {self.pk}"


class Favorite(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="favorites",)
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="favorites",)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"

        constraints = [models.UniqueConstraint(fields=("user", "listing"), name="unique_user_listing_favorite",),]

    def __str__(self):
        return f"{self.user.username} - {self.listing.title}"