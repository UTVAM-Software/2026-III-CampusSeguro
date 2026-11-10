"""
Las universidades de la zona de Pachuca y Tizayuca, con sus coordenadas y
los dominios de correo con los que se entra a cada una.

DE DONDE SALEN LAS COORDENADAS
    Del proyecto anterior, donde se buscaron una por una con Nominatim -el
    buscador de OpenStreetMap- a partir de su direccion. No estan inventadas
    ni puestas a ojo sobre el mapa: cada par de coordenadas es el que devuelve
    OpenStreetMap para esa direccion.

DE DONDE SALEN LOS DOMINIOS, Y POR QUE FALTAN TANTOS
    Solo esta puesto el dominio que se pudo comprobar en una fuente de la
    propia universidad. Los demas van vacios A PROPOSITO.

    Un dominio equivocado no es un dato de menos: es una puerta cerrada. Si
    aqui dijera "pachuca.tecnm.mx" y resultara que el alumnado usa otro,
    NADIE de esa universidad podria registrarse, y el mensaje de error le
    diria que use un correo que no tiene. Vacio significa "sin restriccion",
    que es el estado honesto cuando no se sabe. El panel avisa de cuales
    estan asi para que alguien los complete.

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
    lo que ya existe en vez de duplicarlo. Los dominios solo los pone donde
    todavia no hay ninguno, para no pisar lo que alguien haya configurado
    desde la aplicacion (Panel -> Campus).
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

# Los dominios comprobados, cada uno con la fuente donde se comprobo.
#
# UAEH   uaeh.edu.mx
#        Sus "Lineamientos para el uso del correo institucional" dicen que el
#        correo bajo ese dominio es "el medio oficial, prioritario y
#        obligatorio" para toda su comunidad, de todos los niveles. Uno solo
#        para alumnado y personal: no hay subdominio de alumnos.
#        uaeh.edu.mx/planeacion/sistemas/contenidos/lineamientos-correo/
#
# IPN    alumno.ipn.mx (alumnado) + ipn.mx (personal)
#        La politica de cuentas del IPN llama cuenta institucional definitiva
#        a la de "@alumno.ipn.mx". Van los dos porque en UPIIH hay cuentas de
#        las dos clases.
#        upiita.ipn.mx/adjuntos/correo/Politicasalumnoguinda.pdf
#
# UTVAM  utvam.edu.mx
#        Lo confirmo el equipo, que estudia ahi. Su sitio publica documentos
#        bajo ese dominio pero en ninguna pagina dice el formato del correo
#        del alumnado, asi que la fuente buena aqui es la de dentro.
#
# Los que quedaron vacios y por que:
#   TecNM Pachuca     su sitio aparece como itpachuca.edu.mx y sus contactos
#                     como @tecnm.mx; ninguna pagina publica el formato del
#                     alumnado.
#   Tec de Monterrey  usa varios subdominios a la vez -su propio soporte
#                     responde desde @servicios.tec.mx-. Poner "tec.mx" a
#                     secas es una apuesta.
#   La Salle, UPN, UPMH
#                     sin fuente publica que lo diga.
#
#: (nombre, direccion, latitud, longitud, dominios de correo)
CAMPUS = [
    ("Instituto Tecnológico de Pachuca (TecNM)",
     "Boulevard Felipe Ángeles s/n, Infonavit Venta Prieta, Pachuca de Soto, Hidalgo, C.P. 42083",
     "20.0840575", "-98.7750467", ""),
    ("Tecnológico de Monterrey – Campus Hidalgo",
     "Boulevard Felipe Ángeles 2003, Venta Prieta, Pachuca de Soto, Hidalgo, C.P. 42080",
     "20.0963225", "-98.7650544", ""),
    ("UAEH – Campus La Concepción (ICSHu e ICSa)",
     "Circuito Ex Hacienda La Concepción s/n, Carretera Pachuca–Actopan, San Agustín Tlaxiaca, Hidalgo, C.P. 42160",
     "20.1213997", "-98.7966816", "uaeh.edu.mx"),
    ("UAEH – Ciudad del Conocimiento",
     "Carretera Pachuca–Tulancingo km 4.5, Carboneras, Mineral de la Reforma, Hidalgo, C.P. 42184",
     "20.0945563", "-98.7104973", "uaeh.edu.mx"),
    ("UAEH – Edificio Central",
     "Calle Mariano Abasolo, Centro Histórico, Pachuca de Soto, Hidalgo, C.P. 42010",
     "20.1281399", "-98.7342268", "uaeh.edu.mx"),
    ("UAEH – Escuela Superior de Tizayuca",
     "Carretera Federal Tizayuca–Pachuca km 2.5, Haciendas de Tizayuca, Tizayuca, Hidalgo, C.P. 43800",
     "19.8656196", "-98.9697053", "uaeh.edu.mx"),
    ("UAEH – Instituto de Ciencias Económico Administrativas (ICEA)",
     "Circuito La Concepción km 2.5, San Juan Tilcuautla, San Agustín Tlaxiaca, Hidalgo, C.P. 42160",
     "20.1414935", "-98.8050337", "uaeh.edu.mx"),
    ("Universidad La Salle Pachuca",
     "Calle San Juan Bautista de La Salle, San Agustín Tlaxiaca, Hidalgo, C.P. 42160",
     "20.1341424", "-98.8057568", ""),
    ("Universidad Pedagógica Nacional – Unidad Hidalgo",
     "Avenida Los Pirules, El Tezontle, Pachuca de Soto, Hidalgo, C.P. 42083",
     "20.0821400", "-98.7781708", ""),
    ("Universidad Politécnica Metropolitana de Hidalgo",
     "Boulevard Acceso a Tolcayuca 1009, Tolcayuca, Hidalgo, C.P. 43860",
     "19.9460146", "-98.8890693", ""),
    ("UPIIH – Instituto Politécnico Nacional, Campus Hidalgo",
     "Carretera Pachuca–Actopan km 1+500, Ciudad del Conocimiento y la Cultura, San Agustín Tlaxiaca, Hidalgo, C.P. 42162",
     "20.1137009", "-98.8426278", "alumno.ipn.mx, ipn.mx"),
    ("UTVAM – Universidad Tecnológica de la Zona Metropolitana del Valle de México",
     "Boulevard Miguel Hidalgo y Costilla 5, Los Héroes Tizayuca, Tizayuca, Hidalgo, C.P. 43816",
     "19.8637000", "-98.9820000", "utvam.edu.mx"),
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
    con_dominio = 0
    respetados = []

    for nombre, direccion, latitud, longitud, dominios in CAMPUS:
        campus, creado = Campus.objects.update_or_create(
            nombre=nombre,
            defaults={
                "direccion": direccion,
                "latitud": Decimal(latitud),
                "longitud": Decimal(longitud),
            },
        )
        nuevos += creado

        # Solo donde no hay nada. Si alguien lo puso desde el Panel, manda lo
        # suyo: conoce su universidad mejor que esta lista.
        if dominios and not campus.dominios_correo:
            campus.dominios_correo = dominios
            campus.save(update_fields=["dominios_correo"])
            con_dominio += 1
        elif dominios and campus.dominios_correo != dominios:
            respetados.append(f"{campus.nombre}: {campus.dominios_correo}")

    sin_dominio = Campus.objects.filter(dominios_correo="").count()

    print(f"{len(CAMPUS)} campus en total, {nuevos} nuevos.")
    print(f"{con_dominio} dominios puestos.")

    for linea in respetados:
        print(f"  (ya tenia otro, se respeta) {linea}")

    if sin_dominio:
        print(
            f"{sin_dominio} campus siguen SIN dominio: admiten cualquier correo. "
            "Se ponen desde Panel -> Campus."
        )


if __name__ == "__main__":
    main()
