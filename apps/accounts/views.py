from rest_framework.generics import (
    CreateAPIView,
    RetrieveAPIView,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)

from apps.accounts.models import User
from apps.accounts.serializers import (
    UserDetailSerializer,
    UserRegistrationSerializer,
)

from django.shortcuts import render

# Create your views here.
class UserRegistrationView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = (AllowAny,)


class CurrentUserView(RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user