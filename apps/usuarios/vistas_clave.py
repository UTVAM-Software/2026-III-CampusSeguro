"""
Recuperar la contraseña olvidada.

Son las cuatro vistas de Django, que ya traen hecho lo delicado:

    - El enlace lleva un testigo firmado que incluye el hash de la contraseña
      actual. En cuanto se usa para poner una nueva, el hash cambia y el
      enlace deja de valer. No hay que inventar nada para que caduque al
      usarse.
    - Vale media hora (`PASSWORD_RESET_TIMEOUT`).
    - No dice si ese correo tiene cuenta. Pedir el enlace para una dirección
      cualquiera responde lo mismo que para una real: si no, esta pantalla
      sería una forma de averiguar quién está registrado aquí.

LO QUE SÍ HAY QUE CAMBIAR
    `PasswordResetForm` busca a quién escribirle con `filter(is_active=True)`,
    y en este proyecto `is_active` es una propiedad de Python, no una columna:
    el campo de la base se llama `activo`. Sin cambiarlo, la consulta revienta.

ESTO ES LO QUE EL PROYECTO VIEJO TENÍA Y AQUÍ FALTABA
    Mientras no existió, quien olvidaba su contraseña se quedaba fuera de su
    cuenta para siempre y solo se arreglaba por consola.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import reverse_lazy


class RecuperarClaveForm(PasswordResetForm):
    """A quién le escribimos."""

    def get_users(self, email):
        """
        Las cuentas con ese correo que pueden entrar.

        Django filtra por `is_active`, que aquí no es una columna. Se cambia
        por `activo`, que es la de verdad.

        `has_usable_password` deja fuera a las cuentas creadas sin contraseña
        —por consola, por ejemplo—: mandarles un enlace para "recuperar" algo
        que nunca tuvieron solo confunde.
        """
        Usuario = get_user_model()

        return (
            u for u in Usuario.objects.filter(correo__iexact=email, activo=True)
            if u.has_usable_password()
        )


class PedirClaveView(PasswordResetView):
    """Pantalla 1: escribe tu correo."""

    template_name = 'usuarios/clave/pedir.html'
    email_template_name = 'usuarios/clave/correo.txt'
    subject_template_name = 'usuarios/clave/asunto.txt'
    form_class = RecuperarClaveForm
    success_url = reverse_lazy('clave-enviada')


class ClaveEnviadaView(PasswordResetDoneView):
    """
    Pantalla 2: "si existe esa cuenta, le escribimos".

    El "si existe" no es un descuido de redacción: es lo que impide usar esta
    pantalla para averiguar qué correos están registrados.
    """

    template_name = 'usuarios/clave/enviada.html'


class NuevaClaveView(PasswordResetConfirmView):
    """Pantalla 3: la del enlace. Escribe la nueva."""

    template_name = 'usuarios/clave/nueva.html'
    success_url = reverse_lazy('clave-lista')


class ClaveListaView(PasswordResetCompleteView):
    """Pantalla 4: ya está, entra."""

    template_name = 'usuarios/clave/lista.html'
