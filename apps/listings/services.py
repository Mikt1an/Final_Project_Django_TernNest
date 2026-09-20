from hashlib import sha256

from django.utils import timezone

from apps.listings.models import (
    ListingView,
    SearchHistory,
)


def _get_viewer_key(request):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"

    if request.session.session_key is None:
        request.session.create()

    session_hash = sha256(
        request.session.session_key.encode(
            "utf-8"
        )
    ).hexdigest()

    return f"session:{session_hash}"


def record_listing_view(
    *,
    listing,
    request,
):
    if (
        request.user.is_authenticated
        and listing.owner_id == request.user.id
    ):
        return False

    user = (
        request.user
        if request.user.is_authenticated
        else None
    )

    listing_view, created = (
        ListingView.objects.get_or_create(
            listing=listing,
            viewer_key=_get_viewer_key(
                request
            ),
            viewed_on=timezone.localdate(),
            defaults={
                "user": user,
            },
        )
    )

    if not created:
        ListingView.objects.filter(
            pk=listing_view.pk
        ).update(
            updated_at=timezone.now()
        )

    return created


def record_search_query(
    *,
    request,
    query,
):
    cleaned_query = " ".join(
        str(query or "").split()
    )

    if not cleaned_query:
        return None

    normalized_query = (
        SearchHistory.normalize_query(
            cleaned_query
        )
    )

    query_max_length = (
        SearchHistory
        ._meta
        .get_field("query")
        .max_length
    )

    normalized_max_length = (
        SearchHistory
        ._meta
        .get_field(
            "normalized_query"
        )
        .max_length
    )

    if (
        len(cleaned_query)
        > query_max_length
        or len(normalized_query)
        > normalized_max_length
    ):
        return None

    user = (
        request.user
        if request.user.is_authenticated
        else None
    )

    return SearchHistory.objects.create(
        user=user,
        searcher_key=_get_viewer_key(
            request
        ),
        query=cleaned_query,
        searched_on=timezone.localdate(),
    )