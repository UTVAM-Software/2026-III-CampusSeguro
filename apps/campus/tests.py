"""
Los campus.

Verlos hace falta para elegir el tuyo al registrarte. Crearlos, cambiarlos y
borrarlos no es de cualquiera: un campus se lleva por delante los reportes,
los avisos y los puntos de apoyo de toda su gente.
"""

from apps.usuarios.tests_base import BaseConCuentas

from .models import Correccion, PuntoApoyo


class QuienTocaLosCampusTests(BaseConCuentas):
    def test_verlos_lo_puede_cualquiera_que_haya_entrado(self):
        c = self.entrar(self.ana)

        self.assertEqual(c.get('/campus/').status_code, 200)
        self.assertEqual(c.get(f'/campus/{self.campus.pk}/').status_code, 200)

    def test_crearlos_cambiarlos_y_borrarlos_no(self):
        c = self.entrar(self.ana)

        self.assertEqual(c.get('/campus/create/').status_code, 403)
        self.assertEqual(c.get(f'/campus/{self.campus.pk}/update/').status_code, 403)
        self.assertEqual(c.get(f'/campus/{self.campus.pk}/delete/').status_code, 403)

    def test_ni_siquiera_quien_administra_un_campus(self):
        """
        Los campus son de la SUPERADMINISTRACIÓN, como en el proyecto
        anterior. Un campus se lleva por delante los reportes, los avisos y
        los puntos de apoyo de toda su gente: quien administra el suyo no
        tiene por qué poder tocar los de otra universidad.
        """
        c = self.entrar(self.jefa)

        self.assertEqual(c.get('/campus/create/').status_code, 403)
        self.assertEqual(c.get(f'/campus/{self.campus.pk}/update/').status_code, 403)
        self.assertEqual(c.get(f'/campus/{self.campus.pk}/delete/').status_code, 403)

    def test_la_superadministracion_si(self):
        c = self.entrar(self.mandamas)

        self.assertEqual(c.get('/campus/create/').status_code, 200)
        self.assertEqual(c.get(f'/campus/{self.campus.pk}/update/').status_code, 200)

    def test_la_pantalla_no_ofrece_lo_que_luego_rechaza(self):
        # Esconder el boton no protege nada -la direccion se escribe a mano-,
        # es para no ensenar una puerta que se cierra en la cara.
        html = self.entrar(self.ana).get('/campus/').content.decode()
        self.assertNotIn('Nuevo campus', html)

        html = self.entrar(self.mandamas).get('/campus/').content.decode()
        self.assertIn('Nuevo campus', html)


class PuntosDeApoyoTests(BaseConCuentas):
    """
    Enfermeria, vigilancia, modulos de ayuda, botones de emergencia.

    El modelo existia desde el primer dia y no tenia ni una pantalla: no se
    podian ni crear ni ver.
    """

    def setUp(self):
        super().setUp()

        from apps.campus.models import PuntoApoyo

        self.abierto = PuntoApoyo.objects.create(
            campus=self.campus, nombre='Enfermería', tipo='enfermeria',
            latitud=20.101100, longitud=-98.759100,
        )
        self.cerrado = PuntoApoyo.objects.create(
            campus=self.campus, nombre='Caseta vieja', tipo='caseta',
            latitud=20.101200, longitud=-98.759200, activo=False,
        )
        self.de_otro = PuntoApoyo.objects.create(
            campus=self.otro_campus, nombre='Enfermería de allá', tipo='enfermeria',
            latitud=19.432600, longitud=-99.133200,
        )

    def test_se_ven_los_del_campus_propio(self):
        puntos = self.entrar(self.ana).get('/puntos-apoyo/').context['object_list']

        self.assertIn(self.abierto, puntos)
        self.assertNotIn(self.de_otro, puntos)

    def test_un_punto_cerrado_no_se_ensena(self):
        """
        Mandar a alguien a una caseta cerrada es peor que no ensenarle nada:
        va hasta alli contando con que hay alguien.
        """
        c = self.entrar(self.ana)

        self.assertNotIn(self.cerrado, c.get('/puntos-apoyo/').context['object_list'])
        self.assertEqual(c.get(f'/puntos-apoyo/{self.cerrado.pk}/').status_code, 404)

    def test_quien_administra_si_ve_los_cerrados(self):
        # Los necesita para poder reactivarlos.
        puntos = self.entrar(self.jefa).get('/puntos-apoyo/').context['object_list']

        self.assertIn(self.cerrado, puntos)

    def test_crearlos_y_borrarlos_es_de_quien_administra(self):
        c = self.entrar(self.ana)

        self.assertEqual(c.get('/puntos-apoyo/create/').status_code, 403)
        self.assertEqual(c.get(f'/puntos-apoyo/{self.abierto.pk}/update/').status_code, 403)
        self.assertEqual(c.get(f'/puntos-apoyo/{self.abierto.pk}/delete/').status_code, 403)
        self.assertEqual(self.entrar(self.jefa).get('/puntos-apoyo/create/').status_code, 200)

    def test_la_pantalla_no_ofrece_lo_que_rechaza(self):
        html = self.entrar(self.ana).get('/puntos-apoyo/').content.decode()
        self.assertNotIn('Nuevo punto de apoyo', html)

        html = self.entrar(self.jefa).get('/puntos-apoyo/').content.decode()
        self.assertIn('Nuevo punto de apoyo', html)

    def test_el_descargo_sigue_puesto(self):
        """
        Que un punto exista no garantiza que este atendido ahora mismo, y la
        pantalla tiene que decirlo.
        """
        html = self.entrar(self.ana).get('/puntos-apoyo/').content.decode()

        self.assertIn('no garantiza', html)


class FormularioDePuntoTests(BaseConCuentas):
    """
    Lo que el formulario de un punto de apoyo deja pasar y lo que no.

    Un punto mal puesto manda a alguien a caminar hasta un sitio donde no hay
    nada, y eso de noche es exactamente lo que esta aplicacion tendria que
    evitar.
    """

    def crear(self, **extra):
        datos = {
            'campus': self.campus.pk, 'nombre': 'Enfermería', 'tipo': 'enfermeria',
            'descripcion': '', 'horario': '',
            'latitud': '20.100000', 'longitud': '-98.700000', 'activo': 'on',
        }
        datos.update(extra)
        return self.entrar(self.jefa).post('/puntos-apoyo/create/', datos)

    def test_se_crea(self):
        self.crear()

        self.assertTrue(PuntoApoyo.objects.filter(nombre='Enfermería').exists())

    def test_sin_coordenadas_no_pasa(self):
        """Sin ubicación no se puede dibujar en el mapa, que es para lo que sirve."""
        self.crear(latitud='', longitud='')

        self.assertFalse(PuntoApoyo.objects.exists())

    def test_sin_tipo_no_pasa(self):
        self.crear(tipo='')

        self.assertFalse(PuntoApoyo.objects.exists())

    def test_el_tipo_viene_sin_elegir(self):
        respuesta = self.entrar(self.jefa).get('/puntos-apoyo/create/')

        self.assertContains(respuesta, 'Elige un tipo')
        self.assertContains(respuesta, 'Elige el campus')

    def test_las_coordenadas_van_escondidas(self):
        """Las rellena el selector de ubicación, no se teclean."""
        respuesta = self.entrar(self.jefa).get('/puntos-apoyo/create/')

        self.assertContains(respuesta, 'type="hidden" name="latitud"')

    def test_quien_no_administra_no_entra(self):
        """
        403 y no 404: registrar puntos de apoyo es una sección entera que no
        es suya, no un registro ajeno escondido.
        """
        self.assertEqual(
            self.entrar(self.ana).get('/puntos-apoyo/create/').status_code, 403
        )


class AvisarDeUnPuntoTests(BaseConCuentas):
    """
    La comunidad avisa, la administracion corrige.

    POR QUE NO SE DEJA EDITAR EL PUNTO A CUALQUIERA
        Decir "aqui hay una enfermeria" es decirle a alguien que a las diez
        de la noche puede caminar hasta ahi y encontrar a una persona. Si eso
        lo pudiera escribir cualquiera, la primera broma manda a alguien a un
        edificio vacio justo cuando mas lo necesita.
    """

    def setUp(self):
        super().setUp()

        self.punto = PuntoApoyo.objects.create(
            campus=self.campus, nombre='Enfermería', tipo='enfermeria',
            latitud=19.8637, longitud=-98.9820, horario='8 a 20',
        )
        self.de_otro = PuntoApoyo.objects.create(
            campus=self.otro_campus, nombre='Caseta', tipo='caseta',
            latitud=19.4, longitud=-99.1,
        )

    def avisar(self, usuario, punto=None, **extra):
        datos = {'motivo': 'cerrado', 'comentario': 'Lleva cerrada un mes.'}
        datos.update(extra)
        return self.entrar(usuario).post(
            f'/puntos-apoyo/{(punto or self.punto).pk}/avisar/', datos
        )

    def test_quien_estudia_puede_avisar(self):
        self.avisar(self.ana)

        aviso = Correccion.objects.get()
        self.assertEqual(aviso.punto, self.punto)
        self.assertEqual(aviso.usuario, self.ana)
        self.assertFalse(aviso.atendida)

    def test_avisar_NO_cambia_el_punto(self):
        """
        Lo mas importante de este archivo. Si un aviso diera de baja el
        punto, bastaria con ponerse de acuerdo unas cuantas personas para
        borrar la enfermeria del mapa.
        """
        self.avisar(self.ana)
        self.punto.refresh_from_db()

        self.assertTrue(self.punto.activo)
        self.assertEqual(self.punto.horario, '8 a 20')

    def test_no_se_avisa_dos_veces_de_lo_mismo(self):
        """
        Si no, diez pulsaciones seguidas llenan la cola de quien administra y
        tapan los avisos de los demas.
        """
        self.avisar(self.ana)
        self.avisar(self.ana)

        self.assertEqual(Correccion.objects.count(), 1)

    def test_despues_de_atenderlo_si_se_puede_volver_a_avisar(self):
        """Porque puede volver a estar mal, y mas tarde es informacion nueva."""
        self.avisar(self.ana)
        Correccion.objects.update(atendida=True)

        self.avisar(self.ana)

        self.assertEqual(Correccion.objects.count(), 2)

    def test_no_se_avisa_de_un_punto_de_otro_campus(self):
        """
        Es informacion de otra comunidad: ni se ve ni se toca. 404 y no 403,
        igual que en el resto del proyecto.
        """
        respuesta = self.avisar(self.ana, punto=self.de_otro)

        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(Correccion.objects.exists())

    def test_sin_motivo_no_se_guarda(self):
        self.avisar(self.ana, motivo='')

        self.assertFalse(Correccion.objects.exists())

    def test_el_formulario_sale_en_la_ficha_del_punto(self):
        respuesta = self.entrar(self.ana).get(f'/puntos-apoyo/{self.punto.pk}/')

        self.assertContains(respuesta, '¿Algo de esto está mal?')


class ColaDeAvisosTests(BaseConCuentas):
    def setUp(self):
        super().setUp()

        self.punto = PuntoApoyo.objects.create(
            campus=self.campus, nombre='Enfermería', tipo='enfermeria',
            latitud=19.8637, longitud=-98.9820,
        )
        self.aviso = Correccion.objects.create(
            punto=self.punto, usuario=self.ana, motivo='horario',
        )

    def test_quien_no_administra_no_ve_la_cola(self):
        self.assertEqual(
            self.entrar(self.ana).get('/correcciones/').status_code, 403
        )

    def test_quien_administra_la_ve(self):
        respuesta = self.entrar(self.jefa).get('/correcciones/')

        self.assertEqual([c.pk for c in respuesta.context['object_list']], [self.aviso.pk])

    def test_atenderlo_lo_saca_de_la_cola_y_NO_toca_el_punto(self):
        self.entrar(self.jefa).post(f'/correcciones/{self.aviso.pk}/atender/')

        self.aviso.refresh_from_db()
        self.punto.refresh_from_db()

        self.assertTrue(self.aviso.atendida)
        self.assertIsNotNone(self.aviso.fecha_atendida)
        self.assertTrue(self.punto.activo)

    def test_lo_atendido_no_se_borra(self):
        """
        Saber que un punto dio problemas tres veces en un mes es justo lo que
        hace falta para decidir darlo de baja.
        """
        self.entrar(self.jefa).post(f'/correcciones/{self.aviso.pk}/atender/')

        self.assertTrue(Correccion.objects.filter(pk=self.aviso.pk).exists())
        self.assertIn(
            self.aviso,
            self.entrar(self.jefa).get('/correcciones/').context['atendidas'],
        )

    def test_no_se_atiende_un_aviso_de_otro_campus(self):
        otro = PuntoApoyo.objects.create(
            campus=self.otro_campus, nombre='Caseta', tipo='caseta',
            latitud=19.4, longitud=-99.1,
        )
        ajeno = Correccion.objects.create(
            punto=otro, usuario=self.beto, motivo='cerrado',
        )

        respuesta = self.entrar(self.jefa).post(f'/correcciones/{ajeno.pk}/atender/')
        ajeno.refresh_from_db()

        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(ajeno.atendida)

    def test_sale_en_el_panel(self):
        respuesta = self.entrar(self.jefa).get('/panel/')

        self.assertEqual(respuesta.context['correcciones'], 1)
        self.assertContains(respuesta, '/correcciones/')


class CrearYCorregirUnAvisoTests(BaseConCuentas):
    """
    Las dos pantallas que completan el CRUD de `Correccion`.

    La puerta buena sigue siendo el boton dentro de la ficha del punto. Esta
    es la pantalla suelta: se elige el punto de una lista.
    """

    def setUp(self):
        super().setUp()

        self.punto = PuntoApoyo.objects.create(
            campus=self.campus, nombre='Enfermería', tipo='enfermeria',
            latitud=19.8637, longitud=-98.9820,
        )
        self.de_otro_campus = PuntoApoyo.objects.create(
            campus=self.otro_campus, nombre='Caseta', tipo='caseta',
            latitud=19.4, longitud=-99.1,
        )

    def crear(self, quien, **extra):
        datos = {
            'punto': self.punto.pk, 'motivo': 'cerrado',
            'comentario': 'Lleva cerrada un mes.',
        }
        datos.update(extra)
        return self.entrar(quien).post('/correcciones/create/', datos)

    # ----------------------------- Crear ------------------------------ #

    def test_quien_estudia_puede_avisar_desde_la_pantalla_suelta(self):
        self.crear(self.ana)

        aviso = Correccion.objects.get()
        self.assertEqual(aviso.punto, self.punto)
        self.assertEqual(aviso.usuario, self.ana)
        self.assertFalse(aviso.atendida)

    def test_el_aviso_se_guarda_a_nombre_de_quien_lo_escribe(self):
        """
        `usuario` no esta en el formulario. Si estuviera, seria una lista con
        todas las personas del campus para avisar a nombre de otra.
        """
        self.crear(self.ana, usuario=self.beto.pk)

        self.assertEqual(Correccion.objects.get().usuario, self.ana)

    def test_la_lista_de_puntos_se_recorta_al_campus(self):
        """
        Si no, el desplegable seria un directorio de los puntos de todas las
        universidades.
        """
        opciones = self.entrar(self.ana).get(
            '/correcciones/create/'
        ).context['form'].fields['punto'].queryset

        self.assertIn(self.punto, opciones)
        self.assertNotIn(self.de_otro_campus, opciones)

    def test_no_se_avisa_de_un_punto_de_otro_campus(self):
        self.crear(self.ana, punto=self.de_otro_campus.pk)

        self.assertFalse(Correccion.objects.exists())

    def test_tampoco_se_avisa_dos_veces_de_lo_mismo(self):
        """
        Es la misma regla que en la ficha del punto. Sin ella aqui, esta
        pantalla seria la puerta de atras para llenar la cola de quien
        administra con diez avisos del mismo sitio.
        """
        self.crear(self.ana)
        respuesta = self.crear(self.ana)

        self.assertEqual(Correccion.objects.count(), 1)
        self.assertContains(respuesta, 'todavía lo estamos revisando')

    def test_pero_si_ya_lo_revisaron_se_puede_volver_a_avisar(self):
        self.crear(self.ana)
        Correccion.objects.update(atendida=True)

        self.crear(self.ana)

        self.assertEqual(Correccion.objects.count(), 2)

    # ---------------------------- Corregir ---------------------------- #

    def test_quien_lo_escribio_lo_corrige(self):
        self.crear(self.ana)
        aviso = Correccion.objects.get()

        self.entrar(self.ana).post(f'/correcciones/{aviso.pk}/update/', {
            'punto': self.punto.pk, 'motivo': 'horario',
            'comentario': 'Me equivoqué: es el horario.',
        })
        aviso.refresh_from_db()

        self.assertEqual(aviso.motivo, 'horario')

    def test_nadie_mas_lo_corrige(self):
        """
        Un aviso es el relato de alguien. Que la administracion pudiera
        reescribirlo dejaria a esa persona diciendo algo que no dijo.

        404 y no 403: un 403 confirmaria que ese aviso existe.
        """
        self.crear(self.ana)
        aviso = Correccion.objects.get()

        for quien in (self.beto, self.jefa, self.mandamas):
            with self.subTest(rol=quien.rol):
                self.assertEqual(
                    self.entrar(quien).get(
                        f'/correcciones/{aviso.pk}/update/'
                    ).status_code,
                    404,
                )

    def test_una_vez_revisado_ya_no_se_toca(self):
        """
        Cambiarlo despues reescribe lo que ya se leyo y sobre lo que ya se
        decidio. A partir de ahi es historial.
        """
        self.crear(self.ana)
        Correccion.objects.update(atendida=True)
        aviso = Correccion.objects.get()

        self.assertEqual(
            self.entrar(self.ana).get(
                f'/correcciones/{aviso.pk}/update/'
            ).status_code,
            404,
        )

    def test_corregir_un_aviso_NO_lo_da_por_revisado(self):
        """
        Son dos acciones distintas y piden permisos distintos: dar por
        revisado es `administrar_campus`.
        """
        self.crear(self.ana)
        aviso = Correccion.objects.get()

        self.entrar(self.ana).post(f'/correcciones/{aviso.pk}/update/', {
            'punto': self.punto.pk, 'motivo': 'horario', 'comentario': '',
        })
        aviso.refresh_from_db()

        self.assertFalse(aviso.atendida)

    def test_quien_estudia_no_da_por_revisado_ningun_aviso(self):
        """
        Lo que se arreglo al anadir estas pantallas: `atender` pedia
        `change_correccion`, el mismo permiso que hace falta para corregir el
        aviso propio. Con el, quien estudia habria podido vaciar la cola de
        la administracion.
        """
        self.crear(self.ana)
        aviso = Correccion.objects.get()

        respuesta = self.entrar(self.ana).post(f'/correcciones/{aviso.pk}/atender/')
        aviso.refresh_from_db()

        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(aviso.atendida)

    def test_quien_administra_si(self):
        self.crear(self.ana)
        aviso = Correccion.objects.get()

        self.entrar(self.jefa).post(f'/correcciones/{aviso.pk}/atender/')
        aviso.refresh_from_db()

        self.assertTrue(aviso.atendida)
