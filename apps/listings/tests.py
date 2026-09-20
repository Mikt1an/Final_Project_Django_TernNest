import tempfile
from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.listings.models import (
    Amenity,
    Favorite,
    Listing,
    ListingImage,
)


User = get_user_model()


class ListingCleaningGapAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="listing.owner@example.com",
            password="StrongPass123!",
            first_name="Laura",
            last_name="Owner",
            phone_number="+491700000031",
        )

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

    def test_authenticated_user_can_create_draft_listing(
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