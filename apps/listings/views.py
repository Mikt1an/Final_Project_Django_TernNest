from django.db import transaction
from django.db.models import (
    Avg,
    Count,
    Max,
    Q,
)
from django.db.models.deletion import (
    ProtectedError,
)
from django.shortcuts import (
    get_object_or_404,
)

from rest_framework import status
from rest_framework.exceptions import (
    ValidationError,
)
from rest_framework.generics import (
    DestroyAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    SAFE_METHODS,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listings.filters import (
    filter_listings,
)
from apps.listings.models import (
    Amenity,
    Favorite,
    Listing,
    ListingImage,
    ListingView,
    SearchHistory,
)
from apps.listings.permissions import (
    IsAdminOrReadOnly,
    IsFavoriteOwner,
    IsListingImageOwnerOrReadOnly,
    IsListingOwnerOrReadOnly,
)
from apps.listings.serializers import (
    AmenitySerializer,
    FavoriteSerializer,
    ListingImageSerializer,
    ListingReadSerializer,
    ListingViewHistorySerializer,
    ListingWriteSerializer,
    PopularSearchSerializer,
)
from apps.listings.services import (
    record_listing_view,
    record_search_query,
)


def get_visible_listings(user):
    queryset = (
        Listing.objects
        .select_related(
            "owner",
        )
        .prefetch_related(
            "amenities",
            "images",
        )
        .annotate(
            average_rating=Avg(
                "bookings__review__rating"
            ),
            reviews_count_value=Count(
                "bookings__review",
                distinct=True,
            ),
            views_count_value=Count(
                "views",
                distinct=True,
            ),
        )
    )

    if user.is_authenticated:
        return (
            queryset
            .filter(
                Q(is_active=True)
                | Q(owner=user)
            )
            .distinct()
        )

    return queryset.filter(
        is_active=True
    )


class AmenityListCreateView(
    ListCreateAPIView,
):
    queryset = Amenity.objects.all()

    serializer_class = (
        AmenitySerializer
    )

    permission_classes = (
        IsAdminOrReadOnly,
    )


class AmenityDetailView(
    RetrieveUpdateDestroyAPIView,
):
    queryset = Amenity.objects.all()

    serializer_class = (
        AmenitySerializer
    )

    permission_classes = (
        IsAdminOrReadOnly,
    )


class ListingListCreateView(
    ListCreateAPIView,
):
    permission_classes = (
        IsListingOwnerOrReadOnly,
    )

    def get_queryset(self):
        queryset = get_visible_listings(
            self.request.user
        )

        if self.request.method != "GET":
            return queryset

        return filter_listings(
            queryset,
            self.request.query_params,
        )

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListingReadSerializer

        return ListingWriteSerializer

    def list(
        self,
        request,
        *args,
        **kwargs,
    ):
        response = super().list(
            request,
            *args,
            **kwargs,
        )

        record_search_query(
            request=request,
            query=(
                request.query_params.get(
                    "search"
                )
            ),
        )

        return response

    def perform_create(
        self,
        serializer,
    ):
        serializer.save(
            owner=self.request.user
        )


class ListingDetailView(
    RetrieveUpdateDestroyAPIView,
):
    permission_classes = (
        IsListingOwnerOrReadOnly,
    )

    def get_queryset(self):
        return get_visible_listings(
            self.request.user
        )

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListingReadSerializer

        return ListingWriteSerializer

    def retrieve(
        self,
        request,
        *args,
        **kwargs,
    ):
        listing = self.get_object()

        created = record_listing_view(
            listing=listing,
            request=request,
        )

        if created:
            current_count = getattr(
                listing,
                "views_count_value",
                None,
            )

            if current_count is not None:
                listing.views_count_value = (
                    current_count + 1
                )

        serializer = self.get_serializer(
            listing
        )

        return Response(
            serializer.data
        )

    def destroy(
        self,
        request,
        *args,
        **kwargs,
    ):
        listing = self.get_object()

        try:
            with transaction.atomic():
                listing.views.all().delete()
                listing.images.all().delete()
                listing.delete()

        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "This listing cannot be "
                        "permanently deleted because "
                        "it has linked data such as "
                        "bookings, favorites or "
                        "blocked periods. Deactivate "
                        "it instead."
                    )
                },
                status=(
                    status.HTTP_409_CONFLICT
                ),
            )

        return Response(
            status=(
                status.HTTP_204_NO_CONTENT
            )
        )


class ListingImageListCreateView(
    ListCreateAPIView,
):
    serializer_class = (
        ListingImageSerializer
    )

    permission_classes = (
        IsListingOwnerOrReadOnly,
    )

    def get_listing(self):
        queryset = (
            Listing.objects
            .select_related(
                "owner"
            )
        )

        if (
            self.request.method
            in SAFE_METHODS
        ):
            if (
                self.request
                .user
                .is_authenticated
            ):
                queryset = (
                    queryset.filter(
                        Q(is_active=True)
                        | Q(
                            owner=(
                                self.request.user
                            )
                        )
                    )
                )

            else:
                queryset = (
                    queryset.filter(
                        is_active=True,
                    )
                )

        listing = get_object_or_404(
            queryset,
            pk=self.kwargs[
                "listing_pk"
            ],
        )

        self.check_object_permissions(
            self.request,
            listing,
        )

        return listing

    def get_queryset(self):
        return (
            ListingImage.objects
            .filter(
                listing=(
                    self.get_listing()
                ),
            )
        )

    def perform_create(
        self,
        serializer,
    ):
        serializer.save(
            listing=self.get_listing(),
        )


class ListingImageDetailView(
    RetrieveUpdateDestroyAPIView,
):
    serializer_class = (
        ListingImageSerializer
    )

    permission_classes = (
        IsListingImageOwnerOrReadOnly,
    )

    def get_queryset(self):
        queryset = (
            ListingImage.objects
            .select_related(
                "listing",
                "listing__owner",
            )
            .filter(
                listing_id=self.kwargs[
                    "listing_pk"
                ],
            )
        )

        if (
            self.request.method
            in SAFE_METHODS
        ):
            if (
                self.request
                .user
                .is_authenticated
            ):
                queryset = (
                    queryset.filter(
                        Q(
                            listing__is_active=True
                        )
                        | Q(
                            listing__owner=(
                                self.request.user
                            )
                        )
                    )
                )

            else:
                queryset = (
                    queryset.filter(
                        listing__is_active=True,
                    )
                )

        return queryset


class FavoriteListCreateView(
    ListCreateAPIView,
):
    serializer_class = (
        FavoriteSerializer
    )

    permission_classes = (
        IsFavoriteOwner,
    )

    def get_queryset(self):
        return (
            Favorite.objects
            .filter(
                user=self.request.user,
            )
            .select_related(
                "listing",
                "listing__owner",
            )
        )

    def perform_create(
        self,
        serializer,
    ):
        listing = (
            serializer
            .validated_data["listing"]
        )

        if Favorite.objects.filter(
            user=self.request.user,
            listing=listing,
        ).exists():
            raise ValidationError(
                {
                    "listing": (
                        "This listing is already "
                        "in your favorites."
                    )
                }
            )

        serializer.save(
            user=self.request.user
        )


class FavoriteDetailView(
    DestroyAPIView,
):
    serializer_class = (
        FavoriteSerializer
    )

    permission_classes = (
        IsFavoriteOwner,
    )

    def get_queryset(self):
        return (
            Favorite.objects
            .filter(
                user=self.request.user,
            )
            .select_related(
                "listing",
            )
        )


class ListingViewHistoryView(
    ListAPIView,
):
    serializer_class = (
        ListingViewHistorySerializer
    )

    permission_classes = (
        IsAuthenticated,
    )

    def get_queryset(self):
        return (
            ListingView.objects
            .filter(
                user=self.request.user,
                listing__is_active=True,
            )
            .select_related(
                "listing",
                "listing__owner",
            )
            .prefetch_related(
                "listing__amenities",
                "listing__images",
            )
        )


class PopularSearchListView(
    APIView,
):
    permission_classes = (
        AllowAny,
    )

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        popular_searches = (
            SearchHistory.objects
            .values(
                "normalized_query"
            )
            .annotate(
                search_count=Count(
                    "id"
                ),
                last_searched_at=Max(
                    "created_at"
                ),
            )
            .order_by(
                "-search_count",
                "-last_searched_at",
                "normalized_query",
            )[:5]
        )

        serializer = (
            PopularSearchSerializer(
                popular_searches,
                many=True,
            )
        )

        return Response(
            serializer.data
        )