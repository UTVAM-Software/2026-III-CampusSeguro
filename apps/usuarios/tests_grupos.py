"""
Los grupos y permisos de Django (Puntos 3 y 4 de la tarea).

Lo que se comprueba aquí:
    - Toda vista con sesión declara `permission_required`.
    - Cada cuenta está en el grupo de su rol, y cambia de grupo si cambia de rol.
    - Lo que puede hacer una cuenta lo deciden sus permisos: quitarle uno a un
      grupo cierra la pantalla que lo pide.
    - El CRUD de grupos y permisos desde la app, y lo que NO se deja tocar.
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase
from django.urls import NoReverseMatch, get_resolver, reverse

from apps.campus.models import Campus
from apps.usuarios.models import Usuario
from apps.usuarios.roles import NOMBRES_GRUPOS_DE_ROL
from apps.usuarios.tests_permisos import ABIERTA, QUIEN_ENTRA


def permiso(nombre):
    app, codigo = nombre.split('.')
    return Permission.objects.get(content_type__app_label=app, codename=codigo)


class TodaVistaPidePermisoTests(TestCase):
    def test_toda_vista_con_sesion_declara_permission_required(self):
        """
        El Punto 3 de la tarea: en cada vista se ve de forma explícita qué
        permiso pide. Si alguien añade una vista y se le olvida, esto falla.
        """
        sin_permiso = []

        for nombre in list(get_resolver().reverse_dict):
            if not isinstance(nombre, str) or nombre.startswith('admin'):
                continue
            if QUIEN_ENTRA.get(nombre) == ABIERTA:
                continue

            vista = get_resolver().resolve(reverse_sin_args(nombre)).func
            clase = getattr(vista, 'view_class', None)

            if not getattr(clase, 'permission_required', None):
                sin_permiso.append(nombre)

        self.assertEqual(sin_permiso, [], 'Vistas sin permission_required.')


def reverse_sin_args(nombre):
    """Una dirección cualquiera de esa ruta, solo para saber qué vista atiende."""
    for intento in ([], [1], ['MQ', 'x']):
        try:
            return reverse(nombre, args=intento)
        except NoReverseMatch:
            continue
    raise AssertionError(f'No se pudo construir {nombre}')


class GruposDeRolTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campus = Campus.objects.create(nombre='Uno', latitud=19.8, longitud=-98.9)

    def cuenta(self, rol='estudiante', correo='ana@a.mx'):
        return Usuario.objects.create_user(
            correo=correo, nombre='Ana', password='x' * 20, campus=self.campus, rol=rol,
        )

    def nombres_de_grupos(self, usuario):
        return sorted(usuario.groups.values_list('name', flat=True))

    def test_existen_los_tres_grupos_de_rol(self):
        for nombre in NOMBRES_GRUPOS_DE_ROL:
            with self.subTest(grupo=nombre):
                self.assertTrue(Group.objects.get(name=nombre).permissions.exists())

    def test_cada_cuenta_entra_en_el_grupo_de_su_rol(self):
        self.assertEqual(self.nombres_de_grupos(self.cuenta('estudiante', 'e@a.mx')), ['Estudiante'])
        self.assertEqual(self.nombres_de_grupos(self.cuenta('admin', 'a@a.mx')), ['Administrador de campus'])
        self.assertEqual(self.nombres_de_grupos(self.cuenta('superadmin', 's@a.mx')), ['Superadministrador'])

    def test_al_cambiar_de_rol_cambia_de_grupo(self):
        ana = self.cuenta()
        ana.rol = 'admin'
        ana.save()

        self.assertEqual(self.nombres_de_grupos(ana), ['Administrador de campus'])
        self.assertTrue(ana.es_admin)

    def test_es_admin_y_es_superadmin_salen_de_permisos(self):
        estudiante = self.cuenta('estudiante', 'e@a.mx')
        admin = self.cuenta('admin', 'a@a.mx')
        superadmin = self.cuenta('superadmin', 's@a.mx')

        self.assertEqual((estudiante.es_admin, estudiante.es_superadmin), (False, False))
        self.assertEqual((admin.es_admin, admin.es_superadmin), (True, False))
        self.assertEqual((superadmin.es_admin, superadmin.es_superadmin), (True, True))

    def test_solo_la_superadministracion_entra_a_admin(self):
        self.assertFalse(self.cuenta('admin', 'a@a.mx').is_staff)
        self.assertTrue(self.cuenta('superadmin', 's@a.mx').is_staff)

    def test_createsuperuser_crea_un_superadministrador(self):
        """Antes ponía rol 'admin': esa cuenta no podía ni crear un campus."""
        call_command(
            'createsuperuser', interactive=False, correo='root@a.mx', nombre='Root',
            verbosity=0,
        )
        root = Usuario.objects.get(correo='root@a.mx')

        self.assertEqual(root.rol, 'superadmin')
        self.assertTrue(root.is_superuser)
        self.assertTrue(root.is_staff)
        self.assertTrue(root.es_superadmin)


class LoQueDecideEsElPermisoTests(TestCase):
    """permission_required en acción: el permiso abre y cierra las pantallas."""

    @classmethod
    def setUpTestData(cls):
        cls.campus = Campus.objects.create(nombre='Uno', latitud=19.8, longitud=-98.9)
        cls.ana = Usuario.objects.create_user(
            correo='ana@a.mx', nombre='Ana', password='x' * 20, campus=cls.campus,
        )

    def test_sin_el_permiso_la_pantalla_responde_403(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse('reporte-create')).status_code, 200)

        Group.objects.get(name='Estudiante').permissions.remove(permiso('reportes.add_reporte'))
        ana = Usuario.objects.get(pk=self.ana.pk)  # sin la caché de permisos
        self.client.force_login(ana)

        self.assertEqual(self.client.get(reverse('reporte-create')).status_code, 403)

    def test_un_grupo_extra_suma_permisos(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse('punto-create')).status_code, 403)

        puntos = Group.objects.create(name='Encargados de puntos')
        puntos.permissions.add(permiso('campus.add_puntoapoyo'))
        self.ana.groups.add(puntos)

        self.client.force_login(Usuario.objects.get(pk=self.ana.pk))
        self.assertEqual(self.client.get(reverse('punto-create')).status_code, 200)

    def test_un_permiso_suelto_tambien_cuenta(self):
        self.ana.user_permissions.add(permiso('usuarios.administrar_campus'))

        ana = Usuario.objects.get(pk=self.ana.pk)
        self.assertTrue(ana.es_admin)

        self.client.force_login(ana)
        self.assertEqual(self.client.get(reverse('panel')).status_code, 200)


class CrudDeGruposYPermisosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campus = Campus.objects.create(nombre='Uno', latitud=19.8, longitud=-98.9)
        cls.jefa = Usuario.objects.create_user(
            correo='jefa@a.mx', nombre='Jefa', password='x' * 20,
            campus=cls.campus, rol='superadmin',
        )
        cls.ana = Usuario.objects.create_user(
            correo='ana@a.mx', nombre='Ana', password='x' * 20, campus=cls.campus,
        )

    def setUp(self):
        self.client.force_login(self.jefa)

    def test_crear_un_grupo_con_permisos_y_miembros(self):
        exportar = permiso('reportes.view_reporte')

        respuesta = self.client.post(reverse('grupo-create'), {
            'name': 'Brigada', 'permissions': [exportar.pk], 'miembros': [self.ana.pk],
        })

        brigada = Group.objects.get(name='Brigada')
        self.assertRedirects(respuesta, reverse('grupo-detail', args=[brigada.pk]))
        self.assertEqual(list(brigada.permissions.all()), [exportar])
        self.assertIn(brigada, self.ana.groups.all())
        # Sigue en el de su rol.
        self.assertTrue(self.ana.groups.filter(name='Estudiante').exists())

    def test_los_grupos_de_rol_no_se_borran(self):
        estudiante = Group.objects.get(name='Estudiante')
        respuesta = self.client.post(reverse('grupo-delete', args=[estudiante.pk]))

        self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(Group.objects.filter(pk=estudiante.pk).exists())

    def test_a_los_grupos_de_rol_no_se_les_cambia_el_nombre(self):
        estudiante = Group.objects.get(name='Estudiante')
        self.client.post(reverse('grupo-update', args=[estudiante.pk]), {
            'name': 'Otro nombre',
            'permissions': list(estudiante.permissions.values_list('pk', flat=True)),
        })

        estudiante.refresh_from_db()
        self.assertEqual(estudiante.name, 'Estudiante')

    def test_crear_editar_y_borrar_un_permiso_propio(self):
        tipo = ContentType.objects.get(app_label='reportes', model='reporte')

        self.client.post(reverse('permiso-create'), {
            'name': 'Puede exportar reportes', 'codename': 'exportar_reporte',
            'content_type': tipo.pk,
        })
        nuevo = Permission.objects.get(codename='exportar_reporte')

        self.client.post(reverse('permiso-update', args=[nuevo.pk]), {
            'name': 'Puede exportar reportes a Excel', 'codename': 'exportar_reporte',
            'content_type': tipo.pk,
        })
        nuevo.refresh_from_db()
        self.assertEqual(nuevo.name, 'Puede exportar reportes a Excel')

        self.client.post(reverse('permiso-delete', args=[nuevo.pk]))
        self.assertFalse(Permission.objects.filter(pk=nuevo.pk).exists())

    def test_los_permisos_de_django_no_se_editan_ni_se_borran(self):
        ver = permiso('reportes.view_reporte')

        self.assertEqual(self.client.get(reverse('permiso-update', args=[ver.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('permiso-delete', args=[ver.pk])).status_code, 404)

    def test_no_se_crean_permisos_con_nombre_de_los_de_django(self):
        tipo = ContentType.objects.get(app_label='reportes', model='reporte')
        respuesta = self.client.post(reverse('permiso-create'), {
            'name': 'Trampa', 'codename': 'view_algo', 'content_type': tipo.pk,
        })

        self.assertEqual(respuesta.status_code, 200)  # vuelve el formulario con el error
        self.assertFalse(Permission.objects.filter(codename='view_algo').exists())

    def test_dar_grupos_y_permisos_a_una_cuenta_sin_perder_su_rol(self):
        brigada = Group.objects.create(name='Brigada')
        suelto = permiso('campus.add_puntoapoyo')

        self.client.post(reverse('usuario-update', args=[self.ana.pk]), {
            'nombre': 'Ana', 'apellidos': '', 'correo': 'ana@a.mx', 'telefono': '',
            'rol': 'estudiante', 'campus': self.campus.pk, 'activo': 'on',
            'groups': [brigada.pk], 'user_permissions': [suelto.pk],
        })

        ana = Usuario.objects.get(pk=self.ana.pk)
        self.assertEqual(
            sorted(ana.groups.values_list('name', flat=True)), ['Brigada', 'Estudiante'],
        )
        self.assertEqual(list(ana.user_permissions.all()), [suelto])
        self.assertTrue(ana.has_perm('campus.add_puntoapoyo'))

    def test_crear_cuenta_con_contrasena_que_sirve_para_entrar(self):
        self.client.post(reverse('usuario-create'), {
            'nombre': 'Beto', 'apellidos': '', 'correo': 'beto@a.mx', 'telefono': '',
            'campus': self.campus.pk, 'rol': 'admin', 'activo': 'on',
            'password': 'Campus-Seguro-2026', 'password2': 'Campus-Seguro-2026',
        })

        beto = Usuario.objects.get(correo='beto@a.mx')
        self.assertTrue(beto.check_password('Campus-Seguro-2026'))
        self.assertTrue(beto.groups.filter(name='Administrador de campus').exists())
        self.assertTrue(self.client.login(username='beto@a.mx', password='Campus-Seguro-2026'))
