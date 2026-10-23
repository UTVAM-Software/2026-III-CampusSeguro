"""
Las cuentas: entrar, registrarse y quién puede qué.

Estas pruebas no comprueban que el programa funcione: comprueban que NO deje
hacer lo que no debe. Son las que avisan si alguien quita un `get_queryset` o
devuelve un campo a un formulario sin darse cuenta de lo que abre.
"""

import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate
from django.test import SimpleTestCase

from .models import Usuario
from .tests_base import CLAVE, BaseConCuentas


class ContrasenaTests(BaseConCuentas):
    def test_se_guarda_cifrada_y_con_argon2(self):
        self.assertNotIn(CLAVE, self.ana.password)
        self.assertTrue(self.ana.password.startswith('argon2$argon2id$'))

    def test_entra_con_la_correcta_y_no_con_otra(self):
        self.assertIsNotNone(authenticate(correo="ana@x.edu", password=CLAVE))
        self.assertIsNone(authenticate(correo="ana@x.edu", password="otra"))

    def test_una_cuenta_sin_acceso_no_entra(self):
        """
        Quitar el acceso es apagar `activo`, no borrar la cuenta: sus reportes
        y su historial siguen donde estaban.
        """
        self.ana.activo = False
        self.ana.save()

        self.assertIsNone(authenticate(correo="ana@x.edu", password=CLAVE))


class EntrarYSalirTests(BaseConCuentas):
    def test_sin_sesion_no_se_llega_a_los_datos(self):
        for ruta in ('/', '/reportes/', '/viajes/', '/ubicaciones/'):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)

                self.assertEqual(respuesta.status_code, 302)
                self.assertIn('/entrar/', respuesta.headers['Location'])

    def test_la_pantalla_de_entrar_no_pide_sesion(self):
        # Pedirla sería pedir la llave para poder recoger la llave.
        for ruta in ('/entrar/', '/registro/'):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_con_la_clave_correcta_entra(self):
        respuesta = self.client.post(
            '/entrar/', {'username': 'ana@x.edu', 'password': CLAVE}
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_con_la_clave_equivocada_se_queda_fuera(self):
        self.client.post('/entrar/', {'username': 'ana@x.edu', 'password': 'otra'})

        self.assertEqual(self.client.get('/').status_code, 302)

    def test_el_error_no_dice_cual_de_los_dos_fallo(self):
        """
        Decir "ese correo no existe" regalaría una forma de averiguar quién
        tiene cuenta aquí, probando correos uno a uno.
        """
        respuesta = self.client.post(
            '/entrar/', {'username': 'nadie@x.edu', 'password': 'otra'}
        )
        texto = respuesta.content.decode().lower()

        self.assertNotIn('no existe', texto)
        self.assertNotIn('no está registrado', texto)

    def test_salir_solo_por_post(self):
        """
        Si salir fuera un enlace, bastaría una imagen escondida en otra página
        apuntando ahí para cerrarle la sesión a quien la abriera.
        """
        c = self.entrar(self.ana)

        self.assertEqual(c.get('/salir/').status_code, 405)
        self.assertEqual(c.post('/salir/').status_code, 302)
        self.assertEqual(c.get('/').status_code, 302)


class RegistroTests(BaseConCuentas):
    def datos(self, **cambios):
        base = {
            'nombre': 'Nueva', 'apellidos': 'Cuenta', 'correo': 'nueva@x.edu',
            'telefono': '', 'campus': self.campus.pk,
            'password': CLAVE, 'password2': CLAVE,
        }
        base.update(cambios)
        return base

    def test_quien_se_registra_no_elige_su_rol(self):
        """
        LA PRUEBA MÁS IMPORTANTE DE ESTE ARCHIVO.

        `rol` no está en el formulario, así que mandarlo no sirve de nada. Si
        algún día alguien lo añade a `fields` "para que se pueda elegir el
        campus y el rol de una vez", esto falla y se entera antes de subirlo.

        No hace falta saber programar para intentarlo: se añade un campo con
        las herramientas del navegador y se envía.
        """
        self.client.post('/registro/', self.datos(rol='admin'))

        cuenta = Usuario.objects.get(correo='nueva@x.edu')
        self.assertEqual(cuenta.rol, 'estudiante')
        self.assertFalse(cuenta.es_admin)

    def test_la_contrasena_queda_cifrada(self):
        self.client.post('/registro/', self.datos())

        cuenta = Usuario.objects.get(correo='nueva@x.edu')
        self.assertNotIn(CLAVE, cuenta.password)
        self.assertTrue(cuenta.password.startswith('argon2$'))

    def test_dos_contrasenas_distintas_no_crean_nada(self):
        self.client.post('/registro/', self.datos(password2='otra'))

        self.assertFalse(Usuario.objects.filter(correo='nueva@x.edu').exists())

    def test_no_se_repite_un_correo(self):
        self.client.post('/registro/', self.datos(correo='ana@x.edu'))

        self.assertEqual(Usuario.objects.filter(correo='ana@x.edu').count(), 1)

    def test_el_correo_se_guarda_en_minusculas(self):
        # Si no, Ana@x.edu y ana@x.edu serían dos cuentas y el unique de la
        # columna no lo impediría.
        self.client.post('/registro/', self.datos(correo='NUEVA@X.EDU'))

        self.assertTrue(Usuario.objects.filter(correo='nueva@x.edu').exists())


class QuienVeLasCuentasTests(BaseConCuentas):
    def test_la_lista_de_cuentas_es_de_la_superadministracion(self):
        """
        La ficha de alguien lleva su correo y su teléfono. La lista entera es
        un directorio de datos de contacto de toda la comunidad.

        Quien administra un campus TAMPOCO la ve: para publicar un aviso o
        revisar un reporte no hace falta la ficha de nadie. Es el reparto del
        proyecto anterior.
        """
        self.assertEqual(self.entrar(self.ana).get('/usuarios/').status_code, 403)
        self.assertEqual(self.entrar(self.jefa).get('/usuarios/').status_code, 403)
        self.assertEqual(self.entrar(self.mandamas).get('/usuarios/').status_code, 200)

    def test_nadie_mira_la_ficha_de_otra_persona(self):
        c = self.entrar(self.ana)

        self.assertEqual(c.get(f'/usuarios/{self.ana.pk}/').status_code, 200)
        self.assertEqual(c.get(f'/usuarios/{self.beto.pk}/').status_code, 404)

    def test_nadie_se_hace_administrador_editandose(self):
        """
        El rol solo está en el formulario si quien edita administra. Si no,
        editarse a uno mismo sería el camino más corto para subir de rango.
        """
        self.entrar(self.ana).post(
            f'/usuarios/{self.ana.pk}/update/',
            {'nombre': 'Ana', 'apellidos': '', 'correo': 'ana@x.edu',
             'telefono': '', 'rol': 'admin', 'campus': self.campus.pk, 'activo': 'on'},
        )

        self.ana.refresh_from_db()
        self.assertEqual(self.ana.rol, 'estudiante')

    def test_borrar_cuentas_es_de_la_superadministracion(self):
        # 403 y no 404: borrar cuentas es una seccion entera que no es suya,
        # no una fila ajena escondida.
        for quien in (self.ana, self.jefa):
            with self.subTest(rol=quien.rol):
                self.assertEqual(
                    self.entrar(quien).get(
                        f'/usuarios/{self.beto.pk}/delete/'
                    ).status_code,
                    403,
                )

    def test_quien_administra_un_campus_no_se_asciende(self):
        """
        El rol solo esta en el formulario de la superadministracion. Si
        estuviera en el de quien administra un campus, editarse a uno mismo
        seria el camino mas corto hasta el techo del sistema.
        """
        self.entrar(self.jefa).post(
            f'/usuarios/{self.jefa.pk}/update/',
            {'nombre': 'Jefa', 'apellidos': '', 'correo': 'jefa@x.edu',
             'telefono': '', 'rol': 'superadmin', 'campus': self.campus.pk,
             'activo': 'on'},
        )
        self.jefa.refresh_from_db()

        self.assertEqual(self.jefa.rol, 'admin')


class TodasLasPuertasTests(SimpleTestCase):
    """
    Que no quede ninguna ruta sin cerrar.

    Es fácil añadir una vista nueva a un `urls.py` y olvidar el
    `login_required`: no falla nada, no avisa nadie, y queda abierta. Esto
    recorre los cinco archivos de rutas y lo comprueba.
    """

    #: Las únicas que pueden estar abiertas, y por qué: son las que sirven
    #: para conseguir la sesión.
    ABIERTAS = {
        'EntrarView', 'SalirView', 'RegistroView',
        # Las de recuperar la contrasena: quien llega ahi es justo quien no
        # puede entrar. Pedir sesion seria pedir la llave para recoger la
        # llave.
        'PedirClaveView', 'ClaveEnviadaView', 'NuevaClaveView', 'ClaveListaView',
        # Las pantallas de error (400, 403, 404, 500), que solo se registran
        # con DEBUG encendido para poder mirarlas mientras se trabajan. No
        # ensenan ningun dato: son texto fijo.
        'TemplateView',
    }

    def test_ninguna_vista_se_queda_sin_pedir_sesion(self):
        sueltas = []

        raiz = Path(settings.BASE_DIR)

        # `config/urls.py` tambien, y no estaba: ahi vivian el inicio, el
        # mapa y el PANEL, y el panel se habia quedado sin `login_required`.
        # Una visita sin sesion llegaba hasta el mixin de administracion y lo
        # reventaba con un 500.
        for rutas in [*(raiz / 'apps').glob('*/urls.py'), raiz / 'config' / 'urls.py']:
            texto = rutas.read_text(encoding='utf-8')

            for linea in texto.splitlines():
                if '.as_view()' not in linea:
                    continue

                encontrada = re.search(r'(\w+)\.as_view\(', linea)

                if not encontrada:
                    continue

                vista = encontrada.group(1)

                if vista in self.ABIERTAS or 'login_required' in linea:
                    continue

                sueltas.append(f"{rutas.parent.name}: {vista}")

        self.assertEqual(
            sueltas, [],
            "Rutas sin login_required. Cualquiera que escriba la dirección "
            "entra sin cuenta.",
        )


class FalloCSRFTests(BaseConCuentas):
    """
    Lo que se ve cuando caduca un formulario.

    Es un caso real y frecuente: una pestana que llevaba abierta un rato, o el
    boton de "reintentar" del navegador reenviando un envio viejo. Django trae
    para eso una pagina amarilla en ingles que habla de CsrfViewMiddleware y
    enlaza a su documentacion: le habla a quien programa, no a quien usa la
    aplicacion.
    """

    def test_el_formulario_caducado_ensena_nuestra_pantalla(self):
        from django.test import Client

        # enforce_csrf_checks: sin esto el cliente de pruebas se salta la
        # comprobacion y la prueba pasaria sin comprobar nada.
        cliente = Client(enforce_csrf_checks=True)
        respuesta = cliente.post('/entrar/', {'username': 'ana@x.edu', 'password': 'x'})
        html = respuesta.content.decode()

        self.assertEqual(respuesta.status_code, 403)
        self.assertIn('Esta página llevaba demasiado tiempo abierta', html)
        self.assertNotIn('CsrfViewMiddleware', html)


class EtiquetasEnVariasLineasTests(SimpleTestCase):
    """
    Que ninguna etiqueta de plantilla quede partida en dos líneas.

    POR QUÉ ES UNA PRUEBA Y NO UNA REGLA DE ESTILO
        Django no parsea una etiqueta partida: la imprime tal cual, con las
        llaves y todo, en mitad de la pantalla. No falla nada, no avisa
        nadie, y el texto sale publicado.

        Pasó de verdad: un `{# ... #}` de dos líneas en base.html salía en la
        esquina de TODAS las pantallas de la aplicación —y, como dentro
        llevaba la palabra `<details>`, el navegador la leía como HTML y
        además dibujaba un desplegable que decía "Detalles".

        Vale para las tres formas: `{% ... %}`, `{{ ... }}` y `{# ... #}`.
        Para un comentario largo está `{% comment %}`, que sí admite varias
        líneas.
    """

    APERTURAS = {'{%': '%}', '{{': '}}', '{#': '#}'}

    def test_ninguna_etiqueta_se_parte_en_dos_lineas(self):
        sueltas = []
        raiz = Path(settings.BASE_DIR)

        for plantilla in raiz.glob('**/*.html'):
            if '.venv' in plantilla.parts:
                continue

            for numero, linea in enumerate(
                plantilla.read_text(encoding='utf-8').splitlines(), start=1
            ):
                for abre, cierra in self.APERTURAS.items():
                    if linea.count(abre) > linea.count(cierra):
                        sueltas.append(
                            f'{plantilla.relative_to(raiz)}:{numero}  {linea.strip()[:60]}'
                        )

        self.assertEqual(
            sueltas, [],
            'Etiquetas abiertas y sin cerrar en la misma línea. Django las '
            'imprime tal cual en la pantalla.',
        )
