from django.contrib import admin

from .models import Booking, BlockedPeriod


admin.site.register(Booking)
admin.site.register(BlockedPeriod)