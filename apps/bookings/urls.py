from django.urls import path

from apps.bookings.views import (
    BlockedPeriodDetailView,
    BlockedPeriodListCreateView,
    BookingCancelView,
    BookingRejectView,
    BookingCompleteView,
    BookingConfirmView,
    BookingDetailView,
    BookingListCreateView,
)


app_name = "bookings"


urlpatterns = [
    path(
        "blocked-periods/",
        BlockedPeriodListCreateView.as_view(),
        name="blocked-period-list-create",
    ),
    path(
        "blocked-periods/<int:pk>/",
        BlockedPeriodDetailView.as_view(),
        name="blocked-period-detail",
    ),
    path(
        "",
        BookingListCreateView.as_view(),
        name="booking-list-create",
    ),
    path(
        "<int:pk>/",
        BookingDetailView.as_view(),
        name="booking-detail",
    ),
    path(
        "<int:pk>/cancel/",
        BookingCancelView.as_view(),
        name="booking-cancel",
    ),
    path(
        "<int:pk>/reject/",
        BookingRejectView.as_view(),
        name="booking-reject",
    ),
    path(
        "<int:pk>/confirm/",
        BookingConfirmView.as_view(),
        name="booking-confirm",
    ),
    path(
        "<int:pk>/complete/",
        BookingCompleteView.as_view(),
        name="booking-complete",
    ),
]