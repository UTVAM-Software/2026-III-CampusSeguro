"""
Recuperar la contraseña olvidada.

Hasta ahora no existía: quien la olvidaba se quedaba fuera de su cuenta para
siempre y solo se arreglaba por consola.
"""

import re

from django.core import mail
from django.test import override_settings

from .tests_base import CLAVE, BaseConCuentas

#: En las pruebas se usa el backend que guarda los mensajes en memoria, no el
#: de consola ni SMTP: así se puede leer el enlace que se envió.
EN_MEMORIA = 'django.core.mail.backends.locmem.EmailBackend'


@override_settings(EMAIL_BACKEND=EN_MEMORIA)
class RecuperarLaClaveTests(BaseConCuentas):
    NUEVA = 'andador-largo-7'

    def pedir(self, correo):
        return self.client.post('/clave/', {'email': correo})

    def enlace(self):
        """La dirección de recuperación que venía dentro del correo."""
        cuerpo = mail.outbox[0].body
        return re.search(r'(/clave/nueva/[^\s]+)', cuerpo).group(1)

    def test_llega_un_correo_con_su_enlace(self):
        self.pedir('ana@x.edu')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('ana@x.edu', mail.outbox[0].to)
        self.assertIn('/clave/nueva/', mail.outbox[0].body)

    def test_el_enlace_deja_poner_una_nueva(self):
        self.pedir('ana@x.edu')

        # El enlace redirige a una direccion con la palabra `set-password`,
        # donde vive de verdad el formulario: Django saca el testigo de la
        # direccion y lo guarda en la sesion para no dejarlo en el historial.
        destino = self.client.get(self.enlace(), follow=True).redirect_chain[-1][0]

        self.client.post(destino, {
            'new_password1': self.NUEVA, 'new_password2': self.NUEVA,
        })
        self.ana.refresh_from_db()

        self.assertTrue(self.ana.check_password(self.NUEVA))

    def test_el_enlace_solo_sirve_una_vez(self):
        """
        El testigo lleva dentro el hash de la contraseña actual. Al cambiarla
        el hash cambia, y el enlace que quede en el buzon deja de valer.
        """
        self.pedir('ana@x.edu')
        enlace = self.enlace()

        destino = self.client.get(enlace, follow=True).redirect_chain[-1][0]
        self.client.post(destino, {
            'new_password1': self.NUEVA, 'new_password2': self.NUEVA,
        })

        self.assertContains(self.client.get(enlace, follow=True), 'ya no vale')

    def test_un_correo_que_no_existe_responde_lo_mismo(self):
        """
        Lo mas importante de este archivo. Si la pantalla dijera "te mandamos
        el enlace" solo cuando la cuenta existe, seria una forma de averiguar
        que correos estan registrados aqui.
        """
        de_verdad = self.client.post('/clave/', {'email': 'ana@x.edu'}, follow=True)
        inventado = self.client.post('/clave/', {'email': 'nadie@x.edu'}, follow=True)

        self.assertEqual(de_verdad.status_code, inventado.status_code)
        self.assertEqual(de_verdad.content, inventado.content)
        self.assertEqual(len(mail.outbox), 1)

    def test_a_una_cuenta_dada_de_baja_no_se_le_escribe(self):
        self.ana.activo = False
        self.ana.save()

        self.pedir('ana@x.edu')

        self.assertEqual(len(mail.outbox), 0)

    def test_la_nueva_pasa_por_las_reglas(self):
        """Las mismas de AUTH_PASSWORD_VALIDATORS que al registrarse."""
        self.pedir('ana@x.edu')
        destino = self.client.get(self.enlace(), follow=True).redirect_chain[-1][0]

        self.client.post(destino, {'new_password1': '12345', 'new_password2': '12345'})
        self.ana.refresh_from_db()

        self.assertTrue(self.ana.check_password(CLAVE))

    def test_un_testigo_inventado_no_abre_el_formulario(self):
        respuesta = self.client.get('/clave/nueva/MQ/inventado-aqui/', follow=True)

        self.assertContains(respuesta, 'ya no vale')

    def test_el_enlace_sale_en_la_pantalla_de_entrar(self):
        """
        Estuvo quitado a proposito mientras no habia correo configurado:
        llevaba a una pantalla que prometia un mensaje que no se enviaba.
        """
        self.assertContains(self.client.get('/entrar/'), '/clave/')


class CorreoInstitucionalTests(BaseConCuentas):
    """
    Solo se registra quien tiene correo del campus que elige.

    POR QUÉ IMPORTA
        Sin esto, cualquiera con una cuenta de Gmail se registra en cualquier
        universidad y ve los reportes de esa comunidad: dónde hay mala
        iluminación, por dónde pasa la gente, a qué hora. Pertenecer al
        campus es lo único que da derecho a ver eso.
    """

    NUEVA = 'sendero-9-nocturno'

    def setUp(self):
        super().setUp()

        self.campus.dominios_correo = 'uni.edu.mx, alumno.uni.edu.mx'
        self.campus.save()

    def registrar(self, correo, campus=None):
        from apps.usuarios.models import Usuario

        self.client.post('/registro/', {
            'nombre': 'Nueva', 'apellidos': 'Cuenta', 'correo': correo,
            'telefono': '', 'campus': (campus or self.campus).pk,
            'password': self.NUEVA, 'password2': self.NUEVA,
        })
        return Usuario.objects.filter(correo=correo).exists()

    def test_con_el_correo_del_campus_se_registra(self):
        self.assertTrue(self.registrar('nueva@uni.edu.mx'))

    def test_tambien_con_el_dominio_del_alumnado(self):
        """Casi ninguna universidad tiene uno solo."""
        self.assertTrue(self.registrar('nueva@alumno.uni.edu.mx'))

    def test_con_gmail_no(self):
        self.assertFalse(self.registrar('nueva@gmail.com'))

    def test_un_dominio_que_solo_ACABA_igual_tampoco(self):
        """
        "uni.edu.mx.otracosa.com" acaba en el dominio bueno. Si la
        comprobación fuera "acaba en", cualquiera se registraría comprando un
        dominio así.
        """
        self.assertFalse(self.registrar('nueva@uni.edu.mx.otracosa.com'))

    def test_el_correo_de_OTRO_campus_tampoco(self):
        """
        Lo importante: el filtro es por el campus ELEGIDO, no "es de alguna
        universidad de la lista".
        """
        self.otro_campus.dominios_correo = 'otra.edu.mx'
        self.otro_campus.save()

        self.assertFalse(self.registrar('nueva@otra.edu.mx', campus=self.campus))

    def test_un_campus_sin_dominios_admite_cualquiera(self):
        """
        Si vacío significara "nadie", añadir este campo habría cerrado el
        registro en todas las universidades a la vez.
        """
        self.campus.dominios_correo = ''
        self.campus.save()

        self.assertTrue(self.registrar('nueva@gmail.com'))

    def test_el_error_dice_que_correo_hace_falta(self):
        respuesta = self.client.post('/registro/', {
            'nombre': 'Nueva', 'apellidos': 'Cuenta', 'correo': 'nueva@gmail.com',
            'telefono': '', 'campus': self.campus.pk,
            'password': self.NUEVA, 'password2': self.NUEVA,
        })

        self.assertContains(respuesta, '@uni.edu.mx')

    def test_las_cuentas_que_ya_existian_siguen_entrando(self):
        """
        La restricción es para registrarse. Aplicarla al entrar dejaría fuera
        de golpe a todo el mundo el día que se configure un dominio.
        """
        self.assertTrue(
            self.client.login(correo='ana@x.edu', password=CLAVE)
        )
