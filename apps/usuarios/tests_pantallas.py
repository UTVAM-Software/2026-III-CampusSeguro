"""
Que todas las pantallas carguen.

POR QUÉ HACE FALTA UNA PRUEBA PARA ALGO TAN TONTO
    Una plantilla rota no rompe ninguna de las otras pruebas: aquellas miran
    permisos y datos, no HTML. Un `{% if %}` mal escrito, un `{% url %}` con
    el nombre cambiado o un filtro que no está cargado solo salen cuando
    alguien abre esa página —y si es una que se visita poco, sale en la
    demostración delante del profesor.

    Esto recorre todas las pantallas con sesión y comprueba que devuelven 200.
    No juzga el diseño; comprueba que existen y que Django sabe dibujarlas.

NO SUSTITUYE A LAS PRUEBAS DE PERMISOS
    Aquí todo se mira con la cuenta que puede. Quién puede ver qué está en las
    pruebas de cada app, que es donde tiene que estar.
"""

from apps.campus.models import Campus, PuntoApoyo
from apps.comunicacion.models import Aviso, Notificacion
from apps.reportes.models import Reporte, ReporteConfirmacion
from apps.viajes.models import UbicacionViaje, Viaje, ViajeAcompanante

from .tests_base import BaseConCuentas


class PantallasQueCarganTests(BaseConCuentas):
    def setUp(self):
        super().setUp()

        self.punto = PuntoApoyo.objects.create(
            campus=self.campus, nombre="Enfermería", tipo="enfermeria",
            latitud=20.101100, longitud=-98.759100, horario="8 a 20",
        )
        self.reporte = Reporte.objects.create(
            usuario=self.ana, campus=self.campus, tipo="iluminacion",
            descripcion="Lámpara fundida", latitud=20.101100, longitud=-98.759100,
        )
        ReporteConfirmacion.objects.create(
            reporte=self.reporte, usuario=self.beto, confirma=True, comentario="Sigue",
        )
        self.viaje = Viaje.objects.create(
            usuario=self.ana, origen="Biblioteca", destino="Paradero",
        )
        self.acompanante = ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado="aceptado",
        )
        self.ubicacion = UbicacionViaje.objects.create(
            viaje=self.viaje, latitud=20.101100, longitud=-98.759100,
        )
        self.aviso = Aviso.objects.create(
            campus=self.campus, autor=self.jefa, titulo="Obra", contenido="Pasillo cerrado",
        )
        self.notificacion = Notificacion.objects.create(
            usuario=self.ana, titulo="Hola", mensaje="Un mensaje",
        )

    def comprobar(self, usuario, direcciones):
        c = self.entrar(usuario)

        for direccion in direcciones:
            with self.subTest(direccion=direccion):
                self.assertEqual(c.get(direccion).status_code, 200)

    def test_las_pantallas_de_cualquiera(self):
        self.comprobar(self.ana, [
            '/',
            '/mapa/', '/mapa/?categoria=obras', '/mapa/?categoria=noexiste',
            '/puntos-apoyo/', f'/puntos-apoyo/{self.punto.pk}/',
            '/reportes/', f'/reportes/{self.reporte.pk}/', '/reportes/create/',
            '/confirmaciones/',
            '/viajes/', f'/viajes/{self.viaje.pk}/', '/viajes/create/',
            f'/viajes/{self.viaje.pk}/update/',
            '/destinos/', '/destinos/create/',
            '/acompanantes/', f'/acompanantes/{self.acompanante.pk}/',
            '/acompanantes/create/',
            '/ubicaciones/', f'/ubicaciones/{self.ubicacion.pk}/', '/ubicaciones/create/',
            '/avisos/', f'/avisos/{self.aviso.pk}/',
            '/notificaciones/', f'/notificaciones/{self.notificacion.pk}/',
            f'/usuarios/{self.ana.pk}/', f'/usuarios/{self.ana.pk}/update/',
            '/perfil/', '/perfil/?seccion=seguridad', '/perfil/contrasena/',
            '/campus/',
        ])

    def test_las_pantallas_de_quien_administra_un_campus(self):
        self.comprobar(self.jefa, [
            '/panel/', '/correcciones/',
            '/puntos-apoyo/create/', f'/puntos-apoyo/{self.punto.pk}/update/',
            f'/puntos-apoyo/{self.punto.pk}/delete/',
            '/campus/', f'/campus/{self.campus.pk}/',
            '/avisos/create/', f'/avisos/{self.aviso.pk}/update/',
        ])

    def test_las_pantallas_de_la_superadministracion(self):
        """Los campus y las cuentas. El reparto del proyecto anterior."""
        self.comprobar(self.mandamas, [
            '/usuarios/', f'/usuarios/{self.ana.pk}/',
            '/usuarios/create/', f'/usuarios/{self.ana.pk}/update/',
            '/campus/create/', f'/campus/{self.campus.pk}/update/',
        ])

    def test_las_pantallas_sin_sesion(self):
        self.assertEqual(self.client.get('/entrar/').status_code, 200)
        self.assertEqual(self.client.get('/registro/').status_code, 200)

    def test_un_viaje_cerrado_tambien_dibuja_su_pantalla(self):
        """
        El detalle cambia de forma según el estado, y cada rama es HTML que
        nadie más recorre. Un fallo en la de "cancelado" solo aparecería el
        día que alguien cancelase un viaje.
        """
        c = self.entrar(self.ana)

        for estado in ('llego_bien', 'cancelado', 'alerta', 'en_curso'):
            with self.subTest(estado=estado):
                Viaje.objects.filter(pk=self.viaje.pk).update(estado=estado)
                self.assertEqual(
                    c.get(f'/viajes/{self.viaje.pk}/').status_code, 200
                )


class InicioTests(BaseConCuentas):
    """
    Lo que se ve al abrir, cuando no hay nada que ver.

    Es el estado en el que está una cuenta recién creada, y el que se ve en
    una demostración: si el inicio se queda en blanco, parece que la
    aplicación está rota.
    """

    def test_sin_viajes_ofrece_planificar_uno(self):
        respuesta = self.entrar(self.ana).get('/')

        self.assertContains(respuesta, 'No tienes viajes en curso')
        self.assertContains(respuesta, 'Planificar viaje')

    def test_sin_reportes_ni_puntos_lo_dice_y_no_ofrece_crearlos(self):
        """
        Sin botón a propósito: "Reportar situación" ya está arriba de esta
        misma pantalla, y los puntos de apoyo los registra quien administra
        —ofrecer esa puerta a quien estudia sería mandarlo a un 403—.
        """
        respuesta = self.entrar(self.ana).get('/')

        self.assertContains(respuesta, 'No hay situaciones registradas')
        self.assertContains(respuesta, 'Aún no hay puntos de apoyo')
        self.assertNotContains(respuesta, 'Nuevo punto de apoyo')

    def test_un_aviso_caducado_no_sale_en_el_inicio(self):
        """
        Lo que se enseña aquí se da por vigente. Un aviso que caducó la
        semana pasada presentado como de hoy es información falsa.
        """
        from apps.comunicacion.models import Aviso

        ayer = __import__('django.utils', fromlist=['timezone']).timezone.localdate()
        ayer = ayer - __import__('datetime').timedelta(days=1)

        Aviso.objects.create(
            campus=self.campus, autor=self.jefa, titulo='Caducado',
            contenido='x', fecha_expiracion=ayer,
        )
        Aviso.objects.create(
            campus=self.campus, autor=self.jefa, titulo='Vigente', contenido='x',
        )

        respuesta = self.entrar(self.ana).get('/')

        self.assertContains(respuesta, 'Vigente')
        self.assertNotContains(respuesta, 'Caducado')


class MapaTests(BaseConCuentas):
    """
    El mapa: qué se enseña y qué deja fuera el filtro.

    El filtro vive en la dirección, así que estas pruebas son las que
    comprueban que una dirección escrita a mano no puede sacar nada que no
    debería salir.
    """

    def setUp(self):
        super().setUp()

        self.obras = Reporte.objects.create(
            usuario=self.ana, campus=self.campus, tipo='obras',
            descripcion='Zanja abierta', latitud=20.1, longitud=-98.7,
        )
        self.fuga = Reporte.objects.create(
            usuario=self.ana, campus=self.campus, tipo='fuga',
            descripcion='Agua en el pasillo', latitud=20.2, longitud=-98.8,
        )
        self.de_otro_campus = Reporte.objects.create(
            usuario=self.beto, campus=self.otro_campus, tipo='obras',
            descripcion='No es de aquí', latitud=19.4, longitud=-99.1,
        )

    def test_sin_filtro_salen_los_de_tu_campus_y_solo_esos(self):
        reportes = self.entrar(self.ana).get('/mapa/').context['reportes']

        self.assertEqual({r.pk for r in reportes}, {self.obras.pk, self.fuga.pk})

    def test_el_filtro_recorta(self):
        reportes = self.entrar(self.ana).get('/mapa/?categoria=obras').context['reportes']

        self.assertEqual([r.pk for r in reportes], [self.obras.pk])

    def test_se_pueden_elegir_varias(self):
        respuesta = self.entrar(self.ana).get('/mapa/?categoria=obras&categoria=fuga')

        self.assertEqual(len(respuesta.context['reportes']), 2)

    def test_una_categoria_inventada_se_tira(self):
        """
        Lo que llega por la dirección se cruza con las categorías que
        existen. Si no, escribir cualquier cosa daría una lista vacía y
        parecería que no hay nada registrado.
        """
        respuesta = self.entrar(self.ana).get('/mapa/?categoria=../../etc/passwd')

        self.assertEqual(respuesta.context['categorias_activas'], [])
        self.assertEqual(len(respuesta.context['reportes']), 2)

    def test_con_filtro_y_sin_resultados_ofrece_quitarlo(self):
        """
        Dos huecos distintos: "no hay nada" y "tu filtro no deja ver lo que
        sí hay". Si se vieran igual, quien filtró se iría creyendo que su
        campus no tiene nada registrado.
        """
        respuesta = self.entrar(self.ana).get('/mapa/?categoria=accidente')

        self.assertContains(respuesta, 'Ninguna situación coincide con el filtro')
        self.assertContains(respuesta, 'Quitar el filtro')

    def test_los_datos_del_mapa_no_llevan_los_de_otro_campus(self):
        """
        El JSON que recibe el navegador es público para quien abra la
        pantalla: lo que no deba verse no puede ir ahí, por mucho que el
        mapa no lo dibuje.
        """
        datos = self.entrar(self.ana).get('/mapa/').context['datos_mapa']

        self.assertEqual(len(datos['reportes']), 2)
        self.assertNotIn(
            'No es de aquí', [r['descripcion'] for r in datos['reportes']]
        )

    def test_el_globo_de_un_reporte_dice_cuando_se_registro(self):
        """
        Lo único que este sistema afirma de un reporte es que alguien lo
        registró en un sitio y una fecha. Sin el cuándo, lo de anoche y lo de
        hace medio año son el mismo punto en la pantalla.
        """
        datos = self.entrar(self.ana).get('/mapa/').context['datos_mapa']

        self.assertEqual(len(datos['reportes']), 2)

        for reporte in datos['reportes']:
            self.assertTrue(
                reporte['cuando'].startswith('hace '),
                f"sin fecha legible en el globo: {reporte['cuando']!r}",
            )

    def test_el_globo_de_un_punto_de_apoyo_dice_su_horario(self):
        """
        «Aquí hay una enfermería» es media verdad si cierra a las nueve y son
        las once.
        """
        PuntoApoyo.objects.create(
            campus=self.campus, nombre='Enfermería', tipo='enfermeria',
            latitud=20.1, longitud=-98.7, horario='Lunes a viernes 8 a 20',
        )

        datos = self.entrar(self.ana).get('/mapa/').context['datos_mapa']

        self.assertEqual(datos['puntos'][0]['horario'], 'Lunes a viernes 8 a 20')

    def test_un_punto_sin_horario_llega_vacio_y_no_desaparece(self):
        """
        Llega vacío a propósito: el globo escribe «Sin horario registrado»,
        que no es lo mismo que estar abierto.
        """
        PuntoApoyo.objects.create(
            campus=self.campus, nombre='Caseta', tipo='caseta',
            latitud=20.1, longitud=-98.7,
        )

        datos = self.entrar(self.ana).get('/mapa/').context['datos_mapa']

        self.assertEqual(datos['puntos'][0]['horario'], '')

    def test_la_leyenda_explica_cada_marcador(self):
        """
        Se miran las clases y no los textos: «Pendiente» también sale en las
        insignias de la lista, así que buscar la palabra pasaría aunque
        alguien borrara la leyenda entera.
        """
        respuesta = self.entrar(self.ana).get('/mapa/')

        for estado in ('pendiente', 'verificado', 'resuelto', 'rechazado'):
            self.assertContains(respuesta, f'leyenda__marca--{estado}')

        self.assertContains(respuesta, 'leyenda__marca--apoyo')

    def test_sin_campus_el_mapa_carga_igual(self):
        """Una cuenta recién creada por consola no tiene campus todavía."""
        self.ana.campus = None
        self.ana.save()

        respuesta = self.entrar(self.ana).get('/mapa/')

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Sin campus asignado')


class NingunaSeccionSinPuertaTests(BaseConCuentas):
    """
    Que a toda lista se llegue pulsando, no escribiendo la dirección.

    POR QUÉ HACE FALTA
        El inicio tenía un "Todo lo demás" con nueve botones que era el
        directorio de la aplicación. Al quitarlo —no está en el diseño— cinco
        secciones se quedaban sin ninguna puerta: seguían funcionando, nadie
        veía nada roto, y simplemente no se podía llegar a ellas.

        Esto recorre las pantallas donde debería estar cada enlace y
        comprueba que está. Si alguien reordena una plantilla y se lleva uno
        por delante, falla aquí y no en la demostración.
    """

    def setUp(self):
        super().setUp()

        self.viaje = Viaje.objects.create(
            usuario=self.ana, origen='Biblioteca', destino='Paradero',
        )
        PuntoApoyo.objects.create(
            campus=self.campus, nombre='Enfermería', tipo='enfermeria',
            latitud=20.1, longitud=-98.7,
        )

    def comprobar(self, usuario, desde, direccion):
        respuesta = self.entrar(usuario).get(desde)

        self.assertContains(
            respuesta, f'href="{direccion}"',
            msg_prefix=f'{desde} ya no enlaza a {direccion}',
        )

    def test_las_confirmaciones_desde_la_lista_de_reportes(self):
        self.comprobar(self.ana, '/reportes/', '/confirmaciones/')

    def test_los_avisos_desde_las_notificaciones(self):
        """La campana lleva a notificaciones, así que la puerta está ahí."""
        self.comprobar(self.ana, '/notificaciones/', '/avisos/')

    def test_los_acompanantes_desde_el_detalle_del_viaje(self):
        self.comprobar(self.ana, f'/viajes/{self.viaje.pk}/', '/acompanantes/')

    def test_los_destinos_guardados_desde_la_lista_de_viajes(self):
        self.comprobar(self.ana, '/viajes/', '/destinos/')

    def test_las_ubicaciones_desde_el_detalle_del_viaje(self):
        self.comprobar(self.ana, f'/viajes/{self.viaje.pk}/', '/ubicaciones/')

    def test_los_avisos_sobre_puntos_desde_los_puntos_de_apoyo(self):
        self.comprobar(self.jefa, '/puntos-apoyo/', '/correcciones/')

    def test_los_campus_desde_los_puntos_de_apoyo(self):
        """Solo para la superadministracion: es quien puede tocarlos."""
        self.comprobar(self.mandamas, '/puntos-apoyo/', '/campus/')

    def test_el_inicio_ya_no_es_el_directorio(self):
        """
        Si vuelve el menú de nueve botones, esta prueba lo dice. No es que
        estuviera mal: es que el inicio es para lo que pasa hoy, no para
        listar las tablas de la base de datos.
        """
        respuesta = self.entrar(self.ana).get('/')

        self.assertNotContains(respuesta, 'Todo lo demás')


class PanelTests(BaseConCuentas):
    """
    El panel de quien administra.

    Lo que mas importa aqui no son las cifras: es que no salgan las de otro
    campus, y que quien no administra no entre.
    """

    def setUp(self):
        super().setUp()

        for _ in range(3):
            Reporte.objects.create(
                usuario=self.ana, campus=self.campus, tipo='obras',
                descripcion='Zanja abierta', latitud=20.1, longitud=-98.7,
            )
        Reporte.objects.create(
            usuario=self.beto, campus=self.otro_campus, tipo='fuga',
            descripcion='No es de aquí', latitud=19.4, longitud=-99.1,
        )

    def test_quien_no_administra_no_entra(self):
        """
        403 y no 404: el panel es una seccion entera que no es suya, no un
        registro ajeno escondido.
        """
        self.assertEqual(self.entrar(self.ana).get('/panel/').status_code, 403)

    def test_solo_cuenta_los_de_tu_campus(self):
        """
        Un panel con los numeros de todas las universidades no le sirve a
        quien administra una, y de paso diria cuantas hay y como les va.
        """
        resumen = self.entrar(self.jefa).get('/panel/').context['resumen']

        self.assertEqual(resumen['total'], 3)

    def test_los_pendientes_llevan_a_su_reporte(self):
        """Es lo unico del panel sobre lo que se puede actuar."""
        respuesta = self.entrar(self.jefa).get('/panel/')

        self.assertEqual(len(respuesta.context['pendientes']), 3)
        self.assertContains(respuesta, 'Esperan verificación')

    def test_sin_periodo_anterior_no_inventa_un_porcentaje(self):
        """
        Pasar de cero a tres no es un aumento del infinito por ciento: son
        tres reportes. `variacion` queda en None y la pantalla lo dice.
        """
        tendencia = self.entrar(self.jefa).get('/panel/').context['tendencia']

        self.assertEqual(tendencia['actual'], 3)
        self.assertEqual(tendencia['previo'], 0)
        self.assertIsNone(tendencia['variacion'])

    def test_una_zona_con_un_solo_reporte_no_es_una_concentracion(self):
        zonas = self.entrar(self.jefa).get('/panel/').context['zonas']

        # Los tres estan en el mismo punto: esa zona si, y es la unica.
        self.assertEqual(len(zonas), 1)
        self.assertEqual(zonas[0]['total'], 3)

    def test_los_porcentajes_no_revientan_sin_reportes(self):
        """Division por cero. El campus de una cuenta recien creada esta vacio."""
        Reporte.objects.all().delete()

        respuesta = self.entrar(self.jefa).get('/panel/')

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(all(f['porcentaje'] == 0 for f in respuesta.context['categorias']))

    def test_sale_en_la_navegacion_solo_de_quien_administra(self):
        self.assertContains(self.entrar(self.jefa).get('/'), 'href="/panel/"')
        self.assertNotContains(self.entrar(self.ana).get('/'), 'href="/panel/"')
