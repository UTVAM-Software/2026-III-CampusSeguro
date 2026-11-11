"""
Los viajes a los que se les pasó la hora límite.

CÓMO SE DISPARA, Y POR QUÉ ASÍ
    No hay proceso en segundo plano: la revisión la hacen la pantalla de
    inicio y la lista de viajes al dibujarse. Eso significa que si nadie abre
    Campus Seguro, nadie recibe el aviso. Para que llegara solo haría falta
    un programador de tareas en un servidor, y esto se instala en una laptop.

    Por eso también hay un comando, `manage.py revisar_viajes`, que es el que
    se programaría ese día. La lógica no cambia: cambia quién la llama.
"""

from django.utils import timezone

from .models import Viaje


def revisar_vencidos():
    """
    Avisa de todos los viajes cuya hora límite ya pasó.

    Devuelve cuántos viajes pasaron a «Alerta». Se puede llamar las veces que
    haga falta: un viaje avisado deja de estar «en curso», así que la
    siguiente llamada ya no lo encuentra.

    Se cuentan los viajes y no lo que devuelve cada aviso: ese número es a
    cuánta gente se avisó, y vale cero cuando el viaje no tiene acompañantes.
    Un viaje así también vence, y también tiene que contarse.
    """
    vencidos = list(Viaje.objects.filter(
        estado='en_curso',
        fecha_expiracion__isnull=False,
        fecha_expiracion__lt=timezone.now(),
    ))

    for viaje in vencidos:
        viaje.avisar_que_se_paso_la_hora()

    return len(vencidos)
