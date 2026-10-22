"""
Cómo se cuentan los tiempos en pantalla.

`timesince` de Django dice "0 minutos" para algo que acaba de pasar, y eso se
lee raro justo donde más se mira: el reporte que alguien acaba de publicar.
Este filtro dice "hace un momento" en ese caso y delega en Django para todo lo
demás, que ya lo hace bien y traducido.

NO VIVE EN UNA APP, Y ES A PROPÓSITO
    Las etiquetas de plantilla suelen ir dentro de una app, pero esta no es de
    ninguna: la usan reportes, viajes y comunicación. Se registra a mano en
    TEMPLATES['OPTIONS']['libraries'], que es la forma que da Django para
    justamente esto, en vez de inventar una app vacía para colgarla.
"""

from django import template
from django.utils import timezone
from django.utils.timesince import timesince

register = template.Library()

#: Por debajo de esto no se dan números: "hace un momento" es más honesto que
#: "hace 14 segundos", que sugiere una precisión que a nadie le sirve.
UN_MOMENTO = 60


@register.filter
def hace(fecha):
    """'hace un momento', 'hace 3 minutos', 'hace 2 días'."""
    if not fecha:
        return ""

    segundos = (timezone.now() - fecha).total_seconds()

    # Una fecha futura no debería existir, pero si llega por un reloj
    # desajustado, decir "hace -5 minutos" sería peor que no decir nada.
    if segundos < UN_MOMENTO:
        return "hace un momento"

    # `depth=1` deja una sola unidad: "hace 3 dias" en vez de "hace 3 dias, 5
    # horas". En una lista lo que se quiere saber es si fue hoy o hace una
    # semana, no la cuenta exacta.
    return f"hace {timesince(fecha, depth=1)}"
