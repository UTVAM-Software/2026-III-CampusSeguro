from django.urls import path

from .views import (
    CampusListView, CampusDetailView, CampusCreateView,
    CampusUpdateView, CampusDeleteView,
    PuntoListView, PuntoDetailView, PuntoCreateView,
    PuntoUpdateView, PuntoDeleteView,
    AvisarDePuntoView, CorreccionListView, AtenderCorreccionView,
    CorreccionCreateView, CorreccionUpdateView,
    CorreccionDetailView, CorreccionDeleteView,
)
from django.contrib.auth.decorators import login_required



urlpatterns = [
    path('campus/', login_required(CampusListView.as_view()), name='campus-list'),
    path('campus/<int:pk>/', login_required(CampusDetailView.as_view()), name='campus-detail'),
    path('campus/create/', login_required(CampusCreateView.as_view()), name='campus-create'),
    path('campus/<int:pk>/update/', login_required(CampusUpdateView.as_view()), name='campus-update'),
    path('campus/<int:pk>/delete/', login_required(CampusDeleteView.as_view()), name='campus-delete'),

    path('puntos-apoyo/', login_required(PuntoListView.as_view()), name='punto-list'),
    path('puntos-apoyo/<int:pk>/', login_required(PuntoDetailView.as_view()), name='punto-detail'),
    path('puntos-apoyo/create/', login_required(PuntoCreateView.as_view()), name='punto-create'),
    path('puntos-apoyo/<int:pk>/update/', login_required(PuntoUpdateView.as_view()), name='punto-update'),
    path('puntos-apoyo/<int:pk>/delete/', login_required(PuntoDeleteView.as_view()), name='punto-delete'),

    # La comunidad avisa de que un punto esta mal; la administracion corrige.
    # Avisar va por POST -crea algo- y lo puede hacer cualquiera de su campus.
    path('puntos-apoyo/<int:pk>/avisar/', login_required(AvisarDePuntoView.as_view()), name='punto-avisar'),
    path('correcciones/', login_required(CorreccionListView.as_view()), name='correccion-list'),
    path('correcciones/<int:pk>/atender/', login_required(AtenderCorreccionView.as_view()), name='correccion-atender'),
    path('correcciones/create/', login_required(CorreccionCreateView.as_view()), name='correccion-create'),
    path('correcciones/<int:pk>/', login_required(CorreccionDetailView.as_view()), name='correccion-detail'),
    path('correcciones/<int:pk>/update/', login_required(CorreccionUpdateView.as_view()), name='correccion-update'),
    path('correcciones/<int:pk>/delete/', login_required(CorreccionDeleteView.as_view()), name='correccion-delete'),
]