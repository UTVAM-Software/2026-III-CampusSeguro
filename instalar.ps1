# Instalador de Campus Seguro para un servidor Windows.
#
# Mismo procedimiento que instalar.sh, paso por paso. Se descarga suelto y se
# ejecuta desde cualquier carpeta: el primer paso es traer el codigo.
#
#     powershell -ExecutionPolicy Bypass -File instalar.ps1
#
# Hace, y solo hace, los cinco pasos:
#
#     1. el ambiente virtual
#     2. descargar el codigo
#     3. configurar lo que hace falta para que funcione
#     4. las herramientas propias de Django
#     5. levantar el servicio web
#
# Se puede volver a correr: actualiza el codigo y no pisa ni la base de datos
# ni la configuracion.

param(
    [string]$Repo    = 'https://github.com/UTVAM-Software/2026-III-CampusSeguro.git',
    [string]$Carpeta = 'campus-seguro',
    [int]   $Puerto  = 8000,
    [string]$Hosts   = 'localhost,127.0.0.1',
    [string]$Admin   = 'admin@campusseguro.local',
    [string]$Clave   = ''
)

$ErrorActionPreference = 'Stop'

function Paso($t) { Write-Host "`n==> $t" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "    ok $t" -ForegroundColor Green }
function Alto($t) { Write-Host "`nFALLO: $t" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------- requisitos
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Alto 'hace falta git.' }

$py = $null
foreach ($c in @('python', 'py')) {
    if (Get-Command $c -ErrorAction SilentlyContinue) {
        & $c -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { $py = $c; break }
    }
}
if (-not $py) { Alto 'hace falta Python 3.10 o superior.' }
Ok (& $py --version)

# ------------------------------------------- 2. descargar el codigo (primero)
# Antes que el ambiente virtual: el ambiente vive DENTRO del proyecto.
Paso '2/5  Codigo fuente'
if (Test-Path (Join-Path $Carpeta '.git')) {
    git -C $Carpeta pull --ff-only
    if ($LASTEXITCODE -ne 0) { Alto 'no se pudo actualizar el codigo.' }
    Ok "actualizado en $Carpeta"
} else {
    git clone --quiet $Repo $Carpeta
    if ($LASTEXITCODE -ne 0) { Alto 'no se pudo descargar el codigo.' }
    Ok "descargado en $Carpeta"
}
Set-Location $Carpeta

# ------------------------------------------------------ 1. ambiente virtual
Paso '1/5  Ambiente virtual'
if (Test-Path '.venv') {
    Ok 'ya existia'
} else {
    & $py -m venv .venv
    if ($LASTEXITCODE -ne 0) { Alto 'no se pudo crear el ambiente virtual.' }
    Ok 'creado'
}
$venv = '.venv\Scripts\python.exe'
if (-not (Test-Path $venv)) { Alto 'el ambiente virtual no quedo utilizable.' }

& $venv -m pip install --quiet --upgrade pip
& $venv -m pip install --quiet -r requirements.txt
if ($LASTEXITCODE -ne 0) { Alto 'no se pudieron instalar las dependencias.' }
Ok 'dependencias instaladas'

# ----------------------------------------------------------- 3. configuracion
Paso '3/5  Configuracion'
if (Test-Path '.env') {
    Ok '.env ya existia; no se toca'
} else {
    $secreto = & $venv -c 'from django.core.management.utils import get_random_secret_key as c; print(c())'
    @(
        '# Generado por el instalador. No se sube al repositorio.'
        "SECRET_KEY=$secreto"
        'DEBUG=False'
        "ALLOWED_HOSTS=$Hosts"
        ''
        '# Cookies solo por HTTPS. Ponlo en True EN CUANTO el servidor tenga'
        '# certificado: hasta entonces, encenderlo impide iniciar sesion.'
        'HTTPS=False'
        ''
        '# Sin servidor de correo todavia: los mensajes de recuperar contrasena'
        '# se escriben en la consola. Para enviarlos de verdad, pon EMAIL_HOST'
        '# y borra la linea de EMAIL_BACKEND.'
        'EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend'
        'EMAIL_HOST='
    ) | Set-Content -Path '.env' -Encoding utf8
    Ok '.env creado con una clave secreta nueva'
}

# ---------------------------------------------- 4. herramientas de Django
Paso '4/5  Base de datos, estaticos y cuenta de administracion'
& $venv manage.py migrate --noinput | Out-Null
if ($LASTEXITCODE -ne 0) { Alto 'fallaron las migraciones.' }
Ok 'base de datos al dia'

& $venv manage.py collectstatic --noinput | Out-Null
if ($LASTEXITCODE -ne 0) { Alto 'fallo collectstatic.' }
Ok 'archivos estaticos reunidos'

& $venv herramientas\cargar_campus.py | Out-Null
if ($LASTEXITCODE -ne 0) { Alto 'no se pudieron cargar los campus.' }
Ok 'campus cargados'

$generada = $false
if (-not $Clave) {
    $Clave = & $venv -c 'import secrets; print(secrets.token_urlsafe(12))'
    $generada = $true
}
& $venv manage.py crear_superusuario --correo $Admin --clave $Clave | Out-Null
if ($LASTEXITCODE -ne 0) { Alto 'no se pudo crear la cuenta de administracion.' }
Ok "cuenta de administracion: $Admin"

# Las advertencias que quedan son de HTTPS, y son ciertas: este servidor
# todavia no tiene certificado. Se van solas al poner HTTPS=True.
& $venv manage.py check --deploy --fail-level ERROR 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Alto 'la revision de despliegue encontro errores.' }
Ok 'revision de despliegue superada'

# --------------------------------------------------------- 5. servicio web
Paso '5/5  Servicio web'
$primero = ($Hosts -split ',')[0]
Write-Host "    escuchando en http://${primero}:$Puerto/"
Write-Host "`n    Falta el certificado: mientras se sirva por http, deja"
Write-Host "    HTTPS=False en .env. Con el certificado puesto, cambialo a"
Write-Host "    True y las cookies pasan a viajar solo cifradas."
if ($generada) {
    Write-Host "`n    Entra con  $Admin"
    Write-Host "    contrasena $Clave"
    Write-Host '    (apuntala: no se vuelve a mostrar)'
}
Write-Host "`n    Ctrl+C para detenerlo.`n"

& $venv -m waitress --listen="0.0.0.0:$Puerto" config.wsgi:application
