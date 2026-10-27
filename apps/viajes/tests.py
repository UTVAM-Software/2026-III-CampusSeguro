"""
Los viajes: quién puede saber a dónde va alguien y por dónde pasó.

Es lo más delicado que guarda el sistema. Un reporte se publica para que lo
vea la comunidad; un viaje, no: es el recorrido de una persona concreta, con
su hora y su destino.
"""

from django.utils import timezone

from apps.usuarios.tests_base import BaseConCuentas

from .forms import ViajeForm
from .models import DestinoGuardado, UbicacionViaje, Viaje, ViajeAcompanante


class BaseConViaje(BaseConCuentas):
    def setUp(self):
        super().setUp()

        self.viaje = Viaje.objects.create(
            usuario=self.ana, origen="Biblioteca", destino="Paradero",
        )
        self.ubicacion = UbicacionViaje.objects.create(
            viaje=self.viaje, latitud=20.101100, longitud=-98.759100,
        )


class PrivacidadDelViajeTests(BaseConViaje):
    def test_el_viaje_de_otra_persona_no_existe_para_ti(self):
        """
        404 y no 403, a propósito: un 403 confirmaría que ese viaje existe, y
        eso ya dice que Ana viajó. Quien no va en él no tiene por qué saberlo.
        """
        c = self.entrar(self.beto)

        self.assertEqual(c.get(f'/viajes/{self.viaje.pk}/').status_code, 404)
        self.assertEqual(c.get(f'/viajes/{self.viaje.pk}/update/').status_code, 404)
        self.assertEqual(c.get(f'/viajes/{self.viaje.pk}/delete/').status_code, 404)

    def test_ni_siquiera_quien_administra(self):
        """
        Administrar el campus no es poder mirar por dónde anda la gente. Esto
        es distinto de los reportes, que sí se revisan.
        """
        self.assertEqual(
            self.entrar(self.jefa).get(f'/viajes/{self.viaje.pk}/').status_code, 404
        )

    def test_la_lista_solo_trae_los_tuyos(self):
        c = self.entrar(self.beto)

        self.assertEqual(len(c.get('/viajes/').context['object_list']), 0)
        self.assertEqual(
            len(self.entrar(self.ana).get('/viajes/').context['object_list']), 1
        )

    def test_quien_acepto_acompanar_si_lo_ve(self):
        ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='aceptado'
        )

        self.assertEqual(
            self.entrar(self.beto).get(f'/viajes/{self.viaje.pk}/').status_code, 200
        )

    def test_a_quien_solo_invitaron_todavia_no(self):
        """
        Invitar a alguien no puede ser una forma de que te vea la ubicación
        sin que tú lo sepas: hace falta que haya dicho que sí.
        """
        ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='invitado'
        )

        self.assertEqual(
            self.entrar(self.beto).get(f'/viajes/{self.viaje.pk}/').status_code, 404
        )

    def test_acompanar_deja_mirar_pero_no_borrar(self):
        ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='aceptado'
        )
        c = self.entrar(self.beto)

        self.assertEqual(c.get(f'/viajes/{self.viaje.pk}/').status_code, 200)
        self.assertEqual(c.get(f'/viajes/{self.viaje.pk}/delete/').status_code, 404)


class RastroDeUbicacionesTests(BaseConViaje):
    def test_por_donde_paso_alguien_no_lo_ve_cualquiera(self):
        c = self.entrar(self.beto)

        self.assertEqual(len(c.get('/ubicaciones/').context['object_list']), 0)
        self.assertEqual(c.get(f'/ubicaciones/{self.ubicacion.pk}/').status_code, 404)

    def test_quien_viaja_si(self):
        c = self.entrar(self.ana)

        self.assertEqual(len(c.get('/ubicaciones/').context['object_list']), 1)
        self.assertEqual(c.get(f'/ubicaciones/{self.ubicacion.pk}/').status_code, 200)

    def test_quien_acompana_tambien(self):
        ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='aceptado'
        )

        self.assertEqual(
            len(self.entrar(self.beto).get('/ubicaciones/').context['object_list']), 1
        )


class DeQuienEsElViajeTests(BaseConViaje):
    def test_no_se_crea_un_viaje_a_nombre_de_otra_persona(self):
        """
        `usuario` no está en el formulario: lo pone la sesión. Mandarlo no
        sirve de nada, y esta prueba falla si alguien lo devuelve a `fields`.
        """
        self.entrar(self.beto).post('/viajes/create/', {
            'origen': 'A', 'destino': 'B', 'estado': 'en_curso',
            'usuario': self.ana.pk,
        })

        nuevo = Viaje.objects.exclude(pk=self.viaje.pk).get()
        self.assertEqual(nuevo.usuario, self.beto)

    def test_no_te_apuntas_de_acompanante_al_viaje_de_otro(self):
        """
        Si la lista de viajes del formulario trajera todos, apuntarse como
        acompañante del viaje de cualquiera sería elegirlo del desplegable —y
        con eso, verle la ubicación.
        """
        self.entrar(self.beto).post('/acompanantes/create/', {
            'viaje': self.viaje.pk, 'acompanante': self.beto.pk, 'estado': 'aceptado',
        })

        self.assertFalse(ViajeAcompanante.objects.exists())

    def test_tampoco_le_escribes_ubicaciones_al_viaje_de_otro(self):
        self.entrar(self.beto).post('/ubicaciones/create/', {
            'viaje': self.viaje.pk, 'latitud': '1.000000', 'longitud': '1.000000',
        })

        self.assertEqual(UbicacionViaje.objects.count(), 1)


class FechasTests(BaseConCuentas):
    def test_no_se_elige_una_fecha_que_ya_paso(self):
        """
        Regla de Lady, y sigue valiendo: una hora límite que ya pasó nace
        vencida y el acompañamiento no serviría para nada.

        La comprobación estaba puesta sobre `fecha_fin` —cuándo terminó el
        viaje—, que ya no se elige: la pone el sistema al cerrarlo. Ahora
        vigila la hora límite, que es el dato que sí se pide.
        """
        ayer = timezone.now() - timezone.timedelta(days=1)

        self.entrar(self.ana).post('/viajes/create/', {
            'origen': 'A', 'destino': 'B',
            'fecha_expiracion': ayer.strftime('%Y-%m-%dT%H:%M'),
        })

        self.assertFalse(Viaje.objects.exists())


class ElegirEnElMapaTests(BaseConCuentas):
    """
    Planificar un viaje señalando en el mapa, no escribiendo coordenadas.
    """

    def test_el_viaje_guarda_las_coordenadas_que_puso_el_mapa(self):
        manana = timezone.now() + timezone.timedelta(hours=2)

        self.entrar(self.ana).post('/viajes/create/', {
            'origen': 'Biblioteca', 'destino': 'Paradero',
            'latitud_origen': '19.864522', 'longitud_origen': '-98.981229',
            'latitud_destino': '19.865600', 'longitud_destino': '-98.969700',
            'fecha_expiracion': manana.strftime('%Y-%m-%dT%H:%M'),
        })

        viaje = Viaje.objects.get()

        self.assertEqual(str(viaje.latitud_origen), '19.864522')
        self.assertEqual(str(viaje.longitud_destino), '-98.969700')
        self.assertEqual(viaje.usuario, self.ana)

    def test_las_coordenadas_no_se_piden_escritas(self):
        """
        Van escondidas: las rellena el mapa. Si alguien las devuelve a cajas
        de texto, esta prueba lo dice en vez de dejar que vuelva la pantalla
        donde había que saberse la latitud.
        """
        formulario = ViajeForm()

        for nombre in ('latitud_origen', 'longitud_origen',
                       'latitud_destino', 'longitud_destino'):
            self.assertTrue(
                formulario.fields[nombre].widget.is_hidden,
                f'{nombre} volvió a pedirse escrito a mano',
            )

    def test_sin_mapa_el_viaje_se_guarda_igual(self):
        """
        Las coordenadas son opcionales. Sin JavaScript el viaje se crea sin
        ellas —no con unas inventadas—, y la pantalla sigue sirviendo.
        """
        self.entrar(self.ana).post('/viajes/create/', {
            'origen': 'Biblioteca', 'destino': 'Paradero',
        })

        viaje = Viaje.objects.get()

        self.assertIsNone(viaje.latitud_origen)

    def test_los_atajos_son_tus_destinos_y_solo_los_tuyos(self):
        """
        A dónde suele ir alguien es tan suyo como el viaje. Si los atajos
        salieran de todo el mundo, esta pantalla diría dónde vive Beto.
        """
        DestinoGuardado.objects.create(
            usuario=self.ana, etiqueta='Casa', latitud=20.1, longitud=-98.7,
        )
        DestinoGuardado.objects.create(
            usuario=self.beto, etiqueta='Casa de Beto',
            latitud=20.2, longitud=-98.8,
        )

        respuesta = self.entrar(self.ana).get('/viajes/create/')

        etiquetas = [d.etiqueta for d in respuesta.context['destinos']]

        self.assertEqual(etiquetas, ['Casa'])

    def test_al_editar_tambien_estan_los_atajos(self):
        DestinoGuardado.objects.create(
            usuario=self.ana, etiqueta='Casa', latitud=20.1, longitud=-98.7,
        )
        viaje = Viaje.objects.create(
            usuario=self.ana, origen='A', destino='B',
        )

        respuesta = self.entrar(self.ana).get(f'/viajes/{viaje.pk}/update/')

        self.assertEqual(len(respuesta.context['destinos']), 1)


class CerrarPorLaPuertaDeAtrasTests(BaseConViaje):
    """
    Que no haya una segunda forma de cerrar un viaje.

    Pasó de verdad: el formulario enseñaba el campo `estado`, así que editar
    el viaje y elegir "Llegó bien" lo daba por terminado sin borrar las
    posiciones. El viaje salía cerrado en la lista y el recorrido seguía en
    la base, que es justo lo que la aplicación promete no hacer.
    """

    def test_el_formulario_no_puede_tocar_el_estado(self):
        self.entrar(self.ana).post(f'/viajes/{self.viaje.pk}/update/', {
            'origen': 'Biblioteca', 'destino': 'Otro paradero',
            'estado': 'llego_bien',
        })

        self.viaje.refresh_from_db()

        # El destino sí cambia: así se sabe que el formulario se guardó, y no
        # que la prueba pasa porque no se guardó nada.
        self.assertEqual(self.viaje.destino, 'Otro paradero')
        self.assertEqual(self.viaje.estado, 'en_curso')

    def test_el_formulario_no_puede_dejar_el_rastro_guardado(self):
        """
        Lo que de verdad importa: si alguna vez vuelve a poderse cerrar desde
        aquí, que al menos no sea en silencio y con las posiciones dentro.
        """
        self.entrar(self.ana).post(f'/viajes/{self.viaje.pk}/update/', {
            'origen': 'Biblioteca', 'destino': 'Paradero',
            'estado': 'llego_bien',
        })

        self.viaje.refresh_from_db()

        if not self.viaje.esta_en_curso:
            self.assertEqual(self.viaje.ubicaciones.count(), 0)

    def test_estado_y_fecha_fin_no_estan_en_el_formulario(self):
        """
        Se mira la lista de campos y no solo el resultado de un POST: así, el
        día que alguien vuelva a `exclude`, esta prueba lo dice por su nombre
        en vez de dejar que se note cuando ya no se note.
        """
        campos = ViajeForm().fields

        self.assertNotIn('estado', campos)
        self.assertNotIn('fecha_fin', campos)

    def test_cerrar_dos_veces_no_mueve_nada(self):
        """Recargar la pantalla después de pulsar no reescribe la llegada."""
        self.assertTrue(self.viaje.cerrar('llego_bien'))

        primera = self.viaje.fecha_fin

        self.assertFalse(self.viaje.cerrar('cancelado'))
        self.viaje.refresh_from_db()

        self.assertEqual(self.viaje.estado, 'llego_bien')
        self.assertEqual(self.viaje.fecha_fin, primera)


class CerrarElViajeTests(BaseConViaje):
    """
    "Llegué bien" y "Cancelar viaje": los dos botones del detalle.

    Existen porque la pantalla los enseña. Un botón dibujado que no hace nada
    es peor que no tenerlo: quien lo pulsa se va creyendo que avisó.
    """

    def test_llegue_bien_cierra_el_viaje(self):
        self.entrar(self.ana).post(f'/viajes/{self.viaje.pk}/llegue/')
        self.viaje.refresh_from_db()

        self.assertEqual(self.viaje.estado, 'llego_bien')
        self.assertIsNotNone(self.viaje.fecha_fin)

    def test_cancelar_cierra_el_viaje(self):
        self.entrar(self.ana).post(f'/viajes/{self.viaje.pk}/cancelar/')
        self.viaje.refresh_from_db()

        self.assertEqual(self.viaje.estado, 'cancelado')

    def test_no_se_cierra_con_un_GET(self):
        """
        Va por POST. Si respondiera a GET, cualquier cosa que vaya precargando
        enlaces -el navegador, un antivirus, el previsualizador de un chat-
        podría cerrarle el viaje a alguien que solo estaba mirando.
        """
        self.assertEqual(
            self.entrar(self.ana).get(f'/viajes/{self.viaje.pk}/llegue/').status_code,
            405,
        )
        self.viaje.refresh_from_db()
        self.assertEqual(self.viaje.estado, 'en_curso')

    def test_quien_acompana_no_cierra_el_viaje_de_otra_persona(self):
        """Acompañar deja mirar. Cerrar el viaje es de quien viaja."""
        ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='aceptado'
        )

        respuesta = self.entrar(self.beto).post(f'/viajes/{self.viaje.pk}/llegue/')
        self.viaje.refresh_from_db()

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(self.viaje.estado, 'en_curso')

    def test_cerrarlo_dos_veces_no_cambia_el_primero(self):
        """
        Recargar la página después de cancelar no puede convertir ese viaje en
        uno que llegó bien, ni reescribir la hora.
        """
        c = self.entrar(self.ana)
        c.post(f'/viajes/{self.viaje.pk}/cancelar/')
        self.viaje.refresh_from_db()
        hora = self.viaje.fecha_fin

        c.post(f'/viajes/{self.viaje.pk}/llegue/')
        self.viaje.refresh_from_db()

        self.assertEqual(self.viaje.estado, 'cancelado')
        self.assertEqual(self.viaje.fecha_fin, hora)

    def test_un_viaje_cerrado_ya_no_admite_ubicaciones(self):
        """
        Al cerrarlo, la pantalla dice "dejaste de compartir tu ubicación". Sin
        esto sería mentira: el formulario seguía ofreciendo el viaje cerrado.
        """
        c = self.entrar(self.ana)
        c.post(f'/viajes/{self.viaje.pk}/llegue/')

        c.post('/ubicaciones/create/', {
            'viaje': self.viaje.pk, 'latitud': '1.000000', 'longitud': '1.000000',
        })

        self.assertEqual(UbicacionViaje.objects.count(), 0)

    def test_al_cerrarlo_se_borra_el_recorrido(self):
        """
        El perfil y la pantalla de viajes prometen que no se guarda historial
        de recorridos. Mientras las posiciones se quedaran en la base, eso
        era mentira: el viaje terminaba y el rastro seguía ahí para siempre.

        Lo que se conserva es el viaje -a dónde fuiste y cuándo-, no el
        camino.
        """
        self.assertEqual(self.viaje.ubicaciones.count(), 1)

        self.entrar(self.ana).post(f'/viajes/{self.viaje.pk}/llegue/')

        self.assertEqual(self.viaje.ubicaciones.count(), 0)
        self.assertTrue(Viaje.objects.filter(pk=self.viaje.pk).exists())

    def test_cancelarlo_tambien_borra_el_recorrido(self):
        """Cancelar no es menos: la promesa no depende de cómo termine."""
        self.entrar(self.ana).post(f'/viajes/{self.viaje.pk}/cancelar/')

        self.assertEqual(self.viaje.ubicaciones.count(), 0)

    def test_no_toca_el_recorrido_de_otro_viaje(self):
        otro = Viaje.objects.create(
            usuario=self.ana, origen='A', destino='B',
        )
        UbicacionViaje.objects.create(viaje=otro, latitud=1, longitud=1)

        self.entrar(self.ana).post(f'/viajes/{self.viaje.pk}/llegue/')

        self.assertEqual(otro.ubicaciones.count(), 1)


class MinutosRestantesTests(BaseConViaje):
    def test_sin_hora_limite_no_se_inventa_un_numero(self):
        """
        None, y la pantalla escribe "Sin límite". Un "45 min" que no sale de
        ningún dato deja a quien acompaña esperando una alarma que no suena.
        """
        self.assertIsNone(self.viaje.minutos_restantes)

    def test_con_hora_limite_cuenta_los_minutos(self):
        self.viaje.fecha_expiracion = timezone.now() + timezone.timedelta(minutes=30)

        self.assertIn(self.viaje.minutos_restantes, (29, 30))

    def test_una_hora_limite_pasada_no_da_negativo(self):
        self.viaje.fecha_expiracion = timezone.now() - timezone.timedelta(hours=2)

        self.assertEqual(self.viaje.minutos_restantes, 0)



class ResponderUnaInvitacionTests(BaseConViaje):
    """
    Aceptar o rechazar que te acompañen contigo.

    ES LA PERSONA INVITADA QUIEN DECIDE
        Hasta ahora el estado de un acompañante solo lo podía cambiar el
        dueño del viaje. Es decir: quien te invitaba podía marcar que habías
        aceptado, y con eso empezabas a verle la ubicación sin haber dicho
        que sí —o peor, él daba por hecho que lo veías—.
    """

    def setUp(self):
        super().setUp()

        self.invitacion = ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='invitado',
        )

    def test_aceptar(self):
        self.entrar(self.beto).post(
            f'/acompanantes/{self.invitacion.pk}/responder/', {'respuesta': 'aceptar'}
        )
        self.invitacion.refresh_from_db()

        self.assertEqual(self.invitacion.estado, 'aceptado')

    def test_rechazar(self):
        self.entrar(self.beto).post(
            f'/acompanantes/{self.invitacion.pk}/responder/', {'respuesta': 'rechazar'}
        )
        self.invitacion.refresh_from_db()

        self.assertEqual(self.invitacion.estado, 'rechazado')

    def test_quien_viaja_no_acepta_por_ti(self):
        """
        Lo importante de todo esto: aceptar es lo que abre la ubicación.
        Si quien invita pudiera aceptar en tu nombre, bastaría con invitarte
        para verte -o para que creyera que lo estás viendo-.
        """
        respuesta = self.entrar(self.ana).post(
            f'/acompanantes/{self.invitacion.pk}/responder/', {'respuesta': 'aceptar'}
        )
        self.invitacion.refresh_from_db()

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(self.invitacion.estado, 'invitado')

    def test_una_invitacion_ya_respondida_no_se_responde_otra_vez(self):
        self.invitacion.estado = 'rechazado'
        self.invitacion.save()

        self.entrar(self.beto).post(
            f'/acompanantes/{self.invitacion.pk}/responder/', {'respuesta': 'aceptar'}
        )
        self.invitacion.refresh_from_db()

        self.assertEqual(self.invitacion.estado, 'rechazado')

    def test_sale_en_la_pantalla_de_viajes(self):
        respuesta = self.entrar(self.beto).get('/viajes/')

        self.assertContains(respuesta, 'Te invitaron a acompañar')
        self.assertContains(respuesta, 'Aceptar y acompañar')

    def test_mientras_no_aceptes_no_ves_el_viaje(self):
        """Invitar no puede ser una forma de que te vean la ubicación."""
        self.assertEqual(
            self.entrar(self.beto).get(f'/viajes/{self.viaje.pk}/').status_code, 404
        )


class SeccionesDeViajesTests(BaseConViaje):
    def test_el_viaje_en_curso_va_aparte_del_historial(self):
        ctx = self.entrar(self.ana).get('/viajes/').context

        self.assertEqual(ctx['viaje_en_curso'], self.viaje)
        self.assertNotIn(self.viaje, ctx['historial'])

    def test_al_cerrarlo_pasa_al_historial(self):
        c = self.entrar(self.ana)
        c.post(f'/viajes/{self.viaje.pk}/llegue/')

        ctx = c.get('/viajes/').context

        self.assertIsNone(ctx['viaje_en_curso'])
        self.assertIn(self.viaje, ctx['historial'])

    def test_el_historial_es_solo_tuyo(self):
        """
        Acompañar un viaje deja verlo mientras dura, no tenerlo en tu
        historial: no fuiste tú quien viajó.
        """
        ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='aceptado'
        )
        self.entrar(self.ana).post(f'/viajes/{self.viaje.pk}/llegue/')

        self.assertEqual(len(self.entrar(self.beto).get('/viajes/').context['historial']), 0)


class InvitarseASiMismoTests(BaseConViaje):
    """
    Salía en la pantalla de viajes como "Te invitaron a acompañar: tú" en tu
    propio viaje. Además de absurdo no significa nada: acompañar sirve para
    que otra persona vea dónde vas, y tú ya lo sabes.
    """

    def test_no_te_invitas_a_tu_propio_viaje(self):
        self.entrar(self.ana).post('/acompanantes/create/', {
            'viaje': self.viaje.pk, 'acompanante': self.ana.pk,
        })

        self.assertFalse(ViajeAcompanante.objects.exists())

    def test_la_lista_tampoco_te_ofrece(self):
        """
        Se comprueba en los dos sitios: aquí para no ofrecer algo que luego
        se rechaza, y en `clean` para una petición escrita a mano.
        """
        respuesta = self.entrar(self.ana).get('/acompanantes/create/')
        opciones = respuesta.context['form'].fields['acompanante'].queryset

        self.assertNotIn(self.ana, opciones)
        self.assertIn(self.beto, opciones)

    def test_el_estado_no_se_elige_al_invitar(self):
        """
        Si quien invita pudiera marcarla como aceptada, bastaría con
        invitarte para dar por hecho que aceptaste -y aceptar es justo lo que
        abre tu ubicación-.
        """
        self.entrar(self.ana).post('/acompanantes/create/', {
            'viaje': self.viaje.pk, 'acompanante': self.beto.pk, 'estado': 'aceptado',
        })

        self.assertEqual(ViajeAcompanante.objects.get().estado, 'invitado')


class CompartirLaPosicionTests(BaseConViaje):
    """
    La pieza que convierte "comparto mi ubicación" en algo que pasa.

    Hasta ahora las posiciones se escribían a mano en un formulario de la
    lista de ubicaciones. Nadie va a rellenar un formulario mientras camina
    de noche hacia el paradero.
    """

    def enviar(self, cliente, pk=None, **datos):
        cuerpo = {'latitud': '20.100000', 'longitud': '-98.700000'}
        cuerpo.update(datos)
        return cliente.post(f'/viajes/{pk or self.viaje.pk}/posicion/', cuerpo)

    def test_quien_viaja_guarda_su_posicion(self):
        antes = self.viaje.ubicaciones.count()
        respuesta = self.enviar(self.entrar(self.ana))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.viaje.ubicaciones.count(), antes + 1)

    def test_quien_acompana_no_escribe_posiciones(self):
        """
        Acompañar es mirar. Si quien acompaña pudiera escribir posiciones,
        podría fabricar un rastro que dijera que fuiste por donde no fuiste.
        """
        ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='aceptado'
        )
        antes = self.viaje.ubicaciones.count()

        respuesta = self.enviar(self.entrar(self.beto))

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(self.viaje.ubicaciones.count(), antes)

    def test_un_viaje_cerrado_no_recibe_mas(self):
        """La pantalla dice que dejaste de compartir. Tiene que ser verdad."""
        c = self.entrar(self.ana)
        c.post(f'/viajes/{self.viaje.pk}/llegue/')

        respuesta = self.enviar(c)

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(self.viaje.ubicaciones.count(), 0)

    def test_una_latitud_imposible_no_se_guarda(self):
        """
        Las coordenadas vienen del navegador, o sea de fuera. Una latitud de
        500 no existe, y guardada deja un punto imposible en el mapa de quien
        te acompaña.
        """
        antes = self.viaje.ubicaciones.count()
        respuesta = self.enviar(self.entrar(self.ana), latitud='500.000000')

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.viaje.ubicaciones.count(), antes)

    def test_un_texto_en_vez_de_un_numero_tampoco(self):
        respuesta = self.enviar(self.entrar(self.ana), longitud='por ahi')

        self.assertEqual(respuesta.status_code, 400)


class ConsultarLaUltimaPosicionTests(BaseConViaje):
    def test_quien_acompana_la_consulta(self):
        ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='aceptado'
        )

        datos = self.entrar(self.beto).get(f'/viajes/{self.viaje.pk}/ultima/').json()

        self.assertTrue(datos['hay'])
        self.assertTrue(datos['enCurso'])

    def test_quien_solo_fue_invitado_no(self):
        """
        Mientras no aceptes no ves nada del viaje. Invitar no puede ser una
        forma de que te vean la ubicación sin saberlo —ni al revés—.
        """
        ViajeAcompanante.objects.create(
            viaje=self.viaje, acompanante=self.beto, estado='invitado'
        )

        self.assertEqual(
            self.entrar(self.beto).get(f'/viajes/{self.viaje.pk}/ultima/').status_code,
            404,
        )

    def test_un_desconocido_tampoco(self):
        self.assertEqual(
            self.entrar(self.beto).get(f'/viajes/{self.viaje.pk}/ultima/').status_code,
            404,
        )

    def test_no_devuelve_las_coordenadas_en_crudo(self):
        """
        Lo que hace falta en pantalla es CUANDO fue la ultima posicion, no
        donde. El mapa del viaje es otra cosa; esto se consulta cada medio
        minuto y no tiene por que ir repartiendo el punto exacto.
        """
        datos = self.entrar(self.ana).get(f'/viajes/{self.viaje.pk}/ultima/').json()

        self.assertNotIn('latitud', datos)
        self.assertNotIn('longitud', datos)


class DestinosGuardadosTests(BaseConCuentas):
    """
    Los sitios a los que va alguien siempre.

    Es la lista de donde vive y a donde sale. No la ve nadie mas: ni quien
    administra el campus, ni la superadministracion.
    """

    def setUp(self):
        super().setUp()

        from apps.viajes.models import DestinoGuardado

        self.casa = DestinoGuardado.objects.create(
            usuario=self.ana, etiqueta='Casa',
            latitud=19.864600, longitud=-98.981200,
        )

    def crear(self, quien, **extra):
        datos = {
            'etiqueta': 'Trabajo', 'referencia': 'Centro',
            'latitud': '19.863700', 'longitud': '-98.982000',
        }
        datos.update(extra)
        return self.entrar(quien).post('/destinos/create/', datos)

    def test_se_guarda_a_nombre_de_quien_lo_crea(self):
        """
        `usuario` no esta en el formulario. Si estuviera, seria una lista
        con todas las personas del sistema para elegir a quien le guardas un
        destino -y con ello, donde vive-.
        """
        from apps.viajes.models import DestinoGuardado

        self.crear(self.beto, usuario=self.ana.pk)

        self.assertEqual(DestinoGuardado.objects.get(etiqueta='Trabajo').usuario, self.beto)

    def test_cada_quien_ve_los_suyos(self):
        self.crear(self.beto)

        mios = self.entrar(self.ana).get('/destinos/').context['object_list']

        self.assertEqual([d.pk for d in mios], [self.casa.pk])

    def test_el_destino_de_otra_persona_no_existe_para_ti(self):
        """
        404 y no 403: un 403 confirmaria que esa persona guardo un sitio con
        ese numero, y la lista entera dice donde vive.
        """
        c = self.entrar(self.beto)

        self.assertEqual(c.get(f'/destinos/{self.casa.pk}/update/').status_code, 404)
        self.assertEqual(c.get(f'/destinos/{self.casa.pk}/delete/').status_code, 404)

    def test_ni_siquiera_la_superadministracion(self):
        c = self.entrar(self.mandamas)

        self.assertEqual(len(c.get('/destinos/').context['object_list']), 0)
        self.assertEqual(c.get(f'/destinos/{self.casa.pk}/update/').status_code, 404)

    def test_no_se_repite_la_etiqueta(self):
        """
        Dos "Casa" en la misma lista no se podrian distinguir al elegir.
        """
        from apps.viajes.models import DestinoGuardado

        self.crear(self.ana, etiqueta='Casa')

        self.assertEqual(DestinoGuardado.objects.filter(usuario=self.ana).count(), 1)

    def test_pero_otra_persona_si_puede_tener_su_Casa(self):
        from apps.viajes.models import DestinoGuardado

        self.crear(self.beto, etiqueta='Casa')

        self.assertEqual(DestinoGuardado.objects.filter(etiqueta='Casa').count(), 2)

    def test_sin_coordenadas_no_se_guarda(self):
        from apps.viajes.models import DestinoGuardado

        self.crear(self.ana, latitud='', longitud='')

        self.assertFalse(DestinoGuardado.objects.filter(etiqueta='Trabajo').exists())

    def test_salen_como_atajo_al_comparar_caminos(self):
        """Para esto se guardan: ahi lo caro de conseguir son las coordenadas."""
        respuesta = self.entrar(self.ana).get('/rutas/')

        self.assertContains(respuesta, 'data-destino-guardado')
        self.assertContains(respuesta, 'Casa')

    def test_los_atajos_son_solo_los_tuyos(self):
        self.crear(self.beto, etiqueta='Su casa')

        respuesta = self.entrar(self.ana).get('/rutas/')

        self.assertNotContains(respuesta, 'Su casa')

    def test_borrarlo_no_toca_los_viajes(self):
        """
        Los que ya hiciste a ese sitio se quedan en tu historial: el destino
        guardado es un atajo para escribirlo, no el viaje.
        """
        viaje = Viaje.objects.create(usuario=self.ana, origen='A', destino='Casa')

        self.entrar(self.ana).post(f'/destinos/{self.casa.pk}/delete/')

        self.assertTrue(Viaje.objects.filter(pk=viaje.pk).exists())
