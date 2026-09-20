from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.listings.models import Listing


# Create your models here.
class Booking(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings",)
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="bookings",)

    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    book_days = models.PositiveIntegerField(validators=[MinValueValidator(1)],)

    guests = models.PositiveIntegerField(validators=[MinValueValidator(1)],)

    total_price = models.DecimalField(max_digits=10, decimal_places=2,)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING,)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(check_out__gt=models.F("check_in")),
                name="booking_check_out_after_check_in",
            ),
            models.CheckConstraint(
                condition=models.Q(book_days__gte=1),
                name="booking_book_days_positive",
            ),
        )

    def __str__(self):
        return (
            f"{self.guest} - {self.listing.title} "
            f"({self.check_in} - {self.check_out})"
            f"({self.book_days} days)"
        )


class BlockedPeriod(TimeStampedModel):
    class Reason(models.TextChoices):
        MAINTENANCE = "maintenance", "Maintenance"
        RENOVATION = "renovation", "Renovation"
        OWNER_STAY = "owner_stay", "Owner stay"
        VACATION = "vacation", "Vacation"
        OTHER = "other", "Other"

    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="blocked_periods",)

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.OTHER,)

    note = models.CharField(max_length=255, blank=True, default="",)

    class Meta:
        ordering = ("start_at",)
        verbose_name = "Blocked period"
        verbose_name_plural = "Blocked periods"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    end_at__gt=models.F("start_at"),
                ),
                name="blocked_period_end_after_start",
            ),
        ]

    def __str__(self):
        return (
            f"{self.listing.title}: "
            f"{self.start_at} - {self.end_at}"
        )