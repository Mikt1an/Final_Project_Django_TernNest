import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import (
    SimpleUploadedFile,
)
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.roles import (
    LANDLORD_GROUP,
    TENANT_GROUP,
    has_role,
)


User = get_user_model()


class AccountsAPITestCase(APITestCase):
    password = "StrongPass123!"

    def create_user(
        self,
        *,
        email="user@example.com",
        phone_number="+491700000100",
        password=None,
        first_name="Test",
        last_name="User",
    ):
        return User.objects.create_user(
            email=email,
            password=password or self.password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )


class RegistrationAPITests(AccountsAPITestCase):
    def setUp(self):
        self.url = reverse(
            "accounts:register"
        )

    def valid_payload(self, **overrides):
        payload = {
            "email": "new.user@example.com",
            "first_name": "New",
            "last_name": "User",
            "phone_number": "+491700000101",
            "password": self.password,
            "password_confirm": self.password,
        }

        payload.update(overrides)

        return payload

    def test_user_can_register(self):
        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            User.objects.count(),
            1,
        )

        user = User.objects.get()

        self.assertEqual(
            user.email,
            "new.user@example.com",
        )
        self.assertTrue(
            user.check_password(self.password)
        )
        self.assertNotIn(
            "password",
            response.data,
        )
        self.assertNotIn(
            "password_confirm",
            response.data,
        )

    def test_registered_user_receives_tenant_role(self):
        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get()

        self.assertTrue(
            has_role(
                user,
                TENANT_GROUP,
            )
        )
        self.assertEqual(
            list(
                user.groups
                .order_by("name")
                .values_list(
                    "name",
                    flat=True,
                )
            ),
            [TENANT_GROUP],
        )

    def test_email_is_stored_in_lowercase(self):
        response = self.client.post(
            self.url,
            self.valid_payload(
                email="Mixed.Email@Example.COM"
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get()

        self.assertEqual(
            user.email,
            "mixed.email@example.com",
        )

    def test_password_confirmation_must_match(self):
        response = self.client.post(
            self.url,
            self.valid_payload(
                password_confirm="DifferentPass456!"
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "password_confirm",
            response.data,
        )
        self.assertEqual(
            User.objects.count(),
            0,
        )

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            self.url,
            self.valid_payload(
                password="password",
                password_confirm="password",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "password",
            response.data,
        )

    def test_invalid_phone_number_is_rejected(self):
        response = self.client.post(
            self.url,
            self.valid_payload(
                phone_number="01700000101"
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "phone_number",
            response.data,
        )

    def test_required_fields_are_validated(self):
        payload = self.valid_payload()
        payload.pop("first_name")

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "first_name",
            response.data,
        )

    def test_duplicate_email_is_rejected(self):
        self.create_user(
            email="existing@example.com",
            phone_number="+491700000102",
        )

        response = self.client.post(
            self.url,
            self.valid_payload(
                email="existing@example.com"
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "email",
            response.data,
        )

    def test_case_insensitive_duplicate_email_is_rejected(
        self,
    ):
        self.create_user(
            email="existing@example.com",
            phone_number="+491700000103",
        )

        response = self.client.post(
            self.url,
            self.valid_payload(
                email="EXISTING@EXAMPLE.COM"
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "email",
            response.data,
        )
        self.assertEqual(
            User.objects.count(),
            1,
        )

    def test_duplicate_phone_number_is_rejected(self):
        self.create_user(
            email="existing@example.com",
            phone_number="+491700000104",
        )

        response = self.client.post(
            self.url,
            self.valid_payload(
                email="another@example.com",
                phone_number="+491700000104",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "phone_number",
            response.data,
        )


class AuthenticationAPITests(AccountsAPITestCase):
    def setUp(self):
        self.user = self.create_user(
            email="login@example.com",
            phone_number="+491700000111",
        )

        self.login_url = reverse(
            "accounts:login"
        )
        self.refresh_url = reverse(
            "accounts:token-refresh"
        )

    def test_user_can_login_with_email(self):
        response = self.client.post(
            self.login_url,
            {
                "email": self.user.email,
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            "access",
            response.data,
        )
        self.assertIn(
            "refresh",
            response.data,
        )

    def test_login_with_wrong_password_is_rejected(self):
        response = self.client.post(
            self.login_url,
            {
                "email": self.user.email,
                "password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_refresh_token_returns_new_access_token(self):
        login_response = self.client.post(
            self.login_url,
            {
                "email": self.user.email,
                "password": self.password,
            },
            format="json",
        )

        response = self.client.post(
            self.refresh_url,
            {
                "refresh": login_response.data[
                    "refresh"
                ],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            "access",
            response.data,
        )

    def test_invalid_refresh_token_is_rejected(self):
        response = self.client.post(
            self.refresh_url,
            {
                "refresh": "invalid-token",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class CurrentUserAPITests(AccountsAPITestCase):
    def setUp(self):
        self.user = self.create_user(
            email="profile@example.com",
            phone_number="+491700000121",
            first_name="Profile",
            last_name="User",
        )

        self.other_user = self.create_user(
            email="other@example.com",
            phone_number="+491700000122",
            first_name="Other",
            last_name="User",
        )

        self.url = reverse(
            "accounts:current-user"
        )

        self.client.force_authenticate(
            user=self.user
        )

    def test_authentication_is_required(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_receives_own_profile(self):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            self.user.pk,
        )
        self.assertEqual(
            response.data["email"],
            self.user.email,
        )
        self.assertNotIn(
            "password",
            response.data,
        )

    def test_user_profile_contains_roles(self):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["roles"],
            [TENANT_GROUP],
        )

    def test_user_can_update_profile(self):
        response = self.client.patch(
            self.url,
            {
                "email": "Updated.User@Example.COM",
                "first_name": "Updated",
                "last_name": "Profile",
                "phone_number": "+491700000123",
                "birth_date": "1990-05-15",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertEqual(
            self.user.email,
            "updated.user@example.com",
        )
        self.assertEqual(
            self.user.first_name,
            "Updated",
        )
        self.assertEqual(
            self.user.last_name,
            "Profile",
        )
        self.assertEqual(
            self.user.phone_number,
            "+491700000123",
        )
        self.assertEqual(
            self.user.birth_date.isoformat(),
            "1990-05-15",
        )

    def test_duplicate_email_update_is_rejected(self):
        response = self.client.patch(
            self.url,
            {
                "email": "OTHER@EXAMPLE.COM",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "email",
            response.data,
        )

    def test_duplicate_phone_update_is_rejected(self):
        response = self.client.patch(
            self.url,
            {
                "phone_number": (
                    self.other_user.phone_number
                ),
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "phone_number",
            response.data,
        )

    def test_put_is_not_allowed(self):
        response = self.client.put(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_verification_status_cannot_be_updated(self):
        response = self.client.patch(
            self.url,
            {
                "is_verified": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertFalse(
            self.user.is_verified
        )

    def test_user_can_upload_avatar(self):
        avatar_content = (
            b"GIF89a"
            b"\x01\x00\x01\x00"
            b"\x80\x00\x00"
            b"\x00\x00\x00"
            b"\xff\xff\xff"
            b"!\xf9\x04\x01\x00\x00\x00\x00"
            b",\x00\x00\x00\x00"
            b"\x01\x00\x01\x00\x00"
            b"\x02\x02D\x01\x00;"
        )

        avatar = SimpleUploadedFile(
            "avatar.gif",
            avatar_content,
            content_type="image/gif",
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                response = self.client.patch(
                    self.url,
                    {
                        "avatar": avatar,
                    },
                    format="multipart",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )

                self.user.refresh_from_db()

                self.assertTrue(
                    self.user.avatar.name.startswith(
                        "users/avatars/"
                    )
                )


class BecomeLandlordAPITests(AccountsAPITestCase):
    def setUp(self):
        Group.objects.get_or_create(
            name=LANDLORD_GROUP
        )

        self.user = self.create_user(
            email="tenant@example.com",
            phone_number="+491700000141",
        )

        self.url = reverse(
            "accounts:become-landlord"
        )

    def test_authentication_is_required(self):
        response = self.client.post(
            self.url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertFalse(
            has_role(
                self.user,
                LANDLORD_GROUP,
            )
        )

    def test_tenant_can_become_landlord(self):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.client.post(
            self.url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["detail"],
            "Landlord role has been added.",
        )
        self.assertFalse(
            response.data["already_landlord"]
        )
        self.assertEqual(
            response.data["roles"],
            [
                LANDLORD_GROUP,
                TENANT_GROUP,
            ],
        )
        self.assertTrue(
            has_role(
                self.user,
                LANDLORD_GROUP,
            )
        )
        self.assertTrue(
            has_role(
                self.user,
                TENANT_GROUP,
            )
        )

    def test_become_landlord_is_idempotent(self):
        self.client.force_authenticate(
            user=self.user
        )

        first_response = self.client.post(
            self.url,
            format="json",
        )
        second_response = self.client.post(
            self.url,
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(
            second_response.data[
                "already_landlord"
            ]
        )
        self.assertEqual(
            second_response.data["detail"],
            "Landlord role is already active.",
        )
        self.assertEqual(
            second_response.data["roles"],
            [
                LANDLORD_GROUP,
                TENANT_GROUP,
            ],
        )
        self.assertEqual(
            self.user.groups.filter(
                name=LANDLORD_GROUP
            ).count(),
            1,
        )


class ChangePasswordAPITests(AccountsAPITestCase):
    def setUp(self):
        self.user = self.create_user(
            email="password@example.com",
            phone_number="+491700000131",
        )

        self.url = reverse(
            "accounts:change-password"
        )

        self.client.force_authenticate(
            user=self.user
        )

    def valid_payload(self):
        return {
            "current_password": self.password,
            "new_password": "NewStrongPass456!",
            "new_password_confirm": (
                "NewStrongPass456!"
            ),
        }

    def test_authentication_is_required(self):
        self.client.force_authenticate(
            user=None
        )

        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_wrong_current_password_is_rejected(self):
        payload = self.valid_payload()
        payload["current_password"] = (
            "WrongPassword123!"
        )

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "current_password",
            response.data,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(self.password)
        )

    def test_new_password_confirmation_must_match(
        self,
    ):
        payload = self.valid_payload()
        payload["new_password_confirm"] = (
            "DifferentPass789!"
        )

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "new_password_confirm",
            response.data,
        )

    def test_weak_new_password_is_rejected(self):
        payload = self.valid_payload()
        payload["new_password"] = "password"
        payload["new_password_confirm"] = "password"

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "new_password",
            response.data,
        )

    def test_user_can_change_password(self):
        new_password = "NewStrongPass456!"

        response = self.client.post(
            self.url,
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.user.refresh_from_db()

        self.assertTrue(
            self.user.check_password(new_password)
        )
        self.assertFalse(
            self.user.check_password(self.password)
        )

        self.client.force_authenticate(
            user=None
        )

        old_login_response = self.client.post(
            reverse("accounts:login"),
            {
                "email": self.user.email,
                "password": self.password,
            },
            format="json",
        )

        new_login_response = self.client.post(
            reverse("accounts:login"),
            {
                "email": self.user.email,
                "password": new_password,
            },
            format="json",
        )

        self.assertEqual(
            old_login_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            new_login_response.status_code,
            status.HTTP_200_OK,
        )