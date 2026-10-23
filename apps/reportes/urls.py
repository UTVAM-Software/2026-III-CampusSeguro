from django.urls import path

from .views import (
    ReporteListView, ReporteDetailView, ReporteCreateView,
    ReporteUpdateView, ReporteDeleteView,
    ConfirmacionListView, ConfirmacionDetailView, ConfirmacionCreateView,
    ConfirmacionUpdateView, ConfirmacionDeleteView,
    ReporteConfirmarView,
)
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # Reportes
    path('reportes/', login_required(ReporteListView.as_view()), name='reporte-list'),
    path('reportes/<int:pk>/', login_required(ReporteDetailView.as_view()), name='reporte-detail'),
    path('reportes/create/', login_required(ReporteCreateView.as_view()), name='reporte-create'),
    path('reportes/<int:pk>/update/', login_required(ReporteUpdateView.as_view()), name='reporte-update'),
    path('reportes/<int:pk>/delete/', login_required(ReporteDeleteView.as_view()), name='reporte-delete'),

    # Confirmaciones de reporte
    path('confirmaciones/', login_required(ConfirmacionListView.as_view()), name='confirmacion-list'),
    path('confirmaciones/<int:pk>/', login_required(ConfirmacionDetailView.as_view()), name='confirmacion-detail'),
    path('confirmaciones/create/', login_required(ConfirmacionCreateView.as_view()), name='confirmacion-create'),
    path('confirmaciones/<int:pk>/update/', login_required(ConfirmacionUpdateView.as_view()), name='confirmacion-update'),
    path('confirmaciones/<int:pk>/delete/', login_required(ConfirmacionDeleteView.as_view()), name='confirmacion-delete'),

    # Confirmar reporte
    path('reportes/<int:pk>/confirmar/', login_required(ReporteConfirmarView.as_view()), name='reporte-confirmar'),
]