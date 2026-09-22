from django.contrib.auth.models import Group


TENANT_GROUP = "Tenant"
LANDLORD_GROUP = "Landlord"

ROLE_NAMES = frozenset({
    TENANT_GROUP,
    LANDLORD_GROUP,
})


def has_role(user, role_name: str) -> bool:
    if role_name not in ROLE_NAMES:
        raise ValueError(f"Unknown role: {role_name}")

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return user.groups.filter(name=role_name).exists()


def add_role(user, role_name: str) -> None:
    if role_name not in ROLE_NAMES:
        raise ValueError(f"Unknown role: {role_name}")

    group = Group.objects.get(name=role_name)
    user.groups.add(group)