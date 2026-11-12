"""
Crear la cuenta que administra el sistema, sin preguntar nada.

    manage.py crear_superusuario --correo a@b.mx --clave "..." --campus 1

POR QUE NO SIRVE EL `createsuperuser` DE DJANGO
    Pregunta por la consola, y un instalador no tiene a nadie delante que
    conteste. El suyo con `--noinput` saca la clave de una variable de
    entorno, pero no pone el campus, y una cuenta sin campus abre la
    aplicacion con casi todas las pantallas vacias.

SI YA EXISTE, NO LA TOCA
    El instalador se puede volver a correr sobre una instalacion que ya
    estaba. Pisar la contrasena de quien administra seria la peor forma de
    enterarse.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.campus.models import Campus
from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Crea la cuenta de superadministrador sin pedir nada por consola.'

    def add_arguments(self, parser):
        parser.add_argument('--correo', required=True)
        parser.add_argument('--clave', required=True)
        parser.add_argument('--nombre', default='Administracion')
        parser.add_argument(
            '--campus',
            help='Id o nombre del campus. Si se omite, el primero que haya.',
        )

    def handle(self, *args, **opciones):
        correo = opciones['correo'].strip().lower()

        if Usuario.objects.filter(correo=correo).exists():
            self.stdout.write(f'La cuenta {correo} ya existe; no se toca.')
            return

        campus = self.buscar_campus(opciones.get('campus'))

        Usuario.objects.create_user(
            correo=correo,
            nombre=opciones['nombre'],
            password=opciones['clave'],
            campus=campus,
            rol='superadmin',
            is_staff=True,
            is_superuser=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Cuenta de superadministrador creada: {correo}'
        ))

    def buscar_campus(self, pedido):
        if pedido:
            campus = (
                Campus.objects.filter(pk=pedido).first() if pedido.isdigit()
                else Campus.objects.filter(nombre__icontains=pedido).first()
            )

            if campus is None:
                raise CommandError(f'No encontre el campus {pedido!r}.')

            return campus

        campus = Campus.objects.order_by('pk').first()

        if campus is None:
            raise CommandError(
                'No hay ningun campus. Corre antes herramientas/cargar_campus.py.'
            )

        return campus
