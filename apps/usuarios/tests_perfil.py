"""
El perfil: tu foto, tu teléfono y tu seguridad.

LAS FOTOS NO SE ESCRIBEN EN media/
    `MEDIA_ROOT` apunta a una carpeta temporal que se borra al terminar. Sin
    esto, cada vez que alguien corriera las pruebas dejaría archivos sueltos
    en la carpeta de medios del proyecto, y acabarían en el repositorio.
"""

import shutil
import tempfile
from io import BytesIO

from django.contrib.sessions.models import Session
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from .models import Usuario
from .tests_base import CLAVE, BaseConCuentas

MEDIOS = tempfile.mkdtemp()


def imagen(ancho=800, alto=400, formato='JPEG', nombre='foto.jpg', tipo='image/jpeg'):
    """Una imagen de verdad, hecha al vuelo. Apaisada a propósito."""
    import os

    from PIL import Image

    # Ruido y no un color plano: un PNG de 2600x2600 todo rojo se comprime a
    # unos pocos kilobytes y no serviria para probar el limite de tamano.
    foto = Image.frombytes('RGB', (ancho, alto), os.urandom(ancho * alto * 3))

    memoria = BytesIO()
    foto.save(memoria, format=formato)

    return SimpleUploadedFile(nombre, memoria.getvalue(), content_type=tipo)


@override_settings(MEDIA_ROOT=MEDIOS)
class FotoDePerfilTests(BaseConCuentas):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIOS, ignore_errors=True)
        super().tearDownClass()

    def test_la_foto_se_guarda_cuadrada_y_pequena(self):
        """
        Se ve a 48 px en la lateral. Guardar el original de un teléfono sería
        bajarse varios megas para pintarlo del tamaño de una moneda, y quien
        se los baja suele estar con datos móviles.
        """
        from PIL import Image

        self.entrar(self.ana).post('/perfil/', {'foto': imagen(), 'telefono': ''})
        self.ana.refresh_from_db()

        with Image.open(self.ana.foto) as guardada:
            self.assertEqual(guardada.size, (256, 256))
            self.assertEqual(guardada.format, 'JPEG')

    def test_el_nombre_del_archivo_no_es_adivinable(self):
        """
        La carpeta de medios se sirve tal cual. Si la foto se llamara
        "ana.jpg" o "perfil_3.jpg", cualquiera podría probar esa dirección y
        mirar la foto de otra persona sin tener permiso para nada.
        """
        self.entrar(self.ana).post('/perfil/', {'foto': imagen(), 'telefono': ''})
        self.ana.refresh_from_db()

        nombre = self.ana.foto.name

        self.assertNotIn('ana', nombre.lower())
        self.assertNotIn('foto.jpg', nombre)

    def test_al_cambiarla_se_borra_la_anterior(self):
        """Si no, cada cambio deja un archivo en disco que ya no nombra nadie."""
        c = self.entrar(self.ana)

        c.post('/perfil/', {'foto': imagen(), 'telefono': ''})
        self.ana.refresh_from_db()
        primera = self.ana.foto.path

        c.post('/perfil/', {'foto': imagen(), 'telefono': ''})
        self.ana.refresh_from_db()

        self.assertNotEqual(self.ana.foto.path, primera)
        self.assertFalse(__import__('os').path.exists(primera))

    def test_un_archivo_que_no_es_imagen_no_pasa(self):
        """
        El tipo que manda el navegador es lo que el navegador DICE, no lo que
        el archivo es. Se comprueba abriéndolo de verdad.
        """
        falsa = SimpleUploadedFile('foto.jpg', b'esto no es una imagen', 'image/jpeg')

        self.entrar(self.ana).post('/perfil/', {'foto': falsa, 'telefono': ''})
        self.ana.refresh_from_db()

        self.assertFalse(self.ana.foto)

    def test_una_foto_enorme_no_pasa(self):
        """
        Una imagen de VERDAD y grande, no basura con nombre de .jpg: eso lo
        para antes el propio ImageField de Django. Lo que se comprueba aquí
        es el límite de tamaño, que es lo que frena a quien suba el archivo
        sin comprimir de una cámara.

        El límite se mira en el servidor. El `accept` del campo de archivo es
        una comodidad para quien usa el navegador, no una barrera: se salta
        mandando la petición a mano.
        """
        gorda = imagen(ancho=2600, alto=2600, formato='PNG',
                       nombre='foto.png', tipo='image/png')
        self.assertGreater(gorda.size, 2 * 1024 * 1024)

        respuesta = self.entrar(self.ana).post('/perfil/', {'foto': gorda, 'telefono': ''})
        self.ana.refresh_from_db()

        self.assertFalse(self.ana.foto)
        self.assertContains(respuesta, 'no puede pasar de 2 MB')


class DatosDelPerfilTests(BaseConCuentas):
    def test_el_telefono_se_guarda(self):
        self.entrar(self.ana).post('/perfil/', {'telefono': '771 123 4567'})
        self.ana.refresh_from_db()

        self.assertEqual(self.ana.telefono, '771 123 4567')

    def test_se_puede_dejar_vacio(self):
        """
        El teléfono es opcional y la pantalla lo dice. Si al guardar el resto
        se volviera obligatorio, esa frase sería mentira.
        """
        self.ana.telefono = '7711234567'
        self.ana.save()

        self.entrar(self.ana).post('/perfil/', {'telefono': ''})
        self.ana.refresh_from_db()

        self.assertEqual(self.ana.telefono, '')

    def test_no_se_cambia_el_rol_desde_el_perfil(self):
        """
        El formulario solo trae foto y teléfono. Mandar `rol` no sirve de
        nada, y esta prueba falla si alguien lo añade a `fields`: sería el
        camino más corto para hacerse administrador.
        """
        self.entrar(self.ana).post('/perfil/', {'telefono': '', 'rol': 'admin'})
        self.ana.refresh_from_db()

        self.assertEqual(self.ana.rol, 'estudiante')

    def test_tampoco_el_correo_ni_el_campus(self):
        """
        El correo identifica la cuenta y el campus decide qué reportes y qué
        avisos se ven. Cambiarse el campus sería elegir de qué universidad
        quieres ver las cosas.
        """
        self.entrar(self.ana).post('/perfil/', {
            'telefono': '', 'correo': 'otra@x.edu', 'campus': self.otro_campus.pk,
        })
        self.ana.refresh_from_db()

        self.assertEqual(self.ana.correo, 'ana@x.edu')
        self.assertEqual(self.ana.campus, self.campus)

    def test_el_perfil_es_siempre_el_tuyo(self):
        """
        La dirección no lleva pk: la vista devuelve `request.user`. Así no
        existe la pregunta de si alguien puede editar a otra persona.
        """
        self.entrar(self.beto).post('/perfil/', {'telefono': '7799999999'})

        self.ana.refresh_from_db()
        self.beto.refresh_from_db()

        self.assertEqual(self.ana.telefono, '')
        self.assertEqual(self.beto.telefono, '7799999999')

    def test_un_telefono_con_letras_no_pasa(self):
        respuesta = self.entrar(self.ana).post('/perfil/', {'telefono': 'llámame'})
        self.ana.refresh_from_db()

        self.assertEqual(self.ana.telefono, '')
        self.assertContains(respuesta, 'no son válidos')


class SesionesAbiertasTests(BaseConCuentas):
    def abrir_otra_sesion(self, usuario):
        """Otra sesión de la misma cuenta, como si fuera otro dispositivo."""
        from django.test import Client

        otro = Client()
        otro.force_login(usuario)
        return otro

    def test_cierra_las_demas_y_deja_la_tuya(self):
        """
        Quien pulsa esto está diciendo "me dejé la sesión abierta en otro
        sitio". Cerrarle además la de aquí lo echaría de la aplicación como
        premio por protegerse.
        """
        self.abrir_otra_sesion(self.ana)
        self.abrir_otra_sesion(self.ana)
        c = self.entrar(self.ana)

        c.post('/perfil/sesiones/')

        # La de este cliente sigue valiendo: entra a una pantalla con sesión.
        self.assertEqual(c.get('/perfil/').status_code, 200)
        self.assertEqual(self.sesiones_de(self.ana), 1)

    def test_no_toca_las_sesiones_de_otras_personas(self):
        self.abrir_otra_sesion(self.beto)
        self.entrar(self.ana).post('/perfil/sesiones/')

        self.assertEqual(self.sesiones_de(self.beto), 1)

    def sesiones_de(self, usuario):
        return sum(
            1 for s in Session.objects.all()
            if s.get_decoded().get('_auth_user_id') == str(usuario.pk)
        )


class CambiarLaClaveTests(BaseConCuentas):
    NUEVA = 'paradero-7-nocturno'

    def test_hay_que_saber_la_actual(self):
        """
        Es lo que frena a quien encuentre un teléfono desbloqueado con la
        sesión abierta. El proyecto viejo lo hacía por correo, y ahí esa
        misma persona pide el enlace y lo abre en ese mismo teléfono.
        """
        self.entrar(self.ana).post('/perfil/contrasena/', {
            'old_password': 'la-que-no-es',
            'new_password1': self.NUEVA, 'new_password2': self.NUEVA,
        })
        self.ana.refresh_from_db()

        self.assertTrue(self.ana.check_password(CLAVE))

    def test_con_la_actual_se_cambia(self):
        self.entrar(self.ana).post('/perfil/contrasena/', {
            'old_password': CLAVE,
            'new_password1': self.NUEVA, 'new_password2': self.NUEVA,
        })
        self.ana.refresh_from_db()

        self.assertTrue(self.ana.check_password(self.NUEVA))

    def test_la_nueva_pasa_por_las_reglas(self):
        """Las mismas de AUTH_PASSWORD_VALIDATORS que al registrarse."""
        self.entrar(self.ana).post('/perfil/contrasena/', {
            'old_password': CLAVE, 'new_password1': '12345', 'new_password2': '12345',
        })
        self.ana.refresh_from_db()

        self.assertTrue(self.ana.check_password(CLAVE))

    def test_cambiarla_no_te_echa_a_ti(self):
        """
        Django invalida las sesiones al cambiar la contraseña. La de aquí se
        renueva, porque echar a alguien de la aplicación por protegerse sería
        castigar lo correcto.
        """
        c = self.entrar(self.ana)
        c.post('/perfil/contrasena/', {
            'old_password': CLAVE,
            'new_password1': self.NUEVA, 'new_password2': self.NUEVA,
        })

        self.assertEqual(c.get('/perfil/').status_code, 200)


class CampanaTests(BaseConCuentas):
    def test_cuenta_solo_las_tuyas_sin_leer(self):
        """
        La campana sale en todas las pantallas. Si contara las de todo el
        mundo, diría cuánta gente hay en el sistema.
        """
        from apps.comunicacion.models import Notificacion

        Notificacion.objects.create(usuario=self.ana, titulo='a', mensaje='x')
        Notificacion.objects.create(usuario=self.ana, titulo='b', mensaje='x', leida=True)
        Notificacion.objects.create(usuario=self.beto, titulo='c', mensaje='x')

        respuesta = self.entrar(self.ana).get('/')

        self.assertEqual(respuesta.context['sin_leer'], 1)

    def test_sin_sesion_no_se_cuenta_nada(self):
        """El procesador de contexto sale antes de tocar la base."""
        self.assertNotIn('sin_leer', self.client.get('/entrar/').context)


class AvatarTests(BaseConCuentas):
    def test_sin_foto_sale_la_inicial(self):
        respuesta = self.entrar(self.ana).get('/perfil/')

        self.assertContains(respuesta, '>A</span>')

    @override_settings(MEDIA_ROOT=MEDIOS)
    def test_con_foto_sale_la_foto(self):
        c = self.entrar(self.ana)
        c.post('/perfil/', {'foto': imagen(), 'telefono': ''})

        self.assertContains(c.get('/perfil/'), 'avatar--foto')

        Usuario.objects.get(pk=self.ana.pk).foto.delete(save=True)
