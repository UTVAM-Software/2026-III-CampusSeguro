from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from django.forms import modelform_factory

from .forms import CuentaForm, RegistroForm, UsuarioAdminForm
from .models import Usuario
from .permisos import PermisoRequeridoMixin


# ----- Entrar, salir y registrarse -----
class EntrarView(LoginView):
    """
    La pantalla de inicio de sesión.

    Se apoya en la LoginView de Django, que ya trae lo que es fácil hacer mal:
    compara la contraseña en tiempo constante, rota la cookie de sesión al
    entrar —para que una sesión vista antes de entrar no valga después— y no
    dice nunca si el fallo fue el correo o la contraseña. Decirlo sería
    regalar una lista de qué correos tienen cuenta aquí.
    """

    template_name = 'usuarios/acceso.html'
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        # La pantalla lleva los DOS formularios: entrar y crear cuenta están
        # en la misma tarjeta, cada uno a su vista. Por eso esta vista tiene
        # que mandar también el de registro, aunque no sea suyo.
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault('formulario_entrar', contexto['form'])
        contexto.setdefault('formulario_registro', RegistroForm())
        return contexto


class SalirView(LogoutView):
    """
    Cerrar la sesión.

    Solo responde a POST, y por eso el botón de "Salir" es un formulario y no
    un enlace: si fuera un enlace, una imagen escondida en otra página podría
    apuntar ahí y cerrarle la sesión a quien la abriera.
    """


class RegistroView(CreateView):
    """Crear una cuenta uno mismo. El rol no se elige: ver RegistroForm."""

    model = Usuario
    form_class = RegistroForm
    template_name = 'usuarios/acceso.html'
    success_url = reverse_lazy('entrar')

    def get_context_data(self, **kwargs):
        from django.contrib.auth.forms import AuthenticationForm

        contexto = super().get_context_data(**kwargs)

        # `modo` deja la tarjeta abierta por el lado del registro. Sin esto,
        # un fallo al crear la cuenta devolveria la pantalla enseñando el lado
        # de entrar, con los errores escondidos detras.
        contexto['modo'] = 'registro'
        contexto['formulario_registro'] = contexto['form']
        contexto.setdefault('formulario_entrar', AuthenticationForm())
        return contexto

    def form_valid(self, formulario):
        respuesta = super().form_valid(formulario)
        messages.success(self.request, 'Cuenta creada. Ya puedes entrar.')
        return respuesta


# ----- Usuarios -----

class SoloYoOSuperadminMixin:
    """
    Tu propia cuenta, o todas si administras el sistema.

    La ficha de alguien lleva su correo y su teléfono. Que cualquiera que
    entre pueda recorrer la lista entera es un directorio con los datos de
    contacto de toda la comunidad, servido en bandeja.

    Quien administra un campus TAMPOCO: para su trabajo -avisos, reportes,
    puntos de apoyo- no hace falta la ficha de nadie, y dársela sería
    repartir los datos de contacto de su universidad entera.

    QUIEN AUDITA LAS LEE TODAS, Y ESO ES SOLO PARA LEER
        Este recorte lo comparten la ficha y el formulario de editar. Al
        ensancharlo para que la auditoría pudiera VER cualquier cuenta, se
        le abrió también EDITARLAS: tiene `change_usuario` para su propio
        perfil, y con el recorte ancho esa llave valía para la cuenta de
        cualquiera. Se podía cambiar el nombre y el correo de otra persona
        desde un rol que se llama "solo lectura".

        Por eso el formulario de editar tiene el suyo propio, abajo, y este
        se queda para las pantallas que únicamente muestran.
    """

    def get_queryset(self):
        if self.request.user.es_superadmin or self.request.user.puede_auditar:
            return Usuario.objects.all()

        return Usuario.objects.filter(pk=self.request.user.pk)


class SoloMiCuentaOSuperadminMixin:
    """
    El recorte de las pantallas que ESCRIBEN sobre una cuenta.

    Igual que el de arriba pero sin la auditoría: leer todas las fichas y
    poder cambiarlas no son la misma cosa, y mezclarlas en un solo recorte
    fue justo lo que abrió el agujero.
    """

    def get_queryset(self):
        if self.request.user.es_superadmin:
            return Usuario.objects.all()

        return Usuario.objects.filter(pk=self.request.user.pk)


class UsuarioListView(PermisoRequeridoMixin, ListView):
    """
    El directorio de la comunidad: correos y telefonos de todo el mundo.

    Por eso no basta con `view_usuario`, que lo tiene cualquiera para su
    propia ficha. Lo abren quien administra el sistema y quien audita, y la
    segunda llave se comprueba abajo porque `permission_required` exigiria
    las dos juntas.
    """

    permission_required = 'usuarios.administrar_sistema'
    model = Usuario

    def has_permission(self):
        usuario = self.request.user
        return usuario.es_superadmin or usuario.puede_auditar


class UsuarioDetailView(PermisoRequeridoMixin, SoloYoOSuperadminMixin, DetailView):
    permission_required = 'usuarios.view_usuario'
    model = Usuario


class UsuarioCreateView(PermisoRequeridoMixin, CreateView):
    permission_required = 'usuarios.add_usuario'
    model = Usuario
    # Con contraseña: UsuarioAdminForm la valida y la guarda cifrada.
    form_class = UsuarioAdminForm
    success_url = reverse_lazy('usuario-list')


class UsuarioUpdateView(
    PermisoRequeridoMixin, SoloMiCuentaOSuperadminMixin, UpdateView
):
    permission_required = 'usuarios.change_usuario'
    model = Usuario

    def get_success_url(self):
        # El superadmin vuelve a la lista; los demás, a su propia ficha
        # (la lista no es para ellos y les daría 403).
        if self.request.user.es_superadmin:
            return reverse_lazy('usuario-list')
        return reverse_lazy('usuario-detail', args=[self.object.pk])

    def get_form_class(self):
        # El rol y el acceso solo los toca la superadministración. Si
        # estuvieran en el formulario de cualquiera, editarse a uno mismo
        # sería el camino más corto para hacerse administrador.
        #
        # Y tampoco los toca quien administra un campus: podría ascenderse a
        # sí mismo a superadministrador, que es el techo del sistema.
        campos = ['nombre', 'apellidos', 'correo', 'telefono']

        if self.request.user.es_superadmin:
            # Y sus grupos y permisos de Django (Punto 4 de la tarea).
            campos += ['rol', 'campus', 'activo', 'groups', 'user_permissions']

        return modelform_factory(Usuario, form=CuentaForm, fields=campos)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        # Los grupos y permisos van aparte: el grupo del rol no sale en el
        # formulario y no se puede perder al guardar.
        form.guardar_acceso(self.object)
        return respuesta


class UsuarioDeleteView(PermisoRequeridoMixin, DeleteView):
    permission_required = 'usuarios.delete_usuario'
    model = Usuario
    success_url = reverse_lazy('usuario-list')