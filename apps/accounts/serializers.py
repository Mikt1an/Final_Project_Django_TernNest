from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

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
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "is_verified",
            "created_at",
            "updated_at",
        )


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False,)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False,)

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
        read_only_fields = ("id",)

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if password != password_confirm:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        user = User(
            email=attrs.get("email"),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )

        try:
            validate_password(password, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        return User.objects.create_user(password=password, **validated_data,)