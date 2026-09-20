from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from apps.listings.models import SearchHistory


User = get_user_model()


class SearchHistoryAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="search.user@example.com",
            password="StrongPass123!",
            first_name="Search",
            last_name="User",
            phone_number="+491700000401",
        )

        self.list_url = reverse(
            "listings:listing-list-create"
        )

        self.popular_url = reverse(
            "listings:popular-search-list"
        )

    def perform_search(self, query):
        return self.client.get(
            self.list_url,
            {
                "search": query,
            },
        )

    def test_authenticated_search_is_recorded(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        response = self.perform_search(
            "Apartment"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        search = SearchHistory.objects.get()

        self.assertEqual(
            search.user,
            self.user,
        )
        self.assertEqual(
            search.searcher_key,
            f"user:{self.user.pk}",
        )
        self.assertEqual(
            search.query,
            "Apartment",
        )
        self.assertEqual(
            search.normalized_query,
            "apartment",
        )

    def test_anonymous_search_is_recorded(
        self,
    ):
        response = self.perform_search(
            "Studio"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        search = SearchHistory.objects.get()

        self.assertIsNone(
            search.user
        )
        self.assertTrue(
            search.searcher_key.startswith(
                "session:"
            )
        )
        self.assertGreater(
            len(search.searcher_key),
            len("session:"),
        )

    def test_empty_search_is_not_recorded(
        self,
    ):
        first_response = self.perform_search(
            ""
        )

        second_response = self.perform_search(
            "     "
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
            SearchHistory.objects.count(),
            0,
        )

    def test_search_query_is_normalized(
        self,
    ):
        response = self.perform_search(
            "  Luxury   APARTMENT  "
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        search = SearchHistory.objects.get()

        self.assertEqual(
            search.query,
            "Luxury APARTMENT",
        )
        self.assertEqual(
            search.normalized_query,
            "luxury apartment",
        )

    def test_repeated_searches_are_recorded_separately(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        first_response = self.perform_search(
            "Munich"
        )

        second_response = self.perform_search(
            "Munich"
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
            SearchHistory.objects.filter(
                normalized_query="munich"
            ).count(),
            2,
        )

    def test_popular_searches_group_normalized_queries(
        self,
    ):
        self.client.force_authenticate(
            user=self.user
        )

        self.perform_search(
            "City Apartment"
        )
        self.perform_search(
            "city   apartment"
        )
        self.perform_search(
            "  CITY APARTMENT  "
        )

        response = self.client.get(
            self.popular_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data,
            [
                {
                    "query": "city apartment",
                    "search_count": 3,
                },
            ],
        )

    def test_popular_searches_are_ordered_by_count(
        self,
    ):
        for _ in range(3):
            self.perform_search(
                "Apartment"
            )

        for _ in range(2):
            self.perform_search(
                "Studio"
            )

        self.perform_search(
            "House"
        )

        response = self.client.get(
            self.popular_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            [
                item["query"]
                for item in response.data
            ],
            [
                "apartment",
                "studio",
                "house",
            ],
        )
        self.assertEqual(
            [
                item["search_count"]
                for item in response.data
            ],
            [
                3,
                2,
                1,
            ],
        )

    def test_popular_searches_are_limited_to_five(
        self,
    ):
        queries = (
            "Apartment",
            "Studio",
            "House",
            "Munich",
            "Berlin",
            "Vienna",
        )

        for query in queries:
            self.perform_search(
                query
            )

        response = self.client.get(
            self.popular_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(response.data),
            5,
        )