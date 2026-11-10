"""
El aviso de que se pasó la hora límite.

Es la pieza que convierte «comparto mi ubicación» en «alguien se entera si no
llego». Hasta ahora el estado `alerta` existía en el modelo y la pantalla del
viaje sabía dibujarlo, pero nadie lo ponía nunca: la hora pasaba y no ocurría
nada.
"""

from django.core.management import call_command
from django.utils import timezone

from apps.comunicacion.models import Notificacion
from apps.usuarios.tests_base import BaseConCuentas

from .alertas import revisar_vencidos
from .models import UbicacionViaje, Viaje, ViajeAcompanante


class BaseConViajeVencido(BaseConCuentas):
    def setUp(self):
        super().setUp()

        self.viaje = Viaje.objects.create(
            usuario=self.ana, origen='Biblioteca', destino='Paradero',
            fecha_expiracion=timezone.now() - timezone.timedelta(minutes=5),
        )
        self.acompana = ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='aceptado',
        )
        Notificacion.objects.all().delete()


class SePasoLaHoraTests(BaseConViajeVencido):
    def test_el_viaje_pasa_a_alerta(self):
        self.assertEqual(revisar_vencidos(), 1)
        self.viaje.refresh_from_db()

        self.assertEqual(self.viaje.estado, 'alerta')

    def test_se_avisa_a_quien_acompana(self):
        revisar_vencidos()

        aviso = Notificacion.objects.get(usuario=self.beto)

        self.assertIn('no ha confirmado que llegó', aviso.titulo)
        self.assertIn('Paradero', aviso.mensaje)

    def test_tambien_se_le_recuerda_a_quien_viaja(self):
        """
        Lo más probable es que haya llegado y se le olvidara decirlo, y eso
        se arregla solo con recordárselo.
        """
        revisar_vencidos()

        aviso = Notificacion.objects.get(usuario=self.ana)

        self.assertEqual(aviso.titulo, '¿Llegaste bien?')

    def test_no_se_borran_las_ubicaciones(self):
        """
        Lo contrario de cerrar el viaje, y a propósito: las posiciones son
        justo lo que hace falta cuando alguien no ha llegado. Una alerta dice
        «ve a mirar»; borrar el rastro ahí sería lo contrario de ayudar.
        """
        UbicacionViaje.objects.create(
            viaje=self.viaje, latitud=20.1, longitud=-98.7,
        )

        revisar_vencidos()

        self.assertEqual(self.viaje.ubicaciones.count(), 1)

    def test_no_se_avisa_dos_veces(self):
        """
        Lo revisan la pantalla de inicio y la lista de viajes, así que esto
        corre a cada rato. Un aviso repetido en cada recarga sería una
        campana que nadie vuelve a mirar.
        """
        revisar_vencidos()
        revisar_vencidos()
        revisar_vencidos()

        self.assertEqual(Notificacion.objects.filter(usuario=self.beto).count(), 1)

    def test_a_quien_solo_fue_invitado_no_se_le_avisa(self):
        """
        Invitar a alguien no puede ser una forma de mandarle alarmas sin que
        lo haya aceptado.
        """
        self.acompana.estado = 'invitado'
        self.acompana.save()

        revisar_vencidos()

        self.assertFalse(Notificacion.objects.filter(usuario=self.beto).exists())


class LoQueNoSeTocaTests(BaseConCuentas):
    def test_un_viaje_sin_hora_limite_no_vence_nunca(self):
        Viaje.objects.create(
            usuario=self.ana, origen='A', destino='B', fecha_expiracion=None,
        )

        self.assertEqual(revisar_vencidos(), 0)

    def test_un_viaje_con_la_hora_por_delante_no_se_toca(self):
        viaje = Viaje.objects.create(
            usuario=self.ana, origen='A', destino='B',
            fecha_expiracion=timezone.now() + timezone.timedelta(hours=1),
        )

        self.assertEqual(revisar_vencidos(), 0)
        viaje.refresh_from_db()

        self.assertEqual(viaje.estado, 'en_curso')

    def test_un_viaje_ya_cerrado_no_salta(self):
        """Llegaste tarde pero llegaste: nadie tiene que enterarse de nada."""
        viaje = Viaje.objects.create(
            usuario=self.ana, origen='A', destino='B',
            fecha_expiracion=timezone.now() - timezone.timedelta(hours=1),
        )
        viaje.cerrar('llego_bien')

        self.assertEqual(revisar_vencidos(), 0)
        viaje.refresh_from_db()

        self.assertEqual(viaje.estado, 'llego_bien')

    def test_un_viaje_vencido_sin_acompanantes_tambien_cuenta(self):
        """
        `avisar_que_se_paso_la_hora()` devuelve a cuánta gente avisó, y eso
        vale cero sin acompañantes. Contar eso en vez de los viajes dejaría
        fuera precisamente a quien viaja sola.
        """
        Viaje.objects.create(
            usuario=self.ana, origen='A', destino='B',
            fecha_expiracion=timezone.now() - timezone.timedelta(minutes=1),
        )

        self.assertEqual(revisar_vencidos(), 1)


class AlAbrirLaAppTests(BaseConViajeVencido):
    def test_la_pantalla_de_inicio_lo_revisa(self):
        """
        No hay proceso en segundo plano: la revisión la dispara abrir la
        aplicación. Si esto deja de llamarse, la alerta no suena nunca.
        """
        self.entrar(self.beto).get('/')
        self.viaje.refresh_from_db()

        self.assertEqual(self.viaje.estado, 'alerta')
        self.assertTrue(Notificacion.objects.filter(usuario=self.beto).exists())

    def test_la_lista_de_viajes_tambien(self):
        self.entrar(self.ana).get('/viajes/')
        self.viaje.refresh_from_db()

        self.assertEqual(self.viaje.estado, 'alerta')


class ElComandoTests(BaseConViajeVencido):
    def test_el_comando_hace_lo_mismo(self):
        """
        Es el que se programaría el día que esto viva en un servidor, así que
        tiene que hacer exactamente lo mismo que la revisión al abrir.
        """
        call_command('revisar_viajes')
        self.viaje.refresh_from_db()

        self.assertEqual(self.viaje.estado, 'alerta')
        self.assertTrue(Notificacion.objects.filter(usuario=self.beto).exists())
