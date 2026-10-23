"""
Cliente de OSRM: el recorrido a pie real entre dos puntos.

QUÉ APORTA
    La línea que de verdad siguen las calles, no la recta entre origen y
    destino. Sin esto, contar los reportes "cerca del camino" sería contarlos
    cerca de una línea que nadie va a caminar —una que cruza manzanas,
    edificios y una barranca si hace falta—.

QUÉ INSTANCIA, Y POR QUÉ NO LA DE DEMOSTRACIÓN
    `router.project-osrm.org` IGNORA el perfil: aunque se le pida `foot`,
    devuelve la ruta de coche. Los minutos que da son a velocidad de coche, y
    el trayecto pasa por vías que un peatón no usa. Enseñárselos a alguien
    que va caminando sería falso.

    Se usa la instancia de peatón de FOSSGIS, la que mueve el propio sitio de
    OpenStreetMap. Comprobado contra el servicio real entre UTVAM y la
    Escuela Superior de Tizayuca: 2404 m, 32 minutos. Eso son 4.5 km/h, una
    caminata de verdad.

    Detalle que confunde: en la URL, el segmento `/foot/` lo ignora OSRM. El
    perfil lo decide la INSTANCIA, o sea el host. Quien "arregle" el host y
    deje el segmento se llevará rutas de coche sin enterarse.

LA PETICIÓN SALIENTE SE ATA CORTO
    Es la única petición que este proyecto hace a un servicio ajeno, así que
    aquí es donde importa:

    - El host es fijo, de la configuración. De quien usa la aplicación nunca
      llega una dirección ni un identificador en texto: solo coordenadas, ya
      validadas, formateadas con %.6f. En la URL no puede entrar otra cosa
      que dígitos, punto y signo.
    - Las redirecciones, prohibidas. Sin eso, una respuesta 302 podría llevar
      la petición a una dirección interna de la red donde corre el servidor.
    - Hay tiempo máximo y tope de tamaño: un servicio gratuito y ajeno no
      puede dejar colgado a un trabajador del servidor para siempre.
"""

import json
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache

#: Cuánto se recuerda un trayecto ya consultado. Los servicios públicos de
#: OpenStreetMap son gratuitos y piden un uso comedido: dos personas que van
#: del mismo sitio al mismo sitio no tienen por qué generar dos peticiones.
CACHE_SEGUNDOS = 300

#: Decimales de las coordenadas en la clave de caché. Cuatro son ~11 m: dos
#: personas en la misma esquina comparten resultado, y no se guarda una
#: posición más precisa de la que hace falta.
CACHE_DECIMALES = 4

#: Lo máximo que se lee de la respuesta. Una ruta de dos kilómetros ocupa
#: unos 10 KB; esto es holgado y a la vez impide que una respuesta enorme
#: -por error o a propósito- se coma la memoria del servidor.
MAX_BYTES = 2 * 1024 * 1024

#: Segundos de espera. Pasado esto se da por no disponible: más vale decirlo
#: que tener a alguien mirando una pantalla parada.
ESPERA = 8


class ServicioNoDisponible(Exception):
    """
    No se pudo obtener el recorrido.

    Se lanza a propósito en vez de devolver una línea recta inventada. Una
    ruta falsa haría que el recuento de condiciones saliera sobre un camino
    que no existe, y daría un número con aspecto de válido. La pantalla tiene
    que decir que el servicio no respondió.
    """


def _url(origen, destino):
    """
    La dirección de la consulta, con las coordenadas como números y nada más.

    OSRM las quiere en orden longitud,latitud —al revés de como se escriben
    en todas partes—. Es el error más fácil de cometer aquí y manda la
    consulta al otro lado del mundo.
    """
    return (
        f"{settings.OSRM_HOST}/route/v1/foot/"
        f"{origen[1]:.6f},{origen[0]:.6f};{destino[1]:.6f},{destino[0]:.6f}"
        "?alternatives=true&overview=full&geometries=geojson"
    )


def rutas(origen, destino):
    """
    Los caminos a pie entre dos puntos (lat, lng).

    Devuelve una lista de diccionarios con `puntos` —la lista de (lat, lng)
    del recorrido—, `metros` y `minutos`. Vacía nunca: si no hay camino,
    lanza `ServicioNoDisponible`, que es distinto de "hay cero rutas".
    """
    clave = "osrm:{:.{d}f},{:.{d}f}:{:.{d}f},{:.{d}f}".format(
        *origen, *destino, d=CACHE_DECIMALES
    )
    guardado = cache.get(clave)

    if guardado is not None:
        return guardado

    peticion = urllib.request.Request(
        _url(origen, destino),
        headers={"User-Agent": "Campus Seguro (proyecto escolar)"},
    )

    try:
        with _abridor().open(peticion, timeout=ESPERA) as respuesta:
            datos = json.loads(respuesta.read(MAX_BYTES).decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as fallo:
        raise ServicioNoDisponible(str(fallo)) from fallo

    if datos.get("code") != "Ok" or not datos.get("routes"):
        raise ServicioNoDisponible(datos.get("code", "sin respuesta"))

    encontradas = [
        {
            # De vuelta a (lat, lng), que es como se escribe en el resto del
            # proyecto. Dejarlo al revés aquí sería sembrar el mismo error
            # más adelante.
            "puntos": [(lat, lng) for lng, lat in ruta["geometry"]["coordinates"]],
            "metros": int(ruta["distance"]),
            "minutos": int(round(ruta["duration"] / 60)),
        }
        for ruta in datos["routes"]
    ]

    cache.set(clave, encontradas, CACHE_SEGUNDOS)
    return encontradas


def _abridor():
    """Un abridor que NO sigue redirecciones."""

    class SinRedirecciones(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    return urllib.request.build_opener(SinRedirecciones)
