from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.bookings.models import Booking, BlockedPeriod
from apps.listings.models import Listing


User = get_user_model()


class BookingCreateAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            first_name="Olivia",
            last_name="Owner",
            phone_number="+491700000001",
        )

        self.guest = User.objects.create_user(
            email="guest@example.com",
            password="StrongPass123!",
            first_name="Grace",
            last_name="Guest",
            phone_number="+491700000002",
        )

        self.listing = Listing.objects.create(
            owner=self.owner,
            title="Test apartment",
            description="Apartment used in booking API tests.",
            listing_type=Listing.ListingType.APARTMENT,
            country="Germany",
            city="Munich",
            address="Teststrasse 1",
            earliest_check_in_time=time(15, 0),
            latest_check_out_time=time(11, 0),
            price_per_night=Decimal("120.00"),
            max_guests=4,
            bedrooms=2,
            beds=2,
            bathrooms=1,
            is_active=True,
        )

        self.url = reverse(
            "bookings:booking-list-create"
        )

        self.client.force_authenticate(
            user=self.guest
        )

    def make_datetime(
        self,
        days_from_today,
        hour,
        minute=0,
    ):
        target_date = (
            timezone.localdate()
            + timedelta(days=days_from_today)
        )

        value = datetime.combine(
            target_date,
            time(hour, minute),
        )

        return timezone.make_aware(
            value,
            timezone.get_current_timezone(),
        )

    def booking_payload(
        self,
        *,
        listing=None,
        check_in=None,
        check_out=None,
        guests=2,
    ):
        if listing is None:
            listing = self.listing

        if check_in is None:
            check_in = self.make_datetime(10, 15)

        if check_out is None:
            check_out = self.make_datetime(13, 11)

        return {
            "listing": listing.pk,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": guests,
        }

    def create_existing_booking(
        self,
        *,
        check_in=None,
        check_out=None,
        status_value=Booking.Status.CONFIRMED,
    ):
        if check_in is None:
            check_in = self.make_datetime(10, 15)

        if check_out is None:
            check_out = self.make_datetime(13, 11)

        book_days = (
            check_out.date()
            - check_in.date()
        ).days

        return Booking.objects.create(
            guest=self.guest,
            listing=self.listing,
            check_in=check_in,
            check_out=check_out,
            book_days=book_days,
            guests=2,
            total_price=(
                self.listing.price_per_night
                * book_days
            ),
            status=status_value,
        )

    def test_authentication_is_required(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.url,
            self.booking_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            Booking.objects.count(),
            0,
        )

    def test_booking_is_created_and_values_are_calculated(self):
        payload = self.booking_payload()

        # ignor:
        payload.update(
            {
                "book_days": 999,
                "total_price": "1.00",
                "status": Booking.Status.COMPLETED,
            }
        )

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            Booking.objects.count(),
            1,
        )

        booking = Booking.objects.get()

        self.assertEqual(
            booking.guest,
            self.guest,
        )
        self.assertEqual(
            booking.listing,
            self.listing,
        )
        self.assertEqual(
            booking.book_days,
            3,
        )
        self.assertEqual(
            booking.total_price,
            Decimal("360.00"),
        )
        self.assertEqual(
            booking.status,
            Booking.Status.PENDING,
        )

    def test_owner_cannot_book_own_listing(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.url,
            self.booking_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            Booking.objects.count(),
            0,
        )

    def test_inactive_listing_cannot_be_booked(self):
        self.listing.is_active = False
        self.listing.save(
            update_fields=("is_active",)
        )

        response = self.client.post(
            self.url,
            self.booking_payload(),
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

    def test_guest_limit_is_checked(self):
        response = self.client.post(
            self.url,
            self.booking_payload(guests=5),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "guests",
            response.data,
        )

    def test_check_in_must_be_in_future(self):
        response = self.client.post(
            self.url,
            self.booking_payload(
                check_in=self.make_datetime(-1, 15),
                check_out=self.make_datetime(2, 11),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "check_in",
            response.data,
        )

    def test_booking_requires_at_least_one_night(self):
        response = self.client.post(
            self.url,
            self.booking_payload(
                check_in=self.make_datetime(10, 15),
                check_out=self.make_datetime(10, 20),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "check_out",
            response.data,
        )

    def test_check_in_cannot_be_too_early(self):
        response = self.client.post(
            self.url,
            self.booking_payload(
                check_in=self.make_datetime(10, 14),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "check_in",
            response.data,
        )

    def test_check_out_cannot_be_too_late(self):
        response = self.client.post(
            self.url,
            self.booking_payload(
                check_out=self.make_datetime(13, 12),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "check_out",
            response.data,
        )

    def test_overlapping_booking_is_rejected(self):
        self.create_existing_booking()

        response = self.client.post(
            self.url,
            self.booking_payload(
                check_in=self.make_datetime(12, 15),
                check_out=self.make_datetime(15, 11),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "non_field_errors",
            response.data,
        )

    def test_cancelled_booking_does_not_block_dates(self):
        self.create_existing_booking(
            status_value=Booking.Status.CANCELLED,
        )

        response = self.client.post(
            self.url,
            self.booking_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            Booking.objects.count(),
            2,
        )

    def test_blocked_period_prevents_booking(self):
        BlockedPeriod.objects.create(
            listing=self.listing,
            start_at=self.make_datetime(11, 0),
            end_at=self.make_datetime(12, 23),
            reason=BlockedPeriod.Reason.MAINTENANCE,
            note="Scheduled maintenance",
        )

        response = self.client.post(
            self.url,
            self.booking_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "non_field_errors",
            response.data,
        )

    def test_same_day_turnover_is_allowed_after_default_gap(self):
        self.create_existing_booking(
            check_in=self.make_datetime(10, 15),
            check_out=self.make_datetime(12, 11),
        )

        response = self.client.post(
            self.url,
            self.booking_payload(
                check_in=self.make_datetime(12, 15),
                check_out=self.make_datetime(14, 11),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )


class BookingActionsAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="booking.owner@example.com",
            password="StrongPass123!",
            first_name="Olivia",
            last_name="Owner",
            phone_number="+491700000011",
        )

        self.guest = User.objects.create_user(
            email="booking.guest@example.com",
            password="StrongPass123!",
            first_name="Grace",
            last_name="Guest",
            phone_number="+491700000012",
        )

        self.outsider = User.objects.create_user(
            email="outsider@example.com",
            password="StrongPass123!",
            first_name="Oscar",
            last_name="Outsider",
            phone_number="+491700000013",
        )

        self.listing = Listing.objects.create(
            owner=self.owner,
            title="Booking actions apartment",
            description="Apartment used for booking action tests.",
            listing_type=Listing.ListingType.APARTMENT,
            country="Germany",
            city="Munich",
            address="Actionstrasse 1",
            earliest_check_in_time=time(15, 0),
            latest_check_out_time=time(11, 0),
            price_per_night=Decimal("100.00"),
            max_guests=4,
            bedrooms=2,
            beds=2,
            bathrooms=1,
            is_active=True,
        )

        self.booking = self.create_booking()

        self.list_url = reverse(
            "bookings:booking-list-create"
        )

    def make_datetime(
        self,
        days_from_today,
        hour,
        minute=0,
    ):
        target_date = (
            timezone.localdate()
            + timedelta(days=days_from_today)
        )

        value = datetime.combine(
            target_date,
            time(hour, minute),
        )

        return timezone.make_aware(
            value,
            timezone.get_current_timezone(),
        )

    def create_booking(
        self,
        *,
        check_in=None,
        check_out=None,
        status_value=Booking.Status.PENDING,
    ):
        if check_in is None:
            check_in = self.make_datetime(10, 15)

        if check_out is None:
            check_out = self.make_datetime(13, 11)

        book_days = (
            check_out.date()
            - check_in.date()
        ).days

        return Booking.objects.create(
            guest=self.guest,
            listing=self.listing,
            check_in=check_in,
            check_out=check_out,
            book_days=book_days,
            guests=2,
            total_price=(
                self.listing.price_per_night
                * book_days
            ),
            status=status_value,
        )

    def move_booking_to_past(
        self,
        status_value,
    ):
        self.booking.check_in = self.make_datetime(
            -5,
            15,
        )
        self.booking.check_out = self.make_datetime(
            -2,
            11,
        )
        self.booking.book_days = 3
        self.booking.total_price = Decimal("300.00")
        self.booking.status = status_value

        self.booking.save(
            update_fields=(
                "check_in",
                "check_out",
                "book_days",
                "total_price",
                "status",
            )
        )

    def get_response_items(self, response):
        if (
            isinstance(response.data, dict)
            and "results" in response.data
        ):
            return response.data["results"]

        return response.data

    def test_booking_list_requires_authentication(self):
        response = self.client.get(
            self.list_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_booking_list_is_limited_to_participants(self):
        expected_results = (
            (self.guest, [self.booking.pk]),
            (self.owner, [self.booking.pk]),
            (self.outsider, []),
        )

        for user, expected_ids in expected_results:
            with self.subTest(user=user.email):
                self.client.force_authenticate(
                    user=user
                )

                response = self.client.get(
                    self.list_url
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )

                items = self.get_response_items(
                    response
                )

                actual_ids = [
                    item["id"]
                    for item in items
                ]

                self.assertEqual(
                    actual_ids,
                    expected_ids,
                )

    def test_only_participants_can_view_booking_detail(self):
        detail_url = reverse(
            "bookings:booking-detail",
            kwargs={"pk": self.booking.pk},
        )

        for user in (self.guest, self.owner):
            with self.subTest(user=user.email):
                self.client.force_authenticate(
                    user=user
                )

                response = self.client.get(
                    detail_url
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )

        self.client.force_authenticate(
            user=self.outsider
        )

        response = self.client.get(
            detail_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_guest_can_cancel_pending_booking(self):
        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            reverse(
                "bookings:booking-cancel",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.CANCELLED,
        )

    def test_owner_can_cancel_pending_booking(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            reverse(
                "bookings:booking-cancel",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.CANCELLED,
        )

    def test_outsider_cannot_cancel_booking(self):
        self.client.force_authenticate(
            user=self.outsider
        )

        response = self.client.post(
            reverse(
                "bookings:booking-cancel",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.PENDING,
        )

    def test_completed_booking_cannot_be_cancelled(self):
        self.booking.status = Booking.Status.COMPLETED
        self.booking.save(
            update_fields=("status",)
        )

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            reverse(
                "bookings:booking-cancel",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_owner_can_confirm_pending_booking(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            reverse(
                "bookings:booking-confirm",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.CONFIRMED,
        )

    def test_guest_cannot_confirm_booking(self):
        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            reverse(
                "bookings:booking-confirm",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_confirm_requires_pending_status(self):
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save(
            update_fields=("status",)
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            reverse(
                "bookings:booking-confirm",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_booking_cannot_be_completed_before_checkout(self):
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save(
            update_fields=("status",)
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            reverse(
                "bookings:booking-complete",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_owner_can_complete_booking_after_checkout(self):
        self.move_booking_to_past(
            Booking.Status.CONFIRMED
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            reverse(
                "bookings:booking-complete",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            Booking.Status.COMPLETED,
        )

    def test_guest_cannot_complete_booking(self):
        self.move_booking_to_past(
            Booking.Status.CONFIRMED
        )

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            reverse(
                "bookings:booking-complete",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_only_confirmed_booking_can_be_completed(self):
        self.move_booking_to_past(
            Booking.Status.PENDING
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            reverse(
                "bookings:booking-complete",
                kwargs={"pk": self.booking.pk},
            ),
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


class BlockedPeriodAPITests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="period.owner@example.com",
            password="StrongPass123!",
            first_name="Peter",
            last_name="Owner",
            phone_number="+491700000021",
        )

        self.other_owner = User.objects.create_user(
            email="other.owner@example.com",
            password="StrongPass123!",
            first_name="Oliver",
            last_name="Owner",
            phone_number="+491700000022",
        )

        self.listing = self.create_listing(
            owner=self.owner,
            title="Owner apartment",
            address="Ownerstrasse 1",
        )

        self.other_listing = self.create_listing(
            owner=self.other_owner,
            title="Other apartment",
            address="Otherstrasse 2",
        )

        self.list_url = reverse(
            "bookings:blocked-period-list-create"
        )

    def create_listing(
        self,
        *,
        owner,
        title,
        address,
    ):
        return Listing.objects.create(
            owner=owner,
            title=title,
            description="Listing used in blocked period tests.",
            listing_type=Listing.ListingType.APARTMENT,
            country="Germany",
            city="Munich",
            address=address,
            earliest_check_in_time=time(15, 0),
            latest_check_out_time=time(11, 0),
            price_per_night=Decimal("100.00"),
            max_guests=4,
            bedrooms=2,
            beds=2,
            bathrooms=1,
            is_active=True,
        )

    def make_datetime(
        self,
        days_from_today,
        hour,
        minute=0,
    ):
        target_date = (
            timezone.localdate()
            + timedelta(days=days_from_today)
        )

        value = datetime.combine(
            target_date,
            time(hour, minute),
        )

        return timezone.make_aware(
            value,
            timezone.get_current_timezone(),
        )

    def period_payload(
        self,
        *,
        listing=None,
        start_at=None,
        end_at=None,
    ):
        if listing is None:
            listing = self.listing

        if start_at is None:
            start_at = self.make_datetime(10, 9)

        if end_at is None:
            end_at = self.make_datetime(12, 18)

        return {
            "listing": listing.pk,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "reason": BlockedPeriod.Reason.MAINTENANCE,
            "note": "Scheduled maintenance",
        }

    def create_period(
        self,
        *,
        listing=None,
        start_at=None,
        end_at=None,
    ):
        if listing is None:
            listing = self.listing

        if start_at is None:
            start_at = self.make_datetime(10, 9)

        if end_at is None:
            end_at = self.make_datetime(12, 18)

        return BlockedPeriod.objects.create(
            listing=listing,
            start_at=start_at,
            end_at=end_at,
            reason=BlockedPeriod.Reason.MAINTENANCE,
            note="Scheduled maintenance",
        )

    def create_booking(
        self,
        *,
        status_value=Booking.Status.CONFIRMED,
    ):
        check_in = self.make_datetime(10, 15)
        check_out = self.make_datetime(13, 11)
        book_days = 3

        return Booking.objects.create(
            guest=self.other_owner,
            listing=self.listing,
            check_in=check_in,
            check_out=check_out,
            book_days=book_days,
            guests=2,
            total_price=Decimal("300.00"),
            status=status_value,
        )

    def get_response_items(self, response):
        if (
            isinstance(response.data, dict)
            and "results" in response.data
        ):
            return response.data["results"]

        return response.data

    def test_authentication_is_required(self):
        get_response = self.client.get(
            self.list_url
        )

        post_response = self.client.post(
            self.list_url,
            self.period_payload(),
            format="json",
        )

        self.assertEqual(
            get_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            post_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_owner_can_create_blocked_period(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.period_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            BlockedPeriod.objects.count(),
            1,
        )

        period = BlockedPeriod.objects.get()

        self.assertEqual(
            period.listing,
            self.listing,
        )
        self.assertEqual(
            period.reason,
            BlockedPeriod.Reason.MAINTENANCE,
        )

    def test_non_owner_cannot_create_blocked_period(self):
        self.client.force_authenticate(
            user=self.other_owner
        )

        response = self.client.post(
            self.list_url,
            self.period_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            BlockedPeriod.objects.count(),
            0,
        )

    def test_blocked_period_cannot_start_in_past(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.period_payload(
                start_at=self.make_datetime(-1, 9),
                end_at=self.make_datetime(2, 18),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "start_at",
            response.data,
        )

    def test_end_must_be_later_than_start(self):
        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.period_payload(
                start_at=self.make_datetime(10, 9),
                end_at=self.make_datetime(9, 18),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "end_at",
            response.data,
        )

    def test_overlapping_blocked_period_is_rejected(self):
        self.create_period()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.period_payload(
                start_at=self.make_datetime(11, 9),
                end_at=self.make_datetime(14, 18),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "non_field_errors",
            response.data,
        )

    def test_active_booking_prevents_blocking_period(self):
        self.create_booking()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.period_payload(
                start_at=self.make_datetime(11, 9),
                end_at=self.make_datetime(12, 18),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "non_field_errors",
            response.data,
        )

    def test_cancelled_booking_does_not_prevent_period(self):
        self.create_booking(
            status_value=Booking.Status.CANCELLED
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.list_url,
            self.period_payload(
                start_at=self.make_datetime(11, 9),
                end_at=self.make_datetime(12, 18),
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_list_contains_only_owned_periods(self):
        owned_period = self.create_period()

        self.create_period(
            listing=self.other_listing,
            start_at=self.make_datetime(15, 9),
            end_at=self.make_datetime(16, 18),
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

        items = self.get_response_items(
            response
        )

        self.assertEqual(
            [
                item["id"]
                for item in items
            ],
            [owned_period.pk],
        )

    def test_owner_can_retrieve_period(self):
        period = self.create_period()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.get(
            reverse(
                "bookings:blocked-period-detail",
                kwargs={"pk": period.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            period.pk,
        )

    def test_owner_can_update_period(self):
        period = self.create_period()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.patch(
            reverse(
                "bookings:blocked-period-detail",
                kwargs={"pk": period.pk},
            ),
            {
                "note": "Updated maintenance note",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        period.refresh_from_db()

        self.assertEqual(
            period.note,
            "Updated maintenance note",
        )

    def test_owner_can_delete_period(self):
        period = self.create_period()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.delete(
            reverse(
                "bookings:blocked-period-detail",
                kwargs={"pk": period.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            BlockedPeriod.objects.filter(
                pk=period.pk
            ).exists()
        )

    def test_non_owner_cannot_access_period(self):
        period = self.create_period()

        detail_url = reverse(
            "bookings:blocked-period-detail",
            kwargs={"pk": period.pk},
        )

        self.client.force_authenticate(
            user=self.other_owner
        )

        get_response = self.client.get(
            detail_url
        )
        patch_response = self.client.patch(
            detail_url,
            {"note": "Unauthorized update"},
            format="json",
        )
        delete_response = self.client.delete(
            detail_url
        )

        self.assertEqual(
            get_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            patch_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertTrue(
            BlockedPeriod.objects.filter(
                pk=period.pk
            ).exists()
        )

    def test_owner_cannot_move_period_to_another_users_listing(
        self,
    ):
        period = self.create_period()

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.patch(
            reverse(
                "bookings:blocked-period-detail",
                kwargs={"pk": period.pk},
            ),
            {
                "listing": self.other_listing.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        period.refresh_from_db()

        self.assertEqual(
            period.listing,
            self.listing,
        )