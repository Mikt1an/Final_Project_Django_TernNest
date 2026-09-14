from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

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

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="listings",)
    title = models.CharField(max_length=200,)
    description = models.TextField()
    listing_type = models.CharField(max_length=20, choices=ListingType.choices, default=ListingType.APARTMENT,)

    country = models.CharField(max_length=100,)
    city = models.CharField(max_length=100,)
    address = models.CharField(max_length=255,)

    price_per_night = models.DecimalField(max_digits=10, decimal_places=2,)

    max_guests = models.PositiveIntegerField(default=1,)
    bedrooms = models.PositiveIntegerField(default=1,)
    beds = models.PositiveIntegerField(default=1,)
    bathrooms = models.PositiveIntegerField(default=1,)

    amenities = models.ManyToManyField(Amenity, related_name="listings", blank=True,)

    is_active = models.BooleanField(default=True,)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Listing"
        verbose_name_plural = "Listings"

    def __str__(self):
        return self.title


class ListingImage(TimeStampedModel):
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="images",)

    image = models.ImageField(upload_to="listings/",)

    is_main = models.BooleanField(default=False,)

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