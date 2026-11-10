"""
Los viajes a los que se les pasó la hora límite.

CÓMO SE DISPARA, Y POR QUÉ ASÍ
    No hay un proceso en segundo plano. La revisión se hace al abrir la
    aplicación: la pantalla de inicio y la lista de viajes la llaman antes de
    dibujarse.

    Lo honesto es decir qué significa eso: si nadie abre Campus Seguro, nadie
    recibe el aviso. Para que llegara sin que nadie mire haría falta un
    programador de tareas -cron, Celery- corriendo en un servidor, y este
    proyecto se instala en una laptop.

    Por eso lo de aquí también se puede llamar desde fuera:

        .venv/Scripts/python.exe manage.py revisar_viajes

    Ese comando es el que se programaría el día que esto viva en un servidor.
    La lógica no cambia: cambia quién la llama.

ES BARATA
    `se_paso_la_hora` se traduce a una consulta con tres condiciones sobre
    campos indexables, y en el caso normal no devuelve nada. Lo que cuesta
    -escribir notificaciones- solo ocurre cuando de verdad venció un viaje.
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
