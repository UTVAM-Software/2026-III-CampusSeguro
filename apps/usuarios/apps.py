from django.apps import AppConfig
from django.db.models.signals import post_migrate


def crear_grupos_de_rol(sender, **kwargs):
    """
    Al terminar `migrate`, que existan los grupos de rol con sus permisos.

    LOS PERMISOS SE CREAN PRIMERO
        Django crea los permisos de cada app al terminar `migrate`, una app
        detrás de otra. Cuando le toca a esta, los de las apps que van
        después (reportes, viajes, comunicación) todavía no existen. Por eso
        se crean aquí todos antes de armar los grupos: si no, los grupos
        nacerían sin esos permisos.
    """
    from django.apps import apps
    from django.contrib.auth.management import create_permissions

    for app_config in apps.get_app_configs():
        create_permissions(app_config, verbosity=0, using=kwargs.get('using', 'default'))

    from .roles import asegurar_grupos

    asegurar_grupos()


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.usuarios'

    def ready(self):
        post_migrate.connect(crear_grupos_de_rol, sender=self)
