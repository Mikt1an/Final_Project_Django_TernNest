from rest_framework.permissions import (
    BasePermission,
    SAFE_METHODS,
)

from apps.listings.models import Listing


class IsAdminOrReadOnly(BasePermission):
    message = "Only administrators can modify amenities."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return request.user.is_authenticated and request.user.is_staff


class IsListingOwnerOrReadOnly(BasePermission):
    message = "Only the listing owner can modify this listing."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return request.user.is_authenticated and obj.owner_id == request.user.id


class IsListingImageOwnerOrReadOnly(BasePermission):
    message = (
        "Only the listing owner can add, modify, "
        "or delete its images."
    )

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if not request.user.is_authenticated:
            return False

        if request.method == "POST":
            listing_id = request.data.get("listing")

            if listing_id is None:
                return True

            return Listing.objects.filter(pk=listing_id, owner_id=request.user.id,).exists()

        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return request.user.is_authenticated and obj.listing.owner_id == request.user.id


class IsFavoriteOwner(BasePermission):
    message = "You can only manage your own favorites."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id