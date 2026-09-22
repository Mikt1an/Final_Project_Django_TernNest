from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.roles import (
    LANDLORD_GROUP,
    TENANT_GROUP,
)


ROLE_PERMISSIONS = {
    TENANT_GROUP: {
        "listings": {
            "view_listing",
            "view_amenity",
            "add_favorite",
            "view_favorite",
            "delete_favorite",
        },
        "bookings": {
            "add_booking",
            "view_booking",
            "change_booking",
        },
        "reviews": {
            "add_review",
            "view_review",
            "change_review",
            "delete_review",
            "add_reviewimage",
            "view_reviewimage",
            "delete_reviewimage",
        },
    },
    LANDLORD_GROUP: {
        "listings": {
            "add_listing",
            "view_listing",
            "change_listing",
            "delete_listing",
            "add_listingimage",
            "view_listingimage",
            "change_listingimage",
            "delete_listingimage",
            "view_amenity",
        },
        "bookings": {
            "view_booking",
            "change_booking",
            "add_blockedperiod",
            "view_blockedperiod",
            "change_blockedperiod",
            "delete_blockedperiod",
        },
        "reviews": {
            "view_review",
            "view_reviewimage",
        },
    },
}


class Command(BaseCommand):
    help = "Create TernNest user groups and assign permissions"

    @transaction.atomic
    def handle(self, *args, **options):
        groups = {}

        for group_name, permission_map in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)

            resolved_permissions = []
            missing_permissions = []

            for app_label, codenames in permission_map.items():
                permissions = list(
                    Permission.objects.filter(
                        content_type__app_label=app_label,
                        codename__in=codenames,
                    )
                )

                found_codenames = {
                    permission.codename
                    for permission in permissions
                }

                missing_permissions.extend(
                    f"{app_label}.{codename}"
                    for codename in codenames
                    if codename not in found_codenames
                )

                resolved_permissions.extend(permissions)

            if missing_permissions:
                raise CommandError(
                    "Permissions were not found: "
                    + ", ".join(sorted(missing_permissions))
                )

            group.permissions.set(resolved_permissions)

            groups[group_name] = group

            action = "created" if created else "updated"

            self.stdout.write(
                self.style.SUCCESS(
                    f"{group_name}: {action}, "
                    f"{len(resolved_permissions)} permissions assigned"
                )
            )

        self.assign_existing_users(groups)

    def assign_existing_users(self, groups):
        User = get_user_model()

        tenant_group = groups[TENANT_GROUP]
        landlord_group = groups[LANDLORD_GROUP]

        regular_users = User.objects.filter(
            is_superuser=False,
        )

        for user in regular_users.iterator():
            user.groups.add(tenant_group)

        existing_landlords = (
            User.objects
            .filter(
                is_superuser=False,
                listings__isnull=False,
            )
            .distinct()
        )

        for user in existing_landlords.iterator():
            user.groups.add(landlord_group)

        tenant_count = (
            User.objects
            .filter(groups__name=TENANT_GROUP)
            .distinct()
            .count()
        )

        landlord_count = (
            User.objects
            .filter(groups__name=LANDLORD_GROUP)
            .distinct()
            .count()
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Existing users assigned: "
                f"{tenant_count} tenants, "
                f"{landlord_count} landlords"
            )
        )