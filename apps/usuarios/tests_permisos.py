"""
Quién puede entrar a cada dirección, escrita y comprobada.

PARA QUÉ ESTE ARCHIVO
    Esconder un botón no protege nada: la dirección sigue ahí y se escribe a
    mano en la barra del navegador. Esto recorre TODAS las rutas del proyecto
    con una cuenta de cada rol y comprueba que responden lo que deben.

    Y lo más importante: si alguien añade una ruta y no la declara en la
    tabla de abajo, esta prueba falla. No se puede añadir una pantalla sin
    decir quién puede verla.

LO QUE ENCONTRÓ CUANDO SE ESCRIBIÓ
    El panel de administración no llevaba `login_required`. Como
    `SoloAdminMixin` preguntaba `request.user.es_admin` y una visita sin
    sesión es un `AnonymousUser` —que no tiene ese atributo—, la pantalla
    respondía un 500 en vez de mandar a entrar. Con DEBUG encendido, un 500
    enseña el código y las variables.

LAS CUATRO FORMAS DE DECIR QUE NO
    Cada una dice algo distinto, y la diferencia importa:

    ABIERTA        Sin sesión. Solo las que sirven para conseguirla.
    CUALQUIERA     Cualquier cuenta. Lo que hay dentro ya va filtrado.
    SOLO_ADMIN     403. "Esta sección no es para tu cuenta": la pantalla
                   existe y da igual que se sepa. Quien administra un campus
                   y la superadministración.
    SOLO_SUPERADMIN 403 también para quien administra un campus. Los campus
                   y las cuentas: uno se lleva por delante los datos de toda
                   su gente, la otra es el directorio de la comunidad.
    SOLO_TUYO      404. "Aquí no hay nada": un 403 confirmaría que ese
                   viaje o esa notificación existen, y quién viaja a dónde
                   no es algo que deba filtrarse a quien no va en él.
    SOLO_TU_CAMPUS 404. Lo de otra universidad no existe para ti.
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import NoReverseMatch, get_resolver, reverse

from apps.campus.models import Campus, Correccion, PuntoApoyo
from apps.comunicacion.models import Aviso, Notificacion
from apps.reportes.models import Reporte, ReporteConfirmacion
from apps.usuarios.models import Usuario
from apps.viajes.models import (
    DestinoGuardado, UbicacionViaje, Viaje, ViajeAcompanante,
)

ABIERTA = 'abierta'
CUALQUIERA = 'cualquiera'
SOLO_ADMIN = 'solo_admin'
SOLO_SUPERADMIN = 'solo_superadmin'
SOLO_TUYO = 'solo_tuyo'
SOLO_TU_CAMPUS = 'solo_tu_campus'

#: Quién puede entrar a cada dirección. Toda ruta del proyecto tiene que
#: estar aquí: la prueba falla con las que falten.
QUIEN_ENTRA = {
    # --- Conseguir la sesión. Son las únicas sin ella. ---
    'entrar': ABIERTA,
    'registro': ABIERTA,
    'salir': ABIERTA,
    'clave-pedir': ABIERTA,
    'clave-enviada': ABIERTA,
    'clave-nueva': ABIERTA,
    'clave-lista': ABIERTA,

    # --- Pantallas de todo el mundo. Lo de dentro va filtrado. ---
    'index': CUALQUIERA,
    'mapa': CUALQUIERA,
    'ruta-consultar': CUALQUIERA,
    'perfil': CUALQUIERA,
    'cambiar-clave': CUALQUIERA,
    'cerrar-otras-sesiones': CUALQUIERA,
    'campus-list': CUALQUIERA,
    'campus-detail': CUALQUIERA,
    'punto-list': CUALQUIERA,
    'reporte-list': CUALQUIERA,
    'reporte-create': CUALQUIERA,
    'confirmacion-list': CUALQUIERA,
    'confirmacion-create': CUALQUIERA,
    'viaje-list': CUALQUIERA,
    'viaje-create': CUALQUIERA,
    'acompanante-list': CUALQUIERA,
    'acompanante-create': CUALQUIERA,
    'ubicacion-list': CUALQUIERA,
    'ubicacion-create': CUALQUIERA,
    'aviso-list': CUALQUIERA,
    'notificacion-list': CUALQUIERA,
    'notificacion-create': CUALQUIERA,
    'destino-list': CUALQUIERA,
    'destino-create': CUALQUIERA,

    # --- Quien administra. 403 para los demás. ---
    'panel': SOLO_ADMIN,
    'usuario-list': SOLO_SUPERADMIN,
    'usuario-create': SOLO_SUPERADMIN,
    'usuario-delete': SOLO_SUPERADMIN,
    'campus-create': SOLO_SUPERADMIN,
    'campus-update': SOLO_SUPERADMIN,
    'campus-delete': SOLO_SUPERADMIN,
    'punto-create': SOLO_ADMIN,
    'punto-update': SOLO_ADMIN,
    'punto-delete': SOLO_ADMIN,
    'aviso-create': SOLO_ADMIN,
    'aviso-update': SOLO_ADMIN,
    'aviso-delete': SOLO_ADMIN,
    # Avisar de que un punto está mal lo puede cualquiera; corregir el
    # aviso, solo quien lo escribió y mientras no lo hayan revisado.
    'correccion-create': CUALQUIERA,
    'correccion-update': SOLO_TUYO,
    'correccion-list': SOLO_ADMIN,
    'correccion-atender': SOLO_ADMIN,
    'correccion-detail': SOLO_ADMIN,
    'correccion-delete': SOLO_ADMIN,

    # --- Grupos y permisos de Django (Punto 4). Solo superadministracion. ---
    'grupo-list': SOLO_SUPERADMIN,
    'grupo-detail': SOLO_SUPERADMIN,
    'grupo-create': SOLO_SUPERADMIN,
    'grupo-update': SOLO_SUPERADMIN,
    'grupo-delete': SOLO_SUPERADMIN,
    'permiso-list': SOLO_SUPERADMIN,
    'permiso-detail': SOLO_SUPERADMIN,
    'permiso-create': SOLO_SUPERADMIN,
    'permiso-update': SOLO_SUPERADMIN,
    'permiso-delete': SOLO_SUPERADMIN,

    # --- Tuyo y de nadie más. 404 para el resto. ---
    #
    # Los viajes son lo más delicado que guarda el sistema: ni siquiera
    # quien administra los ve. Es el recorrido de una persona concreta.
    'viaje-detail': SOLO_TUYO,
    'viaje-update': SOLO_TUYO,
    'viaje-delete': SOLO_TUYO,
    'viaje-llegue': SOLO_TUYO,
    'viaje-cancelar': SOLO_TUYO,
    'viaje-posicion': SOLO_TUYO,
    'viaje-ultima': SOLO_TUYO,
    'acompanante-update': SOLO_TUYO,
    'acompanante-delete': SOLO_TUYO,
    'invitacion-responder': SOLO_TUYO,
    'ubicacion-detail': SOLO_TUYO,
    'ubicacion-update': SOLO_TUYO,
    'ubicacion-delete': SOLO_TUYO,
    'confirmacion-detail': SOLO_TUYO,
    'confirmacion-update': SOLO_TUYO,
    'confirmacion-delete': SOLO_TUYO,
    'notificacion-detail': SOLO_TUYO,
    'notificacion-update': SOLO_TUYO,
    'notificacion-delete': SOLO_TUYO,
    'notificacion-leida': SOLO_TUYO,
    'destino-detail': SOLO_TUYO,
    'destino-update': SOLO_TUYO,
    'destino-delete': SOLO_TUYO,
    'usuario-detail': SOLO_TUYO,
    'usuario-update': SOLO_TUYO,
    # Quien acompaña un viaje ve su invitación; cualquier otro, 404.
    'acompanante-detail': SOLO_TUYO,
    # De quien escribió el reporte, o de quien administra el campus.
    'reporte-update': SOLO_TUYO,
    'reporte-delete': SOLO_TUYO,

    # --- De tu universidad. Lo de otra no existe para ti. ---
    'punto-detail': SOLO_TU_CAMPUS,
    'punto-avisar': SOLO_TU_CAMPUS,
    'reporte-detail': SOLO_TU_CAMPUS,
    'reporte-confirmar': SOLO_TU_CAMPUS,
    'aviso-detail': SOLO_TU_CAMPUS,
}

#: Las que solo responden a POST. Un GET devuelve 405 antes de mirar
#: permisos, así que hay que llamarlas como se llaman de verdad.
SOLO_POST = {
    'viaje-llegue', 'viaje-cancelar', 'viaje-posicion', 'invitacion-responder',
    'punto-avisar', 'correccion-atender', 'notificacion-leida',
    'reporte-confirmar', 'cerrar-otras-sesiones', 'salir',
}


class QuienEntraDondeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uno = Campus.objects.create(nombre='Uno', latitud=19.8, longitud=-98.9)
        cls.dos = Campus.objects.create(nombre='Dos', latitud=20.1, longitud=-98.7)

        def cuenta(correo, rol, campus):
            return Usuario.objects.create_user(
                correo=correo, nombre=correo.split('@')[0], password='x' * 20,
                campus=campus, rol=rol,
            )

        cls.duena = cuenta('duena@a.mx', 'estudiante', cls.uno)
        cls.intrusa = cuenta('intrusa@a.mx', 'estudiante', cls.uno)
        cls.de_otro = cuenta('otro@b.mx', 'estudiante', cls.dos)
        # Una segunda y una tercera cuenta de estudiante. Antes tenian rol
        # `docente` y `seguridad`, que no daban ni quitaban nada; el reparto
        # del proyecto anterior solo tiene tres roles.
        cls.otra = cuenta('otra@a.mx', 'estudiante', cls.uno)
        cls.tercera = cuenta('tercera@a.mx', 'estudiante', cls.uno)
        cls.jefa = cuenta('jefa@a.mx', 'admin', cls.uno)
        cls.mandamas = cuenta('mandamas@a.mx', 'superadmin', cls.uno)

        # Todo lo de abajo es de `duena`, del campus `uno`.
        punto = PuntoApoyo.objects.create(
            campus=cls.uno, nombre='Enfermería', tipo='enfermeria',
            latitud=19.8, longitud=-98.9,
        )
        reporte = Reporte.objects.create(
            usuario=cls.duena, campus=cls.uno, tipo='obras',
            descripcion='Zanja abierta', latitud=19.8, longitud=-98.9,
        )
        confirmacion = ReporteConfirmacion.objects.create(
            reporte=reporte, usuario=cls.duena, confirma=True,
        )
        viaje = Viaje.objects.create(usuario=cls.duena, origen='A', destino='B')
        acompanante = ViajeAcompanante.objects.create(
            viaje=viaje, acompanante=cls.duena,
        )
        ubicacion = UbicacionViaje.objects.create(
            viaje=viaje, latitud=19.8, longitud=-98.9,
        )
        aviso = Aviso.objects.create(
            campus=cls.uno, titulo='T', contenido='C', autor=cls.jefa,
        )
        notificacion = Notificacion.objects.create(
            usuario=cls.duena, titulo='T', mensaje='M',
        )
        correccion = Correccion.objects.create(
            punto=punto, usuario=cls.duena, motivo='cerrado',
        )
        destino = DestinoGuardado.objects.create(
            usuario=cls.duena, etiqueta='Casa', latitud=19.8, longitud=-98.9,
        )

        # Un grupo y un permiso creados desde la app: los de rol y los de
        # Django no se borran ni se editan, asi que no sirven para probar
        # las pantallas de editar y eliminar.
        brigada = Group.objects.create(name='Brigada')
        exportar = Permission.objects.create(
            name='Puede exportar reportes', codename='exportar_reporte',
            content_type=ContentType.objects.get(app_label='reportes', model='reporte'),
        )

        cls.ARGS = {
            'punto-detail': [punto.pk], 'punto-update': [punto.pk],
            'punto-delete': [punto.pk], 'punto-avisar': [punto.pk],
            'campus-detail': [cls.uno.pk], 'campus-update': [cls.uno.pk],
            'campus-delete': [cls.uno.pk],
            'reporte-detail': [reporte.pk], 'reporte-update': [reporte.pk],
            'reporte-delete': [reporte.pk], 'reporte-confirmar': [reporte.pk],
            'confirmacion-detail': [confirmacion.pk],
            'confirmacion-update': [confirmacion.pk],
            'confirmacion-delete': [confirmacion.pk],
            'viaje-detail': [viaje.pk], 'viaje-update': [viaje.pk],
            'viaje-delete': [viaje.pk], 'viaje-llegue': [viaje.pk],
            'viaje-cancelar': [viaje.pk], 'viaje-posicion': [viaje.pk],
            'viaje-ultima': [viaje.pk],
            'acompanante-detail': [acompanante.pk],
            'acompanante-update': [acompanante.pk],
            'acompanante-delete': [acompanante.pk],
            'invitacion-responder': [acompanante.pk],
            'ubicacion-detail': [ubicacion.pk], 'ubicacion-update': [ubicacion.pk],
            'ubicacion-delete': [ubicacion.pk],
            'aviso-detail': [aviso.pk], 'aviso-update': [aviso.pk],
            'aviso-delete': [aviso.pk],
            'notificacion-detail': [notificacion.pk],
            'notificacion-update': [notificacion.pk],
            'notificacion-delete': [notificacion.pk],
            'notificacion-leida': [notificacion.pk],
            'usuario-detail': [cls.duena.pk], 'usuario-update': [cls.duena.pk],
            'usuario-delete': [cls.duena.pk],
            'correccion-atender': [correccion.pk],
            'correccion-detail': [correccion.pk],
            'correccion-update': [correccion.pk],
            'correccion-delete': [correccion.pk],
            'destino-update': [destino.pk], 'destino-delete': [destino.pk],
            'destino-detail': [destino.pk],
            'grupo-detail': [brigada.pk], 'grupo-update': [brigada.pk],
            'grupo-delete': [brigada.pk],
            'permiso-detail': [exportar.pk], 'permiso-update': [exportar.pk],
            'permiso-delete': [exportar.pk],
            'clave-nueva': ['MQ', 'inventado'],
        }

    # ------------------------------------------------------------------ #

    def rutas(self):
        """Los nombres de todas las rutas del proyecto, menos las de Django."""
        return sorted(
            n for n in get_resolver().reverse_dict
            if isinstance(n, str) and not n.startswith('admin')
        )

    def pedir(self, nombre, usuario=None):
        cliente = Client()

        if usuario is not None:
            cliente.force_login(usuario)

        url = reverse(nombre, args=self.ARGS.get(nombre, []))

        return cliente.post(url) if nombre in SOLO_POST else cliente.get(url)

    # ------------------------------------------------------------------ #

    def test_toda_ruta_declara_quien_puede_entrar(self):
        """
        El cerrojo de verdad de este archivo.

        Sin esto, añadir una pantalla nueva y olvidarse de su permiso no
        rompería nada: la prueba seguiría en verde porque no la mira.
        """
        sin_declarar = [n for n in self.rutas() if n not in QUIEN_ENTRA]

        self.assertEqual(
            sin_declarar, [],
            'Rutas sin declarar en QUIEN_ENTRA. Di quién puede entrar antes '
            'de darlas por buenas.',
        )

    def test_toda_ruta_se_puede_construir(self):
        """Si falta un argumento en ARGS, el resto de pruebas no la mira."""
        rotas = []

        for nombre in self.rutas():
            try:
                reverse(nombre, args=self.ARGS.get(nombre, []))
            except NoReverseMatch:
                rotas.append(nombre)

        self.assertEqual(rotas, [], 'Faltan argumentos en ARGS para estas rutas.')

    def test_sin_sesion_no_se_entra_a_ninguna(self):
        """
        Lo que pidió quien usa esto: que saber la dirección no sirva de nada.

        Una visita sin sesión acaba en la pantalla de entrar. En NINGÚN caso
        un 200, y en ningún caso un 500 —que además enseñaría el código con
        DEBUG encendido—.
        """
        for nombre in self.rutas():
            if QUIEN_ENTRA.get(nombre) == ABIERTA:
                continue

            with self.subTest(ruta=nombre):
                respuesta = self.pedir(nombre)

                self.assertEqual(
                    respuesta.status_code, 302,
                    f'{nombre} no manda a entrar',
                )
                self.assertIn('/entrar/', respuesta.headers['Location'])

    def test_las_abiertas_lo_estan_a_proposito(self):
        """Son las que sirven para conseguir la sesión, y solo esas."""
        for nombre, quien in QUIEN_ENTRA.items():
            if quien != ABIERTA:
                continue

            with self.subTest(ruta=nombre):
                self.assertNotEqual(self.pedir(nombre).status_code, 500)

    def test_quien_no_administra_recibe_403(self):
        """
        403 y no 404: son secciones enteras que no son suyas, no registros
        ajenos escondidos. Y se comprueba con los cuatro roles que no
        administran, no solo con quien estudia.
        """
        otros = (self.intrusa, self.de_otro, self.otra, self.tercera)

        for nombre, quien in QUIEN_ENTRA.items():
            if quien != SOLO_ADMIN:
                continue

            for usuario in otros:
                with self.subTest(ruta=nombre, rol=usuario.rol):
                    self.assertEqual(self.pedir(nombre, usuario).status_code, 403)

    def test_quien_administra_si_entra(self):
        for nombre, quien in QUIEN_ENTRA.items():
            if quien != SOLO_ADMIN:
                continue

            with self.subTest(ruta=nombre):
                self.assertIn(self.pedir(nombre, self.jefa).status_code, (200, 302))

    def test_lo_ajeno_responde_404(self):
        """
        404 y no 403: un 403 confirmaría que ese viaje existe, y con eso ya
        se sabe que esa persona viajó.

        Quien administra tampoco: administrar el campus no es poder mirar
        por dónde anda la gente. Las dos excepciones son los reportes
        -que sí se revisan- y las cuentas.
        """
        # Las unicas que quien administra SI puede abrir de otra persona:
        # los reportes -que se revisan- y, para la superadministracion, las
        # cuentas. Esa comprobacion va en su propia prueba.
        revisa_la_administracion = {'reporte-update', 'reporte-delete'}

        for nombre, quien in QUIEN_ENTRA.items():
            if quien != SOLO_TUYO:
                continue

            miran = [self.intrusa, self.de_otro]

            if nombre not in revisa_la_administracion:
                miran.append(self.jefa)

            for usuario in miran:
                with self.subTest(ruta=nombre, rol=usuario.rol):
                    self.assertEqual(self.pedir(nombre, usuario).status_code, 404)

    def test_lo_de_otra_universidad_responde_404(self):
        """
        Un reporte es información de la comunidad, pero de SU comunidad. Lo
        que pasa en otra universidad no le sirve a nadie de aquí, y la lista
        completa diría cuántos campus hay y cómo les va.
        """
        for nombre, quien in QUIEN_ENTRA.items():
            if quien != SOLO_TU_CAMPUS:
                continue

            with self.subTest(ruta=nombre):
                self.assertEqual(self.pedir(nombre, self.de_otro).status_code, 404)

    def test_lo_de_tu_universidad_si_se_ve(self):
        """La otra cara: que el filtro por campus no deje fuera a los propios."""
        for nombre, quien in QUIEN_ENTRA.items():
            if quien != SOLO_TU_CAMPUS:
                continue

            with self.subTest(ruta=nombre):
                self.assertIn(
                    self.pedir(nombre, self.intrusa).status_code, (200, 302)
                )

    def test_ninguna_ruta_revienta_con_ningun_rol(self):
        """
        Ni un solo 500, con ninguna cuenta.

        Un 500 no es solo un fallo: con DEBUG encendido enseña el código y
        las variables, y apagado deja un error en el registro que parece un
        problema del servidor y no un intento de entrar donde no se puede.
        Así se encontró el del panel.
        """
        todos = (
            None, self.intrusa, self.de_otro, self.otra,
            self.tercera, self.jefa, self.mandamas,
        )

        for nombre in self.rutas():
            for usuario in todos:
                with self.subTest(ruta=nombre, rol=usuario.rol if usuario else 'anónimo'):
                    self.assertLess(self.pedir(nombre, usuario).status_code, 500)

    def test_quien_administra_un_campus_no_toca_el_sistema(self):
        """
        El reparto que tenía el proyecto anterior: los campus y las cuentas
        son de la superadministración.

        Un campus se lleva por delante los reportes, los avisos y los puntos
        de apoyo de toda su gente. Y la lista de cuentas es el directorio con
        los correos y los teléfonos de la comunidad entera. Para publicar un
        aviso o revisar un reporte no hace falta ninguna de las dos.
        """
        for nombre, quien in QUIEN_ENTRA.items():
            if quien != SOLO_SUPERADMIN:
                continue

            with self.subTest(ruta=nombre):
                self.assertEqual(self.pedir(nombre, self.jefa).status_code, 403)

    def test_la_superadministracion_si_entra(self):
        for nombre, quien in QUIEN_ENTRA.items():
            if quien != SOLO_SUPERADMIN:
                continue

            with self.subTest(ruta=nombre):
                self.assertIn(self.pedir(nombre, self.mandamas).status_code, (200, 302))

    def test_quien_estudia_tampoco(self):
        for nombre, quien in QUIEN_ENTRA.items():
            if quien != SOLO_SUPERADMIN:
                continue

            with self.subTest(ruta=nombre):
                self.assertEqual(self.pedir(nombre, self.intrusa).status_code, 403)

    def test_la_ficha_de_otra_persona_es_de_la_superadministracion(self):
        """
        Quien administra un campus no necesita la ficha de nadie: lleva el
        correo y el teléfono, y dársela sería repartir los datos de contacto
        de su universidad entera.
        """
        for nombre in ('usuario-detail', 'usuario-update'):
            with self.subTest(ruta=nombre):
                self.assertEqual(self.pedir(nombre, self.jefa).status_code, 404)
                self.assertEqual(self.pedir(nombre, self.mandamas).status_code, 200)

    def test_quien_administra_un_campus_no_se_asciende(self):
        """
        El rol no está en el formulario de nadie que no sea
        superadministrador. Si estuviera, editarse a uno mismo sería el
        camino más corto hasta el techo del sistema.
        """
        formulario = self.client_de(self.jefa).get(
            reverse('usuario-update', args=[self.jefa.pk])
        ).context['form']

        self.assertNotIn('rol', formulario.fields)

    def client_de(self, usuario):
        cliente = Client()
        cliente.force_login(usuario)
        return cliente
