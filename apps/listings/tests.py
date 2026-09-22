import tempfile
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import (
    APIClient,
    APITestCase,
)

from apps.accounts.roles import LANDLORD_GROUP
from apps.bookings.models import Booking, BlockedPeriod
from apps.listings.models import (
    Amenity,
    Favorite,
    Listing,
    ListingImage,
    ListingView,
)
from apps.reviews.models import Review


User = get_user_model()


def assign_landlord_role(user):
    landlord_group, _ = Group.objects.get_or_create(
        name=LANDLORD_GROUP,
    )
    user.groups.add(landlord_group)


class ListingCleaningGapAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="listing.owner@example.com",
            password="StrongPass123!",
            first_name="Laura",
            last_name="Owner",
            phone_number="+491700000031",
        )
        assign_landlord_role(self.owner)

        self.client.force_authenticate(
            user=self.owner
        )

        self.list_url = reverse(
            "listings:listing-list-create"
        )

    def listing_payload(
        self,
        *,
        check_in_time="14:00:00",
        check_out_time="11:00:00",
    ):
        return {
            "title": "Cleaning gap apartment",
            "description": (
                "Listing used to test property turnover."
            ),
            "listing_type": (
                Listing.ListingType.APARTMENT
            ),
            "country": "Germany",
            "city": "Munich",
            "address": "Cleaningstrasse 1",
            "earliest_check_in_time": check_in_time,
            "latest_check_out_time": check_out_time,
            "price_per_night": "100.00",
            "max_guests": 4,
            "bedrooms": 2,
            "beds": 2,
            "bathrooms": 1,
        }

    def create_listing(self):
        return Listing.objects.create(
            owner=self.owner,
            title="Existing apartment",
            description="Existing test listing.",
            listing_type=Listing.ListingType.APARTMENT,
            country="Germany",
            city="Munich",
            address="Existingstrasse 2",
            earliest_check_in_time=time(15, 0),
            latest_check_out_time=time(11, 0),
            price_per_night=Decimal("100.00"),
            max_guests=4,
            bedrooms=2,
            beds=2,
            bathrooms=1,
            is_active=False,
        )

    def test_exact_minimum_cleaning_gap_is_allowed(self):
        response = self.client.post(
            self.list_url,
            self.listing_payload(
                check_in_time="14:00:00",
                check_out_time="11:00:00",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        listing = Listing.objects.get()

        self.assertEqual(
            listing.earliest_check_in_time,
            time(14, 0),
        )
        self.assertEqual(
            listing.latest_check_out_time,
            time(11, 0),
        )
        self.assertFalse(
            listing.is_active
        )

    def test_cleaning_gap_shorter_than_minimum_is_rejected(
        self,
    ):
        response = self.client.post(
            self.list_url,
            self.listing_payload(
                check_in_time="13:59:00",
                check_out_time="11:00:00",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "earliest_check_in_time",
            response.data,
        )
        self.assertEqual(
            Listing.objects.count(),
            0,
        )

    def test_check_in_at_check_out_time_is_rejected(self):
        response = self.client.post(
            self.list_url,
            self.listing_payload(
                check_in_time="11:00:00",
                check_out_time="11:00:00",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "earliest_check_in_time",
            response.data,
        )

    def test_update_cannot_reduce_cleaning_gap(self):
        listing = self.create_listing()

        response = self.client.patch(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            ),
            {
                "earliest_check_in_time": "13:00:00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "earliest_check_in_time",
            response.data,
        )

        listing.refresh_from_db()

        self.assertEqual(
            listing.earliest_check_in_time,
            time(15, 0),
        )


class ListingCRUDAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="listing.crud.owner@example.com",
            password="StrongPass123!",
            first_name="Listing",
            last_name="Owner",
            phone_number="+491700000201",
        )
        self.other_user = User.objects.create_user(
            email="listing.other@example.com",
            password="StrongPass123!",
            first_name="Other",
            last_name="User",
            phone_number="+491700000202",
        )
        self.tenant_user = User.objects.create_user(
            email="listing.tenant@example.com",
            password="StrongPass123!",
            first_name="Listing",
            last_name="Tenant",
            phone_number="+491700000203",
        )

        assign_landlord_role(self.owner)
        assign_landlord_role(self.other_user)

        self.list_url = reverse(
            "listings:listing-list-create"
        )

    def listing_payload(self, **overrides):
        payload = {
            "title": "Test apartment",
            "description": (
                "A comfortable apartment for API tests."
            ),
            "listing_type": (
                Listing.ListingType.APARTMENT
            ),
            "country": "Germany",
            "city": "Munich",
            "address": "Teststrasse 10",
            "earliest_check_in_time": "15:00:00",
            "latest_check_out_time": "11:00:00",
            "price_per_night": "120.00",
            "max_guests": 4,
            "bedrooms": 2,
            "beds": 2,
            "bathrooms": 1,
            "is_active": True,
        }
        payload.update(overrides)
        return payload

    def create_listing(
        self,
        *,
        owner=None,
        title="Test apartment",
        is_active=False,
        listing_type=Listing.ListingType.APARTMENT,
        bedrooms=2,
    ):
        return Listing.objects.create(
            owner=owner or self.owner,
            title=title,
            description=(
                "A comfortable apartment for API tests."
            ),
            listing_type=listing_type,
            country="Germany",
            city="Munich",
            address=f"{title} address",
            earliest_check_in_time=time(15, 0),
            latest_check_out_time=time(11, 0),
            price_per_night=Decimal("120.00"),
            max_guests=4,
            bedrooms=bedrooms,
            beds=2,
            bathrooms=1,
            is_active=is_active,
        )

    def make_image(self, name="listing.gif"):
        content = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff!\xf9\x04"
            b"\x01\x00\x00\x00\x00,\x00\x00\x00"
            b"\x00\x01\x00\x01\x00\x00\x02\x02D"
            b"\x01\x00;"
        )

        return SimpleUploadedFile(
            name,
            content,
            content_type="image/gif",
        )

    @staticmethod
    def response_items(response):
        if isinstance(response.data, dict):
            return response.data.get(
                "results",
                [],
            )

        return response.data

    def response_ids(self, response):
        return {
            item["id"]
            for item in self.response_items(response)
        }

    def test_unauthenticated_user_cannot_create_listing(
        self,
    ):
        response = self.client.post(
            self.list_url,
            self.listing_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            Listing.objects.count(),
            0,
        )

    def test_tenant_cannot_create_listing(self):
        self.client.force_authenticate(
            user=self.tenant_user
        )

        response = self.client.post(
            self.list_url,
            self.listing_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            Listing.objects.count(),
            0,
        )

    def test_landlord_can_create_draft_listing(
        self,
    ):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.listing_payload(
                is_active=True
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        listing = Listing.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            listing.owner,
            self.owner,
        )
        self.assertFalse(
            listing.is_active
        )

    def test_studio_is_created_with_zero_bedrooms(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.listing_payload(
                listing_type=Listing.ListingType.STUDIO,
                bedrooms=5,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        listing = Listing.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            listing.bedrooms,
            0,
        )

    def test_owner_can_update_draft_listing(self):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.patch(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            ),
            {
                "title": "Updated apartment",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        listing.refresh_from_db()

        self.assertEqual(
            listing.title,
            "Updated apartment",
        )

    def test_non_owner_cannot_update_listing(self):
        listing = self.create_listing(
            is_active=True
        )

        self.client.force_authenticate(
            user=self.other_user
        )

        response = self.client.patch(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            ),
            {
                "title": "Unauthorized update",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        listing.refresh_from_db()

        self.assertNotEqual(
            listing.title,
            "Unauthorized update",
        )

    def test_owner_cannot_publish_listing_without_image(
        self,
    ):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.patch(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            ),
            {
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "image",
            str(response.data).lower(),
        )

        listing.refresh_from_db()

        self.assertFalse(
            listing.is_active
        )

    def test_owner_can_publish_listing_with_image(self):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.owner
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                ListingImage.objects.create(
                    listing=listing,
                    image=self.make_image(),
                    is_main=True,
                )

                response = self.client.patch(
                    reverse(
                        "listings:listing-detail",
                        kwargs={"pk": listing.pk},
                    ),
                    {
                        "is_active": True,
                    },
                    format="json",
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        listing.refresh_from_db()

        self.assertTrue(
            listing.is_active
        )

    def test_owner_can_deactivate_listing(self):
        listing = self.create_listing(
            is_active=True
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.patch(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            ),
            {
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        listing.refresh_from_db()

        self.assertFalse(
            listing.is_active
        )

    def test_anonymous_user_sees_only_active_listings(
        self,
    ):
        active_listing = self.create_listing(
            title="Active listing",
            is_active=True,
        )
        draft_listing = self.create_listing(
            title="Draft listing",
            is_active=False,
        )

        response = self.client.get(
            self.list_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        listing_ids = self.response_ids(
            response
        )

        self.assertIn(
            active_listing.pk,
            listing_ids,
        )
        self.assertNotIn(
            draft_listing.pk,
            listing_ids,
        )

    def test_owner_sees_own_draft_and_public_listings(
        self,
    ):
        own_draft = self.create_listing(
            title="Own draft",
            is_active=False,
        )
        other_active = self.create_listing(
            owner=self.other_user,
            title="Other active",
            is_active=True,
        )
        other_draft = self.create_listing(
            owner=self.other_user,
            title="Other draft",
            is_active=False,
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.get(
            self.list_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        listing_ids = self.response_ids(
            response
        )

        self.assertIn(
            own_draft.pk,
            listing_ids,
        )
        self.assertIn(
            other_active.pk,
            listing_ids,
        )
        self.assertNotIn(
            other_draft.pk,
            listing_ids,
        )

    def test_owner_can_delete_listing_without_booking_history(
        self,
    ):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.delete(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Listing.objects.filter(
                pk=listing.pk
            ).exists()
        )

    def test_non_owner_cannot_delete_listing(self):
        listing = self.create_listing(
            is_active=True
        )

        self.client.force_authenticate(
            user=self.other_user
        )

        response = self.client.delete(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertTrue(
            Listing.objects.filter(
                pk=listing.pk
            ).exists()
        )

    def test_listing_with_booking_history_cannot_be_deleted(
        self,
    ):
        listing = self.create_listing(
            is_active=True
        )
        check_in = (
            timezone.now()
            + timedelta(days=10)
        )
        check_out = (
            check_in
            + timedelta(days=3)
        )

        Booking.objects.create(
            guest=self.other_user,
            listing=listing,
            check_in=check_in,
            check_out=check_out,
            book_days=3,
            guests=2,
            total_price=Decimal("360.00"),
            status=Booking.Status.CONFIRMED,
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.delete(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertTrue(
            Listing.objects.filter(
                pk=listing.pk
            ).exists()
        )

    def test_price_must_be_greater_than_zero(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.listing_payload(
                price_per_night="0.00"
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "price_per_night",
            response.data,
        )

    def test_non_studio_listing_requires_bedroom(
        self,
    ):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.listing_payload(
                listing_type=(
                    Listing.ListingType.APARTMENT
                ),
                bedrooms=0,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "bedrooms",
            response.data,
        )

    def test_max_guests_cannot_exceed_limit(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.listing_payload(
                max_guests=31
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "max_guests",
            response.data,
        )


class ListingRelatedAPITestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="related.owner@example.com",
            password="StrongPass123!",
            first_name="Related",
            last_name="Owner",
            phone_number="+491700000301",
        )
        self.other_user = User.objects.create_user(
            email="related.other@example.com",
            password="StrongPass123!",
            first_name="Related",
            last_name="Other",
            phone_number="+491700000302",
        )
        self.staff_user = User.objects.create_user(
            email="related.admin@example.com",
            password="StrongPass123!",
            first_name="Related",
            last_name="Admin",
            phone_number="+491700000303",
            is_staff=True,
        )

        assign_landlord_role(self.owner)
        assign_landlord_role(self.other_user)

    def create_listing(
        self,
        *,
        owner=None,
        title="Related test apartment",
        is_active=True,
    ):
        return Listing.objects.create(
            owner=owner or self.owner,
            title=title,
            description="Listing used for related API tests.",
            listing_type=Listing.ListingType.APARTMENT,
            country="Germany",
            city="Munich",
            address=f"{title} address",
            earliest_check_in_time=time(15, 0),
            latest_check_out_time=time(11, 0),
            price_per_night=Decimal("120.00"),
            max_guests=4,
            bedrooms=2,
            beds=2,
            bathrooms=1,
            is_active=is_active,
        )

    def listing_payload(self, **overrides):
        payload = {
            "title": "Amenity test apartment",
            "description": "Listing used to test amenities.",
            "listing_type": Listing.ListingType.APARTMENT,
            "country": "Germany",
            "city": "Munich",
            "address": "Amenitystrasse 10",
            "earliest_check_in_time": "15:00:00",
            "latest_check_out_time": "11:00:00",
            "price_per_night": "120.00",
            "max_guests": 4,
            "bedrooms": 2,
            "beds": 2,
            "bathrooms": 1,
        }
        payload.update(overrides)
        return payload

    def make_image(self, name="listing.gif"):
        content = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff!\xf9\x04"
            b"\x01\x00\x00\x00\x00,\x00\x00\x00"
            b"\x00\x01\x00\x01\x00\x00\x02\x02D"
            b"\x01\x00;"
        )

        return SimpleUploadedFile(
            name,
            content,
            content_type="image/gif",
        )

    @staticmethod
    def response_items(response):
        if isinstance(response.data, dict):
            return response.data.get("results", [])

        return response.data


class AmenityAPITests(ListingRelatedAPITestCase):
    def setUp(self):
        super().setUp()

        self.amenity_url = reverse(
            "listings:amenity-list-create"
        )
        self.listing_url = reverse(
            "listings:listing-list-create"
        )

    def test_amenity_list_is_public(self):
        first_amenity = Amenity.objects.create(
            name="Wi-Fi"
        )
        second_amenity = Amenity.objects.create(
            name="Parking"
        )

        response = self.client.get(
            self.amenity_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        amenity_ids = {
            item["id"]
            for item in self.response_items(response)
        }

        self.assertIn(
            first_amenity.pk,
            amenity_ids,
        )
        self.assertIn(
            second_amenity.pk,
            amenity_ids,
        )

    def test_regular_user_cannot_create_amenity(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.amenity_url,
            {"name": "Sauna"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(
            Amenity.objects.filter(
                name="Sauna"
            ).exists()
        )

    def test_staff_user_can_create_amenity(self):
        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            self.amenity_url,
            {"name": "Sauna"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(
            Amenity.objects.filter(
                name="Sauna"
            ).exists()
        )

    def test_staff_user_can_update_amenity(self):
        amenity = Amenity.objects.create(
            name="Old name"
        )

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.patch(
            reverse(
                "listings:amenity-detail",
                kwargs={"pk": amenity.pk},
            ),
            {"name": "Updated name"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        amenity.refresh_from_db()

        self.assertEqual(
            amenity.name,
            "Updated name",
        )

    def test_staff_user_can_delete_amenity(self):
        amenity = Amenity.objects.create(
            name="Temporary amenity"
        )

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.delete(
            reverse(
                "listings:amenity-detail",
                kwargs={"pk": amenity.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Amenity.objects.filter(
                pk=amenity.pk
            ).exists()
        )

    def test_duplicate_amenity_name_is_rejected(self):
        Amenity.objects.create(
            name="Wi-Fi"
        )

        self.client.force_authenticate(
            user=self.staff_user
        )

        response = self.client.post(
            self.amenity_url,
            {"name": "Wi-Fi"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "name",
            response.data,
        )

    def test_listing_accepts_twenty_amenities(self):
        amenities = [
            Amenity.objects.create(
                name=f"Amenity {index}"
            )
            for index in range(1, 21)
        ]

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.listing_url,
            self.listing_payload(
                amenities=[
                    amenity.pk
                    for amenity in amenities
                ]
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        listing = Listing.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            listing.amenities.count(),
            20,
        )

    def test_listing_rejects_more_than_twenty_amenities(
        self,
    ):
        amenities = [
            Amenity.objects.create(
                name=f"Amenity {index}"
            )
            for index in range(1, 22)
        ]

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.listing_url,
            self.listing_payload(
                amenities=[
                    amenity.pk
                    for amenity in amenities
                ]
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "amenities",
            response.data,
        )
        self.assertEqual(
            Listing.objects.count(),
            0,
        )


class ListingImageAPITests(
    ListingRelatedAPITestCase
):
    def image_list_url(self, listing):
        return reverse(
            "listings:listing-image-list-create",
            kwargs={"listing_pk": listing.pk},
        )

    def image_detail_url(self, image):
        return reverse(
            "listings:listing-image-detail",
            kwargs={
                "listing_pk": image.listing_id,
                "pk": image.pk,
            },
        )

    def test_anonymous_user_can_list_active_images(self):
        listing = self.create_listing(
            is_active=True
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                image = ListingImage.objects.create(
                    listing=listing,
                    image=self.make_image(),
                    is_main=True,
                )

                response = self.client.get(
                    self.image_list_url(listing)
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        image_ids = {
            item["id"]
            for item in self.response_items(response)
        }

        self.assertIn(
            image.pk,
            image_ids,
        )

    def test_anonymous_user_cannot_list_draft_images(
        self,
    ):
        listing = self.create_listing(
            is_active=False
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                ListingImage.objects.create(
                    listing=listing,
                    image=self.make_image(),
                    is_main=True,
                )

                response = self.client.get(
                    self.image_list_url(listing)
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_unauthenticated_user_cannot_upload_image(
        self,
    ):
        listing = self.create_listing()

        response = self.client.post(
            self.image_list_url(listing),
            {
                "image": self.make_image(),
                "is_main": True,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            ListingImage.objects.count(),
            0,
        )

    def test_owner_can_upload_image(self):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.owner
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                response = self.client.post(
                    self.image_list_url(listing),
                    {
                        "image": self.make_image(),
                        "is_main": True,
                    },
                    format="multipart",
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        image = ListingImage.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            image.listing,
            listing,
        )
        self.assertTrue(
            image.is_main
        )

    def test_non_owner_cannot_upload_image(self):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.other_user
        )

        response = self.client.post(
            self.image_list_url(listing),
            {
                "image": self.make_image(),
                "is_main": True,
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            ListingImage.objects.count(),
            0,
        )

    def test_fifth_listing_image_is_rejected(self):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.owner
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                for index in range(1, 5):
                    ListingImage.objects.create(
                        listing=listing,
                        image=self.make_image(
                            f"listing-{index}.gif"
                        ),
                        is_main=index == 1,
                    )

                response = self.client.post(
                    self.image_list_url(listing),
                    {
                        "image": self.make_image(
                            "listing-5.gif"
                        ),
                        "is_main": False,
                    },
                    format="multipart",
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "image",
            response.data,
        )
        self.assertEqual(
            listing.images.count(),
            4,
        )

    def test_owner_can_delete_listing_image(self):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.owner
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                image = ListingImage.objects.create(
                    listing=listing,
                    image=self.make_image(),
                    is_main=True,
                )

                response = self.client.delete(
                    self.image_detail_url(image)
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            ListingImage.objects.filter(
                pk=image.pk
            ).exists()
        )

    def test_non_owner_cannot_delete_listing_image(
        self,
    ):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.other_user
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                image = ListingImage.objects.create(
                    listing=listing,
                    image=self.make_image(),
                    is_main=True,
                )

                response = self.client.delete(
                    self.image_detail_url(image)
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertTrue(
            ListingImage.objects.filter(
                pk=image.pk
            ).exists()
        )


class FavoriteAPITests(
    ListingRelatedAPITestCase
):
    def setUp(self):
        super().setUp()

        self.favorite_url = reverse(
            "listings:favorite-list-create"
        )

    def test_favorite_endpoint_requires_authentication(
        self,
    ):
        response = self.client.get(
            self.favorite_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_can_add_listing_to_favorites(self):
        listing = self.create_listing()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.favorite_url,
            {"listing": listing.pk},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        favorite = Favorite.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            favorite.user,
            self.owner,
        )
        self.assertEqual(
            favorite.listing,
            listing,
        )

    def test_duplicate_favorite_is_rejected(self):
        listing = self.create_listing()

        Favorite.objects.create(
            user=self.owner,
            listing=listing,
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.favorite_url,
            {"listing": listing.pk},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "listing",
            response.data,
        )
        self.assertEqual(
            Favorite.objects.filter(
                user=self.owner,
                listing=listing,
            ).count(),
            1,
        )

    def test_user_sees_only_own_favorites(self):
        listing = self.create_listing()

        own_favorite = Favorite.objects.create(
            user=self.owner,
            listing=listing,
        )
        other_favorite = Favorite.objects.create(
            user=self.other_user,
            listing=listing,
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.get(
            self.favorite_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        favorite_ids = {
            item["id"]
            for item in self.response_items(response)
        }

        self.assertIn(
            own_favorite.pk,
            favorite_ids,
        )
        self.assertNotIn(
            other_favorite.pk,
            favorite_ids,
        )

    def test_user_can_remove_own_favorite(self):
        listing = self.create_listing()

        favorite = Favorite.objects.create(
            user=self.owner,
            listing=listing,
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.delete(
            reverse(
                "listings:favorite-detail",
                kwargs={"pk": favorite.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Favorite.objects.filter(
                pk=favorite.pk
            ).exists()
        )

    def test_user_cannot_remove_another_users_favorite(
        self,
    ):
        listing = self.create_listing()

        favorite = Favorite.objects.create(
            user=self.other_user,
            listing=listing,
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.delete(
            reverse(
                "listings:favorite-detail",
                kwargs={"pk": favorite.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(
            Favorite.objects.filter(
                pk=favorite.pk
            ).exists()
        )

    def test_listing_detail_exposes_favorite_state(self):
        listing = self.create_listing()

        favorite = Favorite.objects.create(
            user=self.owner,
            listing=listing,
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.get(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(
            response.data["is_favorite"]
        )
        self.assertEqual(
            response.data["favorite_id"],
            favorite.pk,
        )

    def test_anonymous_listing_detail_has_no_favorite(
        self,
    ):
        listing = self.create_listing()

        Favorite.objects.create(
            user=self.owner,
            listing=listing,
        )

        response = self.client.get(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": listing.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertFalse(
            response.data["is_favorite"]
        )
        self.assertIsNone(
            response.data["favorite_id"]
        )


class ListingFilteringAPITests(
    ListingRelatedAPITestCase
):
    def setUp(self):
        super().setUp()

        self.list_url = reverse(
            "listings:listing-list-create"
        )

    def create_filter_listing(
        self,
        *,
        title,
        description="Comfortable test accommodation.",
        listing_type=Listing.ListingType.APARTMENT,
        country="Germany",
        city="Munich",
        price="100.00",
        max_guests=4,
        bedrooms=2,
        beds=2,
        bathrooms=1,
        amenities=None,
    ):
        listing = Listing.objects.create(
            owner=self.owner,
            title=title,
            description=description,
            listing_type=listing_type,
            country=country,
            city=city,
            address=f"{title} address",
            earliest_check_in_time=time(15, 0),
            latest_check_out_time=time(11, 0),
            price_per_night=Decimal(price),
            max_guests=max_guests,
            bedrooms=bedrooms,
            beds=beds,
            bathrooms=bathrooms,
            is_active=True,
        )

        if amenities:
            listing.amenities.set(
                amenities
            )

        return listing

    def listing_ids(self, response):
        return [
            item["id"]
            for item in self.response_items(response)
        ]

    def create_booking_for_dates(
        self,
        *,
        listing,
        check_in_date,
        check_out_date,
        booking_status=Booking.Status.CONFIRMED,
    ):
        check_in = timezone.make_aware(
            datetime.combine(
                check_in_date,
                time(15, 0),
            )
        )
        check_out = timezone.make_aware(
            datetime.combine(
                check_out_date,
                time(11, 0),
            )
        )

        book_days = (
            check_out_date
            - check_in_date
        ).days

        return Booking.objects.create(
            guest=self.other_user,
            listing=listing,
            check_in=check_in,
            check_out=check_out,
            book_days=book_days,
            guests=2,
            total_price=(
                listing.price_per_night
                * book_days
            ),
            status=booking_status,
        )

    def add_rating(
        self,
        *,
        listing,
        rating,
    ):
        check_out = (
            timezone.now()
            - timedelta(days=1)
        )
        check_in = (
            check_out
            - timedelta(days=2)
        )

        booking = Booking.objects.create(
            guest=self.other_user,
            listing=listing,
            check_in=check_in,
            check_out=check_out,
            book_days=2,
            guests=2,
            total_price=(
                listing.price_per_night
                * 2
            ),
            status=Booking.Status.COMPLETED,
        )

        return Review.objects.create(
            booking=booking,
            rating=rating,
            liked="A completed rated stay.",
            disliked="",
        )

    def test_search_matches_title_and_description(
        self,
    ):
        title_match = self.create_filter_listing(
            title="Mountain Retreat",
        )
        description_match = (
            self.create_filter_listing(
                title="Quiet Apartment",
                description=(
                    "A peaceful home with "
                    "a mountain view."
                ),
            )
        )
        unrelated = self.create_filter_listing(
            title="City Studio",
            description="Located near the central station.",
        )

        response = self.client.get(
            self.list_url,
            {"search": "MOUNTAIN"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        listing_ids = self.listing_ids(
            response
        )

        self.assertIn(
            title_match.pk,
            listing_ids,
        )
        self.assertIn(
            description_match.pk,
            listing_ids,
        )
        self.assertNotIn(
            unrelated.pk,
            listing_ids,
        )

    def test_price_range_filters_listings(self):
        cheap = self.create_filter_listing(
            title="Cheap apartment",
            price="50.00",
        )
        matching = self.create_filter_listing(
            title="Matching apartment",
            price="150.00",
        )
        expensive = self.create_filter_listing(
            title="Expensive apartment",
            price="250.00",
        )

        response = self.client.get(
            self.list_url,
            {
                "min_price": "100.00",
                "max_price": "200.00",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        listing_ids = self.listing_ids(
            response
        )

        self.assertNotIn(
            cheap.pk,
            listing_ids,
        )
        self.assertIn(
            matching.pk,
            listing_ids,
        )
        self.assertNotIn(
            expensive.pk,
            listing_ids,
        )

    def test_listing_type_filter(self):
        apartment = self.create_filter_listing(
            title="Apartment",
            listing_type=(
                Listing.ListingType.APARTMENT
            ),
        )
        house = self.create_filter_listing(
            title="House",
            listing_type=Listing.ListingType.HOUSE,
        )

        response = self.client.get(
            self.list_url,
            {
                "listing_type": (
                    Listing.ListingType.HOUSE
                )
            },
        )

        listing_ids = self.listing_ids(
            response
        )

        self.assertNotIn(
            apartment.pk,
            listing_ids,
        )
        self.assertIn(
            house.pk,
            listing_ids,
        )

    def test_city_and_country_filters_are_case_insensitive(
        self,
    ):
        matching = self.create_filter_listing(
            title="Munich apartment",
            city="Munich",
            country="Germany",
        )
        wrong_country = self.create_filter_listing(
            title="Munich in another country",
            city="Munich",
            country="Austria",
        )
        wrong_city = self.create_filter_listing(
            title="Berlin apartment",
            city="Berlin",
            country="Germany",
        )

        response = self.client.get(
            self.list_url,
            {
                "city": "MUN",
                "country": "germ",
            },
        )

        listing_ids = self.listing_ids(
            response
        )

        self.assertIn(
            matching.pk,
            listing_ids,
        )
        self.assertNotIn(
            wrong_country.pk,
            listing_ids,
        )
        self.assertNotIn(
            wrong_city.pk,
            listing_ids,
        )

    def test_property_detail_filters_can_be_combined(
        self,
    ):
        matching = self.create_filter_listing(
            title="Matching property",
            bedrooms=3,
            beds=4,
            bathrooms=2,
        )
        wrong_bedrooms = self.create_filter_listing(
            title="Wrong bedrooms",
            bedrooms=2,
            beds=4,
            bathrooms=2,
        )
        wrong_beds = self.create_filter_listing(
            title="Wrong beds",
            bedrooms=3,
            beds=3,
            bathrooms=2,
        )

        response = self.client.get(
            self.list_url,
            {
                "bedrooms": 3,
                "beds": 4,
                "bathrooms": 2,
            },
        )

        listing_ids = self.listing_ids(
            response
        )

        self.assertIn(
            matching.pk,
            listing_ids,
        )
        self.assertNotIn(
            wrong_bedrooms.pk,
            listing_ids,
        )
        self.assertNotIn(
            wrong_beds.pk,
            listing_ids,
        )

    def test_guests_filter_uses_minimum_capacity(self):
        too_small = self.create_filter_listing(
            title="Small apartment",
            max_guests=2,
        )
        exact_capacity = self.create_filter_listing(
            title="Exact apartment",
            max_guests=4,
        )
        larger = self.create_filter_listing(
            title="Large apartment",
            max_guests=6,
        )

        response = self.client.get(
            self.list_url,
            {"guests": 4},
        )

        listing_ids = self.listing_ids(
            response
        )

        self.assertNotIn(
            too_small.pk,
            listing_ids,
        )
        self.assertIn(
            exact_capacity.pk,
            listing_ids,
        )
        self.assertIn(
            larger.pk,
            listing_ids,
        )

    def test_amenity_filter_requires_all_selected_amenities(
        self,
    ):
        wifi = Amenity.objects.create(
            name="Filter Wi-Fi"
        )
        pool = Amenity.objects.create(
            name="Filter pool"
        )

        both_amenities = self.create_filter_listing(
            title="Apartment with both",
            amenities=[wifi, pool],
        )
        wifi_only = self.create_filter_listing(
            title="Apartment with Wi-Fi",
            amenities=[wifi],
        )

        response = self.client.get(
            self.list_url,
            {
                "amenities": (
                    f"{wifi.pk},{pool.pk}"
                )
            },
        )

        listing_ids = self.listing_ids(
            response
        )

        self.assertIn(
            both_amenities.pk,
            listing_ids,
        )
        self.assertNotIn(
            wifi_only.pk,
            listing_ids,
        )

    def test_invalid_amenity_ids_are_rejected(self):
        response = self.client.get(
            self.list_url,
            {"amenities": "1,invalid"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "amenities",
            response.data,
        )

    def test_invalid_price_range_is_rejected(self):
        response = self.client.get(
            self.list_url,
            {
                "min_price": "500.00",
                "max_price": "100.00",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "max_price",
            response.data,
        )

    def test_price_can_be_sorted_ascending(self):
        expensive = self.create_filter_listing(
            title="Expensive",
            price="300.00",
        )
        cheap = self.create_filter_listing(
            title="Cheap",
            price="100.00",
        )
        medium = self.create_filter_listing(
            title="Medium",
            price="200.00",
        )

        response = self.client.get(
            self.list_url,
            {"ordering": "price_per_night"},
        )

        self.assertEqual(
            self.listing_ids(response),
            [
                cheap.pk,
                medium.pk,
                expensive.pk,
            ],
        )

    def test_price_can_be_sorted_descending(self):
        expensive = self.create_filter_listing(
            title="Expensive",
            price="300.00",
        )
        cheap = self.create_filter_listing(
            title="Cheap",
            price="100.00",
        )
        medium = self.create_filter_listing(
            title="Medium",
            price="200.00",
        )

        response = self.client.get(
            self.list_url,
            {"ordering": "-price_per_night"},
        )

        self.assertEqual(
            self.listing_ids(response),
            [
                expensive.pk,
                medium.pk,
                cheap.pk,
            ],
        )

    def test_rating_can_be_sorted_descending(self):
        low_rated = self.create_filter_listing(
            title="Low rated",
        )
        high_rated = self.create_filter_listing(
            title="High rated",
        )
        unrated = self.create_filter_listing(
            title="Unrated",
        )

        self.add_rating(
            listing=low_rated,
            rating=2,
        )
        self.add_rating(
            listing=high_rated,
            rating=5,
        )

        response = self.client.get(
            self.list_url,
            {"ordering": "-rating"},
        )

        self.assertEqual(
            self.listing_ids(response),
            [
                high_rated.pk,
                low_rated.pk,
                unrated.pk,
            ],
        )

    def test_newest_listings_can_be_sorted_first(self):
        older = self.create_filter_listing(
            title="Older listing",
        )
        newer = self.create_filter_listing(
            title="Newer listing",
        )

        response = self.client.get(
            self.list_url,
            {"ordering": "-created_at"},
        )

        self.assertEqual(
            self.listing_ids(response),
            [
                newer.pk,
                older.pk,
            ],
        )

    def test_booking_conflict_excludes_listing(self):
        unavailable = self.create_filter_listing(
            title="Unavailable listing",
        )
        available = self.create_filter_listing(
            title="Available listing",
        )

        search_check_in = (
            timezone.localdate()
            + timedelta(days=10)
        )
        search_check_out = (
            search_check_in
            + timedelta(days=5)
        )

        self.create_booking_for_dates(
            listing=unavailable,
            check_in_date=(
                search_check_in
                + timedelta(days=1)
            ),
            check_out_date=(
                search_check_in
                + timedelta(days=3)
            ),
        )

        response = self.client.get(
            self.list_url,
            {
                "check_in": (
                    search_check_in.isoformat()
                ),
                "check_out": (
                    search_check_out.isoformat()
                ),
            },
        )

        listing_ids = self.listing_ids(
            response
        )

        self.assertNotIn(
            unavailable.pk,
            listing_ids,
        )
        self.assertIn(
            available.pk,
            listing_ids,
        )

    def test_cancelled_booking_does_not_exclude_listing(
        self,
    ):
        listing = self.create_filter_listing(
            title="Listing with cancelled booking",
        )

        search_check_in = (
            timezone.localdate()
            + timedelta(days=10)
        )
        search_check_out = (
            search_check_in
            + timedelta(days=5)
        )

        self.create_booking_for_dates(
            listing=listing,
            check_in_date=(
                search_check_in
                + timedelta(days=1)
            ),
            check_out_date=(
                search_check_in
                + timedelta(days=3)
            ),
            booking_status=(
                Booking.Status.CANCELLED
            ),
        )

        response = self.client.get(
            self.list_url,
            {
                "check_in": (
                    search_check_in.isoformat()
                ),
                "check_out": (
                    search_check_out.isoformat()
                ),
            },
        )

        self.assertIn(
            listing.pk,
            self.listing_ids(response),
        )

    def test_blocked_period_excludes_listing(self):
        blocked_listing = self.create_filter_listing(
            title="Blocked listing",
        )
        available_listing = self.create_filter_listing(
            title="Available listing",
        )

        search_check_in = (
            timezone.localdate()
            + timedelta(days=10)
        )
        search_check_out = (
            search_check_in
            + timedelta(days=5)
        )

        blocked_start = timezone.make_aware(
            datetime.combine(
                search_check_in
                + timedelta(days=1),
                time(9, 0),
            )
        )
        blocked_end = timezone.make_aware(
            datetime.combine(
                search_check_in
                + timedelta(days=2),
                time(18, 0),
            )
        )

        BlockedPeriod.objects.create(
            listing=blocked_listing,
            start_at=blocked_start,
            end_at=blocked_end,
            reason=(
                BlockedPeriod.Reason.MAINTENANCE
            ),
            note="Scheduled maintenance.",
        )

        response = self.client.get(
            self.list_url,
            {
                "check_in": (
                    search_check_in.isoformat()
                ),
                "check_out": (
                    search_check_out.isoformat()
                ),
            },
        )

        listing_ids = self.listing_ids(
            response
        )

        self.assertNotIn(
            blocked_listing.pk,
            listing_ids,
        )
        self.assertIn(
            available_listing.pk,
            listing_ids,
        )

    def test_invalid_date_range_is_rejected(self):
        check_in = (
            timezone.localdate()
            + timedelta(days=10)
        )

        response = self.client.get(
            self.list_url,
            {
                "check_in": check_in.isoformat(),
                "check_out": check_in.isoformat(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "check_out",
            response.data,
        )

    def test_both_availability_dates_are_required(self):
        check_in = (
            timezone.localdate()
            + timedelta(days=10)
        )

        response = self.client.get(
            self.list_url,
            {
                "check_in": check_in.isoformat(),
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "check_out",
            response.data,
        )

    def test_rejected_booking_does_not_exclude_listing(
            self,
    ):
        listing = self.create_filter_listing(
            title="Listing with rejected booking",
        )

        search_check_in = (
                timezone.localdate()
                + timedelta(days=10)
        )
        search_check_out = (
                search_check_in
                + timedelta(days=5)
        )

        self.create_booking_for_dates(
            listing=listing,
            check_in_date=(
                    search_check_in
                    + timedelta(days=1)
            ),
            check_out_date=(
                    search_check_in
                    + timedelta(days=3)
            ),
            booking_status=Booking.Status.REJECTED,
        )

        response = self.client.get(
            self.list_url,
            {
                "check_in": search_check_in.isoformat(),
                "check_out": search_check_out.isoformat(),
            },
        )

        self.assertIn(
            listing.pk,
            self.listing_ids(response),
        )


class ListingViewAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="view.owner@example.com",
            password="StrongPass123!",
            first_name="Olivia",
            last_name="Owner",
            phone_number="+491700000501",
        )
        assign_landlord_role(self.owner)

        self.guest = User.objects.create_user(
            email="view.guest@example.com",
            password="StrongPass123!",
            first_name="Grace",
            last_name="Guest",
            phone_number="+491700000502",
        )

        self.other_user = User.objects.create_user(
            email="view.other@example.com",
            password="StrongPass123!",
            first_name="Oscar",
            last_name="Viewer",
            phone_number="+491700000503",
        )

        self.listing = self.create_listing(
            title="Viewed apartment",
        )

        self.detail_url = reverse(
            "listings:listing-detail",
            kwargs={"pk": self.listing.pk},
        )

        self.list_url = reverse(
            "listings:listing-list-create"
        )

        self.history_url = reverse(
            "listings:listing-view-history"
        )

    def create_listing(
        self,
        *,
        title,
        price="100.00",
    ):
        return Listing.objects.create(
            owner=self.owner,
            title=title,
            description=(
                "Listing used for view history tests."
            ),
            listing_type=(
                Listing.ListingType.APARTMENT
            ),
            country="Germany",
            city="Munich",
            address=f"{title} address",
            earliest_check_in_time=time(15, 0),
            latest_check_out_time=time(11, 0),
            price_per_night=Decimal(price),
            max_guests=4,
            bedrooms=2,
            beds=2,
            bathrooms=1,
            is_active=True,
        )

    def response_items(self, response):
        if (
            isinstance(response.data, dict)
            and "results" in response.data
        ):
            return response.data["results"]

        return response.data

    def add_views(
        self,
        *,
        listing,
        count,
    ):
        for index in range(count):
            ListingView.objects.create(
                listing=listing,
                viewer_key=(
                    f"test:{listing.pk}:{index}"
                ),
                viewed_on=timezone.localdate(),
            )

    def test_authenticated_user_counts_once_per_day(
        self,
    ):
        self.client.force_authenticate(
            user=self.guest
        )

        first_response = self.client.get(
            self.detail_url
        )
        second_response = self.client.get(
            self.detail_url
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            ListingView.objects.count(),
            1,
        )
        self.assertEqual(
            first_response.data["views_count"],
            1,
        )
        self.assertEqual(
            second_response.data["views_count"],
            1,
        )

        listing_view = ListingView.objects.get()

        self.assertEqual(
            listing_view.user,
            self.guest,
        )
        self.assertEqual(
            listing_view.viewer_key,
            f"user:{self.guest.pk}",
        )
        self.assertEqual(
            listing_view.viewed_on,
            timezone.localdate(),
        )

    def test_anonymous_session_counts_once_per_day(
        self,
    ):
        first_response = self.client.get(
            self.detail_url
        )
        second_response = self.client.get(
            self.detail_url
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            ListingView.objects.count(),
            1,
        )
        self.assertIsNone(
            ListingView.objects.get().user
        )

    def test_different_anonymous_sessions_are_separate(
        self,
    ):
        first_client = APIClient()
        second_client = APIClient()

        first_client.get(
            self.detail_url
        )
        second_client.get(
            self.detail_url
        )

        self.assertEqual(
            ListingView.objects.count(),
            2,
        )

    def test_owner_view_is_not_counted(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.get(
            self.detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["views_count"],
            0,
        )
        self.assertEqual(
            ListingView.objects.count(),
            0,
        )

    def test_new_day_creates_new_view(self):
        ListingView.objects.create(
            listing=self.listing,
            user=self.guest,
            viewer_key=f"user:{self.guest.pk}",
            viewed_on=(
                timezone.localdate()
                - timedelta(days=1)
            ),
        )

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.get(
            self.detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            ListingView.objects.count(),
            2,
        )
        self.assertEqual(
            response.data["views_count"],
            2,
        )

    def test_view_history_requires_authentication(
        self,
    ):
        response = self.client.get(
            self.history_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_history_contains_only_current_user_views(
        self,
    ):
        own_view = ListingView.objects.create(
            listing=self.listing,
            user=self.guest,
            viewer_key=f"user:{self.guest.pk}",
            viewed_on=timezone.localdate(),
        )

        ListingView.objects.create(
            listing=self.listing,
            user=self.other_user,
            viewer_key=(
                f"user:{self.other_user.pk}"
            ),
            viewed_on=timezone.localdate(),
        )

        ListingView.objects.create(
            listing=self.listing,
            viewer_key="test:anonymous",
            viewed_on=timezone.localdate(),
        )

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.get(
            self.history_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        items = self.response_items(response)

        self.assertEqual(
            len(items),
            1,
        )
        self.assertEqual(
            items[0]["id"],
            own_view.pk,
        )
        self.assertEqual(
            items[0]["listing"]["id"],
            self.listing.pk,
        )

    def test_popular_ordering_uses_view_count(
        self,
    ):
        popular = self.create_listing(
            title="Popular apartment",
        )
        less_popular = self.create_listing(
            title="Less popular apartment",
        )

        self.add_views(
            listing=popular,
            count=3,
        )
        self.add_views(
            listing=less_popular,
            count=1,
        )

        response = self.client.get(
            self.list_url,
            {"ordering": "popular"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            [
                item["id"]
                for item in self.response_items(
                    response
                )
            ],
            [
                popular.pk,
                less_popular.pk,
                self.listing.pk,
            ],
        )

    def test_view_history_does_not_block_deletion(
        self,
    ):
        self.client.force_authenticate(
            user=self.guest
        )
        self.client.get(
            self.detail_url
        )

        self.assertEqual(
            ListingView.objects.count(),
            1,
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.delete(
            self.detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Listing.objects.filter(
                pk=self.listing.pk
            ).exists()
        )
        self.assertEqual(
            ListingView.objects.count(),
            0,
        )
