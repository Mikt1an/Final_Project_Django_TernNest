import random

from datetime import (
    datetime,
    time,
    timedelta,
)

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from faker import Faker

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.listings.models import (
    Amenity,
    Listing,
    ListingImage,
)
from apps.reviews.models import Review


fake = Faker()

Faker.seed(42)
random.seed(42)


DEMO_PASSWORD = "DemoPass123!"

DEMO_OWNER_COUNT = 5
DEMO_GUEST_COUNT = 12


AMENITIES = [
    "Wi-Fi",
    "Kitchen",
    "Heating",
    "Air conditioning",
    "TV",
    "Washing machine",
    "Dishwasher",
    "Coffee maker",
    "Workspace",
    "Parking",
    "Balcony",
    "Elevator",
    "Hair dryer",
    "Iron",
    "Pet friendly",
]


LIKED_REVIEWS = [
    (
        "Very clean apartment with a comfortable bed "
        "and everything we needed."
    ),
    (
        "Great location and the apartment was exactly "
        "as described."
    ),
    (
        "The property was quiet, comfortable and very "
        "well maintained."
    ),
    (
        "Excellent stay with an easy check-in and a "
        "comfortable living area."
    ),
    (
        "The apartment was bright, clean and close to "
        "public transport."
    ),
    (
        "We really enjoyed the neighbourhood and the "
        "property felt very welcoming."
    ),
    (
        "The kitchen was well equipped and the whole "
        "apartment was very clean."
    ),
    (
        "Comfortable property with plenty of space and "
        "a convenient location."
    ),
    (
        "Everything was organised well and the property "
        "matched the description."
    ),
    (
        "A pleasant and relaxing stay with everything "
        "needed for a short trip."
    ),
    (
        "The apartment was spacious and the beds were "
        "very comfortable."
    ),
    (
        "Very convenient location and a smooth arrival "
        "experience."
    ),
]


DISLIKED_REVIEWS = [
    "",
    "",
    "",
    (
        "There was some street noise in the morning."
    ),
    (
        "The Wi-Fi could have been a little faster."
    ),
    (
        "Parking nearby was slightly difficult to find."
    ),
    (
        "The bathroom was smaller than expected."
    ),
    (
        "The kitchen could use a few more utensils."
    ),
    (
        "The building was a little noisy in the evening."
    ),
    (
        "The room became quite warm during the afternoon."
    ),
]


LISTINGS = [
    {
        "title": "Sunny Apartment near English Garden",
        "description": (
            "Bright and comfortable apartment in a quiet neighbourhood "
            "near the English Garden. Features two bedrooms, a spacious "
            "living area and a fully equipped kitchen."
        ),
        "listing_type": "apartment",
        "country": "Germany",
        "city": "Munich",
        "address": "12 Lerchenweg",
        "price_per_night": "145.00",
        "max_guests": 4,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "title": "Cozy Studio in Schwabing",
        "description": (
            "Cozy modern studio in the lively Schwabing district. "
            "A compact and comfortable place for couples or solo travellers."
        ),
        "listing_type": "studio",
        "country": "Germany",
        "city": "Munich",
        "address": "28 Falkenstraße",
        "price_per_night": "89.00",
        "max_guests": 2,
        "bedrooms": 0,
        "beds": 1,
        "bathrooms": 1,
    },
    {
        "title": "Modern Loft near Isar River",
        "description": (
            "Stylish loft close to the Isar River with large windows "
            "and a bright open living space."
        ),
        "listing_type": "apartment",
        "country": "Germany",
        "city": "Munich",
        "address": "7 Uferweg",
        "price_per_night": "125.00",
        "max_guests": 3,
        "bedrooms": 1,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "title": "Quiet Family Apartment in Sendling",
        "description": (
            "Spacious apartment in a quiet residential area of Sendling. "
            "Suitable for families and longer stays."
        ),
        "listing_type": "apartment",
        "country": "Germany",
        "city": "Munich",
        "address": "41 Lindenstraße",
        "price_per_night": "165.00",
        "max_guests": 5,
        "bedrooms": 2,
        "beds": 3,
        "bathrooms": 1,
    },
    {
        "title": "Small House with Garden",
        "description": (
            "Comfortable private house with a small garden and outdoor "
            "seating area. Perfect for families or groups."
        ),
        "listing_type": "house",
        "country": "Germany",
        "city": "Munich",
        "address": "16 Gartenweg",
        "price_per_night": "210.00",
        "max_guests": 6,
        "bedrooms": 3,
        "beds": 4,
        "bathrooms": 2,
    },
    {
        "title": "Old Town Balcony Apartment",
        "description": (
            "Comfortable apartment close to Nuremberg's historic centre "
            "with a quiet balcony."
        ),
        "listing_type": "apartment",
        "country": "Germany",
        "city": "Nuremberg",
        "address": "23 Burgstraße",
        "price_per_night": "115.00",
        "max_guests": 4,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "title": "Minimal Studio near Central Station",
        "description": (
            "Simple and practical studio close to public transport "
            "and Stuttgart city centre."
        ),
        "listing_type": "studio",
        "country": "Germany",
        "city": "Stuttgart",
        "address": "9 Rosenweg",
        "price_per_night": "82.00",
        "max_guests": 2,
        "bedrooms": 0,
        "beds": 1,
        "bathrooms": 1,
    },
    {
        "title": "Riverside Apartment in Cologne",
        "description": (
            "Bright apartment located near the Rhine with two bedrooms "
            "and a spacious living room."
        ),
        "listing_type": "apartment",
        "country": "Germany",
        "city": "Cologne",
        "address": "34 Rheinweg",
        "price_per_night": "135.00",
        "max_guests": 4,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "title": "Creative Loft in Kreuzberg",
        "description": (
            "Modern loft with an open-plan interior inspired by Berlin's "
            "creative atmosphere."
        ),
        "listing_type": "apartment",
        "country": "Germany",
        "city": "Berlin",
        "address": "52 Atelierstraße",
        "price_per_night": "152.00",
        "max_guests": 4,
        "bedrooms": 1,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "title": "Compact Berlin City Studio",
        "description": (
            "Compact studio with a kitchenette and comfortable sleeping "
            "area, ideal for exploring Berlin."
        ),
        "listing_type": "studio",
        "country": "Germany",
        "city": "Berlin",
        "address": "18 Morgenstraße",
        "price_per_night": "76.00",
        "max_guests": 2,
        "bedrooms": 0,
        "beds": 1,
        "bathrooms": 1,
    },
    {
        "title": "Hamburg Harbour Apartment",
        "description": (
            "Spacious apartment inspired by Hamburg's harbour atmosphere "
            "with two bedrooms and two bathrooms."
        ),
        "listing_type": "apartment",
        "country": "Germany",
        "city": "Hamburg",
        "address": "11 Hafenblick",
        "price_per_night": "158.00",
        "max_guests": 4,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 2,
    },
    {
        "title": "Family House near the Lake",
        "description": (
            "Large family house in a peaceful residential area with "
            "plenty of room for groups and families."
        ),
        "listing_type": "house",
        "country": "Germany",
        "city": "Hamburg",
        "address": "6 Seegarten",
        "price_per_night": "225.00",
        "max_guests": 7,
        "bedrooms": 3,
        "beds": 5,
        "bathrooms": 2,
    },
    {
        "title": "Barcelona Beach Apartment",
        "description": (
            "Bright Mediterranean apartment within walking distance "
            "of the beach with a small balcony."
        ),
        "listing_type": "apartment",
        "country": "Spain",
        "city": "Barcelona",
        "address": "27 Carrer del Mar",
        "price_per_night": "175.00",
        "max_guests": 4,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "title": "Gothic Quarter Studio",
        "description": (
            "Charming studio close to Barcelona's historic centre, "
            "ideal for couples and solo travellers."
        ),
        "listing_type": "studio",
        "country": "Spain",
        "city": "Barcelona",
        "address": "14 Carrer de la Lluna",
        "price_per_night": "108.00",
        "max_guests": 2,
        "bedrooms": 0,
        "beds": 1,
        "bathrooms": 1,
    },
    {
        "title": "Mediterranean Family House",
        "description": (
            "Relaxed Mediterranean house with three bedrooms "
            "and a small private terrace."
        ),
        "listing_type": "house",
        "country": "Spain",
        "city": "Valencia",
        "address": "31 Calle del Sol",
        "price_per_night": "195.00",
        "max_guests": 6,
        "bedrooms": 3,
        "beds": 4,
        "bathrooms": 2,
    },
    {
        "title": "Vienna Classic Apartment",
        "description": (
            "Elegant apartment combining a classic interior with "
            "modern amenities and a spacious living room."
        ),
        "listing_type": "apartment",
        "country": "Austria",
        "city": "Vienna",
        "address": "19 Blumenweg",
        "price_per_night": "138.00",
        "max_guests": 4,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "title": "Prague Old Town Hideaway",
        "description": (
            "Comfortable apartment close to Prague's historic centre "
            "with a cosy and quiet interior."
        ),
        "listing_type": "apartment",
        "country": "Czech Republic",
        "city": "Prague",
        "address": "8 Javorová Street",
        "price_per_night": "105.00",
        "max_guests": 3,
        "bedrooms": 1,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "title": "Alpine House with Mountain View",
        "description": (
            "Spacious Alpine-style house with mountain views, "
            "four bedrooms and a large shared living area."
        ),
        "listing_type": "house",
        "country": "Austria",
        "city": "Innsbruck",
        "address": "22 Alpenweg",
        "price_per_night": "240.00",
        "max_guests": 8,
        "bedrooms": 4,
        "beds": 5,
        "bathrooms": 2,
    },
    {
        "title": "Lake View Studio in Salzburg",
        "description": (
            "Bright compact studio with a peaceful atmosphere and "
            "easy access to Salzburg's historic centre."
        ),
        "listing_type": "studio",
        "country": "Austria",
        "city": "Salzburg",
        "address": "15 Seeweg",
        "price_per_night": "112.00",
        "max_guests": 2,
        "bedrooms": 0,
        "beds": 1,
        "bathrooms": 1,
    },
]


class Command(BaseCommand):
    help = "Create demo data for TernNest"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Creating TernNest demo data..."
            )
        )

        owners = self.create_owners()
        guests = self.create_guests()

        amenities = self.create_amenities()

        listings = self.create_listings(
            owners=owners,
            amenities=amenities,
        )

        self.clear_demo_booking_data(
            guests=guests,
            listings=listings,
        )

        statistics = (
            self.create_bookings_and_reviews(
                guests=guests,
                listings=listings,
            )
        )

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "---------------------------------------"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "TernNest demo data created successfully."
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Listings: {len(listings)}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed bookings: "
                f"{statistics['completed']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Reviews: {statistics['reviews']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Confirmed bookings: "
                f"{statistics['confirmed']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Pending bookings: "
                f"{statistics['pending']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Cancelled bookings: "
                f"{statistics['cancelled']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "---------------------------------------"
            )
        )

        self.stdout.write("")

        self.stdout.write(
            "Demo login examples:"
        )

        self.stdout.write(
            f"  owner1@ternnest.test / "
            f"{DEMO_PASSWORD}"
        )

        self.stdout.write(
            f"  guest1@ternnest.test / "
            f"{DEMO_PASSWORD}"
        )

    # =========================================================
    # USERS
    # =========================================================

    def create_owners(self):
        self.stdout.write(
            "\nCreating demo owners..."
        )

        owners = []

        for number in range(
            1,
            DEMO_OWNER_COUNT + 1,
        ):
            email = (
                f"owner{number}@ternnest.test"
            )

            user, created = (
                User.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name":
                            fake.first_name(),
                        "last_name":
                            fake.last_name(),
                        "phone_number":
                            (
                                "+49151100000"
                                f"{number:02d}"
                            ),
                        "is_verified":
                            True,
                    },
                )
            )

            if created:
                user.set_password(
                    DEMO_PASSWORD
                )

                user.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  + {user.email}"
                    )
                )

            else:
                self.stdout.write(
                    f"  = {user.email} "
                    f"already exists"
                )

            owners.append(
                user
            )

        return owners

    def create_guests(self):
        self.stdout.write(
            "\nCreating demo guests..."
        )

        guests = []

        for number in range(
            1,
            DEMO_GUEST_COUNT + 1,
        ):
            email = (
                f"guest{number}"
                f"@ternnest.test"
            )

            user, created = (
                User.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name":
                            fake.first_name(),
                        "last_name":
                            fake.last_name(),
                        "phone_number":
                            (
                                "+49152200000"
                                f"{number:02d}"
                            ),
                        "is_verified":
                            True,
                    },
                )
            )

            if created:
                user.set_password(
                    DEMO_PASSWORD
                )

                user.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  + {user.email}"
                    )
                )

            else:
                self.stdout.write(
                    f"  = {user.email} "
                    f"already exists"
                )

            guests.append(
                user
            )

        return guests

    # =========================================================
    # AMENITIES
    # =========================================================

    def create_amenities(self):
        self.stdout.write(
            "\nCreating amenities..."
        )

        amenities = []

        for amenity_name in AMENITIES:
            amenity, created = (
                Amenity.objects.get_or_create(
                    name=amenity_name
                )
            )

            amenities.append(
                amenity
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  + {amenity.name}"
                    )
                )

        return amenities

    # =========================================================
    # LISTINGS
    # =========================================================

    def create_listings(
        self,
        owners,
        amenities,
    ):
        self.stdout.write(
            "\nCreating listings..."
        )

        listings = []

        for index, data in enumerate(
            LISTINGS,
            start=1,
        ):
            owner = owners[
                (index - 1)
                % len(owners)
            ]

            listing, created = (
                Listing.objects.update_or_create(
                    title=data["title"],
                    defaults={
                        "owner":
                            owner,
                        "description":
                            data["description"],
                        "listing_type":
                            data["listing_type"],
                        "country":
                            data["country"],
                        "city":
                            data["city"],
                        "address":
                            data["address"],
                        "earliest_check_in_time":
                            time(15, 0),
                        "latest_check_out_time":
                            time(11, 0),
                        "price_per_night":
                            Decimal(
                                data["price_per_night"]
                            ),
                        "max_guests":
                            data["max_guests"],
                        "bedrooms":
                            data["bedrooms"],
                        "beds":
                            data["beds"],
                        "bathrooms":
                            data["bathrooms"],
                        "is_active":
                            True,
                    },
                )
            )

            amenity_count = (
                random.randint(
                    4,
                    8,
                )
            )

            listing.amenities.set(
                random.sample(
                    amenities,
                    k=min(
                        amenity_count,
                        len(amenities),
                    ),
                )
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  + [{index}] "
                        f"{listing.title}"
                    )
                )

            else:
                self.stdout.write(
                    f"  = [{index}] "
                    f"{listing.title} "
                    f"updated"
                )

            self.add_images(
                listing=listing,
                folder_number=index,
            )

            listings.append(
                listing
            )

        return listings

    # =========================================================
    # IMAGES
    # =========================================================

    def add_images(
        self,
        listing,
        folder_number,
    ):
        """
        kv1 -> Listing 1
        kv2 -> Listing 2
        ...
        kv19 -> Listing 19
        """

        if listing.images.exists():
            self.stdout.write(
                f"      Images already exist: "
                f"{listing.images.count()}"
            )

            return

        folder = (
            Path(settings.BASE_DIR)
            / "seed_data"
            / "listings"
            / f"kv{folder_number}"
        )

        if not folder.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Folder not found: "
                    f"{folder}"
                )
            )

            return

        allowed_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }

        image_paths = sorted(
            path
            for path in folder.iterdir()
            if (
                path.is_file()
                and
                path.suffix.lower()
                in allowed_extensions
            )
        )

        image_paths = (
            image_paths[:4]
        )

        if not image_paths:
            self.stdout.write(
                self.style.WARNING(
                    f"No images found in "
                    f"kv{folder_number}"
                )
            )

            return

        for (
            image_number,
            image_path,
        ) in enumerate(
            image_paths,
            start=1,
        ):
            listing_image = (
                ListingImage(
                    listing=listing,
                    is_main=(
                        image_number == 1
                    ),
                )
            )

            target_name = (
                f"kv{folder_number}_"
                f"{image_path.name}"
            )

            with image_path.open(
                "rb"
            ) as image_file:
                listing_image.image.save(
                    target_name,
                    File(image_file),
                    save=True,
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"      + "
                    f"{image_path.name}"
                )
            )

    # =========================================================
    # DEMO BOOKING CLEANUP
    # =========================================================

    def clear_demo_booking_data(
        self,
        guests,
        listings,
    ):
        """
        Remove only booking/review data generated
        for our demo guest accounts and demo listings.

        Normal users and their bookings are untouched.
        """

        self.stdout.write(
            "\nResetting generated "
            "bookings and reviews..."
        )

        guest_ids = [
            guest.id
            for guest in guests
        ]

        listing_ids = [
            listing.id
            for listing in listings
        ]

        reviews = (
            Review.objects.filter(
                booking__guest_id__in=(
                    guest_ids
                ),
                booking__listing_id__in=(
                    listing_ids
                ),
            )
        )

        review_count = (
            reviews.count()
        )

        reviews.delete()

        bookings = (
            Booking.objects.filter(
                guest_id__in=(
                    guest_ids
                ),
                listing_id__in=(
                    listing_ids
                ),
            )
        )

        booking_count = (
            bookings.count()
        )

        bookings.delete()

        self.stdout.write(
            f"  Removed "
            f"{review_count} demo reviews."
        )

        self.stdout.write(
            f"  Removed "
            f"{booking_count} demo bookings."
        )

    # =========================================================
    # DATE HELPERS
    # =========================================================

    def make_datetime(
        self,
        date_value,
        time_value,
    ):
        value = datetime.combine(
            date_value,
            time_value,
        )

        if settings.USE_TZ:
            value = timezone.make_aware(
                value,
                timezone.get_current_timezone(),
            )

        return value

    # =========================================================
    # BOOKINGS + REVIEWS
    # =========================================================

    def create_bookings_and_reviews(
            self,
            guests,
            listings,
    ):
        self.stdout.write(
            "\nCreating bookings and reviews..."
        )

        rng = random.Random(
            20260919
        )

        today = timezone.localdate()

        statistics = {
            "completed": 0,
            "reviews": 0,
            "confirmed": 0,
            "pending": 0,
            "cancelled": 0,
        }

        # =========================================================
        # PROCESS EVERY LISTING
        # =========================================================

        for listing_index, listing in enumerate(
                listings,
                start=1,
        ):
            self.stdout.write(
                f"\n  [{listing_index}] "
                f"{listing.title}"
            )

            # -----------------------------------------------------
            # COMPLETED BOOKINGS + REVIEWS
            # -----------------------------------------------------

            review_count = rng.randint(
                2,
                5,
            )

            self.stdout.write(
                f"      Creating "
                f"{review_count} reviews..."
            )

            for review_index in range(
                    review_count
            ):
                guest = guests[
                    (
                            listing_index
                            + review_index
                            - 1
                    )
                    % len(guests)
                    ]

                nights = rng.randint(
                    2,
                    5,
                )

                days_ago = (
                        12
                        + review_index * 14
                        + listing_index % 5
                )

                check_out_date = (
                        today
                        - timedelta(
                    days=days_ago
                )
                )

                check_in_date = (
                        check_out_date
                        - timedelta(
                    days=nights
                )
                )

                check_in = self.make_datetime(
                    check_in_date,
                    listing.earliest_check_in_time,
                )

                check_out = self.make_datetime(
                    check_out_date,
                    listing.latest_check_out_time,
                )

                guests_count = rng.randint(
                    1,
                    max(
                        1,
                        listing.max_guests,
                    ),
                )

                price_per_night = Decimal(
                    str(
                        listing.price_per_night
                    )
                )

                total_price = (
                        price_per_night
                        * nights
                )

                booking = Booking.objects.create(
                    guest=guest,
                    listing=listing,
                    check_in=check_in,
                    check_out=check_out,
                    book_days=nights,
                    guests=guests_count,
                    total_price=total_price,
                    status="completed",
                )

                statistics[
                    "completed"
                ] += 1

                rating = rng.choices(
                    population=[
                        1,
                        2,
                        3,
                        4,
                        5,
                    ],
                    weights=[
                        2,
                        4,
                        12,
                        35,
                        47,
                    ],
                    k=1,
                )[0]

                liked = rng.choice(
                    LIKED_REVIEWS
                )

                disliked = rng.choice(
                    DISLIKED_REVIEWS
                )

                review = Review(
                    booking=booking,
                    rating=rating,
                    liked=liked,
                    disliked=disliked,
                )

                review.full_clean()
                review.save()

                statistics[
                    "reviews"
                ] += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"        + Review "
                        f"{review_index + 1}: "
                        f"{rating}/5"
                    )
                )

            # -----------------------------------------------------
            # FUTURE PENDING / CONFIRMED BOOKING
            # -----------------------------------------------------

            if listing_index <= 10:
                future_guest = guests[
                    (
                            listing_index
                            + 4
                    )
                    % len(guests)
                    ]

                future_nights = rng.randint(
                    2,
                    5,
                )

                future_check_in_date = (
                        today
                        + timedelta(
                    days=(
                            6
                            + listing_index * 3
                    )
                )
                )

                future_check_out_date = (
                        future_check_in_date
                        + timedelta(
                    days=future_nights
                )
                )

                future_check_in = (
                    self.make_datetime(
                        future_check_in_date,
                        listing.earliest_check_in_time,
                    )
                )

                future_check_out = (
                    self.make_datetime(
                        future_check_out_date,
                        listing.latest_check_out_time,
                    )
                )

                if (
                        listing_index % 2
                        == 0
                ):
                    future_status = (
                        "pending"
                    )

                else:
                    future_status = (
                        "confirmed"
                    )

                Booking.objects.create(
                    guest=future_guest,
                    listing=listing,
                    check_in=future_check_in,
                    check_out=future_check_out,
                    book_days=future_nights,
                    guests=rng.randint(
                        1,
                        max(
                            1,
                            listing.max_guests,
                        ),
                    ),
                    total_price=(
                            Decimal(
                                str(
                                    listing.price_per_night
                                )
                            )
                            * future_nights
                    ),
                    status=future_status,
                )

                statistics[
                    future_status
                ] += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"      + "
                        f"{future_status} booking"
                    )
                )

            # -----------------------------------------------------
            # CANCELLED BOOKING
            # -----------------------------------------------------

            if (
                    listing_index % 3
                    == 0
            ):
                cancelled_guest = guests[
                    (
                            listing_index
                            + 7
                    )
                    % len(guests)
                    ]

                cancelled_nights = (
                    rng.randint(
                        2,
                        4,
                    )
                )

                cancelled_check_in_date = (
                        today
                        + timedelta(
                    days=(
                            35
                            + listing_index
                    )
                )
                )

                cancelled_check_out_date = (
                        cancelled_check_in_date
                        + timedelta(
                    days=(
                        cancelled_nights
                    )
                )
                )

                cancelled_check_in = (
                    self.make_datetime(
                        cancelled_check_in_date,
                        listing.earliest_check_in_time,
                    )
                )

                cancelled_check_out = (
                    self.make_datetime(
                        cancelled_check_out_date,
                        listing.latest_check_out_time,
                    )
                )

                Booking.objects.create(
                    guest=cancelled_guest,
                    listing=listing,
                    check_in=cancelled_check_in,
                    check_out=cancelled_check_out,
                    book_days=cancelled_nights,
                    guests=rng.randint(
                        1,
                        max(
                            1,
                            listing.max_guests,
                        ),
                    ),
                    total_price=(
                            Decimal(
                                str(
                                    listing.price_per_night
                                )
                            )
                            * cancelled_nights
                    ),
                    status="cancelled",
                )

                statistics[
                    "cancelled"
                ] += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        "      + cancelled booking"
                    )
                )

        # =========================================================
        # IMPORTANT:
        # THIS PART MUST BE OUTSIDE THE FOR LOOP ABOVE
        # =========================================================

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                "Booking generation finished:"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"  Completed: "
                f"{statistics['completed']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"  Reviews: "
                f"{statistics['reviews']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"  Confirmed: "
                f"{statistics['confirmed']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"  Pending: "
                f"{statistics['pending']}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"  Cancelled: "
                f"{statistics['cancelled']}"
            )
        )

        return statistics