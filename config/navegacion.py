"""
Las áreas de la aplicación.

Viven en un solo sitio para que la barra de abajo del móvil y la lateral del
escritorio no puedan separarse: con dos listas, la que alguien olvide
actualizar es la que deja una sección sin puerta.

SON CINCO, NO NUEVE
    El proyecto tiene nueve listas, pero la mayoría son de cosas que cuelgan
    de otra: los acompañantes de un viaje, las ubicaciones de un viaje, las
    confirmaciones de un reporte. Esas se llegan desde su pantalla madre y
    desde el menú del inicio, que es el directorio completo.

    Meterlas aquí dejaría una barra de nueve pestañas que no cabe en ningún
    teléfono.

LOS AVISOS NO ESTÁN AQUÍ: ESTÁN EN LA CAMPANA
    Tenían su pestaña, y era una pestaña que la mayoría de los días no lleva
    a nada nuevo. La campana de arriba dice cuántos sin leer hay, que es la
    única pregunta que de verdad se hace sobre ellos, y ocupa un icono en
    vez de un quinto del ancho de la pantalla.

    Así queda sitio para Perfil, que antes solo se llegaba pulsando el avatar
    —un objetivo que nadie sabe que es pulsable—.

ESCONDER UN ENLACE NO ES AUTORIZAR
    La entrada de Usuarios solo sale si el rol lo permite, pero eso es
    únicamente la interfaz: quien escriba la dirección se encuentra el 403 que
    pone la vista. Lo de aquí es no ofrecer puertas que se cierran en la cara.

CADA ÁREA DICE QUÉ PERMISO PIDE, Y ES EL MISMO QUE PIDE SU VISTA
    Con la lista fija, un usuario externo veía las cinco pestañas y cuatro le
    respondían 403 —incluida Inicio, que es a donde cae al entrar—. La barra
    ofrece ahora solo lo que esa cuenta puede abrir de verdad.

    El permiso que se escribe aquí tiene que ser el `permission_required` de
    la vista a la que lleva. Si no coinciden, vuelve a haber puertas pintadas.
"""

from django.urls import reverse

# (clave, etiqueta, nombre de ruta, icono, destacada, permiso)
#
# `destacada` es la del centro de la barra del móvil, la que se dibuja como un
# botón redondo: reportar algo es la acción que tiene que estar siempre a un
# toque, no a tres.
AREAS = [
    ("inicio", "Inicio", "index", "inicio", False, "campus.view_campus"),
    ("mapa", "Mapa", "mapa", "mapa", False, "reportes.view_reporte"),
    ("reportar", "Reportar", "reporte-create", "reportar", True, "reportes.add_reporte"),
    ("viajes", "Viajes", "viaje-list", "viajes", False, "viajes.view_viaje"),
    ("perfil", "Perfil", "perfil", "perfil", False, "usuarios.change_usuario"),
    ("panel", "Panel", "panel", "escudo", False, "usuarios.administrar_campus"),
]


def construir(usuario):
    """La lista que se dibuja, según quién esté mirando."""
    return [
        {
            "clave": clave,
            "etiqueta": etiqueta,
            "url": reverse(ruta),
            "icono": icono,
            "destacada": destacada,
        }
        for clave, etiqueta, ruta, icono, destacada, permiso in AREAS
        if usuario.has_perm(permiso)
    ]
