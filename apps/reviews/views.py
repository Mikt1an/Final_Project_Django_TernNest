from rest_framework.exceptions import (
    ValidationError,
)
from rest_framework.generics import (
    CreateAPIView,
    ListCreateAPIView,
    RetrieveDestroyAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)

from apps.reviews.models import (
    Review,
    ReviewImage,
)
from apps.reviews.permissions import (
    CanCreateReview,
    IsReviewAuthorOrReadOnly,
    IsReviewImageAuthorOrReadOnly,
)
from apps.reviews.serializers import (
    ReviewCreateSerializer,
    ReviewImageSerializer,
    ReviewReadSerializer,
    ReviewUpdateSerializer,
)


def get_review_queryset():
    return (
        Review.objects
        .select_related(
            "booking",
            "booking__guest",
            "booking__listing",
            "booking__listing__owner",
        )
        .prefetch_related(
            "images",
        )
    )


class ReviewListCreateView(ListCreateAPIView):
    def get_queryset(self):
        queryset = get_review_queryset()

        listing_id = (self.request.query_params.get("listing"))

        if listing_id is not None:
            try:
                listing_id = int(listing_id)

            except (
                TypeError,
                ValueError,
            ):
                raise ValidationError(
                    {
                        "listing": (
                            "Listing must be "
                            "a valid integer ID."
                        )
                    }
                )

            queryset = queryset.filter(booking__listing_id=(listing_id),)

        return queryset

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ReviewReadSerializer

        return ReviewCreateSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            permission_classes = (IsAuthenticated, CanCreateReview,)

        else:
            permission_classes = AllowAny

        return [permission() for permission in permission_classes]


class ReviewDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = IsReviewAuthorOrReadOnly,

    def get_queryset(self):
        return get_review_queryset()

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH",):
            return ReviewUpdateSerializer

        return ReviewReadSerializer


class ReviewImageCreateView(CreateAPIView):
    queryset = (ReviewImage.objects.select_related("review", "review__booking", "review__booking__guest",))

    serializer_class = ReviewImageSerializer

    permission_classes = (IsAuthenticated, IsReviewImageAuthorOrReadOnly,)


class ReviewImageDetailView(RetrieveDestroyAPIView):
    queryset = (ReviewImage.objects.select_related("review", "review__booking", "review__booking__guest",))

    serializer_class = ReviewImageSerializer

    permission_classes = (IsReviewImageAuthorOrReadOnly,)