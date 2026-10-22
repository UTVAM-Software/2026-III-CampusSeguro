"""
De una clave a su icono, para las plantillas.

El mapa de cada tipo vive en su modelo, pegado a la lista de tipos. Aquí solo
está el puente para poder usarlo desde una plantilla cuando lo que hay a mano
es la clave suelta —en el filtro del mapa, por ejemplo, donde se recorre
`Reporte.TIPOS` y de cada fila solo llega `('obras', 'Obras')`—.

    {% include '_icono.html' with nombre=valor|icono_de_tipo %}
"""

from django import template

register = template.Library()


@register.filter
def icono_de_tipo(valor):
    """El icono de un tipo de reporte. `otros` si esa clave no existe."""
    from apps.reportes.models import Reporte

    return Reporte.ICONOS.get(valor, 'otros')
