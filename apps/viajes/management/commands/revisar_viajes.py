"""
Avisar de los viajes a los que se les paso la hora limite.

    .venv/Scripts/python.exe manage.py revisar_viajes

POR QUE UN COMANDO ADEMAS DE LA REVISION AL ABRIR LA APP
    Hoy la revision la disparan la pantalla de inicio y la lista de viajes,
    asi que si nadie abre Campus Seguro, nadie recibe el aviso. Es la
    limitacion de instalar esto en una laptop en vez de un servidor.

    Este comando es el que se programaria -con cron, o el Programador de
    tareas de Windows- el dia que el proyecto viva en un servidor. La logica
    es la misma; cambia quien la llama.

    Se puede correr las veces que haga falta: un viaje ya avisado deja de
    estar en curso y la siguiente vuelta no lo encuentra.
"""

from django.core.management.base import BaseCommand

from apps.viajes.alertas import revisar_vencidos


class Command(BaseCommand):
    help = 'Avisa a quien acompana de los viajes cuya hora limite ya paso.'

    def handle(self, *args, **opciones):
        cuantos = revisar_vencidos()

        if not cuantos:
            self.stdout.write('Ningun viaje se paso de la hora.')
            return

        self.stdout.write(self.style.SUCCESS(
            f'{cuantos} viaje(s) pasaron a Alerta y se aviso a quien los acompana.'
        ))
