"""
Las universidades de la zona de Pachuca y Tizayuca, con sus coordenadas.

DE DONDE SALEN
    Del proyecto anterior, donde se buscaron una por una con Nominatim -el
    buscador de OpenStreetMap- a partir de su direccion. No estan inventadas
    ni puestas a ojo sobre el mapa: cada par de coordenadas es el que devuelve
    OpenStreetMap para esa direccion.

QUE ARREGLA
    El campus que habia sembrado era un relleno: latitud 15, longitud 52, que
    cae en mitad del oceano Indico. El mapa no se notaba porque encuadra los
    reportes, pero un campus sin reportes abria en el agua, y las rutas
    necesitan el punto de verdad.

    Ese registro NO se borra -tiene colgando las cuentas, el reporte y el
    aviso-: se le ponen encima los datos de UTVAM, que es la universidad de
    este equipo y la que tenian las cuentas en el sistema anterior.

COMO SE USA
    .venv/Scripts/python.exe herramientas/cargar_campus.py

    Se puede correr las veces que haga falta: busca por nombre y actualiza
    lo que ya existe en vez de duplicarlo.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.campus.models import Campus  # noqa: E402

#: El de este equipo. Es el que hereda los datos del campus de relleno.
PROPIO = "UTVAM"

#: (nombre, direccion, latitud, longitud)
CAMPUS = [
    ("Instituto Tecnológico de Pachuca (TecNM)",
     "Boulevard Felipe Ángeles s/n, Infonavit Venta Prieta, Pachuca de Soto, Hidalgo, C.P. 42083",
     "20.0840575", "-98.7750467"),
    ("Tecnológico de Monterrey – Campus Hidalgo",
     "Boulevard Felipe Ángeles 2003, Venta Prieta, Pachuca de Soto, Hidalgo, C.P. 42080",
     "20.0963225", "-98.7650544"),
    ("UAEH – Campus La Concepción (ICSHu e ICSa)",
     "Circuito Ex Hacienda La Concepción s/n, Carretera Pachuca–Actopan, San Agustín Tlaxiaca, Hidalgo, C.P. 42160",
     "20.1213997", "-98.7966816"),
    ("UAEH – Ciudad del Conocimiento",
     "Carretera Pachuca–Tulancingo km 4.5, Carboneras, Mineral de la Reforma, Hidalgo, C.P. 42184",
     "20.0945563", "-98.7104973"),
    ("UAEH – Edificio Central",
     "Calle Mariano Abasolo, Centro Histórico, Pachuca de Soto, Hidalgo, C.P. 42010",
     "20.1281399", "-98.7342268"),
    ("UAEH – Escuela Superior de Tizayuca",
     "Carretera Federal Tizayuca–Pachuca km 2.5, Haciendas de Tizayuca, Tizayuca, Hidalgo, C.P. 43800",
     "19.8656196", "-98.9697053"),
    ("UAEH – Instituto de Ciencias Económico Administrativas (ICEA)",
     "Circuito La Concepción km 2.5, San Juan Tilcuautla, San Agustín Tlaxiaca, Hidalgo, C.P. 42160",
     "20.1414935", "-98.8050337"),
    ("Universidad La Salle Pachuca",
     "Calle San Juan Bautista de La Salle, San Agustín Tlaxiaca, Hidalgo, C.P. 42160",
     "20.1341424", "-98.8057568"),
    ("Universidad Pedagógica Nacional – Unidad Hidalgo",
     "Avenida Los Pirules, El Tezontle, Pachuca de Soto, Hidalgo, C.P. 42083",
     "20.0821400", "-98.7781708"),
    ("Universidad Politécnica Metropolitana de Hidalgo",
     "Boulevard Acceso a Tolcayuca 1009, Tolcayuca, Hidalgo, C.P. 43860",
     "19.9460146", "-98.8890693"),
    ("UPIIH – Instituto Politécnico Nacional, Campus Hidalgo",
     "Carretera Pachuca–Actopan km 1+500, Ciudad del Conocimiento y la Cultura, San Agustín Tlaxiaca, Hidalgo, C.P. 42162",
     "20.1137009", "-98.8426278"),
    ("UTVAM – Universidad Tecnológica de la Zona Metropolitana del Valle de México",
     "Boulevard Miguel Hidalgo y Costilla 5, Los Héroes Tizayuca, Tizayuca, Hidalgo, C.P. 43816",
     "19.8637000", "-98.9820000"),
]


def main():
    # El de relleno: coordenadas que no son de ningun sitio real. Se le ponen
    # encima los datos de UTVAM para no perder lo que cuelga de el.
    relleno = Campus.objects.filter(latitud=Decimal("15"), longitud=Decimal("52")).first()
    propio = next(c for c in CAMPUS if c[0].startswith(PROPIO))

    if relleno:
        relleno.nombre, relleno.direccion = propio[0], propio[1]
        relleno.latitud, relleno.longitud = Decimal(propio[2]), Decimal(propio[3])
        relleno.save()
        print(f"Arreglado el campus de relleno -> {relleno.nombre}")

    nuevos = 0

    for nombre, direccion, latitud, longitud in CAMPUS:
        _, creado = Campus.objects.update_or_create(
            nombre=nombre,
            defaults={
                "direccion": direccion,
                "latitud": Decimal(latitud),
                "longitud": Decimal(longitud),
            },
        )
        nuevos += creado

    print(f"{len(CAMPUS)} campus en total, {nuevos} nuevos.")


if __name__ == "__main__":
    main()
