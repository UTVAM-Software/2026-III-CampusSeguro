from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from .models import Aviso, Notificacion
from .forms import AvisoForm
from apps.usuarios.models import Usuario
from apps.usuarios.permisos import PermisoRequeridoMixin

from django.shortcuts import get_object_or_404, redirect
from django.views import View

# ----- Avisos -----
class SoloMiCampusMixin:
    """
    Los avisos del campus de cada quien.

    Un aviso de otra universidad no le sirve a nadie, y la lista completa
    diría cuántos campus hay y cómo se llaman. Quien administra los ve todos:
    es su trabajo.
    """

    def get_queryset(self):
        avisos = Aviso.objects.all()

        if self.request.user.es_admin:
            return avisos

        return avisos.filter(campus=self.request.user.campus)


class AvisoListView(PermisoRequeridoMixin, SoloMiCampusMixin, ListView):
    permission_required = 'comunicacion.view_aviso'
    model = Aviso


class AvisoDetailView(PermisoRequeridoMixin, SoloMiCampusMixin, DetailView):
    permission_required = 'comunicacion.view_aviso'
    model = Aviso


class AvisoCreateView(PermisoRequeridoMixin, CreateView):
    permission_required = 'comunicacion.add_aviso'
    model = Aviso
    form_class = AvisoForm
    success_url = reverse_lazy('aviso-list')

    def form_valid(self, form):
        # Quien firma el aviso es quien lo publica, no quien se elija en una
        # lista: un aviso del campus firmado a nombre de otra persona es
        # suplantacion, y ademas con el sello de la institucion delante.
        form.instance.autor = self.request.user

        respuesta = super().form_valid(form)
        aviso = self.object

        # Solo si el aviso está activo
        if aviso.activo:
            destinatarios = Usuario.objects.filter(campus=aviso.campus, activo=True)
            if aviso.autor:
                destinatarios = destinatarios.exclude(pk=aviso.autor.pk)

            Notificacion.objects.bulk_create([
                Notificacion(usuario=u, titulo=aviso.titulo, mensaje=aviso.contenido)
                for u in destinatarios
            ])
        return respuesta


class AvisoUpdateView(PermisoRequeridoMixin, UpdateView):
    permission_required = 'comunicacion.change_aviso'
    model = Aviso
    form_class = AvisoForm
    success_url = reverse_lazy('aviso-list')


class AvisoDeleteView(PermisoRequeridoMixin, DeleteView):
    permission_required = 'comunicacion.delete_aviso'
    model = Aviso
    success_url = reverse_lazy('aviso-list')


# ----- Notificaciones -----
class SoloMisNotificacionesMixin:
    """
    Las notificaciones de cada quien, y de nadie mas.

    Aqui llega el aviso de que alguien no ha llegado a su destino, con su
    nombre y a donde iba. La lista las ensenaba todas, de todo el mundo.
    """

    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user)


class NotificacionListView(PermisoRequeridoMixin, SoloMisNotificacionesMixin, ListView):
    permission_required = 'comunicacion.view_notificacion'
    model = Notificacion


class NotificacionDetailView(PermisoRequeridoMixin, SoloMisNotificacionesMixin, DetailView):
    permission_required = 'comunicacion.view_notificacion'
    model = Notificacion


class NotificacionCreateView(PermisoRequeridoMixin, CreateView):
    permission_required = 'comunicacion.add_notificacion'
    model = Notificacion
    # `usuario` fuera: las notificaciones las crea el sistema, y esta pantalla
    # es andamiaje. Mientras el campo estuvo aqui, cualquiera podia dejarle un
    # aviso a otra persona con el texto que quisiera.
    fields = ['titulo', 'mensaje']
    success_url = reverse_lazy('notificacion-list')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class NotificacionUpdateView(PermisoRequeridoMixin, SoloMisNotificacionesMixin, UpdateView):
    permission_required = 'comunicacion.change_notificacion'
    model = Notificacion
    fields = ['titulo', 'mensaje', 'leida']
    success_url = reverse_lazy('notificacion-list')


class NotificacionDeleteView(PermisoRequeridoMixin, SoloMisNotificacionesMixin, DeleteView):
    permission_required = 'comunicacion.delete_notificacion'
    model = Notificacion
    success_url = reverse_lazy('notificacion-list')


class NotificacionMarcarLeidaView(PermisoRequeridoMixin, View):
    permission_required = 'comunicacion.change_notificacion'
    def post(self, request, pk):
        # Filtrando por quien pide: antes se podia marcar como leida la
        # notificacion de cualquiera sabiendo su numero.
        notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
        notificacion.leida = not notificacion.leida
        notificacion.save(update_fields=['leida'])
        return redirect('notificacion-detail', pk=pk)