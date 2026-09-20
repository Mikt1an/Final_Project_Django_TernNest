import base64
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
from apps.listings.models import Listing
from apps.reviews.constants import MAX_REVIEW_IMAGE_SIZE
from apps.reviews.models import Review, ReviewImage


User = get_user_model()


class ReviewAPITestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="review.owner@example.com",
            password="StrongPass123!",
            first_name="Review",
            last_name="Owner",
            phone_number="+491700000401",
        )
        self.guest = User.objects.create_user(
            email="review.guest@example.com",
            password="StrongPass123!",
            first_name="Review",
            last_name="Guest",
            phone_number="+491700000402",
        )
        self.other_user = User.objects.create_user(
            email="review.other@example.com",
            password="StrongPass123!",
            first_name="Review",
            last_name="Other",
            phone_number="+491700000403",
        )

        self.listing = self.create_listing()
        self.booking = self.create_booking()

        self.review_list_url = reverse(
            "reviews:review-list-create"
        )
        self.review_image_url = reverse(
            "reviews:review-image-create"
        )

    def create_listing(
        self,
        *,
        owner=None,
        title="Review test apartment",
    ):
        return Listing.objects.create(
            owner=owner or self.owner,
            title=title,
            description="Listing used for review API tests.",
            listing_type=Listing.ListingType.APARTMENT,
            country="Germany",
            city="Munich",
            address=f"{title} address",
            earliest_check_in_time=time(15, 0),
            latest_check_out_time=time(11, 0),
            price_per_night=Decimal("100.00"),
            max_guests=4,
            bedrooms=2,
            beds=2,
            bathrooms=1,
            is_active=True,
        )

    def create_booking(
        self,
        *,
        guest=None,
        listing=None,
        booking_status=Booking.Status.COMPLETED,
        check_in=None,
        check_out=None,
    ):
        if check_out is None:
            check_out = (
                timezone.now()
                - timedelta(days=1)
            )

        if check_in is None:
            check_in = (
                check_out
                - timedelta(days=2)
            )

        return Booking.objects.create(
            guest=guest or self.guest,
            listing=listing or self.listing,
            check_in=check_in,
            check_out=check_out,
            book_days=2,
            guests=2,
            total_price=Decimal("200.00"),
            status=booking_status,
        )

    def create_review(
        self,
        *,
        booking=None,
        rating=5,
        liked="Excellent location.",
        disliked="",
    ):
        return Review.objects.create(
            booking=booking or self.booking,
            rating=rating,
            liked=liked,
            disliked=disliked,
        )

    def review_payload(self, **overrides):
        payload = {
            "booking": self.booking.pk,
            "rating": 5,
            "liked": "Excellent location and service.",
            "disliked": "",
        }
        payload.update(overrides)
        return payload

    def make_image(
        self,
        name="review.png",
        size=None,
    ):
        content = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"
            "CAQAAAC1HAwCAAAAC0lEQVR42mNk+A8A"
            "AQUBAScY42YAAAAASUVORK5CYII="
        )

        if size is not None and size > len(content):
            content += b"\x00" * (
                size - len(content)
            )

        return SimpleUploadedFile(
            name,
            content,
            content_type="image/png",
        )

    @staticmethod
    def response_items(response):
        if isinstance(response.data, dict):
            return response.data.get("results", [])

        return response.data


class ReviewAPITests(ReviewAPITestCase):
    def test_review_list_is_public(self):
        review = self.create_review()

        response = self.client.get(
            self.review_list_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        review_ids = {
            item["id"]
            for item in self.response_items(response)
        }

        self.assertIn(
            review.pk,
            review_ids,
        )

    def test_review_list_can_be_filtered_by_listing(
        self,
    ):
        first_review = self.create_review()

        second_listing = self.create_listing(
            owner=self.other_user,
            title="Second review apartment",
        )
        second_booking = self.create_booking(
            listing=second_listing,
        )
        second_review = self.create_review(
            booking=second_booking,
            rating=3,
        )

        response = self.client.get(
            self.review_list_url,
            {"listing": self.listing.pk},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        review_ids = {
            item["id"]
            for item in self.response_items(response)
        }

        self.assertIn(
            first_review.pk,
            review_ids,
        )
        self.assertNotIn(
            second_review.pk,
            review_ids,
        )

    def test_invalid_listing_filter_is_rejected(self):
        response = self.client.get(
            self.review_list_url,
            {"listing": "invalid"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "listing",
            response.data,
        )

    def test_unauthenticated_user_cannot_create_review(
        self,
    ):
        response = self.client.post(
            self.review_list_url,
            self.review_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            Review.objects.count(),
            0,
        )

    def test_booking_guest_can_create_review(self):
        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            self.review_list_url,
            self.review_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        review = Review.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            review.booking,
            self.booking,
        )
        self.assertEqual(
            review.rating,
            5,
        )

    def test_other_user_cannot_create_review(self):
        self.client.force_authenticate(
            user=self.other_user
        )

        response = self.client.post(
            self.review_list_url,
            self.review_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            Review.objects.count(),
            0,
        )

    def test_pending_booking_cannot_be_reviewed(self):
        booking = self.create_booking(
            booking_status=Booking.Status.PENDING
        )

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            self.review_list_url,
            self.review_payload(
                booking=booking.pk
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "booking",
            response.data,
        )

    def test_future_stay_cannot_be_reviewed(self):
        check_in = (
            timezone.now()
            + timedelta(days=3)
        )
        check_out = (
            timezone.now()
            + timedelta(days=5)
        )

        booking = self.create_booking(
            booking_status=Booking.Status.COMPLETED,
            check_in=check_in,
            check_out=check_out,
        )

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            self.review_list_url,
            self.review_payload(
                booking=booking.pk
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "booking",
            response.data,
        )

    def test_listing_owner_cannot_review_own_listing(
        self,
    ):
        booking = self.create_booking(
            guest=self.owner,
        )

        self.client.force_authenticate(
            user=self.owner
        )

        response = self.client.post(
            self.review_list_url,
            self.review_payload(
                booking=booking.pk
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "booking",
            response.data,
        )

    def test_review_requires_text(self):
        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            self.review_list_url,
            self.review_payload(
                liked="",
                disliked="",
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

    def test_rating_outside_range_is_rejected(self):
        self.client.force_authenticate(
            user=self.guest
        )

        for rating in (0, 6):
            with self.subTest(rating=rating):
                response = self.client.post(
                    self.review_list_url,
                    self.review_payload(
                        rating=rating
                    ),
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(
                    "rating",
                    response.data,
                )

        self.assertEqual(
            Review.objects.count(),
            0,
        )

    def test_rating_is_optional(self):
        self.client.force_authenticate(
            user=self.guest
        )

        payload = self.review_payload()
        payload.pop("rating")

        response = self.client.post(
            self.review_list_url,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        review = Review.objects.get(
            pk=response.data["id"]
        )

        self.assertIsNone(
            review.rating
        )

    def test_review_text_is_trimmed(self):
        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            self.review_list_url,
            self.review_payload(
                liked="  Great stay.  ",
                disliked="   ",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        review = Review.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            review.liked,
            "Great stay.",
        )
        self.assertEqual(
            review.disliked,
            "",
        )

    def test_review_word_limit_is_enforced(self):
        text = " ".join(
            ["x"] * 351
        )

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            self.review_list_url,
            self.review_payload(
                liked=text
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "liked",
            response.data,
        )

    def test_booking_can_have_only_one_review(self):
        self.create_review()

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            self.review_list_url,
            self.review_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn(
            "booking",
            response.data,
        )
        self.assertEqual(
            Review.objects.count(),
            1,
        )

    def test_author_can_update_review(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.patch(
            reverse(
                "reviews:review-detail",
                kwargs={"pk": review.pk},
            ),
            {
                "rating": 4,
                "liked": "Updated review text.",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        review.refresh_from_db()

        self.assertEqual(
            review.rating,
            4,
        )
        self.assertEqual(
            review.liked,
            "Updated review text.",
        )

    def test_non_author_cannot_update_review(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.other_user
        )

        response = self.client.patch(
            reverse(
                "reviews:review-detail",
                kwargs={"pk": review.pk},
            ),
            {
                "rating": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        review.refresh_from_db()

        self.assertEqual(
            review.rating,
            5,
        )

    def test_update_cannot_remove_all_text(self):
        review = self.create_review(
            liked="Original text.",
            disliked="",
        )

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.patch(
            reverse(
                "reviews:review-detail",
                kwargs={"pk": review.pk},
            ),
            {
                "liked": "",
                "disliked": "",
            },
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

        review.refresh_from_db()

        self.assertEqual(
            review.liked,
            "Original text.",
        )

    def test_author_can_delete_review(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.delete(
            reverse(
                "reviews:review-detail",
                kwargs={"pk": review.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Review.objects.filter(
                pk=review.pk
            ).exists()
        )

    def test_non_author_cannot_delete_review(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.other_user
        )

        response = self.client.delete(
            reverse(
                "reviews:review-detail",
                kwargs={"pk": review.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertTrue(
            Review.objects.filter(
                pk=review.pk
            ).exists()
        )

    def test_listing_rating_and_review_count_are_calculated(
        self,
    ):
        self.create_review(
            rating=3,
            liked="First review.",
        )

        second_guest = User.objects.create_user(
            email="review.second@example.com",
            password="StrongPass123!",
            first_name="Second",
            last_name="Guest",
            phone_number="+491700000404",
        )
        second_booking = self.create_booking(
            guest=second_guest,
        )
        self.create_review(
            booking=second_booking,
            rating=5,
            liked="Second review.",
        )

        response = self.client.get(
            reverse(
                "listings:listing-detail",
                kwargs={"pk": self.listing.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["rating"],
            4.0,
        )
        self.assertEqual(
            response.data["reviews_count"],
            2,
        )


class ReviewImageAPITests(ReviewAPITestCase):
    def image_detail_url(self, image):
        return reverse(
            "reviews:review-image-detail",
            kwargs={"pk": image.pk},
        )

    def test_review_author_can_upload_image(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.guest
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                response = self.client.post(
                    self.review_image_url,
                    {
                        "review": review.pk,
                        "image": self.make_image(),
                    },
                    format="multipart",
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        image = ReviewImage.objects.get(
            pk=response.data["id"]
        )

        self.assertEqual(
            image.review,
            review,
        )

    def test_unauthenticated_user_cannot_upload_image(
        self,
    ):
        review = self.create_review()

        response = self.client.post(
            self.review_image_url,
            {
                "review": review.pk,
                "image": self.make_image(),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            ReviewImage.objects.count(),
            0,
        )

    def test_non_author_cannot_upload_image(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.other_user
        )

        response = self.client.post(
            self.review_image_url,
            {
                "review": review.pk,
                "image": self.make_image(),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            ReviewImage.objects.count(),
            0,
        )

    def test_fourth_review_image_is_rejected(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.guest
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                for index in range(1, 4):
                    ReviewImage.objects.create(
                        review=review,
                        image=self.make_image(
                            f"review-{index}.png"
                        ),
                    )

                response = self.client.post(
                    self.review_image_url,
                    {
                        "review": review.pk,
                        "image": self.make_image(
                            "review-4.png"
                        ),
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
            review.images.count(),
            3,
        )

    def test_invalid_image_extension_is_rejected(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            self.review_image_url,
            {
                "review": review.pk,
                "image": self.make_image(
                    "review.gif"
                ),
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

    def test_oversized_image_is_rejected(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.guest
        )

        response = self.client.post(
            self.review_image_url,
            {
                "review": review.pk,
                "image": self.make_image(
                    size=MAX_REVIEW_IMAGE_SIZE + 1
                ),
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

    def test_review_author_can_delete_image(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.guest
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                image = ReviewImage.objects.create(
                    review=review,
                    image=self.make_image(),
                )

                response = self.client.delete(
                    self.image_detail_url(image)
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            ReviewImage.objects.filter(
                pk=image.pk
            ).exists()
        )

    def test_non_author_cannot_delete_image(self):
        review = self.create_review()

        self.client.force_authenticate(
            user=self.other_user
        )

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                image = ReviewImage.objects.create(
                    review=review,
                    image=self.make_image(),
                )

                response = self.client.delete(
                    self.image_detail_url(image)
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertTrue(
            ReviewImage.objects.filter(
                pk=image.pk
            ).exists()
        )

    def test_review_image_detail_is_public(self):
        review = self.create_review()

        with tempfile.TemporaryDirectory() as media_root:
            with self.settings(
                MEDIA_ROOT=media_root
            ):
                image = ReviewImage.objects.create(
                    review=review,
                    image=self.make_image(),
                )

                response = self.client.get(
                    self.image_detail_url(image)
                )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            image.pk,
        )