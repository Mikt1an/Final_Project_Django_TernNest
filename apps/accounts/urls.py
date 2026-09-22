from django.urls import path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.accounts.views import (
    ChangePasswordView,
    CurrentUserView,
    UserRegistrationView,
    BecomeLandlordView,
)


app_name = "accounts"


urlpatterns = [
    path(
        "register/",
        UserRegistrationView.as_view(),
        name="register",
    ),

    path(
        "login/",
        TokenObtainPairView.as_view(),
        name="login",
    ),

    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),

    path(
        "me/",
        CurrentUserView.as_view(),
        name="current-user",
    ),

    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path(
        "become-landlord/",
        BecomeLandlordView.as_view(),
        name="become-landlord",
    ),
]