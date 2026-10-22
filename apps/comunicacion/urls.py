from django.urls import path

from .views import (
    AvisoListView, AvisoDetailView, AvisoCreateView,
    AvisoUpdateView, AvisoDeleteView,
    NotificacionListView, NotificacionDetailView, NotificacionCreateView,
    NotificacionUpdateView, NotificacionDeleteView,
    NotificacionMarcarLeidaView,
)
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # Avisos
    path('avisos/', login_required(AvisoListView.as_view()), name='aviso-list'),
    path('avisos/<int:pk>/', login_required(AvisoDetailView.as_view()), name='aviso-detail'),
    path('avisos/create/', login_required(AvisoCreateView.as_view()), name='aviso-create'),
    path('avisos/<int:pk>/update/', login_required(AvisoUpdateView.as_view()), name='aviso-update'),
    path('avisos/<int:pk>/delete/', login_required(AvisoDeleteView.as_view()), name='aviso-delete'),

    # Notificaciones
    path('notificaciones/', login_required(NotificacionListView.as_view()), name='notificacion-list'),
    path('notificaciones/<int:pk>/', login_required(NotificacionDetailView.as_view()), name='notificacion-detail'),
    path('notificaciones/create/', login_required(NotificacionCreateView.as_view()), name='notificacion-create'),
    path('notificaciones/<int:pk>/update/', login_required(NotificacionUpdateView.as_view()), name='notificacion-update'),
    path('notificaciones/<int:pk>/delete/', login_required(NotificacionDeleteView.as_view()), name='notificacion-delete'),
    path('notificaciones/<int:pk>/leida/', login_required(NotificacionMarcarLeidaView.as_view()), name='notificacion-leida'),
]