"""
Avisar de los viajes a los que se les paso la hora limite.

    .venv/Scripts/python.exe manage.py revisar_viajes

Es el que se programaria -con cron, o el Programador de tareas de Windows-
el dia que el proyecto viva en un servidor, para que el aviso no dependa de
que alguien abra la aplicacion. Se puede correr las veces que haga falta.
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
