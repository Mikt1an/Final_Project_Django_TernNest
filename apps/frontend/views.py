from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = "frontend/home.html"


class LoginPageView(TemplateView):
    template_name = "frontend/login.html"


class RegisterPageView(TemplateView):
    template_name = "frontend/register.html"


class DashboardPageView(TemplateView):
    template_name = "frontend/dashboard.html"


class FavoritesPageView(TemplateView):
    template_name = "frontend/favorites.html"


class ListingCreatePageView(TemplateView):
    template_name = "frontend/listing_create.html"


class ListingDetailPageView(TemplateView):
    template_name = "frontend/listing_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["listing_id"] = self.kwargs["pk"]

        return context


class ListingEditPageView(TemplateView):
    template_name = "frontend/listing_edit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["listing_id"] = self.kwargs["pk"]

        return context


class ListingAvailabilityPageView(TemplateView):
    template_name = ("frontend/listing_availability.html")

    def get_context_data(self, **kwargs,):
        context = super().get_context_data(**kwargs)

        context["listing_id"] = (self.kwargs["pk"])

        return context


class ReviewCreatePageView(TemplateView):
    template_name = "frontend/review_create.html"

    def get_context_data(self, **kwargs,):
        context = super().get_context_data(**kwargs)

        context["booking_id"] = (self.kwargs["booking_id"])

        return context


class AccountSettingsPageView(TemplateView):
    template_name = "frontend/account_settings.html"