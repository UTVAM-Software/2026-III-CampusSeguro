"""
El montaje que necesitan casi todas las pruebas: un campus y dos cuentas.

Vive aquí y no copiado en cada app porque entonces habría cinco versiones del
mismo `setUp`, y la que alguien olvide actualizar es la que da un falso
aprobado.

LAS PRUEBAS NO TOCAN db.sqlite3
    Django crea una base aparte para correrlas y la borra al terminar. Lo que
    haya en la de desarrollo no influye, y nada de lo que hagan aquí se queda.
"""

from django.test import TestCase

from apps.campus.models import Campus

from .models import Usuario

#: La contraseña de las cuentas de prueba. No es la de nadie: estas cuentas
#: existen solo mientras corre la prueba, en una base que se borra después.
CLAVE = "trayecto7bici"


class BaseConCuentas(TestCase):
    """Un campus, dos estudiantes, quien administra el campus y quien el sistema."""

    def setUp(self):
        self.campus = Campus.objects.create(
            nombre="Demo", direccion="x", latitud=20.101100, longitud=-98.759100
        )
        self.otro_campus = Campus.objects.create(
            nombre="Otro", direccion="y", latitud=19.432600, longitud=-99.133200
        )

        self.ana = Usuario.objects.create_user(
            correo="ana@x.edu", nombre="Ana", password=CLAVE, campus=self.campus
        )
        self.beto = Usuario.objects.create_user(
            correo="beto@x.edu", nombre="Beto", password=CLAVE, campus=self.campus
        )
        # Quien administra SU campus: el panel, los avisos, los puntos de
        # apoyo, revisar reportes.
        self.jefa = Usuario.objects.create_user(
            correo="jefa@x.edu", nombre="Jefa", password=CLAVE,
            campus=self.campus, rol="admin",
        )

        # Quien administra el SISTEMA: además, los campus y las cuentas. Son
        # los tres roles del proyecto anterior, y la diferencia importa: un
        # campus se lleva por delante los datos de toda su gente, y la lista
        # de cuentas es el directorio de la comunidad entera.
        self.mandamas = Usuario.objects.create_user(
            correo="mandamas@x.edu", nombre="Mandamas", password=CLAVE,
            campus=self.campus, rol="superadmin",
        )

    def entrar(self, usuario):
        """Deja la sesión abierta con esa cuenta y devuelve el cliente."""
        self.client.force_login(usuario)
        return self.client
