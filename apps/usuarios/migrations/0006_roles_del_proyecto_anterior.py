"""
Pasa las cuentas a los tres roles del proyecto anterior.

QUE PASA CON LAS QUE TENIAN UN ROL QUE YA NO EXISTE
    `docente`, `administrativo` y `seguridad` pasan a `estudiante`, que es
    exactamente lo que podian hacer: esos tres roles no daban ni quitaban
    nada. Nadie pierde ningun permiso porque no tenian ninguno.

    Sin esto se quedarian con un `rol` que no esta en la lista: la pantalla
    ensenaria la clave cruda en vez de su etiqueta, y `es_admin` seguiria
    diciendo que no -asi que tampoco seria un agujero, solo un desastre
    visual-.

NO SE CREA NINGUN SUPERADMINISTRADOR AQUI
    Una migracion que reparte permisos sola es justo lo que nadie espera que
    haga una migracion. La cuenta se asigna a mano o con el guion de siembra.
"""

from django.db import migrations

#: Lo que podian hacer era lo mismo que un estudiante.
SIN_PERMISOS = ['docente', 'administrativo', 'seguridad']


def adelante(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'Usuario')
    Usuario.objects.filter(rol__in=SIN_PERMISOS).update(rol='estudiante')


def atras(apps, schema_editor):
    """
    No se puede deshacer, y da igual.

    Los tres roles que desaparecen eran indistinguibles de `estudiante`, asi
    que no hay informacion que recuperar: a cual de los tres pertenecia cada
    cuenta no cambiaba nada de lo que esa cuenta podia hacer.
    """


class Migration(migrations.Migration):

    dependencies = [('usuarios', '0005_alter_usuario_rol')]

    operations = [migrations.RunPython(adelante, atras)]
