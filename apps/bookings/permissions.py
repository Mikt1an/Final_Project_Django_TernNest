from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)
from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)

from apps.listings.models import Listing


def _get_requested_listing(request):
    listing_id = request.data.get("listing")

    if listing_id in (None, ""):
        return None

    try:
        return Listing.objects.only(
            "id",
            "owner_id",
        ).get(pk=listing_id)
    except (
        Listing.DoesNotExist,
        DjangoValidationError,
        TypeError,
        ValueError,
    ):
        return None


class CanCreateBooking(BasePermission):
    message = "You cannot book your own listing."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method != "POST":
            return True

        listing = _get_requested_listing(request)

        if listing is None:
            return True

        return listing.owner_id != request.user.id


class IsBookingParticipant(BasePermission):
    message = (
        "Only the guest or the listing owner "
        "can view this booking."
    )

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return obj.guest_id == request.user.id or obj.listing.owner_id == request.user.id


class IsBookingGuest(BasePermission):
    message = "Only the booking guest can perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.guest_id == request.user.id


class IsBookingListingOwner(BasePermission):
    message = "Only the listing owner can perform this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.listing.owner_id == request.user.id


class IsBlockedPeriodListingOwner(BasePermission):
    message = "Only the listing owner can manage blocked periods."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in ("POST", "PUT", "PATCH"):
            listing = _get_requested_listing(request)

            if listing is None:
                return True

            return listing.owner_id == request.user.id

        return True

    def has_object_permission(self, request, view, obj):
        return obj.listing.owner_id == request.user.id