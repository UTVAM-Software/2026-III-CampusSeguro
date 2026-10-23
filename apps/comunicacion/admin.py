"""Los modelos de esta app en el panel /admin/ de Django (respaldo de las pantallas de la app)."""

from django.contrib import admin

from .models import Aviso, Notificacion

admin.site.register([Aviso, Notificacion])
