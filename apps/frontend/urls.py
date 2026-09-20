from django.urls import path

from apps.frontend.views import (
    AccountSettingsPageView,
    DashboardPageView,
    FavoritesPageView,
    HomePageView,
    ListingAvailabilityPageView,
    ListingCreatePageView,
    ListingDetailPageView,
    ListingEditPageView,
    LoginPageView,
    RegisterPageView,
    ReviewCreatePageView,
)


app_name = "frontend"


urlpatterns = [
    path(
        "",
        HomePageView.as_view(),
        name="home",
    ),

    path(
        "login/",
        LoginPageView.as_view(),
        name="login",
    ),

    path(
        "register/",
        RegisterPageView.as_view(),
        name="register",
    ),

    path(
        "dashboard/",
        DashboardPageView.as_view(),
        name="dashboard",
    ),

    path(
        "account/settings/",
        AccountSettingsPageView.as_view(),
        name="account-settings",
    ),

    path(
        "favorites/",
        FavoritesPageView.as_view(),
        name="favorites",
    ),

    path(
        "listings/create/",
        ListingCreatePageView.as_view(),
        name="listing-create",
    ),

    path(
        "listings/<int:pk>/edit/",
        ListingEditPageView.as_view(),
        name="listing-edit",
    ),

    path(
        "listings/<int:pk>/availability/",
        ListingAvailabilityPageView.as_view(),
        name="listing-availability",
    ),

    path(
        "listings/<int:pk>/",
        ListingDetailPageView.as_view(),
        name="listing-detail",
    ),

    path(
        "bookings/<int:booking_id>/review/",
        ReviewCreatePageView.as_view(),
        name="review-create",
    ),
]