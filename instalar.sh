#!/usr/bin/env bash
#
# Instalador de Campus Seguro para un servidor.
#
# Se descarga suelto y se ejecuta desde cualquier carpeta: el primer paso es
# traer el codigo, asi que no hace falta tener el proyecto antes.
#
#     curl -O https://raw.githubusercontent.com/UTVAM-Software/2026-III-CampusSeguro/main/instalar.sh
#     bash instalar.sh
#
# Hace, y solo hace, los cinco pasos del procedimiento:
#
#     1. el ambiente virtual
#     2. descargar el codigo
#     3. configurar lo que hace falta para que funcione
#     4. las herramientas propias de Django
#     5. levantar el servicio web
#
# Se puede volver a correr sobre una instalacion existente: actualiza el
# codigo y no pisa ni la base de datos ni la configuracion.
#
# Variables que se pueden cambiar sin tocar el archivo:
#
#     CARPETA   donde se instala          (campus-seguro)
#     PUERTO    en que puerto escucha     (8000)
#     HOSTS     nombres con los que se le llama, separados por coma
#     ADMIN     correo de quien administra
#     CLAVE     su contrasena             (si no, se genera una)
#
set -euo pipefail

REPO="${REPO:-https://github.com/UTVAM-Software/2026-III-CampusSeguro.git}"
CARPETA="${CARPETA:-campus-seguro}"
PUERTO="${PUERTO:-8000}"
HOSTS="${HOSTS:-localhost,127.0.0.1}"
ADMIN="${ADMIN:-admin@campusseguro.local}"
CLAVE="${CLAVE:-}"

paso() { printf '\n\033[1;34m==> %s\033[0m\n' "$1"; }
ok()   { printf '    \033[32mok\033[0m %s\n' "$1"; }
alto() { printf '\n\033[1;31mFALLO: %s\033[0m\n' "$1" >&2; exit 1; }

trap 'alto "el paso anterior no termino bien. No se levanto el servicio."' ERR

# ---------------------------------------------------------------- requisitos
command -v git >/dev/null 2>&1 || alto 'hace falta git.'

# Se prueba cada candidato callando su salida: en Windows, `python3` es un
# acceso directo a la tienda de Microsoft que imprime un parrafo antes de
# fallar, y ese parrafo en mitad de una instalacion parece un error.
PY=''
for candidato in python3 python; do
    if command -v "$candidato" >/dev/null 2>&1; then
        if "$candidato" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
            PY="$candidato"
            break
        fi
    fi
done
[ -n "$PY" ] || alto 'hace falta Python 3.10 o superior.'
ok "$($PY --version)"

# ------------------------------------------- 2. descargar el codigo (primero)
# Va antes que el ambiente virtual porque el ambiente vive DENTRO del
# proyecto: sin carpeta no hay donde crearlo.
paso '2/5  Codigo fuente'
if [ -d "$CARPETA/.git" ]; then
    git -C "$CARPETA" pull --ff-only
    ok "actualizado en $CARPETA"
else
    git clone --quiet "$REPO" "$CARPETA"
    ok "descargado en $CARPETA"
fi
cd "$CARPETA"

# ------------------------------------------------------ 1. ambiente virtual
paso '1/5  Ambiente virtual'
if [ -d .venv ]; then
    ok 'ya existia'
else
    "$PY" -m venv .venv
    ok 'creado'
fi
VENV=".venv/bin/python"
[ -x "$VENV" ] || VENV=".venv/Scripts/python.exe"
[ -x "$VENV" ] || alto 'el ambiente virtual no quedo utilizable.'

"$VENV" -m pip install --quiet --upgrade pip
"$VENV" -m pip install --quiet -r requirements.txt
ok 'dependencias instaladas'

# ----------------------------------------------------------- 3. configuracion
paso '3/5  Configuracion'
if [ -f .env ]; then
    ok '.env ya existia; no se toca'
else
    SECRETO="$("$VENV" -c 'from django.core.management.utils import get_random_secret_key as c; print(c())')"
    cat > .env <<ENV
# Generado por el instalador. No se sube al repositorio.
SECRET_KEY=$SECRETO
DEBUG=False
ALLOWED_HOSTS=$HOSTS

# Cookies solo por HTTPS. Ponlo en True EN CUANTO el servidor tenga
# certificado: hasta entonces, encenderlo impide iniciar sesion.
HTTPS=False

# Sin servidor de correo todavia: los mensajes de recuperar contrasena se
# escriben en la consola en vez de enviarse. Para enviarlos de verdad, pon
# EMAIL_HOST y borra la linea de EMAIL_BACKEND.
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
ENV
    chmod 600 .env
    ok '.env creado con una clave secreta nueva'
fi

# ---------------------------------------------- 4. herramientas de Django
paso '4/5  Base de datos, estaticos y cuenta de administracion'
"$VENV" manage.py migrate --noinput >/dev/null
ok 'base de datos al dia'

"$VENV" manage.py collectstatic --noinput >/dev/null
ok 'archivos estaticos reunidos'

"$VENV" herramientas/cargar_campus.py >/dev/null
ok 'campus cargados'

if [ -z "$CLAVE" ]; then
    CLAVE="$("$VENV" -c 'import secrets; print(secrets.token_urlsafe(12))')"
    GENERADA=1
fi
"$VENV" manage.py crear_superusuario --correo "$ADMIN" --clave "$CLAVE" >/dev/null
ok "cuenta de administracion: $ADMIN"

# Las advertencias que quedan son todas de HTTPS, y son ciertas: este
# servidor todavia no tiene certificado. Se van solas al poner HTTPS=True.
"$VENV" manage.py check --deploy --fail-level ERROR >/dev/null 2>&1
ok 'revision de despliegue superada (quedan avisos de HTTPS, ver abajo)'

# --------------------------------------------------------- 5. servicio web
paso '5/5  Servicio web'
printf '    escuchando en http://%s:%s/\n' "${HOSTS%%,*}" "$PUERTO"
printf '\n    Falta el certificado: mientras se sirva por http, deja\n'
printf '    HTTPS=False en .env. Con el certificado puesto, cambialo a True\n'
printf '    y las cookies pasan a viajar solo cifradas.\n'
if [ "${GENERADA:-0}" = 1 ]; then
    printf '\n    Entra con  %s\n    contrasena %s\n' "$ADMIN" "$CLAVE"
    printf '    (apuntala: no se vuelve a mostrar)\n'
fi
printf '\n    Ctrl+C para detenerlo.\n\n'

trap - ERR
exec "$VENV" -m waitress --listen="0.0.0.0:$PUERTO" config.wsgi:application
