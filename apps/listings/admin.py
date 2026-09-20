from django.contrib import admin

from .models import Listing, ListingImage, Amenity, Favorite


admin.site.register(Listing)
admin.site.register(ListingImage)
admin.site.register(Amenity)
admin.site.register(Favorite)