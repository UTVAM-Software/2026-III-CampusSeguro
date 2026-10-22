from django.urls import path

from .views import (
    ViajeListView, ViajeDetailView, ViajeCreateView,
    ViajeUpdateView, ViajeDeleteView,
    LlegueBienView, CancelarViajeView, ResponderInvitacionView,
    GuardarPosicionView, UltimaPosicionView,
    DestinoListView, DestinoDetailView, DestinoCreateView, DestinoUpdateView, DestinoDeleteView,
    AcompananteListView, AcompananteDetailView, AcompananteCreateView,
    AcompananteUpdateView, AcompananteDeleteView,
    UbicacionListView, UbicacionDetailView, UbicacionCreateView,
    UbicacionUpdateView, UbicacionDeleteView,
)
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # Viajes
    path('viajes/', login_required(ViajeListView.as_view()), name='viaje-list'),
    path('viajes/<int:pk>/', login_required(ViajeDetailView.as_view()), name='viaje-detail'),
    path('viajes/create/', login_required(ViajeCreateView.as_view()), name='viaje-create'),
    path('viajes/<int:pk>/update/', login_required(ViajeUpdateView.as_view()), name='viaje-update'),
    path('viajes/<int:pk>/delete/', login_required(ViajeDeleteView.as_view()), name='viaje-delete'),

    # Cerrar un viaje. Por POST: cambian datos, y un enlace lo dispararia
    # cualquier cosa que vaya precargando enlaces.
    path('viajes/<int:pk>/llegue/', login_required(LlegueBienView.as_view()), name='viaje-llegue'),
    path('viajes/<int:pk>/cancelar/', login_required(CancelarViajeView.as_view()), name='viaje-cancelar'),

    # Compartir la posicion mientras dura el viaje, y consultarla.
    path('viajes/<int:pk>/posicion/', login_required(GuardarPosicionView.as_view()), name='viaje-posicion'),
    path('viajes/<int:pk>/ultima/', login_required(UltimaPosicionView.as_view()), name='viaje-ultima'),

    # Acompañantes de viaje
    path('acompanantes/', login_required(AcompananteListView.as_view()), name='acompanante-list'),
    path('acompanantes/<int:pk>/', login_required(AcompananteDetailView.as_view()), name='acompanante-detail'),
    path('acompanantes/create/', login_required(AcompananteCreateView.as_view()), name='acompanante-create'),
    path('acompanantes/<int:pk>/update/', login_required(AcompananteUpdateView.as_view()), name='acompanante-update'),
    path('acompanantes/<int:pk>/delete/', login_required(AcompananteDeleteView.as_view()), name='acompanante-delete'),

    # Responder una invitacion. La unica que filtra por `acompanante`: es la
    # persona invitada quien decide, no quien la invito.
    path('acompanantes/<int:pk>/responder/', login_required(ResponderInvitacionView.as_view()), name='invitacion-responder'),

    # Destinos guardados: los sitios a los que vas siempre, para no volver
    # a buscarlos cada vez.
    path('destinos/', login_required(DestinoListView.as_view()), name='destino-list'),
    path('destinos/<int:pk>/', login_required(DestinoDetailView.as_view()), name='destino-detail'),
    path('destinos/create/', login_required(DestinoCreateView.as_view()), name='destino-create'),
    path('destinos/<int:pk>/update/', login_required(DestinoUpdateView.as_view()), name='destino-update'),
    path('destinos/<int:pk>/delete/', login_required(DestinoDeleteView.as_view()), name='destino-delete'),

    # Ubicaciones de viaje
    path('ubicaciones/', login_required(UbicacionListView.as_view()), name='ubicacion-list'),
    path('ubicaciones/<int:pk>/', login_required(UbicacionDetailView.as_view()), name='ubicacion-detail'),
    path('ubicaciones/create/', login_required(UbicacionCreateView.as_view()), name='ubicacion-create'),
    path('ubicaciones/<int:pk>/update/', login_required(UbicacionUpdateView.as_view()), name='ubicacion-update'),
    path('ubicaciones/<int:pk>/delete/', login_required(UbicacionDeleteView.as_view()), name='ubicacion-delete'),
]