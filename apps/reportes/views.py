from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from apps.comunicacion.models import Notificacion
from apps.usuarios.models import Usuario
from apps.usuarios.permisos import PermisoRequeridoMixin

from .forms import ConfirmacionForm, ReporteForm
from .models import Reporte, ReporteConfirmacion


# ----- Reportes -----
class SoloMiCampusMixin:
    """
    Los reportes del campus de cada quien.

    Un reporte SÍ es información de la comunidad -para eso se publica- pero de
    SU comunidad. Lo que pasa en otra universidad no le sirve a nadie de aquí,
    y la lista completa diría cuántos campus hay en el sistema.
    """

    def get_queryset(self):
        reportes = Reporte.objects.all()

        if self.request.user.es_admin:
            return reportes

        return reportes.filter(campus=self.request.user.campus)


class SoloMiosOAdminMixin(SoloMiCampusMixin):
    """Cambiar o borrar un reporte es cosa de quien lo escribió, o de quien administra."""

    def get_queryset(self):
        reportes = super().get_queryset()

        if self.request.user.es_admin:
            return reportes

        return reportes.filter(usuario=self.request.user)


class ReporteListView(PermisoRequeridoMixin, SoloMiCampusMixin, ListView):
    permission_required = 'reportes.view_reporte'
    model = Reporte


class ReporteDetailView(PermisoRequeridoMixin, SoloMiCampusMixin, DetailView):
    permission_required = 'reportes.view_reporte'
    model = Reporte

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        r = self.object
        ctx['confirman'] = r.confirmaciones.filter(confirma=True).count()
        ctx['niegan'] = r.confirmaciones.filter(confirma=False).count()

        # Quien mira puede responder si no es quien lo escribió. Antes aquí se
        # mandaba la lista de todas las personas del campus para elegir a
        # nombre de quién respondías: ahora lo dice la sesión.
        ctx['puede_responder'] = r.usuario_id != self.request.user.pk

        return ctx


class ReporteCreateView(PermisoRequeridoMixin, CreateView):
    permission_required = 'reportes.add_reporte'
    model = Reporte
    # Qué campos hay y por qué faltan los demás: en ReporteForm.
    form_class = ReporteForm
    success_url = reverse_lazy('reporte-list')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.campus = self.request.user.campus
        respuesta = super().form_valid(form)
        r = self.object
        destinatarios = Usuario.objects.filter(campus=r.campus, activo=True).exclude(pk=r.usuario_id)
        Notificacion.objects.bulk_create([
            Notificacion(
                usuario=u,
                titulo=f"Nuevo reporte: {r}",
                mensaje=f"{r.get_tipo_display()} reportado en {r.campus}. ¿Lo puedes confirmar?",
            )
            for u in destinatarios
        ])
        return respuesta


class ReporteUpdateView(PermisoRequeridoMixin, SoloMiosOAdminMixin, UpdateView):
    permission_required = 'reportes.change_reporte'
    model = Reporte
    success_url = reverse_lazy('reporte-list')

    def get_form_class(self):
        # El estado -verificado, rechazado, resuelto- solo lo mueve quien
        # administra. Que el autor pudiera marcar su propio reporte como
        # verificado vaciaría de sentido las confirmaciones.
        if not self.request.user.es_admin:
            return ReporteForm

        from django.forms import modelform_factory

        return modelform_factory(
            Reporte, form=ReporteForm,
            fields=['tipo', 'descripcion', 'latitud', 'longitud', 'foto', 'estado'],
        )


class ReporteDeleteView(PermisoRequeridoMixin, SoloMiosOAdminMixin, DeleteView):
    permission_required = 'reportes.delete_reporte'
    model = Reporte
    success_url = reverse_lazy('reporte-list')


# ----- Confirmaciones de reporte -----
class ConfirmacionListView(PermisoRequeridoMixin, ListView):
    permission_required = 'reportes.view_reporteconfirmacion'
    model = ReporteConfirmacion

    def get_queryset(self):
        """Las respuestas propias. Lo que votó cada quien es suyo."""
        return ReporteConfirmacion.objects.filter(usuario=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        reportes = Reporte.objects.all()

        if not self.request.user.es_admin:
            reportes = reportes.filter(campus=self.request.user.campus)

        ctx['reportes'] = (
            reportes
            .select_related('usuario', 'campus')
            .annotate(
                si=Count('confirmaciones', filter=Q(confirmaciones__confirma=True)),
                no=Count('confirmaciones', filter=Q(confirmaciones__confirma=False)),
            )
            .order_by('-fecha_creacion')
        )
        return ctx


class ConfirmacionDetailView(PermisoRequeridoMixin, DetailView):
    permission_required = 'reportes.view_reporteconfirmacion'
    model = ReporteConfirmacion

    def get_queryset(self):
        return ReporteConfirmacion.objects.filter(usuario=self.request.user)

class QuienRespondeMixin:
    """
    Le pasa al formulario quien tiene la sesion abierta.

    El formulario lo necesita para dos cosas: recortar la lista de reportes a
    los que esa persona puede responder, y rechazar el suyo propio.
    """

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class ConfirmacionCreateView(PermisoRequeridoMixin, QuienRespondeMixin, CreateView):
    permission_required = 'reportes.add_reporteconfirmacion'
    model = ReporteConfirmacion
    form_class = ConfirmacionForm
    success_url = reverse_lazy('confirmacion-list')


class ConfirmacionUpdateView(PermisoRequeridoMixin, QuienRespondeMixin, UpdateView):
    permission_required = 'reportes.change_reporteconfirmacion'
    model = ReporteConfirmacion
    form_class = ConfirmacionForm
    success_url = reverse_lazy('confirmacion-list')

    def get_queryset(self):
        # Cambiar una respuesta es cosa de quien la dio.
        return ReporteConfirmacion.objects.filter(usuario=self.request.user)


class ConfirmacionDeleteView(PermisoRequeridoMixin, DeleteView):
    permission_required = 'reportes.delete_reporteconfirmacion'
    model = ReporteConfirmacion
    success_url = reverse_lazy('confirmacion-list')

    def get_queryset(self):
        return ReporteConfirmacion.objects.filter(usuario=self.request.user)


UMBRAL = 3  # confirmaciones necesarias para cambiar el estado


class ReporteConfirmarView(PermisoRequeridoMixin, View):
    permission_required = 'reportes.add_reporteconfirmacion'
    def post(self, request, pk):
        # Del campus de quien responde: no se confirma lo que pasa en otra
        # universidad.
        reporte = get_object_or_404(Reporte, pk=pk, campus=request.user.campus)

        # Quien responde es quien tiene la sesión abierta. Antes llegaba en el
        # formulario, elegido de una lista: bastaba con cambiar ese valor para
        # votar en nombre de cualquiera, tantas veces como personas hubiera en
        # el campus.
        usuario = request.user

        if usuario.pk == reporte.usuario_id:
            messages.error(request, 'No puedes confirmar tu propio reporte.')
            return redirect('reporte-detail', pk=pk)

        # Si ya había votado, se actualiza su respuesta
        ReporteConfirmacion.objects.update_or_create(
            reporte=reporte,
            usuario=usuario,
            defaults={
                'confirma': request.POST.get('confirma') == '1',
                'comentario': request.POST.get('comentario', '')[:200],
            },
        )

        # Cambio automático de estado
        if reporte.estado == 'pendiente':
            si = reporte.confirmaciones.filter(confirma=True).count()
            no = reporte.confirmaciones.filter(confirma=False).count()
            if si >= UMBRAL:
                reporte.estado = 'verificado'
                reporte.save(update_fields=['estado'])
            elif no >= UMBRAL:
                reporte.estado = 'rechazado'
                reporte.save(update_fields=['estado'])

        messages.success(request, '¡Gracias! Tu respuesta quedó registrada.')
        return redirect('reporte-detail', pk=pk)
