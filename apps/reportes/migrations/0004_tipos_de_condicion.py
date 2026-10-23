"""
Pasa los reportes viejos a las categorias nuevas.

Sin esto, los que ya estaban guardados se quedan con un `tipo` que ya no
existe en la lista: la pantalla los ensenaria con la clave cruda -"robo"- en
vez de su etiqueta, y el filtro del mapa no los encontraria nunca.

LAS TRES QUE DESAPARECEN SE JUNTAN EN UNA
    Robo, acoso y persona sospechosa pasan a "Situacion registrada". Se
    pierde el matiz, y es a proposito: eran tres formas de afirmar un delito
    que nadie ha probado. Lo que queda dicho es que alli paso algo, que es lo
    que de verdad sabe este sistema.

    La descripcion que escribio quien reporto no se toca, asi que lo que
    conto sigue entero en su reporte.
"""

from django.db import migrations

#: De lo viejo a lo nuevo. Lo que no este aqui se queda como esta.
EQUIVALENCIAS = {
    'robo': 'situacion',
    'acoso': 'situacion',
    'sospechoso': 'situacion',
}

#: Para deshacerlo. No es exacto -las tres volverian como "situacion"- porque
#: la informacion que se junta no se puede separar otra vez.
VUELTA = {'situacion': 'otro'}


def adelante(apps, schema_editor):
    Reporte = apps.get_model('reportes', 'Reporte')

    for viejo, nuevo in EQUIVALENCIAS.items():
        Reporte.objects.filter(tipo=viejo).update(tipo=nuevo)


def atras(apps, schema_editor):
    Reporte = apps.get_model('reportes', 'Reporte')

    for nuevo, viejo in VUELTA.items():
        Reporte.objects.filter(tipo=nuevo).update(tipo=viejo)


class Migration(migrations.Migration):

    dependencies = [('reportes', '0003_alter_reporte_tipo')]

    operations = [migrations.RunPython(adelante, atras)]
