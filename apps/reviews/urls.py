from django.urls import path

from apps.reviews.views import (
    ReviewDetailView,
    ReviewImageCreateView,
    ReviewImageDetailView,
    ReviewListCreateView,
)


app_name = "reviews"


urlpatterns = [
    path(
        "",
        ReviewListCreateView.as_view(),
        name="review-list-create",
    ),
    path(
        "images/",
        ReviewImageCreateView.as_view(),
        name="review-image-create",
    ),
    path(
        "images/<int:pk>/",
        ReviewImageDetailView.as_view(),
        name="review-image-detail",
    ),
    path(
        "<int:pk>/",
        ReviewDetailView.as_view(),
        name="review-detail",
    ),
]