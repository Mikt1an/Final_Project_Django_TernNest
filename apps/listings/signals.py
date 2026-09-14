from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from apps.listings.models import Listing
from apps.listings.validators import validate_amenities_count


@receiver(m2m_changed, sender=Listing.amenities.through)
def validate_listing_amenities(
    sender,
    instance,
    action,
    pk_set,
    **kwargs,
):
    if action != "pre_add":
        return

    validate_amenities_count(
        current_count=instance.amenities.count(),
        new_count=len(pk_set),
    )