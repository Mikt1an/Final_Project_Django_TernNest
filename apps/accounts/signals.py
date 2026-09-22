from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.roles import TENANT_GROUP


@receiver(
    post_save,
    sender=settings.AUTH_USER_MODEL,
    dispatch_uid="accounts.assign_default_tenant_group",
)
def assign_default_tenant_group(
    sender,
    instance,
    created,
    raw=False,
    **kwargs,
):
    if raw or not created or instance.is_superuser:
        return

    tenant_group, _ = Group.objects.get_or_create(
        name=TENANT_GROUP,
    )

    instance.groups.add(tenant_group)