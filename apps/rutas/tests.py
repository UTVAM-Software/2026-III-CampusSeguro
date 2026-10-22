"""
Comparar caminos.

Lo que se prueba aqui es sobre todo lo que la pantalla NO puede hacer:
inventarse una ruta cuando el servicio no responde, contar reportes de otro
campus, o contar cosas que estan lejos del camino.
"""

from unittest.mock import patch

from apps.reportes.models import Reporte
from apps.usuarios.tests_base import BaseConCuentas

from .geo import distancia_a_ruta_metros, distancia_metros
from .osrm import ServicioNoDisponible

#: Un tramo recto de unos 200 m hacia el este, en Tizayuca.
TRAMO = [(19.8637, -98.9820), (19.8637, -98.9801)]


class GeometriaTests(BaseConCuentas):
    def test_un_grado_de_latitud_son_unos_111_km(self):
        self.assertAlmostEqual(
            distancia_metros((19.0, -98.0), (20.0, -98.0)), 111_320, delta=50
        )

    def test_la_longitud_encoge_lejos_del_ecuador(self):
        """
        Los meridianos se juntan hacia los polos. Sin el coseno de la
        latitud, un recorrido este-oeste saldria un 6% mas largo aqui.
        """
        recorrido = distancia_metros((20.0, -98.0), (20.0, -97.0))

        self.assertLess(recorrido, 111_320)
        self.assertAlmostEqual(recorrido, 111_320 * 0.9397, delta=200)

    def test_mide_a_la_linea_y_no_a_los_extremos(self):
        """
        Un punto justo encima de la mitad del tramo esta cerca, aunque de los
        dos extremos este lejos. Es la diferencia entre "cerca del camino" y
        "cerca de donde sales".
        """
        medio = (19.86375, -98.98105)

        self.assertLess(distancia_a_ruta_metros(medio, TRAMO), 20)
        self.assertGreater(distancia_metros(medio, TRAMO[0]), 80)

    def test_un_punto_lejos_sale_lejos(self):
        self.assertGreater(distancia_a_ruta_metros((19.8700, -98.9820), TRAMO), 600)


class CompararCaminosTests(BaseConCuentas):
    def setUp(self):
        super().setUp()

        self.campus.latitud, self.campus.longitud = 19.8637, -98.9820
        self.campus.save()

        self.cerca = Reporte.objects.create(
            usuario=self.ana, campus=self.campus, tipo='obras',
            descripcion='Zanja sobre el camino', latitud=19.86375, longitud=-98.98105,
        )
        self.lejos = Reporte.objects.create(
            usuario=self.ana, campus=self.campus, tipo='fuga',
            descripcion='Fuga a varias cuadras', latitud=19.8700, longitud=-98.9820,
        )
        self.de_otro = Reporte.objects.create(
            usuario=self.beto, campus=self.otro_campus, tipo='obras',
            descripcion='De otra universidad', latitud=19.86375, longitud=-98.98105,
        )

    def consultar(self, usuario=None):
        return self.entrar(usuario or self.ana).get('/rutas/', {
            'origen': 'A', 'destino': 'B',
            'latitud_origen': '19.863700', 'longitud_origen': '-98.982000',
            'latitud_destino': '19.863700', 'longitud_destino': '-98.980100',
        })

    def test_cuenta_lo_que_esta_sobre_el_camino(self):
        with patch('apps.rutas.views.rutas', return_value=[
            {'puntos': TRAMO, 'metros': 200, 'minutos': 3}
        ]):
            caminos = self.consultar().context['caminos']

        self.assertEqual(len(caminos), 1)
        self.assertEqual([r.pk for r in caminos[0]['reportes']], [self.cerca.pk])

    def test_no_cuenta_los_de_otro_campus(self):
        """
        Aunque caigan justo encima del camino. Lo de otra universidad no es
        de su comunidad, y contarlo inflaria el numero sin que nadie sepa por
        que.
        """
        with patch('apps.rutas.views.rutas', return_value=[
            {'puntos': TRAMO, 'metros': 200, 'minutos': 3}
        ]):
            caminos = self.consultar().context['caminos']

        self.assertNotIn(self.de_otro.pk, [r.pk for r in caminos[0]['reportes']])

    def test_no_cuenta_los_viejos(self):
        """
        Una lampara fundida hace ocho meses seguramente ya se arreglo.
        Contarla diria algo falso del camino de hoy.
        """
        from django.utils import timezone

        Reporte.objects.filter(pk=self.cerca.pk).update(
            fecha_creacion=timezone.now() - timezone.timedelta(days=90)
        )

        with patch('apps.rutas.views.rutas', return_value=[
            {'puntos': TRAMO, 'metros': 200, 'minutos': 3}
        ]):
            caminos = self.consultar().context['caminos']

        self.assertEqual(caminos[0]['reportes'], [])

    def test_si_el_servicio_falla_no_se_inventa_una_recta(self):
        """
        Lo mas importante de este archivo. Una ruta inventada daria un
        recuento sobre un camino que nadie va a andar, con aspecto de dato
        bueno. La pantalla tiene que decir que el servicio no respondio.
        """
        with patch('apps.rutas.views.rutas', side_effect=ServicioNoDisponible('timeout')):
            respuesta = self.consultar()

        self.assertIsNone(respuesta.context.get('caminos'))
        self.assertContains(respuesta, 'no respondió')

    def test_sin_coordenadas_solo_sale_el_formulario(self):
        respuesta = self.entrar(self.ana).get('/rutas/')

        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.context.get('caminos'))

    def test_una_latitud_imposible_no_llega_al_servicio(self):
        """Estas coordenadas acaban dentro de una direccion que sale del servidor."""
        with patch('apps.rutas.views.rutas') as servicio:
            self.entrar(self.ana).get('/rutas/', {
                'origen': 'A', 'destino': 'B',
                'latitud_origen': '500.000000', 'longitud_origen': '-98.982000',
                'latitud_destino': '19.863700', 'longitud_destino': '-98.980100',
            })

        servicio.assert_not_called()

    def test_sin_sesion_no_se_consulta(self):
        self.assertEqual(self.client.get('/rutas/').status_code, 302)
