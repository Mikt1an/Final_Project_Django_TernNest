from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
)

from rest_framework import serializers


User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
        )
        read_only_fields = fields


class UserDetailSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "birth_date",
            "avatar",
            "is_verified",
            "roles",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_roles(self, obj):
        return list(
            obj.groups
            .order_by("name")
            .values_list(
                "name",
                flat=True,
            )
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "birth_date",
            "avatar",
        )

    def validate_email(self, value):
        """
        Email is also the login name in TernNest.
        """

        value = value.strip().lower()

        user = self.instance

        email_exists = (
            User.objects
            .filter(email__iexact=value)
            .exclude(pk=user.pk)
            .exists()
        )

        if email_exists:
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value

    def validate_phone_number(self, value):
        user = self.instance

        phone_exists = (
            User.objects
            .filter(phone_number=value)
            .exclude(pk=user.pk)
            .exists()
        )

        if phone_exists:
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )

        return value


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "password",
            "password_confirm",
        )
        read_only_fields = (
            "id",
        )

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return value

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if password != password_confirm:
            raise serializers.ValidationError(
                {
                    "password_confirm": (
                        "Passwords do not match."
                    )
                }
            )

        user = User(
            email=attrs.get("email"),
            first_name=attrs.get(
                "first_name",
                "",
            ),
            last_name=attrs.get(
                "last_name",
                "",
            ),
            phone_number=attrs.get(
                "phone_number",
                "",
            ),
        )

        try:
            validate_password(
                password,
                user=user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {
                    "password": list(
                        error.messages
                    )
                }
            ) from error

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")

        password = validated_data.pop("password")

        return User.objects.create_user(
            password=password,
            **validated_data,
        )


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    new_password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        user = self.context["request"].user

        current_password = attrs["current_password"]
        new_password = attrs["new_password"]
        new_password_confirm = attrs["new_password_confirm"]

        if not user.check_password(current_password):
            raise serializers.ValidationError(
                {
                    "current_password": (
                        "Current password is incorrect."
                    )
                }
            )

        if new_password != new_password_confirm:
            raise serializers.ValidationError(
                {
                    "new_password_confirm": (
                        "Passwords do not match."
                    )
                }
            )

        try:
            validate_password(
                new_password,
                user=user,
            )
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {
                    "new_password": list(
                        error.messages
                    )
                }
            ) from error

        return attrs