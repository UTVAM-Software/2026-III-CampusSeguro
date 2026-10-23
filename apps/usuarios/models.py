from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin,
)
from django.db import models
from django.urls import reverse


class UsuarioManager(BaseUserManager):
    """
    Quien crea las cuentas.

    Hace falta porque el modelo no se llama `User` ni entra por un nombre de
    usuario: Django necesita que alguien le diga cómo nace una cuenta y cómo
    nace un superusuario (`manage.py createsuperuser`).
    """

    use_in_migrations = True

    def create_user(self, correo, nombre, password=None, **extra):
        if not correo:
            raise ValueError('El correo es obligatorio')

        # En minúsculas y normalizado: si no, Ana@x.edu y ana@x.edu serían dos
        # cuentas distintas y la de unique=True no lo impediría.
        usuario = self.model(
            correo=self.normalize_email(correo).lower(),
            nombre=nombre.strip(),
            **extra,
        )

        # set_password cifra la contraseña. En claro no llega nunca a la base
        # ni a un registro de texto: lo que se guarda es un resumen del que no
        # se puede volver atrás.
        usuario.set_password(password)
        usuario.save(using=self._db)

        return usuario

    def create_superuser(self, correo, nombre, password=None, **extra):
        # `manage.py createsuperuser` crea la cuenta que administra TODO: rol
        # de superadministración (antes ponía 'admin' y esa cuenta no podía
        # crear campus), superusuario de Django y acceso a /admin/.
        extra.setdefault('rol', 'superadmin')
        extra.setdefault('is_superuser', True)
        extra.setdefault('is_staff', True)
        return self.create_user(correo, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    La cuenta de una persona.

    HEREDA DE AbstractBaseUser, NO DE models.Model
        Eso es lo que le da contraseña y sesión. Antes era un modelo normal:
    se podían listar y editar personas, pero nadie podía entrar al sistema, y
    sin saber quién mira no hay forma de decidir qué puede ver.

    Y DE PermissionsMixin
        Eso le da los GRUPOS y PERMISOS de Django: los campos `groups`,
        `user_permissions` e `is_superuser`, y los métodos `has_perm()` y
        `has_module_perms()`. Sin esto no funcionan `permission_required`,
        `PermissionRequiredMixin` ni el panel /admin/. Ver roles.py.

    NO SE USA EL `User` QUE TRAE DJANGO
    La identidad aquí es el correo, no un nombre de usuario, y el rol es del
    negocio -estudiante, docente, seguridad- no un permiso de administración.
    """

    # LOS TRES ROLES DEL PROYECTO ANTERIOR
    #
    # Eran cinco -se sumaban docente, administrativo y seguridad- y tres de
    # ellos no daban ni quitaban nada: una cuenta con rol `seguridad` podía
    # exactamente lo mismo que una de estudiante. Un rol que no cambia nada
    # es peor que no tenerlo: quien lo asigna cree que está repartiendo
    # permisos y no está repartiendo nada.
    #
    # Estos tres sí se distinguen, y la diferencia está escrita abajo en
    # `es_admin` y `es_superadmin`.
    ROLES = [
        ('estudiante', 'Estudiante'),
        ('admin', 'Administrador de campus'),
        ('superadmin', 'Superadministrador'),
    ]
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100, blank=True)
    correo = models.EmailField(unique=True)
    # Con verbose_name porque si no Django pone "Telefono" sin acento en la
    # etiqueta del formulario, sacandola del nombre del campo.
    telefono = models.CharField('teléfono', max_length=15, blank=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='estudiante')

    # La foto de perfil. Admite vacío: quien no suba ninguna sigue teniendo
    # avatar -la inicial de su nombre en un círculo-, que es lo que había
    # hasta ahora y se ve igual de bien en la lateral.
    #
    # El nombre del archivo lo pone el formulario al azar, y no "perfil.jpg":
    # la carpeta de medios se sirve tal cual, así que un nombre previsible
    # sería una dirección que cualquiera puede probar para ver la foto de otra
    # persona sin tener permiso para nada.
    foto = models.ImageField(
        'foto', upload_to='perfiles/', max_length=500, blank=True, default=''
    )

    # Admite vacío para que se pueda crear la primera cuenta cuando todavía no
    # hay ningún campus: `createsuperuser` sobre una base recién hecha. Quien
    # se registra desde la pantalla sí elige el suyo.
    campus = models.ForeignKey(
        'campus.Campus', on_delete=models.PROTECT, null=True, blank=True
    )

    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Si puede entrar al panel /admin/ de Django. Lo tiene la
    # superadministración: se pone solo al guardar, según el rol.
    is_staff = models.BooleanField('acceso a /admin/', default=False)

    objects = UsuarioManager()

    # Con qué se entra, y qué más pide createsuperuser además de la contraseña.
    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre']

    # A qué campo le escribe Django cuando manda el correo de recuperación.
    # Por omisión busca uno llamado `email`, que aquí no existe: sin esto, la
    # pantalla de "olvidé mi contraseña" no encontraría a nadie nunca y no
    # diría por qué -no avisa de los correos que no existen, a propósito-.
    EMAIL_FIELD = 'correo'

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        # Permisos propios, además de los cuatro que Django crea solo
        # (view, add, change, delete). Son los que distinguen a quien
        # administra: ver roles.py.
        permissions = [
            ('administrar_campus',
             'Puede administrar su campus (panel, avisos, puntos de apoyo y reportes)'),
            ('administrar_sistema',
             'Puede administrar el sistema (campus, cuentas, grupos y permisos)'),
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellidos}".strip()

    def get_absolute_url(self):
        return reverse('usuario-detail', args=[self.pk])

    @property
    def nombre_completo(self):
        """Nombre y apellidos, para las pantallas que no usan `str()`."""
        return str(self)

    # ------------------------------------------------------------------ #
    # El rol y los grupos
    # ------------------------------------------------------------------ #

    def save(self, *args, **kwargs):
        # El acceso a /admin/ va con el rol: lo tiene la superadministración.
        self.is_staff = self.is_superuser or self.rol == 'superadmin'

        super().save(*args, **kwargs)

        # `update_fields` sin `rol` es un guardado parcial -por ejemplo, el de
        # `last_login` al entrar-: ahí el rol no cambió y no hay nada que
        # sincronizar.
        campos = kwargs.get('update_fields')

        if campos is None or 'rol' in campos:
            self.sincronizar_grupo_de_rol()

    def sincronizar_grupo_de_rol(self):
        """
        Mete la cuenta en el grupo de su rol y la saca de los otros dos.

        Los grupos que no son de rol (los que se crean desde la app) no se
        tocan: se suman a los permisos del rol.
        """
        from django.contrib.auth.models import Group

        from .roles import NOMBRES_GRUPOS_DE_ROL, grupo_de_rol

        grupo = grupo_de_rol(self.rol)
        otros = Group.objects.filter(name__in=NOMBRES_GRUPOS_DE_ROL).exclude(pk=grupo.pk)

        self.groups.remove(*otros)
        self.groups.add(grupo)

        # Django guarda los permisos en caché la primera vez que se preguntan.
        # Si no se borra, la cuenta seguiría con los permisos del rol anterior
        # hasta la siguiente petición.
        for cache in ('_perm_cache', '_user_perm_cache', '_group_perm_cache'):
            self.__dict__.pop(cache, None)

    @property
    def es_admin(self):
        """
        Quién administra SU campus: el panel, los avisos, los puntos de
        apoyo, mover el estado de un reporte.

        AHORA SE DECIDE CON UN PERMISO, NO CON EL ROL
            Antes era `rol in ('admin', 'superadmin')`. Ahora es el permiso
            `usuarios.administrar_campus`, que tienen los grupos
            "Administrador de campus" y "Superadministrador". Si el
            superadministrador se lo da a otro grupo desde la app, esas
            cuentas también administran: lo manda el permiso, no un texto.

        INCLUYE AL SUPERADMINISTRADOR, Y ES A PROPÓSITO
            Puede todo lo que puede un administrador de campus, y además lo
            del sistema. Si no estuviera aquí, cada vista que administra algo
            tendría que preguntar por los dos roles, y la que se olvidara de
            uno dejaría al superadministrador fuera de su propia aplicación.
        """
        return self.has_perm('usuarios.administrar_campus')

    @property
    def es_superadmin(self):
        """
        Quién administra el SISTEMA: los campus y las cuentas.

        POR QUÉ ESTAS DOS COSAS Y NO OTRAS
            Un campus se lleva por delante los reportes, los avisos y los
            puntos de apoyo de toda su gente. Y la lista de cuentas es el
            directorio con los correos y los teléfonos de la comunidad
            entera.

            Quien administra un campus no necesita ninguna de las dos para
            su trabajo, y dárselas significaría que puede tocar los datos de
            las demás universidades.

        Igual que `es_admin`, sale de un permiso:
        `usuarios.administrar_sistema`.
        """
        return self.has_perm('usuarios.administrar_sistema')

    @property
    def is_active(self):
        """
        Django pregunta por `is_active` al validar quién entra; en este
        proyecto esa columna se llama `activo`. Quitar el acceso a alguien es
        apagar `activo`: no se borra nada, y sus reportes y su historial siguen
        donde estaban.
        """
        return self.activo
