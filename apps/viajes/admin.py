"""Los modelos de esta app en el panel /admin/ de Django (respaldo de las pantallas de la app)."""

from django.contrib import admin

from .models import Viaje, ViajeAcompanante, UbicacionViaje, DestinoGuardado

admin.site.register([Viaje, ViajeAcompanante, UbicacionViaje, DestinoGuardado])
