"""
El perfil: tus datos y tu seguridad.

Va aparte de `views.py` porque aquello es el CRUD de cuentas que usa quien
administra —la lista, la ficha de cualquiera, dar de alta— y esto es otra
cosa: la pantalla de uno mismo.

DOS SECCIONES EN UNA PANTALLA
    "Tus datos" y "Seguridad". El cambio de una a otra es CSS: dos radios
    escondidos y reglas que miran cuál está marcado. Sin JavaScript, y el
    teclado se mueve entre ellas con las flechas porque son un grupo de
    radios de verdad.

    Cuál llega abierta lo decide el servidor, para que al guardar no se
    vuelva a la primera sección dejando el mensaje de "listo" donde nadie
    está mirando.
"""

from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.contrib.sessions.models import Session
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import UpdateView

from .formularios_perfil import DatosPerfilForm
from .permisos import PermisoRequeridoMixin


def otras_sesiones(request):
    """
    Las sesiones de esta cuenta que NO son la de este navegador.

    Django no guarda a quién pertenece cada sesión: hay que abrir el
    contenido de cada una y mirar dentro. Con las sesiones en la base de
    datos —que es como está montado esto— no hay otra forma.

    Solo se miran las que no han caducado: las vencidas ya no le sirven a
    nadie, y contarlas asustaría sin motivo.
    """
    mias = []

    for sesion in Session.objects.filter(expire_date__gt=timezone.now()):
        if sesion.session_key == request.session.session_key:
            continue

        if sesion.get_decoded().get('_auth_user_id') == str(request.user.pk):
            mias.append(sesion.session_key)

    return Session.objects.filter(session_key__in=mias)


class PerfilView(PermisoRequeridoMixin, UpdateView):
    """
    Tu propia ficha, y la única cuenta que edita es la tuya.

    `get_object` devuelve `request.user` y no busca por `pk` en la dirección:
    así no existe la pregunta de si alguien puede editar a otra persona desde
    aquí. No hay forma de pedirlo.

    La sesión la pide `login_required` en urls.py, como todas las demás de
    este proyecto. Un solo mecanismo y en un solo sitio: con unas vistas
    usando el decorador y otras el mixin, mirar el urls.py ya no basta para
    saber qué está cerrado, y hay una prueba que lo mira ahí.
    """

    permission_required = 'usuarios.change_usuario'
    form_class = DatosPerfilForm
    template_name = 'usuarios/perfil.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sesiones_abiertas'] = otras_sesiones(self.request).count()

        # Qué sección llega abierta. Por omisión la primera; `?seccion=` la
        # cambia, que es como se vuelve aquí después de guardar algo.
        ctx['seccion_perfil'] = self.request.GET.get('seccion', 'datos')
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Listo, guardamos tus datos.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('perfil')


class CerrarOtrasSesionesView(PermisoRequeridoMixin, View):
    """
    Cierra la sesión de esta cuenta en los demás dispositivos.

    POR QUÉ NO CIERRA TAMBIÉN ESTA
        Quien pulsa esto suele estar diciendo "me dejé la sesión abierta en
        otro sitio". Cerrarle además la de aquí lo echaría de la aplicación
        como premio por protegerse.

    Django no trae esto de serie: lo más parecido es cambiar la contraseña,
    que invalida las demás de rebote. Aquí se borran las filas de sesión, que
    es lo que hay cuando las sesiones viven en la base de datos.
    """

    permission_required = 'usuarios.change_usuario'
    def post(self, request):
        cerradas = otras_sesiones(request).delete()[0]

        if cerradas:
            plural = 's' if cerradas != 1 else ''
            messages.success(
                request,
                f'Listo. Se cerró la sesión en {cerradas} dispositivo{plural} más.',
            )
        else:
            messages.info(request, 'No había ninguna otra sesión abierta.')

        return redirect(f"{reverse('perfil')}?seccion=seguridad")


class CambiarClaveView(PermisoRequeridoMixin, PasswordChangeView):
    """
    Cambiar la contraseña sabiendo la actual.

    EL PROYECTO VIEJO LO HACÍA POR CORREO, Y AQUÍ NO
        Allí esta pantalla mandaba un enlace al correo. Aquí no hay servidor
        de correo configurado, así que copiar ese texto sería prometer un
        mensaje que no sale de la máquina: nadie podría cambiar su
        contraseña nunca.

        Pedir la actual tampoco es el mal menor, es mejor: quien encuentre un
        teléfono desbloqueado con la sesión abierta no puede cambiar la
        contraseña sin saberla. Por correo, esa misma persona pide el enlace
        y lo abre en el buzón de ese mismo teléfono.

    `PasswordChangeView` de Django comprueba la actual, pasa la nueva por
    AUTH_PASSWORD_VALIDATORS y renueva la sesión de aquí para que el cambio
    no te eche a ti mismo.
    """

    permission_required = 'usuarios.change_usuario'
    template_name = 'usuarios/cambiar_clave.html'

    def get_success_url(self):
        return f"{reverse('perfil')}?seccion=seguridad"

    def form_valid(self, form):
        messages.success(self.request, 'Listo, tu contraseña quedó cambiada.')
        return super().form_valid(form)
