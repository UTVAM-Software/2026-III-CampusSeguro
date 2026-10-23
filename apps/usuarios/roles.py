"""
Los tres roles del proyecto, convertidos en GRUPOS de Django con PERMISOS.

POR QUÉ GRUPOS Y NO SOLO EL CAMPO `rol`
    El campo `rol` decía quién era cada cuenta, pero Django no lo entiende:
    `permission_required`, `user.has_perm()` y `{{ perms }}` en las plantillas
    trabajan con permisos. Ahora cada rol es un grupo (Estudiante,
    Administrador de campus, Superadministrador) y cada grupo tiene sus
    permisos. Lo que una cuenta puede hacer sale de sus grupos.

EL ROL SIGUE EXISTIENDO
    Es el rol "principal" de la cuenta. Al guardar una cuenta, `Usuario.save()`
    la mete en el grupo de su rol y la saca de los otros dos. Los demás grupos
    que el superadministrador cree desde la app ("Brigada de seguridad", por
    ejemplo) se suman a ese y no se tocan.

LOS PERMISOS DE CADA GRUPO SE PUEDEN CAMBIAR DESDE LA APP
    Lo de abajo son los permisos con los que NACE cada grupo. Si el
    superadministrador los cambia desde la pantalla de Grupos, se respetan:
    `asegurar_grupos()` solo los pone cuando el grupo no existe.
"""

from django.contrib.auth.models import Group, Permission

# Permisos propios del proyecto (están en `Usuario.Meta.permissions`). Los
# demás son los cuatro que Django crea solo para cada modelo:
# view_, add_, change_ y delete_.
ADMINISTRAR_CAMPUS = 'usuarios.administrar_campus'
ADMINISTRAR_SISTEMA = 'usuarios.administrar_sistema'


def _crud(app, modelo, *acciones):
    """`_crud('viajes', 'viaje', 'view', 'add')` -> ['viajes.view_viaje', 'viajes.add_viaje']"""
    return [f'{app}.{accion}_{modelo}' for accion in acciones]


TODO = ('view', 'add', 'change', 'delete')

#: Lo que puede hacer cualquier cuenta. Los registros de otra persona o de
#: otro campus no los ve aunque tenga el permiso: eso lo filtra cada vista con
#: `get_queryset()` y responde 404.
PERMISOS_ESTUDIANTE = [
    *_crud('campus', 'campus', 'view'),
    *_crud('campus', 'puntoapoyo', 'view'),
    # Avisar de que un punto está mal, y corregir lo que escribió. La vista
    # de editar solo deja con los suyos y sin revisar -`get_queryset()`-, y
    # dar por revisado un aviso pide `administrar_campus`, que es otra cosa.
    *_crud('campus', 'correccion', 'add', 'change'),
    *_crud('reportes', 'reporte', *TODO),           # los suyos
    *_crud('reportes', 'reporteconfirmacion', *TODO),
    *_crud('viajes', 'viaje', *TODO),
    *_crud('viajes', 'viajeacompanante', *TODO),
    *_crud('viajes', 'ubicacionviaje', *TODO),
    *_crud('viajes', 'destinoguardado', *TODO),
    *_crud('comunicacion', 'aviso', 'view'),
    *_crud('comunicacion', 'notificacion', *TODO),
    *_crud('usuarios', 'usuario', 'view', 'change'),  # solo su propia ficha
]

#: Quien administra SU campus: el panel, los avisos, los puntos de apoyo y la
#: revisión de reportes y correcciones.
PERMISOS_ADMIN = PERMISOS_ESTUDIANTE + [
    ADMINISTRAR_CAMPUS,
    *_crud('campus', 'puntoapoyo', 'add', 'change', 'delete'),
    *_crud('campus', 'correccion', 'view', 'change', 'delete'),
    *_crud('comunicacion', 'aviso', 'add', 'change', 'delete'),
]

#: Quien administra el SISTEMA: además, los campus, las cuentas y los grupos
#: y permisos de Django.
PERMISOS_SUPERADMIN = PERMISOS_ADMIN + [
    ADMINISTRAR_SISTEMA,
    *_crud('campus', 'campus', 'add', 'change', 'delete'),
    *_crud('usuarios', 'usuario', 'add', 'delete'),
    *_crud('auth', 'group', *TODO),
    *_crud('auth', 'permission', *TODO),
]

#: rol -> (nombre del grupo, permisos con los que nace)
GRUPOS_DE_ROL = {
    'estudiante': ('Estudiante', PERMISOS_ESTUDIANTE),
    'admin': ('Administrador de campus', PERMISOS_ADMIN),
    'superadmin': ('Superadministrador', PERMISOS_SUPERADMIN),
}

#: Los nombres de los tres grupos de rol. No se pueden borrar ni renombrar
#: desde la app: `Usuario.save()` los busca por nombre.
NOMBRES_GRUPOS_DE_ROL = [nombre for nombre, _ in GRUPOS_DE_ROL.values()]


def buscar_permisos(nombres):
    """
    De ['app.codigo', ...] a objetos Permission.

    Los que todavía no existan se ignoran en vez de romper: pasa al crear la
    base desde cero, antes de que Django haya creado los permisos de todas
    las apps. `asegurar_grupos()` se vuelve a llamar al final de `migrate`.
    """
    permisos = []

    for nombre in nombres:
        app, codigo = nombre.split('.')
        permiso = Permission.objects.filter(
            content_type__app_label=app, codename=codigo
        ).first()

        if permiso:
            permisos.append(permiso)

    return permisos


def grupo_de_rol(rol):
    """El grupo de un rol. Si no existe, lo crea con sus permisos de fábrica."""
    nombre, permisos = GRUPOS_DE_ROL.get(rol, GRUPOS_DE_ROL['estudiante'])
    grupo, creado = Group.objects.get_or_create(name=nombre)

    if creado or not grupo.permissions.exists():
        grupo.permissions.set(buscar_permisos(permisos))

    return grupo


def asegurar_grupos():
    """
    Que existan los tres grupos de rol y que cada cuenta esté en el suyo.

    Se llama al terminar `migrate` (ver `UsuariosConfig.ready`). Así una base
    que ya tenía cuentas -la de cada integrante del equipo- queda repartida
    en grupos sin hacer nada a mano.
    """
    from django.db.models import Q

    from .models import Usuario

    for rol in GRUPOS_DE_ROL:
        grupo_de_rol(rol)

    for usuario in Usuario.objects.all():
        usuario.sincronizar_grupo_de_rol()

    # El acceso a /admin/ de las cuentas que ya existían. Las nuevas lo
    # reciben en `Usuario.save()`.
    con_admin = Q(rol='superadmin') | Q(is_superuser=True)
    Usuario.objects.filter(con_admin).update(is_staff=True)
    Usuario.objects.exclude(con_admin).update(is_staff=False)
