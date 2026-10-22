from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from apps.usuarios.permisos import PermisoRequeridoMixin

from .forms import CorreccionForm, PuntoApoyoForm
from .models import Campus, Correccion, PuntoApoyo


# Ver los campus lo puede hacer cualquiera que haya entrado: hace falta para
# elegir el tuyo. Crearlos, cambiarlos y borrarlos es de SUPERADMINISTRACION,
# no de quien administra un campus: uno se lleva por delante los reportes, los
# avisos y los puntos de apoyo de toda su gente, y quien administra el suyo no
# tiene por que poder tocar los de otra universidad.
class CampusListView(PermisoRequeridoMixin, ListView):
    permission_required = 'campus.view_campus'
    model = Campus


class CampusDetailView(PermisoRequeridoMixin, DetailView):
    permission_required = 'campus.view_campus'
    model = Campus


class CampusCreateView(PermisoRequeridoMixin, CreateView):
    permission_required = 'campus.add_campus'
    model = Campus
    fields = '__all__'
    success_url = reverse_lazy('campus-list')


class CampusUpdateView(PermisoRequeridoMixin, UpdateView):
    permission_required = 'campus.change_campus'
    model = Campus
    fields = '__all__'
    success_url = reverse_lazy('campus-list')


class CampusDeleteView(PermisoRequeridoMixin, DeleteView):
    permission_required = 'campus.delete_campus'
    model = Campus
    success_url = reverse_lazy('campus-list')

# ----- Puntos de apoyo -----
class PuntosDeMiCampusMixin:
    """
    Los puntos del campus de cada quien, y solo los que están abiertos.

    LOS INACTIVOS NO SE ENSEÑAN
        Mandar a alguien a una caseta cerrada o a una enfermería que ya no
        existe es peor que no enseñarle nada: va hasta allí contando con que
        hay alguien. Quien administra sí los ve todos, porque necesita poder
        reactivarlos.

    LOS DE OTRO CAMPUS TAMPOCO
        Una enfermería de otra universidad no le sirve a nadie de aquí.
    """

    def get_queryset(self):
        puntos = PuntoApoyo.objects.select_related('campus')

        if self.request.user.es_admin:
            return puntos

        return puntos.filter(campus=self.request.user.campus, activo=True)


class PuntoListView(PermisoRequeridoMixin, PuntosDeMiCampusMixin, ListView):
    permission_required = 'campus.view_puntoapoyo'
    model = PuntoApoyo


class PuntoDetailView(PermisoRequeridoMixin, PuntosDeMiCampusMixin, DetailView):
    permission_required = 'campus.view_puntoapoyo'
    model = PuntoApoyo

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # El formulario de avisar de que algo esta mal. Va aqui y no en una
        # pantalla aparte: quien se entera de que la enfermeria cerro es
        # quien esta mirando su ficha.
        ctx['formulario_correccion'] = CorreccionForm()
        return ctx


class PuntoCreateView(PermisoRequeridoMixin, CreateView):
    permission_required = 'campus.add_puntoapoyo'
    model = PuntoApoyo
    form_class = PuntoApoyoForm
    success_url = reverse_lazy('punto-list')


class PuntoUpdateView(PermisoRequeridoMixin, UpdateView):
    permission_required = 'campus.change_puntoapoyo'
    model = PuntoApoyo
    form_class = PuntoApoyoForm
    success_url = reverse_lazy('punto-list')


class PuntoDeleteView(PermisoRequeridoMixin, DeleteView):
    permission_required = 'campus.delete_puntoapoyo'
    model = PuntoApoyo
    success_url = reverse_lazy('punto-list')


# ----- Correcciones: la comunidad avisa, la administración corrige -----
class AvisarDePuntoView(PermisoRequeridoMixin, View):
    """
    Avisar de que un punto de apoyo está mal.

    SOLO DE UN PUNTO QUE PUEDES VER
        `PuntosDeMiCampusMixin` recorta a los del campus de cada quien. Aquí
        se reusa el mismo filtro: sin él, se podría avisar de puntos de otra
        universidad, que es información que esa persona no tiene por qué
        tener ni tocar.

    NO SE PUEDE AVISAR DOS VECES DE LO MISMO
        Mientras haya uno tuyo sin atender, no se admite otro. Si no, diez
        pulsaciones seguidas llenarían la cola de quien administra y taparían
        los avisos de los demás.
    """

    permission_required = 'campus.add_correccion'
    def post(self, request, pk):
        puntos = PuntoApoyo.objects.all()

        if not request.user.es_admin:
            puntos = puntos.filter(campus=request.user.campus)

        punto = get_object_or_404(puntos, pk=pk)

        if Correccion.objects.filter(
            punto=punto, usuario=request.user, atendida=False
        ).exists():
            messages.info(
                request, 'Ya avisaste de este punto. Lo estamos revisando.'
            )
            return redirect('punto-detail', pk=punto.pk)

        formulario = CorreccionForm(request.POST)

        if not formulario.is_valid():
            messages.error(request, 'Dinos qué está mal para poder corregirlo.')
            return redirect('punto-detail', pk=punto.pk)

        correccion = formulario.save(commit=False)
        correccion.punto = punto
        correccion.usuario = request.user
        correccion.save()

        messages.success(
            request,
            'Gracias. Quien administra el campus lo va a revisar.',
        )
        return redirect('punto-detail', pk=punto.pk)


class CorreccionListView(PermisoRequeridoMixin, ListView):
    """La cola de avisos, para quien administra."""

    permission_required = 'campus.view_correccion'
    model = Correccion
    template_name = 'campus/correccion_list.html'

    def get_queryset(self):
        return (
            Correccion.objects
            .filter(atendida=False, punto__campus=self.request.user.campus)
            .select_related('punto', 'usuario')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Las ya atendidas no se borran: saber que un punto dio problemas
        # tres veces en un mes es justo lo que hace falta para decidir darlo
        # de baja.
        ctx['atendidas'] = (
            Correccion.objects
            .filter(atendida=True, punto__campus=self.request.user.campus)
            .select_related('punto', 'usuario')[:10]
        )
        return ctx


class AtenderCorreccionView(PermisoRequeridoMixin, View):
    """
    Dar por revisado un aviso.

    NO TOCA EL PUNTO, Y ES LO IMPORTANTE
        Marcar esto como atendido solo lo saca de la cola. Corregir el punto
        -cambiarle el horario, darlo de baja- es otra decisión y se hace en
        su formulario. Que un aviso cerrara la enfermería automáticamente
        sería una forma de borrarla del mapa poniéndose de acuerdo unas
        cuantas personas.
    """

    permission_required = 'campus.change_correccion'
    def post(self, request, pk):
        correccion = get_object_or_404(
            Correccion, pk=pk, punto__campus=request.user.campus
        )

        if not correccion.atendida:
            correccion.atendida = True
            correccion.fecha_atendida = timezone.now()
            correccion.save(update_fields=['atendida', 'fecha_atendida'])

        messages.success(request, 'Aviso revisado.')
        return redirect('correccion-list')

class CorreccionesDeMiCampusMixin:
    """Solo los avisos de puntos de TU campus. Los de otro campus dan 404."""

    def get_queryset(self):
        return (
            Correccion.objects
            .filter(punto__campus=self.request.user.campus)
            .select_related('punto', 'usuario')
        )


class CorreccionDetailView(PermisoRequeridoMixin, CorreccionesDeMiCampusMixin, DetailView):
    permission_required = 'campus.view_correccion'
    model = Correccion


class CorreccionDeleteView(PermisoRequeridoMixin, CorreccionesDeMiCampusMixin, DeleteView):
    permission_required = 'campus.delete_correccion'
    model = Correccion
    success_url = reverse_lazy('correccion-list')