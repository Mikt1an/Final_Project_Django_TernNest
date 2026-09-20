from django.urls import path

from apps.listings.views import (
    AmenityDetailView,
    AmenityListCreateView,
    FavoriteDetailView,
    FavoriteListCreateView,
    ListingDetailView,
    ListingImageDetailView,
    ListingImageListCreateView,
    ListingListCreateView,
    ListingViewHistoryView,
    PopularSearchListView,
)


app_name = "listings"


urlpatterns = [
    path(
        "amenities/",
        AmenityListCreateView.as_view(),
        name="amenity-list-create",
    ),
    path(
        "amenities/<int:pk>/",
        AmenityDetailView.as_view(),
        name="amenity-detail",
    ),
    path(
        "favorites/",
        FavoriteListCreateView.as_view(),
        name="favorite-list-create",
    ),
    path(
        "favorites/<int:pk>/",
        FavoriteDetailView.as_view(),
        name="favorite-detail",
    ),
    path(
        "view-history/",
        ListingViewHistoryView.as_view(),
        name="listing-view-history",
    ),
    path(
        "popular-searches/",
        PopularSearchListView.as_view(),
        name="popular-search-list",
    ),
    path(
        "",
        ListingListCreateView.as_view(),
        name="listing-list-create",
    ),
    path(
        "<int:pk>/",
        ListingDetailView.as_view(),
        name="listing-detail",
    ),
    path(
        "<int:listing_pk>/images/",
        ListingImageListCreateView.as_view(),
        name="listing-image-list-create",
    ),
    path(
        "<int:listing_pk>/images/<int:pk>/",
        ListingImageDetailView.as_view(),
        name="listing-image-detail",
    ),
]