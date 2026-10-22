"""
Quién puede ver y tocar qué.

TRES CERROJOS, EN ESTE ORDEN
    1. `login_required` (en cada urls.py)
           ¿Iniciaste sesión? Si no, a la pantalla de entrar.
    2. `permission_required` (en cada vista, con `PermisoRequeridoMixin`)
           ¿Tu cuenta tiene el permiso de Django para esto? Si no, 403.
           Los permisos salen de los grupos de la cuenta: ver roles.py.
    3. `get_queryset()` (en cada vista que muestra registros de alguien)
           ¿Este registro es tuyo o de tu campus? Si no, 404.

DOS FORMAS DE DECIR QUE NO, Y NO SON INTERCAMBIABLES

    403 — "esta sección no es para tu cuenta"
        Para pantallas enteras: la lista de usuarios, crear un campus. La
        página existe y da igual que se sepa; lo que no se puede es entrar.
        Eso lo hace `permission_required`.

    404 — "aquí no hay nada"
        Para cosas de otra persona: el viaje de alguien, su notificación. Un
        403 ahí confirmaría que ese viaje existe, y quién viaja a dónde no es
        algo que deba filtrarse a quien no va en él. Eso no se hace con un
        mixin sino filtrando `get_queryset()`: si la fila no está en el
        conjunto, Django responde 404 solo.

LA AUTORIZACIÓN VA AQUÍ, NO EN LAS PLANTILLAS
    Esconder un botón con `{% if perms.campus.add_campus %}` no protege nada:
    la dirección sigue ahí y se escribe a mano. Las plantillas esconden
    puertas para no ofrecer lo que no se puede abrir; quien cierra con llave
    es esto.
"""

from django.contrib.auth.mixins import PermissionRequiredMixin


class PermisoRequeridoMixin(PermissionRequiredMixin):
    """
    El `PermissionRequiredMixin` de Django, respondiendo 403.

    Cada vista dice qué permiso pide, a la vista de quien lea el código:

        class CampusCreateView(PermisoRequeridoMixin, CreateView):
            permission_required = 'campus.add_campus'

    POR QUÉ `raise_exception = True`
        Sin eso, quien YA entró y no tiene el permiso acabaría en el
        formulario de acceso: lo llenaría otra vez y volvería al mismo sitio.
        Un bucle que parece un fallo del sistema y no una negativa. Con esto
        recibe el 403 ("Esto no es para tu cuenta").

        A una visita SIN sesión no le llega nunca: el `login_required` de
        urls.py la manda a entrar antes.

    VA PRIMERO EN LA LISTA DE CLASES
        `class X(PermisoRequeridoMixin, OtroMixin, ListView)`. Así el permiso
        se revisa antes que cualquier otra cosa, incluso antes de buscar el
        registro.
    """

    raise_exception = True
