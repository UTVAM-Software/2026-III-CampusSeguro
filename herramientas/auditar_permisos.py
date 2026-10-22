"""
Recorre TODAS las rutas con cada rol y dice que responde cada una.

No arregla nada: solo ensena la foto. Lo que no cuadre se corrige y se
bloquea con una prueba.
"""

import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test.utils import setup_test_environment, teardown_test_environment  # noqa: E402
from django.test.runner import DiscoverRunner  # noqa: E402


def main():
    setup_test_environment()
    runner = DiscoverRunner(verbosity=0, interactive=False)
    viejo = runner.setup_databases()

    try:
        auditar()
    finally:
        runner.teardown_databases(viejo)
        teardown_test_environment()


def auditar():
    from django.test import Client
    from django.urls import get_resolver, reverse, NoReverseMatch

    from apps.campus.models import Campus, Correccion, PuntoApoyo
    from apps.comunicacion.models import Aviso, Notificacion
    from apps.reportes.models import Reporte, ReporteConfirmacion
    from apps.usuarios.models import Usuario
    from apps.viajes.models import UbicacionViaje, Viaje, ViajeAcompanante

    uno = Campus.objects.create(nombre="Uno", latitud=19.8, longitud=-98.9)
    dos = Campus.objects.create(nombre="Dos", latitud=20.1, longitud=-98.7)

    def cuenta(correo, rol, campus):
        return Usuario.objects.create_user(
            correo=correo, nombre=correo.split("@")[0], password="x" * 20,
            campus=campus, rol=rol,
        )

    duena = cuenta("duena@a.mx", "estudiante", uno)
    intrusa = cuenta("intrusa@a.mx", "estudiante", uno)
    de_otro = cuenta("otro@b.mx", "estudiante", dos)
    docente = cuenta("docente@a.mx", "docente", uno)
    seguridad = cuenta("seguridad@a.mx", "seguridad", uno)
    jefa = cuenta("jefa@a.mx", "admin", uno)

    # Todo lo de abajo pertenece a `duena`, del campus `uno`.
    punto = PuntoApoyo.objects.create(
        campus=uno, nombre="Enfermería", tipo="enfermeria",
        latitud=19.8, longitud=-98.9,
    )
    reporte = Reporte.objects.create(
        usuario=duena, campus=uno, tipo="obras", descripcion="Zanja abierta",
        latitud=19.8, longitud=-98.9,
    )
    confirmacion = ReporteConfirmacion.objects.create(
        reporte=reporte, usuario=duena, confirma=True,
    )
    viaje = Viaje.objects.create(usuario=duena, origen="A", destino="B")
    acompanante = ViajeAcompanante.objects.create(viaje=viaje, acompanante=intrusa)
    ubicacion = UbicacionViaje.objects.create(viaje=viaje, latitud=19.8, longitud=-98.9)
    aviso = Aviso.objects.create(campus=uno, titulo="T", contenido="C", autor=jefa)
    notificacion = Notificacion.objects.create(usuario=duena, titulo="T", mensaje="M")
    correccion = Correccion.objects.create(punto=punto, usuario=duena, motivo="cerrado")

    ARGS = {
        "punto-detail": [punto.pk], "punto-update": [punto.pk],
        "punto-delete": [punto.pk], "punto-avisar": [punto.pk],
        "campus-detail": [uno.pk], "campus-update": [uno.pk], "campus-delete": [uno.pk],
        "reporte-detail": [reporte.pk], "reporte-update": [reporte.pk],
        "reporte-delete": [reporte.pk], "reporte-confirmar": [reporte.pk],
        "confirmacion-detail": [confirmacion.pk],
        "confirmacion-update": [confirmacion.pk],
        "confirmacion-delete": [confirmacion.pk],
        "viaje-detail": [viaje.pk], "viaje-update": [viaje.pk],
        "viaje-delete": [viaje.pk], "viaje-llegue": [viaje.pk],
        "viaje-cancelar": [viaje.pk], "viaje-posicion": [viaje.pk],
        "viaje-ultima": [viaje.pk],
        "acompanante-detail": [acompanante.pk], "acompanante-update": [acompanante.pk],
        "acompanante-delete": [acompanante.pk], "invitacion-responder": [acompanante.pk],
        "ubicacion-detail": [ubicacion.pk], "ubicacion-update": [ubicacion.pk],
        "ubicacion-delete": [ubicacion.pk],
        "aviso-detail": [aviso.pk], "aviso-update": [aviso.pk], "aviso-delete": [aviso.pk],
        "notificacion-detail": [notificacion.pk],
        "notificacion-update": [notificacion.pk],
        "notificacion-delete": [notificacion.pk],
        "notificacion-leida": [notificacion.pk],
        "usuario-detail": [duena.pk], "usuario-update": [duena.pk],
        "usuario-delete": [duena.pk],
        "correccion-atender": [correccion.pk],
        "clave-nueva": ["MQ", "inventado"],
    }

    quienes = [
        ("anonimo", None), ("intrusa", intrusa), ("otro campus", de_otro),
        ("docente", docente), ("seguridad", seguridad), ("admin", jefa),
    ]

    nombres = sorted(
        k for k in get_resolver().reverse_dict.keys()
        if isinstance(k, str) and not k.startswith("admin")
    )

    print(f"{'ruta':26} " + " ".join(f"{q:>12}" for q, _ in quienes))
    print("-" * 104)

    for nombre in nombres:
        try:
            url = reverse(nombre, args=ARGS.get(nombre, []))
        except NoReverseMatch:
            print(f"{nombre:26}  (no se pudo construir la direccion)")
            continue

        fila = []

        for _, usuario in quienes:
            c = Client()
            if usuario:
                c.force_login(usuario)

            r = c.get(url)
            codigo = r.status_code

            if codigo == 302 and "/entrar/" in r.headers.get("Location", ""):
                fila.append("-> entrar")
            elif codigo == 405:
                # Solo POST. Se prueba otra vez con POST para ver el permiso.
                r = c.post(url)
                destino = r.headers.get("Location", "")
                fila.append(
                    "-> entrar" if r.status_code == 302 and "/entrar/" in destino
                    else f"POST {r.status_code}"
                )
            else:
                fila.append(str(codigo))

        print(f"{nombre:26} " + " ".join(f"{v:>12}" for v in fila))


if __name__ == "__main__":
    main()
