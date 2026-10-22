"""Lo que toda plantilla recibe sin pedirlo."""

from pathlib import Path

from django.conf import settings


def version_css(request):
    """
    Un número que cambia cada vez que se guarda la hoja de estilos.

    PARA QUÉ
        El navegador se queda con la hoja que ya bajó y no vuelve a pedirla:
        el servidor de desarrollo no manda cabeceras que le digan cuánto dura,
        así que el navegador decide por su cuenta. Resultado: se toca el CSS,
        se recarga la página y no cambia nada. Pasa a diario y se pierde un
        rato largo buscando el fallo en el sitio equivocado.

        Con esto la dirección de la hoja lleva pegada la fecha del archivo:

            /static/css/estilos.css?v=1792015200

        Al guardar el archivo cambia la fecha, cambia la dirección, y el
        navegador la pide de nuevo porque para él es otra hoja.

    SI EL ARCHIVO NO ESTÁ
        Devuelve vacío en vez de romper la página. Una hoja sin versión se ve
        igual, solo vuelve el problema de la caché.
    """
    hoja = Path(settings.BASE_DIR) / "static" / "css" / "estilos.css"

    try:
        return {"VERSION_CSS": int(hoja.stat().st_mtime)}
    except OSError:
        return {"VERSION_CSS": ""}


def navegacion(request):
    """
    Las áreas de la aplicación, para la barra de abajo y la lateral.

    Va en un procesador de contexto y no en cada vista porque lo necesitan
    TODAS las pantallas con sesión: ponerlo vista por vista sería treinta
    sitios donde olvidarlo, y la pantalla que lo olvide se queda sin barra.
    """
    if not request.user.is_authenticated:
        return {}

    from apps.comunicacion.models import Notificacion
    from config.navegacion import construir

    mias = Notificacion.objects.filter(usuario=request.user)

    return {
        "navegacion": construir(request.user),
        # Para la campana, que sale en TODAS las pantallas con sesion. Por eso
        # va aqui y no en cada vista: serian treinta sitios donde olvidarlo, y
        # la pantalla que lo olvide ensena la campana a cero teniendo avisos
        # sin leer.
        "sin_leer": mias.filter(leida=False).count(),
        # Las ultimas, para el panel que cuelga de la campana. Cinco: el panel
        # es un vistazo, no la bandeja -esa esta a un clic, en "Ver todas"-.
        "notificaciones_recientes": mias.order_by("-fecha")[:5],
    }


#: De que area es cada ruta. La clave es el principio del nombre de la ruta.
AREA_DE_LA_RUTA = [
    ("index", "inicio"),
    ("mapa", "mapa"),
    ("punto", "mapa"),
    # Los campus y las correcciones solo se administran desde el panel.
    ("campus", "panel"),
    ("correccion", "panel"),
    ("reporte-create", "reportar"),
    ("reporte", None),
    ("confirmacion", None),
    ("viaje", "viajes"),
    ("acompanante", "viajes"),
    ("ubicacion", "viajes"),
    ("destino", "viajes"),
    ("perfil", "perfil"),
    ("cambiar-clave", "perfil"),
    ("cerrar-otras-sesiones", "perfil"),
    ("aviso", None),
    ("notificacion", None),
    ("panel", "panel"),
    ("usuario", "panel"),
    ("grupo", "panel"),
    ("permiso", "panel"),
]


def seccion_activa(request):
    """
    En que area de la navegacion estas, para marcarla en la lateral.

    Se deduce del nombre de la ruta en vez de que cada vista lo declare:
    serian treinta sitios donde ponerlo, y la que se olvide deja la lateral
    sin marcar sin que nadie se entere.

    Las que mapean a None -la lista de reportes, las confirmaciones- no marcan
    ninguna: "Reportar" es la pestana de CREAR uno, y marcarla al mirar la
    lista diria que estas haciendo algo que no estas haciendo.
    """
    ruta = getattr(request, "resolver_match", None)

    if ruta is None or not ruta.url_name:
        return {}

    for principio, area in AREA_DE_LA_RUTA:
        if ruta.url_name == principio or ruta.url_name.startswith(principio + "-"):
            return {"seccion_activa": area} if area else {}

    return {}
