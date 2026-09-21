from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking, BlockedPeriod
from apps.bookings.permissions import (
    CanCreateBooking,
    IsBlockedPeriodListingOwner,
    IsBookingGuest,
    IsBookingListingOwner,
    IsBookingParticipant,
)
from apps.bookings.serializers import (
    BlockedPeriodSerializer,
    BookingCreateSerializer,
    BookingReadSerializer,
)
from apps.bookings.constants import BOOKING_CANCELLATION_DEADLINE_HOURS


def get_booking_queryset():
    return Booking.objects.select_related(
        "guest",
        "listing",
        "listing__owner",
    ).prefetch_related(
        "listing__amenities",
        "listing__images",
    )


class BookingListCreateView(ListCreateAPIView):
    permission_classes = (IsAuthenticated, CanCreateBooking,)

    def get_queryset(self):
        return get_booking_queryset().filter(Q(guest=self.request.user) | Q(listing__owner=self.request.user)).distinct()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return BookingReadSerializer

        return BookingCreateSerializer

    def perform_create(self, serializer):
        serializer.save(guest=self.request.user,)


class BookingDetailView(RetrieveAPIView):
    serializer_class = BookingReadSerializer
    permission_classes = (IsAuthenticated, IsBookingParticipant,)

    def get_queryset(self):
        return get_booking_queryset().filter(Q(guest=self.request.user) | Q(listing__owner=self.request.user)).distinct()


class BookingActionView(APIView):
    def get_booking(self):
        booking = get_object_or_404(get_booking_queryset(), pk=self.kwargs["pk"],)

        self.check_object_permissions(self.request, booking,)

        return booking

    def booking_response(self, booking):
        serializer = BookingReadSerializer(booking, context={"request": self.request,},)

        return Response(serializer.data)


class BookingCancelView(BookingActionView):
    permission_classes = (IsAuthenticated, IsBookingGuest | IsBookingListingOwner,)

    def validate_guest_cancellation(self, booking,):
        if booking.status not in (Booking.Status.PENDING, Booking.Status.CONFIRMED,):
            raise ValidationError(
                {
                    "status": (
                        "Only pending or confirmed "
                        "bookings can be cancelled "
                        "by the guest."
                    )
                }
            )

        cancellation_deadline = (booking.check_in - timedelta(hours=BOOKING_CANCELLATION_DEADLINE_HOURS))

        if timezone.now() > cancellation_deadline:
            raise ValidationError(
                {
                    "status": (
                        "A booking must be cancelled "
                        f"at least "
                        f"{BOOKING_CANCELLATION_DEADLINE_HOURS} "
                        "hours before check-in."
                    )
                }
            )

    def validate_owner_cancellation(self, booking,):
        if booking.status != Booking.Status.CONFIRMED:
            raise ValidationError(
                {
                    "status": (
                        "The listing owner can only "
                        "cancel confirmed bookings. "
                        "Reject a pending booking instead."
                    )
                }
            )

        if booking.check_in <= timezone.now():
            raise ValidationError(
                {
                    "status": (
                        "The listing owner cannot cancel "
                        "a booking after check-in."
                    )
                }
            )

    def post(self, request, *args, **kwargs):
        booking = self.get_booking()

        if booking.guest_id == request.user.id:self.validate_guest_cancellation(booking)
        else:
            self.validate_owner_cancellation(booking)

        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=("status", "updated_at",))

        return self.booking_response(booking)


class BookingRejectView(BookingActionView):
    permission_classes = (IsAuthenticated, IsBookingListingOwner,)

    def post(self, request, *args, **kwargs):
        booking = self.get_booking()

        if booking.status != Booking.Status.PENDING:
            raise ValidationError(
                {
                    "status": (
                        "Only pending bookings "
                        "can be rejected."
                    )
                }
            )

        booking.status = Booking.Status.REJECTED
        booking.save(update_fields=("status", "updated_at",))

        return self.booking_response(booking)


class BookingConfirmView(BookingActionView):
    permission_classes = (IsAuthenticated, IsBookingListingOwner,)

    def post(self, request, *args, **kwargs):
        booking = self.get_booking()

        if booking.status != Booking.Status.PENDING:
            raise ValidationError(
                {
                    "status": (
                        "Only pending bookings "
                        "can be confirmed."
                    )
                }
            )

        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=("status", "updated_at",))

        return self.booking_response(booking)


class BookingCompleteView(BookingActionView):
    permission_classes = (IsAuthenticated, IsBookingListingOwner,)

    def post(self, request, *args, **kwargs):
        booking = self.get_booking()

        if booking.status != Booking.Status.CONFIRMED:
            raise ValidationError(
                {
                    "status": (
                        "Only confirmed bookings "
                        "can be completed."
                    )
                }
            )

        if booking.check_out > timezone.now():
            raise ValidationError(
                {
                    "status": (
                        "A booking cannot be completed "
                        "before check-out."
                    )
                }
            )

        booking.status = Booking.Status.COMPLETED
        booking.save(update_fields=("status", "updated_at",))

        return self.booking_response(booking)


class BlockedPeriodListCreateView(ListCreateAPIView):
    serializer_class = BlockedPeriodSerializer
    permission_classes = (IsAuthenticated, IsBlockedPeriodListingOwner,)

    def get_queryset(self):
        return BlockedPeriod.objects.filter(listing__owner=self.request.user,).select_related("listing", "listing__owner",)


class BlockedPeriodDetailView(RetrieveUpdateDestroyAPIView,):
    serializer_class = BlockedPeriodSerializer
    permission_classes = (IsAuthenticated, IsBlockedPeriodListingOwner,)

    def get_queryset(self):
        return BlockedPeriod.objects.filter(listing__owner=self.request.user,).select_related("listing", "listing__owner",)