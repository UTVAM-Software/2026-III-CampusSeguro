"""
Avisos y notificaciones.

Un aviso lo publica el campus para su gente. Una notificación es de una sola
persona: aquí llega el "alguien no ha llegado a su destino", con su nombre y
a dónde iba.
"""

from apps.usuarios.tests_base import BaseConCuentas

from .models import Aviso, Notificacion


class NotificacionesTests(BaseConCuentas):
    def setUp(self):
        super().setUp()

        self.de_ana = Notificacion.objects.create(
            usuario=self.ana, titulo='Para Ana', mensaje='x'
        )
        self.de_beto = Notificacion.objects.create(
            usuario=self.beto, titulo='Para Beto', mensaje='y'
        )

    def test_cada_quien_ve_solo_las_suyas(self):
        c = self.entrar(self.ana)
        suyas = c.get('/notificaciones/').context['object_list']

        self.assertEqual(len(suyas), 1)
        self.assertEqual(suyas[0], self.de_ana)

    def test_la_de_otra_persona_no_existe_para_ti(self):
        self.assertEqual(
            self.entrar(self.ana).get(f'/notificaciones/{self.de_beto.pk}/').status_code,
            404,
        )

    def test_ni_siquiera_quien_administra(self):
        self.assertEqual(
            self.entrar(self.jefa).get(f'/notificaciones/{self.de_beto.pk}/').status_code,
            404,
        )

    def test_no_se_marca_como_leida_la_de_otra_persona(self):
        """Antes bastaba con saber su número."""
        self.entrar(self.ana).post(f'/notificaciones/{self.de_beto.pk}/leida/')

        self.de_beto.refresh_from_db()
        self.assertFalse(self.de_beto.leida)

    def test_no_se_le_deja_un_aviso_a_otra_persona(self):
        """
        `usuario` no está en el formulario. Si estuviera, cualquiera podría
        dejarle a otro un mensaje con el texto que quisiera, y llegaría con la
        cara del sistema.
        """
        self.entrar(self.ana).post('/notificaciones/create/', {
            'titulo': 'Colado', 'mensaje': 'z', 'usuario': self.beto.pk,
        })

        colada = Notificacion.objects.get(titulo='Colado')
        self.assertEqual(colada.usuario, self.ana)


class AvisosTests(BaseConCuentas):
    def setUp(self):
        super().setUp()

        self.aviso = Aviso.objects.create(
            campus=self.campus, titulo='Aviso', contenido='x', autor=self.jefa
        )

    def test_publicar_es_de_quien_administra(self):
        self.assertEqual(self.entrar(self.ana).get('/avisos/create/').status_code, 403)
        self.assertEqual(self.entrar(self.jefa).get('/avisos/create/').status_code, 200)

    def test_cambiarlo_y_borrarlo_tambien(self):
        c = self.entrar(self.ana)

        self.assertEqual(c.get(f'/avisos/{self.aviso.pk}/update/').status_code, 403)
        self.assertEqual(c.get(f'/avisos/{self.aviso.pk}/delete/').status_code, 403)

    def test_lo_firma_quien_lo_publica(self):
        """
        Un aviso del campus firmado a nombre de otra persona es suplantación,
        y además con el sello de la institución delante.
        """
        self.entrar(self.jefa).post('/avisos/create/', {
            'campus': self.campus.pk, 'titulo': 'Nuevo', 'contenido': 'y',
            'nivel': 'info', 'activo': 'on', 'autor': self.ana.pk,
        })

        nuevo = Aviso.objects.get(titulo='Nuevo')
        self.assertEqual(nuevo.autor, self.jefa)

    def test_cada_campus_ve_los_suyos(self):
        self.beto.campus = self.otro_campus
        self.beto.save()

        self.assertEqual(
            len(self.entrar(self.beto).get('/avisos/').context['object_list']), 0
        )
        self.assertEqual(
            len(self.entrar(self.ana).get('/avisos/').context['object_list']), 1
        )

    def test_publicar_avisa_a_la_gente_del_campus(self):
        """La regla que escribió Lady, y sigue valiendo."""
        self.entrar(self.jefa).post('/avisos/create/', {
            'campus': self.campus.pk, 'titulo': 'Importante', 'contenido': 'y',
            'nivel': 'urgente', 'activo': 'on',
        })

        avisados = Notificacion.objects.filter(titulo='Importante')
        self.assertIn(self.ana, [n.usuario for n in avisados])
        self.assertNotIn(self.jefa, [n.usuario for n in avisados])


class VigenciaDeUnAvisoTests(BaseConCuentas):
    """
    Un aviso caducado se sigue pudiendo abrir —puede llegar un enlace viejo—
    pero la pantalla lo dice. Enseñarlo igual que uno de hoy sería dar por
    vigente algo que ya no lo está, y con esto la gente decide por dónde pasa.
    """

    def crear(self, **extra):
        return Aviso.objects.create(
            campus=self.campus, autor=self.jefa,
            titulo='Obra', contenido='Pasillo cerrado', **extra
        )

    def test_sin_fecha_de_fin_vale_siempre(self):
        self.assertTrue(self.crear().esta_vigente)

    def test_con_la_fecha_pasada_ya_no(self):
        from django.utils import timezone

        ayer = timezone.localdate() - timezone.timedelta(days=1)

        self.assertFalse(self.crear(fecha_expiracion=ayer).esta_vigente)

    def test_el_ultimo_dia_todavia_vale(self):
        """Caduca al acabar ese día, no al empezarlo."""
        from django.utils import timezone

        self.assertTrue(
            self.crear(fecha_expiracion=timezone.localdate()).esta_vigente
        )

    def test_uno_dado_de_baja_tampoco_vale(self):
        self.assertFalse(self.crear(activo=False).esta_vigente)
