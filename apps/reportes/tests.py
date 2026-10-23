"""
Los reportes y sus confirmaciones.

Un reporte SÍ es información de la comunidad: para eso se publica. Lo que no
puede pasar es que alguien lo firme a nombre de otra persona, que lo dé por
verificado él solo, o que vote por los demás.
"""

from apps.usuarios.tests_base import BaseConCuentas

from .models import Reporte, ReporteConfirmacion


class BaseConReporte(BaseConCuentas):
    def setUp(self):
        super().setUp()

        self.reporte = Reporte.objects.create(
            usuario=self.ana, campus=self.campus, tipo='situacion',
            descripcion='Descripción de prueba',
            latitud=20.122877, longitud=-98.736038,
        )


class VerReportesTests(BaseConReporte):
    def test_la_comunidad_del_campus_los_ve(self):
        self.assertEqual(
            self.entrar(self.beto).get(f'/reportes/{self.reporte.pk}/').status_code, 200
        )

    def test_los_de_otro_campus_no(self):
        """
        Lo que pasa en otra universidad no le sirve a nadie de aquí, y la
        lista completa diría cuántos campus hay en el sistema.
        """
        self.beto.campus = self.otro_campus
        self.beto.save()

        c = self.entrar(self.beto)
        self.assertEqual(len(c.get('/reportes/').context['object_list']), 0)
        self.assertEqual(c.get(f'/reportes/{self.reporte.pk}/').status_code, 404)


class CambiarReportesTests(BaseConReporte):
    def test_solo_su_autor_o_quien_administra_lo_edita(self):
        self.assertEqual(
            self.entrar(self.beto).get(f'/reportes/{self.reporte.pk}/update/').status_code,
            404,
        )
        self.assertEqual(
            self.entrar(self.ana).get(f'/reportes/{self.reporte.pk}/update/').status_code,
            200,
        )
        self.assertEqual(
            self.entrar(self.jefa).get(f'/reportes/{self.reporte.pk}/update/').status_code,
            200,
        )

    def test_el_autor_no_marca_su_propio_reporte_como_verificado(self):
        """
        `estado` solo está en el formulario de quien administra. Si el autor
        pudiera darlo por verificado, las confirmaciones no servirían de nada.
        """
        self.entrar(self.ana).post(f'/reportes/{self.reporte.pk}/update/', {
            'tipo': 'situacion', 'descripcion': 'Descripción de prueba',
            'latitud': '20.122877', 'longitud': '-98.736038',
            'estado': 'verificado',
        })

        self.reporte.refresh_from_db()
        self.assertEqual(self.reporte.estado, 'pendiente')

    def test_no_se_firma_un_reporte_a_nombre_de_otra_persona(self):
        self.entrar(self.beto).post('/reportes/create/', {
            'tipo': 'obras', 'descripcion': 'Otro reporte',
            'latitud': '20.100000', 'longitud': '-98.700000',
            'usuario': self.ana.pk, 'campus': self.otro_campus.pk,
        })

        nuevo = Reporte.objects.exclude(pk=self.reporte.pk).get()
        self.assertEqual(nuevo.usuario, self.beto)
        self.assertEqual(nuevo.campus, self.campus)


class ConfirmarTests(BaseConReporte):
    def responder(self, usuario, confirma='1'):
        return self.entrar(usuario).post(
            f'/reportes/{self.reporte.pk}/confirmar/', {'confirma': confirma}
        )

    def test_nadie_confirma_su_propio_reporte(self):
        self.responder(self.ana)

        self.assertFalse(ReporteConfirmacion.objects.exists())

    def test_quien_responde_es_quien_tiene_la_sesion(self):
        """
        Aquí había un desplegable con toda la gente del campus para elegir a
        nombre de quién respondías: bastaba cambiar ese valor para votar por
        cualquiera, tantas veces como personas hubiera.
        """
        self.entrar(self.beto).post(
            f'/reportes/{self.reporte.pk}/confirmar/',
            {'confirma': '1', 'usuario': self.jefa.pk},
        )

        respuesta = ReporteConfirmacion.objects.get()
        self.assertEqual(respuesta.usuario, self.beto)

    def test_responder_dos_veces_cambia_el_voto_pero_no_lo_duplica(self):
        self.responder(self.beto, '1')
        self.responder(self.beto, '0')

        self.assertEqual(ReporteConfirmacion.objects.count(), 1)
        self.assertFalse(ReporteConfirmacion.objects.get().confirma)

    def test_con_tres_que_lo_confirman_queda_verificado(self):
        """El umbral de Lady. Es lo que convierte tres opiniones en un dato."""
        for correo in ('c@x.edu', 'd@x.edu', 'e@x.edu'):
            from apps.usuarios.models import Usuario
            from apps.usuarios.tests_base import CLAVE

            alguien = Usuario.objects.create_user(
                correo=correo, nombre=correo[0].upper(), password=CLAVE,
                campus=self.campus,
            )
            self.responder(alguien, '1')

        self.reporte.refresh_from_db()
        self.assertEqual(self.reporte.estado, 'verificado')

    def test_no_se_responde_a_un_reporte_de_otro_campus(self):
        self.beto.campus = self.otro_campus
        self.beto.save()

        self.responder(self.beto)

        self.assertFalse(ReporteConfirmacion.objects.exists())


class RespuestasPropiasTests(BaseConReporte):
    def test_cada_quien_ve_las_suyas(self):
        ReporteConfirmacion.objects.create(
            reporte=self.reporte, usuario=self.beto, confirma=True
        )

        c = self.entrar(self.jefa)
        self.assertEqual(len(c.get('/confirmaciones/').context['object_list']), 0)

        c = self.entrar(self.beto)
        self.assertEqual(len(c.get('/confirmaciones/').context['object_list']), 1)


class FotoTests(BaseConReporte):
    """
    La foto del reporte.

    Estas dos pruebas existen por un fallo de verdad: el campo se anadio al
    formulario pero la plantilla no llevaba enctype, asi que el navegador no
    mandaba el archivo. El reporte se guardaba igual y la foto se perdia por
    el camino, sin aviso ninguno. Es el peor tipo de fallo: no rompe nada, solo
    deja de hacer su trabajo.
    """

    def imagen(self):
        """Un PNG de un pixel, hecho aqui para no guardar un archivo aparte."""
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        memoria = io.BytesIO()
        Image.new('RGB', (1, 1), '#0b3b61').save(memoria, format='PNG')

        return SimpleUploadedFile('prueba.png', memoria.getvalue(), 'image/png')

    def test_el_formulario_manda_archivos(self):
        html = self.entrar(self.ana).get('/reportes/create/').content.decode()

        self.assertIn('enctype="multipart/form-data"', html)

    def test_la_foto_se_guarda_y_se_ve(self):
        self.entrar(self.ana).post('/reportes/create/', {
            'tipo': 'obras', 'descripcion': 'Zanja abierta con foto',
            'latitud': '20.100000', 'longitud': '-98.700000',
            'foto': self.imagen(),
        })

        reporte = Reporte.objects.get(descripcion='Zanja abierta con foto')
        self.assertTrue(reporte.foto)

        html = self.entrar(self.ana).get(f'/reportes/{reporte.pk}/').content.decode()
        self.assertIn(reporte.foto.url, html)

        reporte.foto.delete(save=False)

    def test_un_ejecutable_con_nombre_de_imagen_no_pasa(self):
        """
        ImageField abre el archivo y comprueba que sea una imagen de verdad.
        Fiarse de la extension seria dejar subir cualquier cosa llamandola
        .png.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.entrar(self.ana).post('/reportes/create/', {
            'tipo': 'obras', 'descripcion': 'Reporte colado de otro campus',
            'latitud': '20.100000', 'longitud': '-98.700000',
            'foto': SimpleUploadedFile('virus.png', b'MZ\x90\x00 no soy una imagen', 'image/png'),
        })

        self.assertFalse(Reporte.objects.filter(descripcion='Reporte colado de otro campus').exists())


class AccionesEnElDetalleTests(BaseConReporte):
    """
    Editar y eliminar salieron de la lista y viven en el detalle.

    En una fila con tres enlaces el dedo acierta el que no era; en el detalle
    ya estas mirando ESE registro. Y se siguen ensenando solo a quien puede.
    """

    def test_la_lista_ya_no_lleva_editar_ni_eliminar(self):
        html = self.entrar(self.ana).get('/reportes/').content.decode()

        self.assertNotIn('reporte-update', html)
        self.assertNotIn('Eliminar', html)

    def test_su_autor_los_ve_en_el_detalle(self):
        html = self.entrar(self.ana).get(f'/reportes/{self.reporte.pk}/').content.decode()

        self.assertIn('Editar', html)

    def test_quien_no_es_su_autor_no(self):
        html = self.entrar(self.beto).get(f'/reportes/{self.reporte.pk}/').content.decode()

        self.assertNotIn('Editar', html)

    def test_quien_administra_si(self):
        html = self.entrar(self.jefa).get(f'/reportes/{self.reporte.pk}/').content.decode()

        self.assertIn('Editar', html)


class FormularioDeReporteTests(BaseConReporte):
    """
    Lo que el formulario deja pasar y lo que no.

    Todo esto se comprueba en el servidor. Lo que hace el navegador —el
    `accept` del campo de archivo, el aviso del guion antes de enviar— es
    comodidad para quien lo usa, no una barrera: se salta mandando la
    petición a mano.
    """

    def crear(self, **extra):
        datos = {
            'tipo': 'obras', 'descripcion': 'Zanja abierta en el pasillo',
            'latitud': '20.100000', 'longitud': '-98.700000',
        }
        datos.update(extra)
        return self.entrar(self.ana).post('/reportes/create/', datos)

    def test_una_descripcion_de_dos_letras_no_pasa(self):
        """
        "si" no sitúa nada ni cuenta qué pasó: el reporte acabaría en el mapa
        ocupando un punto sin decir nada a quien lo abra.
        """
        antes = Reporte.objects.count()
        respuesta = self.crear(descripcion='si')

        self.assertEqual(Reporte.objects.count(), antes)
        self.assertContains(respuesta, 'al menos 10 caracteres')

    def test_sin_categoria_no_pasa(self):
        antes = Reporte.objects.count()
        self.crear(tipo='')

        self.assertEqual(Reporte.objects.count(), antes)

    def test_sin_coordenadas_no_pasa(self):
        """
        Un reporte sin ubicación no se puede enseñar en el mapa, que es para
        lo que sirve registrarlo.
        """
        antes = Reporte.objects.count()
        self.crear(latitud='', longitud='')

        self.assertEqual(Reporte.objects.count(), antes)

    def test_la_categoria_viene_sin_elegir(self):
        """
        "Elige una categoría" y no el "---------" de Django: la primera
        opción de un desplegable es la que más gente deja puesta, y un guion
        no dice que haya que elegir algo.
        """
        respuesta = self.entrar(self.ana).get('/reportes/create/')

        self.assertContains(respuesta, 'Elige una categoría')

    def test_las_coordenadas_van_escondidas(self):
        """
        Las rellenan los botones de ubicación. Teclear 20.122877 a mano es
        pedir una errata que deja el punto en otra calle.
        """
        respuesta = self.entrar(self.ana).get('/reportes/create/')

        self.assertContains(respuesta, 'type="hidden" name="latitud"')

    def test_quien_no_administra_no_ve_el_estado(self):
        """
        Que el autor pudiera marcar su propio reporte como verificado
        vaciaría de sentido las confirmaciones.
        """
        respuesta = self.entrar(self.ana).get('/reportes/create/')

        self.assertNotContains(respuesta, 'name="estado"')
