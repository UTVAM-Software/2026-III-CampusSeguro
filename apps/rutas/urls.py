from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import ConsultarRutaView

urlpatterns = [
    # Va por GET y no por POST: asi una consulta se puede compartir, guardar
    # y deshacer con el boton de atras. No cambia nada en la base.
    path('rutas/', login_required(ConsultarRutaView.as_view()), name='ruta-consultar'),
]
