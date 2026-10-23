"""
Escribe docs/esquema_mysql.sql a partir de los modelos.

PARA QUE SIRVE
    El proyecto corre sobre SQLite. Este script traduce el mismo esquema a
    MySQL para poder verlo en Workbench: se abre con

        Database > Reverse Engineer MySQL Create Script

    y Workbench dibuja solo el diagrama entidad-relacion.

POR QUE SE GENERA Y NO SE ESCRIBE A MANO
    Un .sql escrito a mano se queda viejo en cuanto alguien toca un modelo, y
    nadie se entera hasta que el diagrama de la documentacion dice una cosa y
    la base dice otra. Esto se vuelve a correr y ya.

    Para regenerarlo:

        python herramientas/generar_esquema_mysql.py

COMO TRADUCE
    Se usan los mismos tipos que usaria Django con el conector de MySQL
    (django/db/backends/mysql/base.py). La tabla de equivalencias esta abajo,
    en TIPOS, para que se pueda comprobar.
"""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.apps import apps

#: Lo que pone Django cuando el motor es MySQL.
TIPOS = {
    "AutoField": "integer AUTO_INCREMENT",
    "BigAutoField": "bigint AUTO_INCREMENT",
    "BooleanField": "bool",
    "CharField": "varchar({max_length})",
    "DateField": "date",
    "DateTimeField": "datetime(6)",
    "DecimalField": "numeric({max_digits}, {decimal_places})",
    "EmailField": "varchar({max_length})",
    "FileField": "varchar({max_length})",
    "ImageField": "varchar({max_length})",
    "IntegerField": "integer",
    "PositiveIntegerField": "integer UNSIGNED",
    "SlugField": "varchar({max_length})",
    "TextField": "longtext",
    "UUIDField": "char(32)",
}

APPS_DEL_PROYECTO = ["campus", "usuarios", "reportes", "viajes", "comunicacion"]


def tipo_de(campo) -> str:
    interno = campo.get_internal_type()

    if interno in ("ForeignKey", "OneToOneField"):
        # La columna toma el tipo de la clave a la que apunta, sin el
        # AUTO_INCREMENT: la que se incrementa sola es la original.
        destino = campo.target_field
        return tipo_de(destino).replace(" AUTO_INCREMENT", "")

    plantilla = TIPOS.get(interno)

    if plantilla is None:
        raise SystemExit(f"Falta el tipo {interno} en TIPOS (campo {campo.name})")

    return plantilla.format(
        max_length=getattr(campo, "max_length", None) or 255,
        max_digits=getattr(campo, "max_digits", None),
        decimal_places=getattr(campo, "decimal_places", None),
    )


def columnas_y_claves(modelo):
    columnas, claves = [], []

    for campo in modelo._meta.local_fields:
        pieza = f"  `{campo.column}` {tipo_de(campo)}"

        if campo.primary_key:
            pieza += " NOT NULL PRIMARY KEY"
        else:
            pieza += " NULL" if campo.null else " NOT NULL"

            if campo.unique:
                pieza += " UNIQUE"

        columnas.append(pieza)

        if campo.is_relation and campo.related_model is not None:
            otro = campo.related_model._meta
            claves.append(
                f"  CONSTRAINT `fk_{modelo._meta.db_table}_{campo.column}` "
                f"FOREIGN KEY (`{campo.column}`) "
                f"REFERENCES `{otro.db_table}` (`{otro.pk.column}`)"
            )

    for conjunto in modelo._meta.unique_together:
        nombres = ", ".join(f"`{modelo._meta.get_field(n).column}`" for n in conjunto)
        claves.append(f"  UNIQUE KEY `uq_{modelo._meta.db_table}` ({nombres})")

    return columnas + claves


def ordenar(modelos):
    """
    Primero las tablas a las que apuntan otras.

    Sin esto, una FOREIGN KEY apuntaria a una tabla que todavia no existe y
    Workbench se quejaria al importar.
    """
    pendientes, puestos, orden = list(modelos), set(), []

    while pendientes:
        avanzo = False

        for modelo in list(pendientes):
            necesita = {
                c.related_model
                for c in modelo._meta.local_fields
                if c.is_relation and c.related_model is not None
                and c.related_model is not modelo
            }

            if necesita <= puestos:
                orden.append(modelo)
                puestos.add(modelo)
                pendientes.remove(modelo)
                avanzo = True

        if not avanzo:  # dependencia circular: se sueltan como vengan
            orden.extend(pendientes)
            break

    return orden


def main():
    modelos = [
        m for m in apps.get_models() if m._meta.app_label in APPS_DEL_PROYECTO
    ]

    lineas = [
        "-- Esquema de Campus Seguro en MySQL.",
        "--",
        "-- GENERADO: no se edita a mano. Sale de los modelos de Django con",
        "--     python herramientas/generar_esquema_mysql.py",
        "--",
        "-- El proyecto corre sobre SQLite; esto existe para ver el diagrama en",
        "-- MySQL Workbench, con Database > Reverse Engineer MySQL Create Script.",
        "--",
        f"-- {len(modelos)} tablas del proyecto. Las de Django (django_migrations,",
        "-- auth_permission y demas) no estan aqui: son del framework, no del",
        "-- modelo del negocio.",
        "",
        "-- La base se llama ...-diagrama y NO campus_seguro a proposito: en esta",
        "-- maquina ya hay un MySQL con una base campus_seguro, la del proyecto",
        "-- anterior. Importar esto ahi le meteria once tablas encima.",
        "CREATE DATABASE IF NOT EXISTS campus_seguro_diagrama",
        "  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "USE campus_seguro_diagrama;",
        "",
    ]

    for modelo in ordenar(modelos):
        meta = modelo._meta
        lineas.append(f"-- {meta.verbose_name_plural}")
        lineas.append(f"CREATE TABLE `{meta.db_table}` (")
        lineas.append(",\n".join(columnas_y_claves(modelo)))
        lineas.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
        lineas.append("")

    destino = RAIZ / "docs" / "esquema_mysql.sql"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")

    print(f"{destino}  ({len(modelos)} tablas)")


if __name__ == "__main__":
    main()
