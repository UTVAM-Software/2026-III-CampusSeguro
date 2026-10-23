"""
Deja la base con unos datos mínimos para poder trabajar.

    python herramientas/sembrar_datos.py

PARA QUÉ
    Una base recién migrada está vacía, y con todo vacío no se puede probar
    casi nada: no hay a quién asignar un reporte ni con quién llenar una
    lista. Esto pone lo justo para que las pantallas tengan algo que enseñar.

ESTO ES PARA DESARROLLO, Y NADA MÁS
    Los datos de aquí son de mentira y se nota: "prueba 1", "contenido". No
    sirven para enseñar el sistema como si estuviera en uso, ni para sacar
    cifras, ni para una demostración donde alguien pueda creer que son
    reportes reales de un campus.

    Si un día hay que enseñárselo a alguien, se enseña vacío y con sus huecos
    explicando qué va en cada sitio, o con datos que esa persona meta delante.

DE DÓNDE SALEN
    Son los que Lady tenía en su base el 14/10/2026, copiados tal cual. Se
    perdieron al rehacer la base para arreglar el cambio de modelo de cuenta,
    y quedan aquí para no volver a perderlos.

NO BORRA NADA
    Si ya existe algo con el mismo correo o el mismo nombre, lo deja como
    está. Se puede correr dos veces sin duplicar.
"""

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from apps.campus.models import Campus
from apps.comunicacion.models import Aviso, Notificacion
from apps.reportes.models import Reporte
from apps.usuarios.models import Usuario
from apps.viajes.models import UbicacionViaje, Viaje, ViajeAcompanante

#: La contraseña de las cuentas de prueba. Es de desarrollo y está escrita
#: aquí a propósito: así nadie tiene que adivinarla ni dictarla por chat. En
#: una base de verdad no existiría ninguna cuenta creada por un script.
CLAVE_DE_PRUEBA = "campus-seguro-desarrollo"


def main():
    # El campus de este equipo, con sus coordenadas de verdad.
    #
    # Antes eran 15, 52 -relleno, en mitad del océano Índico-. Las de ahora
    # salen de buscar la dirección en Nominatim, el buscador de
    # OpenStreetMap. Las demás universidades de la zona se cargan aparte, con
    # herramientas/cargar_campus.py.
    campus, _ = Campus.objects.get_or_create(
        nombre=(
            "UTVAM – Universidad Tecnológica de la Zona Metropolitana "
            "del Valle de México"
        ),
        defaults={
            "direccion": (
                "Boulevard Miguel Hidalgo y Costilla 5, Los Héroes Tizayuca, "
                "Tizayuca, Hidalgo, C.P. 43816"
            ),
            "latitud": Decimal("19.863700"),
            "longitud": Decimal("-98.982000"),
        },
    )

    lady = Usuario.objects.filter(correo="lady@gmail.com").first()
    if lady is None:
        lady = Usuario.objects.create_user(
            correo="lady@gmail.com", nombre="GUADALUPE", password=CLAVE_DE_PRUEBA,
            apellidos="SOLIS", telefono="7791092505", campus=campus,
        )

    alexis = Usuario.objects.filter(correo="alexis@gmail.com").first()
    if alexis is None:
        alexis = Usuario.objects.create_user(
            correo="alexis@gmail.com", nombre="CARABEO", password=CLAVE_DE_PRUEBA,
            apellidos="ALEXIS", telefono="1234567892", campus=campus,
            # La cuenta que administra el sistema: los campus y las cuentas.
            # Sin ella esas pantallas no se pueden abrir desde ningun sitio.
            rol="superadmin",
        )

    # Una cuenta por cada rol, para poder entrar con los tres y ver que
    # ensena cada uno. Son los tres del proyecto anterior:
    #
    #   estudiante  lo normal
    #   admin       administra SU campus: panel, avisos, puntos de apoyo,
    #               revisar reportes
    #   superadmin  ademas, el sistema: los campus y las cuentas
    #
    # Antes habia cinco -se sumaban docente, administrativo y seguridad- y
    # tres de ellos no daban ni quitaban nada.
    if not Usuario.objects.filter(correo="admin@gmail.com").exists():
        Usuario.objects.create_user(
            correo="admin@gmail.com", nombre="ADMINISTRACION",
            password=CLAVE_DE_PRUEBA, apellidos="DEL CAMPUS",
            campus=campus, rol="admin",
        )

    reporte, _ = Reporte.objects.get_or_create(
        usuario=lady, campus=campus, tipo="situacion",
        defaults={
            "descripcion": "Situacion registrada en el estacionamiento.",
            "latitud": Decimal("19.864600"),
            "longitud": Decimal("-98.981200"),
        },
    )

    viaje, nuevo = Viaje.objects.get_or_create(
        usuario=lady, origen="tizayuca", destino="veracruz",
    )
    if nuevo:
        # Invita a alexis, no a lady: el viaje es de lady, y nadie se
        # acompana a si mismo -el formulario ya no lo deja-.
        ViajeAcompanante.objects.create(viaje=viaje, acompanante=alexis)
        # La ultima posicion del viaje, saliendo del campus. Estaba en
        # 50, 20 -que cae en Polonia-: el mapa del viaje no ensenaba nada
        # que tuviera sentido.
        UbicacionViaje.objects.create(
            viaje=viaje,
            latitud=Decimal("19.864200"),
            longitud=Decimal("-98.979500"),
        )

    Aviso.objects.get_or_create(
        campus=campus, titulo="prueba 1",
        defaults={
            "contenido": "contenido",
            "autor": lady,
            "fecha_expiracion": date(2026, 10, 14),
        },
    )

    Notificacion.objects.get_or_create(
        usuario=alexis, titulo="prueba 1", defaults={"mensaje": "contenido"},
    )
    Notificacion.objects.get_or_create(
        usuario=alexis,
        titulo=f"Nuevo reporte: {reporte}",
        defaults={"mensaje": f"Situacion registrada en {campus}. ¿La puedes confirmar?"},
    )

    print(
        f"Listo.  campus: {Campus.objects.count()}  "
        f"cuentas: {Usuario.objects.count()}  "
        f"reportes: {Reporte.objects.count()}  "
        f"viajes: {Viaje.objects.count()}  "
        f"avisos: {Aviso.objects.count()}  "
        f"notificaciones: {Notificacion.objects.count()}"
    )
    print("La contraseña de las cuentas está en CLAVE_DE_PRUEBA, arriba en este archivo.")


if __name__ == "__main__":
    main()
