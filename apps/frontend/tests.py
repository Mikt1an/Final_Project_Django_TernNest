from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_home_page_uses_expected_template(self):
        response = self.client.get(
            reverse("frontend:home")
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertTemplateUsed(
            response,
            "frontend/home.html",
        )

    def test_home_page_contains_filter_controls(self):
        response = self.client.get(
            reverse("frontend:home")
        )

        self.assertContains(
            response,
            'id="listing-search-form"',
        )
        self.assertContains(
            response,
            'name="city"',
        )
        self.assertContains(
            response,
            'name="check_in"',
        )
        self.assertContains(
            response,
            'name="check_out"',
        )
        self.assertContains(
            response,
            'name="ordering"',
        )
        self.assertContains(
            response,
            'id="amenities-filter-options"',
        )
        self.assertContains(
            response,
            "frontend/js/home.js",
        )