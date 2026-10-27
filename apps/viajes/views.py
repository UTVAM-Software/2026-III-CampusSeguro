from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from .models import DestinoGuardado, UbicacionViaje, Viaje, ViajeAcompanante
from .forms import AcompananteForm, DestinoGuardadoForm, ViajeForm
from apps.usuarios.permisos import PermisoRequeridoMixin


def viajes_que_puede_ver(usuario):
    """
    Los viajes de esta persona y aquellos que aceptó acompañar. Nadie más.

    Es la pieza más delicada del sistema: aquí se decide quién puede saber a
    dónde va alguien y por dónde pasó. Quien no va en el viaje ni lo acompaña
    no tiene por qué verlo, ni siquiera saber que existe.

    Lo de `estado='aceptado'` importa: a quien solo fue invitado y todavía no
    ha dicho que sí no se le enseña nada. Invitar a alguien no puede ser una
    forma de que te vea la ubicación sin que tú lo sepas.
    """
    return Viaje.objects.filter(
        Q(usuario=usuario)
        | Q(acompanantes__acompanante=usuario, acompanantes__estado='aceptado')
    ).distinct()


class SoloMisViajesMixin:
    """
    Ve los viajes propios y los que acompaña.

    Filtrando el conjunto, y no comprobando después: lo que no está aquí
    devuelve 404, que es lo correcto. Un 403 confirmaría que ese viaje existe.
    """

    def get_queryset(self):
        return viajes_que_puede_ver(self.request.user)


class SoloViajesPropiosMixin:
    """Solo los propios. Acompañar deja mirar, no cambiar ni borrar."""

    def get_queryset(self):
        return Viaje.objects.filter(usuario=self.request.user)


# ----- Viajes -----
class ViajeListView(PermisoRequeridoMixin, SoloMisViajesMixin, ListView):
    """
    Viajes, en cuatro secciones y no en una lista.

    Una lista sola mezcla cosas que se miran por motivos distintos: el viaje
    que tienes abierto ahora, las invitaciones que esperan respuesta, los
    viajes de otra gente que acompañas y los tuyos ya terminados. Lo urgente
    -responder una invitación, ver tu viaje abierto- quedaba al mismo nivel
    que un viaje del mes pasado.
    """

    permission_required = 'viajes.view_viaje'
    model = Viaje

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        usuario = self.request.user

        ctx["viaje_en_curso"] = (
            Viaje.objects.filter(usuario=usuario, estado="en_curso").first()
        )

        # Lo primero de la pantalla: alguien está esperando una respuesta.
        ctx["invitaciones"] = (
            ViajeAcompanante.objects
            .filter(acompanante=usuario, estado="invitado", viaje__estado="en_curso")
            .select_related("viaje", "viaje__usuario")
        )

        ctx["acompanamientos"] = (
            ViajeAcompanante.objects
            .filter(acompanante=usuario, estado="aceptado", viaje__estado="en_curso")
            .select_related("viaje", "viaje__usuario")
        )

        ctx["historial"] = (
            Viaje.objects.filter(usuario=usuario)
            .exclude(estado="en_curso")
            .order_by("-fecha_inicio")
        )
        return ctx


class ViajeDetailView(PermisoRequeridoMixin, SoloMisViajesMixin, DetailView):
    permission_required = 'viajes.view_viaje'
    model = Viaje

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Quien viaja y quien acompana ven la misma pantalla, pero no lo
        # mismo: los botones de cerrar el viaje son de quien viaja, y el
        # telefono al que llamar es de quien acompana.
        ctx['es_viajero'] = self.object.usuario_id == self.request.user.pk
        ctx['ultima_ubicacion'] = (
            self.object.ubicaciones.order_by('-fecha_registro').first()
        )

        # Para el guion que comparte la posicion. Va como DATOS y no como
        # JavaScript escrito dentro de la plantilla: asi no hay forma de que
        # un destino con comillas dentro rompa la pagina.
        ctx['config_viaje'] = {
            'esViajero': ctx['es_viajero'],
            'enCurso': self.object.esta_en_curso,
            'urlPosicion': reverse('viaje-posicion', args=[self.object.pk]),
            'urlUltima': reverse('viaje-ultima', args=[self.object.pk]),
        }
        return ctx


class ConDestinosGuardados:
    """
    Los destinos guardados de quien mira, para ofrecerlos como atajo.

    Los suyos y solo los suyos: a donde suele ir alguien es tan suyo como el
    viaje.
    """

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['destinos'] = DestinoGuardado.objects.filter(
            usuario=self.request.user
        )
        return contexto


class ViajeCreateView(PermisoRequeridoMixin, ConDestinosGuardados, CreateView):
    permission_required = 'viajes.add_viaje'
    model = Viaje
    form_class = ViajeForm
    success_url = reverse_lazy('viaje-list')

    def form_valid(self, form):
        # De quién es el viaje lo dice la sesión, no el formulario. Mientras
        # `usuario` fue un campo más, cualquiera podía crear un viaje a nombre
        # de otra persona sin más que elegirla en la lista.
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class ViajeUpdateView(
    PermisoRequeridoMixin, SoloViajesPropiosMixin, ConDestinosGuardados, UpdateView
):
    permission_required = 'viajes.change_viaje'
    model = Viaje
    form_class = ViajeForm
    success_url = reverse_lazy('viaje-list')


class ViajeDeleteView(PermisoRequeridoMixin, SoloViajesPropiosMixin, DeleteView):
    permission_required = 'viajes.delete_viaje'
    model = Viaje
    success_url = reverse_lazy('viaje-list')


class CerrarViajeView(PermisoRequeridoMixin, View):
    """
    Dar un viaje por terminado: "Llegue bien" o "Cancelar".

    VA POR POST, NUNCA POR GET
        Cambia datos. Si fuera un enlace, el navegador -o cualquier cosa que
        vaya precargando enlaces- podria cerrarle el viaje a alguien que solo
        estaba mirando la pantalla.

    SOLO QUIEN VIAJA
        `usuario=request.user` dentro del get_object_or_404, no comprobado
        despues: quien no sea su dueno recibe un 404 y no llega a enterarse de
        que ese viaje existe. Acompanar deja mirar, no cerrar.

    SOLO UNA VEZ
        Si el viaje ya no esta en curso no se toca nada. Asi recargar la
        pagina despues de pulsar no vuelve a escribir la hora de llegada ni
        convierte un viaje cancelado en uno que llego bien.
    """

    permission_required = 'viajes.change_viaje'
    estado = None
    mensaje = None

    def post(self, request, pk):
        viaje = get_object_or_404(Viaje, pk=pk, usuario=request.user)

        if viaje.cerrar(self.estado):
            messages.success(request, self.mensaje)

        return redirect('viaje-detail', pk=viaje.pk)


class LlegueBienView(CerrarViajeView):
    estado = 'llego_bien'
    mensaje = 'Listo. Dejaste de compartir tu ubicacion.'


class CancelarViajeView(CerrarViajeView):
    estado = 'cancelado'
    mensaje = 'Viaje cancelado. Dejaste de compartir tu ubicacion.'


class GuardarPosicionView(PermisoRequeridoMixin, View):
    """
    Guarda dónde estás ahora mismo, mientras el viaje sigue en curso.

    Es la pieza que convierte "comparto mi ubicación" en algo que de verdad
    pasa. Hasta ahora las posiciones se escribían a mano en un formulario de
    la lista de ubicaciones: nadie las iba a escribir mientras camina.

    SOLO QUIEN VIAJA, Y SOLO SI EL VIAJE SIGUE ABIERTO
        `usuario=request.user, estado='en_curso'` dentro del
        get_object_or_404. Un viaje cerrado no recibe posiciones: la pantalla
        dice que dejaste de compartir, y tiene que ser verdad.

    LAS COORDENADAS SE COMPRUEBAN
        Vienen del navegador, que es tanto como decir que vienen de fuera.
        Una latitud de 500 no existe, y guardada deja un punto imposible en
        el mapa de quien te acompaña.
    """

    permission_required = 'viajes.add_ubicacionviaje'
    def post(self, request, pk):
        viaje = get_object_or_404(
            Viaje, pk=pk, usuario=request.user, estado='en_curso'
        )

        try:
            latitud = Decimal(request.POST['latitud'])
            longitud = Decimal(request.POST['longitud'])
        except (KeyError, InvalidOperation, TypeError):
            return JsonResponse({'error': 'Coordenadas no válidas.'}, status=400)

        if not (-90 <= latitud <= 90) or not (-180 <= longitud <= 180):
            return JsonResponse({'error': 'Coordenadas fuera de rango.'}, status=400)

        UbicacionViaje.objects.create(
            viaje=viaje, latitud=latitud, longitud=longitud
        )

        return JsonResponse({'guardada': True})


class UltimaPosicionView(PermisoRequeridoMixin, View):
    """
    La última posición de un viaje, para quien lo acompaña.

    Se consulta cada pocos segundos desde la pantalla del viaje. Va por aquí
    y no por WebSockets porque esto es lo que se enseña en clase, y para
    saber si alguien sigue en camino preguntar cada medio minuto sobra.

    Lo ven quien viaja y quienes aceptaron acompañarlo, que es exactamente el
    mismo filtro que el resto de la aplicación: `viajes_que_puede_ver`.
    """

    permission_required = 'viajes.view_ubicacionviaje'
    def get(self, request, pk):
        viaje = get_object_or_404(viajes_que_puede_ver(request.user), pk=pk)
        ultima = viaje.ubicaciones.order_by('-fecha_registro').first()

        return JsonResponse({
            'enCurso': viaje.esta_en_curso,
            'estado': viaje.get_estado_display(),
            'hay': ultima is not None,
            # Los segundos, no la hora: quien mira quiere saber si fue hace un
            # momento o hace media hora, y el texto lo arma la pantalla.
            'segundos': (
                int((timezone.now() - ultima.fecha_registro).total_seconds())
                if ultima else None
            ),
        })


class ResponderInvitacionView(PermisoRequeridoMixin, View):
    """
    Aceptar o rechazar que te acompañen contigo.

    ESTO LO DECIDE QUIEN ESTA INVITADO, NO QUIEN VIAJA
        Hasta ahora el estado de un acompañante solo lo podia cambiar el
        dueño del viaje, porque la vista de editar filtra por
        `viaje__usuario`. Es decir: quien te invitaba podia marcar que habias
        aceptado, y con eso empezabas a verle la ubicacion sin haber dicho
        que si. Aqui el filtro es `acompanante=request.user`: solo tu
        respondes tu invitacion.

    Va por POST, porque cambia datos.
    """

    permission_required = 'viajes.change_viajeacompanante'
    def post(self, request, pk):
        invitacion = get_object_or_404(
            ViajeAcompanante, pk=pk, acompanante=request.user, estado='invitado'
        )

        acepta = request.POST.get('respuesta') == 'aceptar'
        invitacion.estado = 'aceptado' if acepta else 'rechazado'
        invitacion.save(update_fields=['estado'])

        if acepta:
            messages.success(
                request,
                f'Listo, acompañas a {invitacion.viaje.usuario}.',
            )
        else:
            messages.info(request, 'Invitacion rechazada.')

        return redirect('viaje-list')


# ----- Acompañantes de viaje -----
class SoloMisAcompanantesMixin:
    """Los de mis viajes, y aquellos en los que yo acompaño."""

    def get_queryset(self):
        usuario = self.request.user
        return ViajeAcompanante.objects.filter(
            Q(viaje__usuario=usuario) | Q(acompanante=usuario)
        ).distinct()


class SoloEnMisViajesMixin:
    """
    Invitar y desinvitar es cosa de quien viaja.

    Además, la lista de viajes del formulario se recorta a los propios: si no,
    cualquiera podría apuntarse como acompañante del viaje de otra persona
    eligiéndolo de la lista, y así verle la ubicación.
    """

    def get_queryset(self):
        return ViajeAcompanante.objects.filter(viaje__usuario=self.request.user)

    def get_form_kwargs(self):
        # El formulario necesita saber quién invita para recortar las dos
        # listas: tus viajes, y cualquiera menos tú.
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs


class AcompananteListView(PermisoRequeridoMixin, SoloMisAcompanantesMixin, ListView):
    permission_required = 'viajes.view_viajeacompanante'
    model = ViajeAcompanante


class AcompananteDetailView(PermisoRequeridoMixin, SoloMisAcompanantesMixin, DetailView):
    permission_required = 'viajes.view_viajeacompanante'
    model = ViajeAcompanante


class AcompananteCreateView(PermisoRequeridoMixin, SoloEnMisViajesMixin, CreateView):
    permission_required = 'viajes.add_viajeacompanante'
    model = ViajeAcompanante
    form_class = AcompananteForm
    success_url = reverse_lazy('acompanante-list')


class AcompananteUpdateView(PermisoRequeridoMixin, SoloEnMisViajesMixin, UpdateView):
    permission_required = 'viajes.change_viajeacompanante'
    model = ViajeAcompanante
    form_class = AcompananteForm
    success_url = reverse_lazy('acompanante-list')


class AcompananteDeleteView(PermisoRequeridoMixin, SoloEnMisViajesMixin, DeleteView):
    permission_required = 'viajes.delete_viajeacompanante'
    model = ViajeAcompanante
    success_url = reverse_lazy('acompanante-list')


# ----- Ubicaciones de viaje -----
class SoloMisUbicacionesMixin:
    """
    Por dónde pasó alguien lo ven quien viaja y quienes lo acompañan.

    De todo lo que guarda este sistema esto es lo más delicado: es el rastro
    de por dónde se mueve una persona. Antes la lista las enseñaba todas, de
    todo el mundo.
    """

    def get_queryset(self):
        return UbicacionViaje.objects.filter(
            viaje__in=viajes_que_puede_ver(self.request.user)
        )


class SoloEnViajesPropiosMixin:
    """Escribir una posición es cosa de quien viaja, en su propio viaje."""

    def get_queryset(self):
        return UbicacionViaje.objects.filter(viaje__usuario=self.request.user)

    def get_form(self, form_class=None):
        formulario = super().get_form(form_class)
        formulario.fields['viaje'].queryset = Viaje.objects.filter(
            usuario=self.request.user
        )
        return formulario


class UbicacionListView(PermisoRequeridoMixin, SoloMisUbicacionesMixin, ListView):
    permission_required = 'viajes.view_ubicacionviaje'
    model = UbicacionViaje


class UbicacionDetailView(PermisoRequeridoMixin, SoloMisUbicacionesMixin, DetailView):
    permission_required = 'viajes.view_ubicacionviaje'
    model = UbicacionViaje


class UbicacionCreateView(PermisoRequeridoMixin, SoloEnViajesPropiosMixin, CreateView):
    permission_required = 'viajes.add_ubicacionviaje'
    model = UbicacionViaje
    fields = '__all__'
    success_url = reverse_lazy('ubicacion-list')

    def get_form(self, form_class=None):
        """
        Solo se puede escribir ubicacion en un viaje que sigue en curso.

        Al cerrar un viaje la pantalla dice "dejaste de compartir tu
        ubicacion". Sin esto seria mentira: el formulario seguia ofreciendo
        los viajes terminados y se les podian seguir anadiendo posiciones.
        """
        formulario = super().get_form(form_class)
        formulario.fields['viaje'].queryset = formulario.fields['viaje'].queryset.filter(
            estado='en_curso'
        )
        return formulario


class UbicacionUpdateView(PermisoRequeridoMixin, SoloEnViajesPropiosMixin, UpdateView):
    permission_required = 'viajes.change_ubicacionviaje'
    model = UbicacionViaje
    fields = '__all__'
    success_url = reverse_lazy('ubicacion-list')


class UbicacionDeleteView(PermisoRequeridoMixin, SoloEnViajesPropiosMixin, DeleteView):
    permission_required = 'viajes.delete_ubicacionviaje'
    model = UbicacionViaje
    success_url = reverse_lazy('ubicacion-list')

# ----- Destinos guardados -----
class SoloMisDestinosMixin:
    """
    Los destinos propios, y de nadie más.

    Es una lista de los sitios a los que va alguien habitualmente: su casa,
    su trabajo, la parada donde la recogen. Dicho de otro modo, dónde vive y
    a qué hora sale. No lo ve ni quien administra.
    """

    def get_queryset(self):
        return DestinoGuardado.objects.filter(usuario=self.request.user)


class DestinoListView(PermisoRequeridoMixin, SoloMisDestinosMixin, ListView):
    permission_required = 'viajes.view_destinoguardado'
    model = DestinoGuardado


class DestinoDetailView(PermisoRequeridoMixin, SoloMisDestinosMixin, DetailView):
    """La ficha de un destino. Como la lista, solo la ve quien lo guardó: los demás, 404."""

    permission_required = 'viajes.view_destinoguardado'
    model = DestinoGuardado


class QuienGuardaMixin:
    """Le pasa al formulario de quién es, para poder comprobar la etiqueta."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs


class DestinoCreateView(PermisoRequeridoMixin, QuienGuardaMixin, CreateView):
    permission_required = 'viajes.add_destinoguardado'
    model = DestinoGuardado
    form_class = DestinoGuardadoForm
    success_url = reverse_lazy('destino-list')

    def form_valid(self, form):
        # De quién es el destino lo dice la sesión, no el formulario.
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DestinoUpdateView(PermisoRequeridoMixin, QuienGuardaMixin, SoloMisDestinosMixin, UpdateView):
    permission_required = 'viajes.change_destinoguardado'
    model = DestinoGuardado
    form_class = DestinoGuardadoForm
    success_url = reverse_lazy('destino-list')


class DestinoDeleteView(PermisoRequeridoMixin, SoloMisDestinosMixin, DeleteView):
    permission_required = 'viajes.delete_destinoguardado'
    model = DestinoGuardado
    success_url = reverse_lazy('destino-list')
