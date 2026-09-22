from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.parsers import (
    FormParser,
    JSONParser,
    MultiPartParser,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.roles import (
    LANDLORD_GROUP,
    TENANT_GROUP,
    add_role,
)
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    UserUpdateSerializer,
)


class UserRegistrationView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [
        AllowAny,
    ]


class CurrentUserView(
    RetrieveUpdateAPIView,
):
    permission_classes = [
        IsAuthenticated,
    ]

    parser_classes = [
        JSONParser,
        FormParser,
        MultiPartParser,
    ]

    # Only GET and PATCH are required for this endpoint.
    # Full profile replacement through PUT is disabled.
    http_method_names = (
        "get",
        "patch",
        "head",
        "options",
    )

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == "GET":
            return UserDetailSerializer

        return UserUpdateSerializer


class ChangePasswordView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = request.user

        user.set_password(
            serializer.validated_data[
                "new_password"
            ]
        )

        user.save()

        return Response(
            {
                "detail": (
                    "Password changed successfully."
                )
            },
            status=status.HTTP_200_OK,
        )


class BecomeLandlordView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        # This endpoint checks actual group membership.
        # Superuser privileges must not replace groups
        # used by the frontend role switcher.
        already_landlord = (
            request.user.groups
            .filter(
                name=LANDLORD_GROUP
            )
            .exists()
        )

        is_tenant = (
            request.user.groups
            .filter(
                name=TENANT_GROUP
            )
            .exists()
        )

        # A landlord keeps the tenant role so that the
        # same account can switch between both modes.
        if not is_tenant:
            add_role(
                request.user,
                TENANT_GROUP,
            )

        if not already_landlord:
            add_role(
                request.user,
                LANDLORD_GROUP,
            )

        roles = list(
            request.user.groups
            .order_by("name")
            .values_list(
                "name",
                flat=True,
            )
        )

        message = (
            "Landlord role is already active."
            if already_landlord
            else "Landlord role has been added."
        )

        return Response(
            {
                "detail": message,
                "already_landlord": (
                    already_landlord
                ),
                "roles": roles,
            },
            status=status.HTTP_200_OK,
        )