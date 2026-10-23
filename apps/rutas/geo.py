"""
Distancias sobre el mapa, sin dependencias.

Hace falta para una sola pregunta: ¿cuántas condiciones registradas hay cerca
de este recorrido? Y "cerca" quiere decir cerca de la LÍNEA, no del punto de
partida: un reporte a 30 m de la mitad del camino importa, y a 30 m en línea
recta del origen pero al otro lado de una barda, no tanto.

LA TIERRA SE APROXIMA A UN PLANO
    A estas distancias -cientos de metros, un par de kilómetros- la curvatura
    no se nota. Se convierten los grados a metros con el factor de la latitud
    y se mide en plano. El error a 20° de latitud y 2 km es de centímetros;
    la propia posición del GPS falla más que eso.
"""

import math

#: Cuántos metros mide un grado de latitud. Es prácticamente constante.
METROS_POR_GRADO = 111_320


def _a_metros(punto, referencia):
    """De (lat, lng) a metros en un plano, tomando `referencia` como origen."""
    lat, lng = punto
    lat0, lng0 = referencia

    # Los meridianos se juntan hacia los polos: un grado de longitud mide
    # menos cuanto más lejos del ecuador. Sin este coseno, un recorrido
    # este-oeste saldría un 6% más largo aquí en Hidalgo.
    return (
        (lng - lng0) * METROS_POR_GRADO * math.cos(math.radians(lat0)),
        (lat - lat0) * METROS_POR_GRADO,
    )


def distancia_metros(uno, otro):
    """Entre dos puntos (lat, lng)."""
    x, y = _a_metros(otro, uno)
    return math.hypot(x, y)


def _distancia_a_segmento(punto, a, b):
    """Del punto a lo más cercano del segmento a-b, todo ya en metros."""
    (px, py), (ax, ay), (bx, by) = punto, a, b
    dx, dy = bx - ax, by - ay

    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)

    # Dónde cae la proyección del punto sobre el segmento, de 0 a 1. Se
    # recorta a ese rango: fuera de él lo más cercano es un extremo, no la
    # prolongación de la recta.
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def distancia_a_ruta_metros(punto, ruta):
    """
    Del punto al trozo más cercano del recorrido.

    `ruta` es la lista de (lat, lng) que devuelve OSRM. Con menos de dos
    puntos no hay recorrido que medir.
    """
    if not ruta:
        return float('inf')

    if len(ruta) == 1:
        return distancia_metros(punto, ruta[0])

    referencia = ruta[0]
    p = _a_metros(punto, referencia)
    puntos = [_a_metros(q, referencia) for q in ruta]

    return min(
        _distancia_a_segmento(p, puntos[i], puntos[i + 1])
        for i in range(len(puntos) - 1)
    )


def longitud_metros(ruta):
    """Lo que mide el recorrido, sumando tramo a tramo."""
    return sum(
        distancia_metros(ruta[i], ruta[i + 1]) for i in range(len(ruta) - 1)
    )
