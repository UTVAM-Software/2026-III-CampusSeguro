# Campus Seguro

Aplicación web de movilidad y prevención para la comunidad universitaria.
Deja registrar condiciones del camino, compartir la ubicación mientras dura
un trayecto y comparar dos rutas a pie por lo que la comunidad ha reportado
en ellas.

**Proyecto escolar.** Ciberseguridad aplicada a los negocios · IEV 901 ·
UTVAM · Docente: Rubén Ramírez Gómez
Hecho por Alexis Carabeo Amaro y Lady Guadalupe Meza Solis.

---

## Lo que esta aplicación NO hace

Está primero porque es lo que más decisiones ha condicionado, y porque es
fácil leer la pantalla equivocada y entender otra cosa.

- **No detecta peligro.** No hay sensores ni modelo que prediga nada.
- **No calcula rutas seguras.** Compara dos caminos por *cuántas condiciones
  ha registrado la comunidad cerca de cada uno*. Un camino sin reportes
  puede no tenerlos porque no pasa nadie por ahí.
- **No pinta zonas peligrosas.** El mapa dibuja puntos: alguien registró
  algo en un sitio y una fecha.
- **No da una puntuación de seguridad.** Un número de 0 a 100 se lee como
  nota por mucho que la letra pequeña diga otra cosa.
- **No guarda el recorrido.** Las posiciones de un viaje se borran al
  cerrarlo. Se conserva a dónde fuiste y cuándo, no el camino.

---

## Instalarlo en un servidor

Un solo archivo. **No hace falta descargar el proyecto antes**: traerlo es
uno de los pasos del instalador.

**Linux o macOS**

```bash
curl -O https://raw.githubusercontent.com/UTVAM-Software/2026-III-CampusSeguro/main/instalar.sh
bash instalar.sh
```

**Windows**, en PowerShell:

```powershell
curl.exe -O https://raw.githubusercontent.com/UTVAM-Software/2026-III-CampusSeguro/main/instalar.ps1
powershell -ExecutionPolicy Bypass -File instalar.ps1
```

Lo único que hace falta tener ya instalado es **git** y **Python 3.10 o
superior**. El instalador hace, en este orden, los cinco pasos:

| | |
|---|---|
| 1 | descarga el código |
| 2 | crea el ambiente virtual e instala las dependencias |
| 3 | genera la clave secreta y escribe el `.env` |
| 4 | migra la base, reúne los estáticos, carga los campus y crea la cuenta de administración |
| 5 | levanta el servicio web |

El ambiente virtual se crea **después** de descargar el código porque vive
dentro del proyecto: sin carpeta no hay dónde crearlo. El orden del
procedimiento se respeta; el físico no puede.

Al terminar imprime con qué cuenta entrar y su contraseña, **que no se
vuelve a mostrar**.

Si algún paso falla se detiene con `FALLO:` y no levanta nada. Se puede
volver a correr sobre una instalación que ya existía: actualiza el código y
no pisa ni la base de datos ni el `.env`.

Se puede cambiar sin editar el archivo:

```bash
PUERTO=8080 HOSTS="campus.utvam.edu.mx" ADMIN="tu@correo.mx" bash instalar.sh
```

```powershell
powershell -ExecutionPolicy Bypass -File instalar.ps1 -Puerto 8080 -Hosts "campus.utvam.edu.mx"
```

### Cuando el servidor tenga certificado

Pon `HTTPS=True` en el `.env` y reinicia. Hasta entonces déjalo en `False`:
las cookies marcadas como seguras no viajan por `http`, y encenderlo antes
de tiempo **impide iniciar sesión** sin decir por qué.

Y para que la recuperación de contraseñas envíe correo de verdad, pon
`EMAIL_HOST` y borra la línea de `EMAIL_BACKEND`.

---

## Arrancarlo para trabajar en él

Esto es para desarrollo. Para un servidor, el instalador de arriba.

Hace falta **Python 3.10 o superior**. No hace falta Node, ni MySQL, ni
ninguna clave de ningún servicio.

```bash
git clone https://github.com/UTVAM-Software/2026-III-CampusSeguro.git
cd 2026-III-CampusSeguro
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver 8001
```

En **Windows** cambia `.venv/bin/python` por `.venv\Scripts\python.exe`, y
si usas CMD en vez de PowerShell, `copy .env.example .env` en vez de `cp`.

**El `cp .env.example .env` no es opcional.** Sin `.env`, `DEBUG` queda
apagado, y con `DEBUG` apagado el proyecto pide un servidor de correo para
arrancar: sin correo nadie puede recuperar su contraseña, y esa pantalla
prometería un mensaje que no se envía. `.env` no se sube al repositorio
porque ahí acaban la clave secreta y, el día que lo haya, la contraseña del
correo.

Queda en **http://127.0.0.1:8001/**.

### Datos para verlo con contenido

Una base recién migrada está vacía y casi todas las pantallas enseñan su
hueco. Para llenarla:

```bash
.venv/Scripts/python.exe herramientas/cargar_campus.py
.venv/Scripts/python.exe herramientas/sembrar_datos.py
```

El primero carga las doce universidades de Pachuca y Tizayuca con sus
coordenadas, y les pone el dominio de correo a las siete que se pudo
comprobar. El segundo crea las cinco cuentas de prueba y contenido para que
las pantallas no salgan vacías: tres puntos de apoyo, un reporte y un aviso
vigente.

Los dos se pueden correr las veces que haga falta: no duplican nada ni pisan
lo que ya exista.

### Cuentas de prueba

Las crea `sembrar_datos.py`. **Todas con la misma contraseña**, que está
escrita en ese archivo (`CLAVE_DE_PRUEBA`):

| Correo | Rol | Para ver |
|---|---|---|
| `lady@gmail.com` | Estudiante | el día a día |
| `admin@gmail.com` | Administrador de campus | panel, avisos, puntos de apoyo |
| `alexis@gmail.com` | Superadministrador | además, campus y cuentas |
| `externo@gmail.com` | Usuario externo | el perfil del visitante: lo público y nada más |
| `lectura@gmail.com` | Solo lectura | el sistema entero, sin poder tocar nada |

No son de nadie: viven solo en la base local, que no se sube al repositorio.

---

## Cómo está armado

Proyecto Django con las apps en `apps/`, como se enseña en clase. Vistas
basadas en clases (`ListView`, `DetailView`, `CreateView`…), plantillas por
app, y CSS escrito a mano — sin Tailwind ni nada que necesite compilarse.

```
config/          ajustes, rutas raíz, y las pantallas que no son de
                 ninguna app (inicio, mapa, panel)
apps/campus/     campus, puntos de apoyo, correcciones
apps/usuarios/   cuentas, acceso, perfil, recuperar contraseña, permisos
apps/reportes/   condiciones registradas y sus confirmaciones
apps/viajes/     viajes, acompañantes, ubicaciones, destinos guardados
apps/comunicacion/  avisos del campus y notificaciones
apps/rutas/      comparar caminos a pie (OSRM)
templates/       base, inicio, mapa, panel y las piezas compartidas
static/          estilos.css y los guiones
herramientas/    scripts que no son parte de la aplicación (ver abajo)
docs/            esquema para dibujar el diagrama en MySQL Workbench
```

### La base de datos

Corre sobre **SQLite** — es la que trae Django y no hay que instalar nada.
`db.sqlite3` no se sube al repositorio.

**MySQL solo se usa para ver el diagrama**, como pidió el docente. El
esquema se genera desde los modelos:

```bash
.venv/Scripts/python.exe herramientas/generar_esquema_mysql.py
```

Escribe `docs/esquema_mysql.sql`, que se abre en MySQL Workbench con
*Database → Reverse Engineer MySQL Create Script* y dibuja solo el diagrama
entidad-relación. Se genera en vez de escribirse a mano para que no diga una
cosa mientras la base dice otra.

### Servicios de fuera

Ninguno pide clave ni tarjeta.

| Para qué | Quién |
|---|---|
| Dibujar el mapa | Esri World Street Map |
| Buscar una dirección | Nominatim (OpenStreetMap) |
| Calcular el camino a pie | OSRM, instancia de peatón de FOSSGIS |

Las teselas no salen de `tile.openstreetmap.org`: sus servidores los pagan
voluntarios y su política de uso no permite que cualquier aplicación tire de
ellos. Nos bloquearon, y el mapa salía cubierto de avisos amarillos.

**El correo** solo hace falta para recuperar contraseñas. En desarrollo se
imprime en la terminal donde corre el servidor, así que el circuito se puede
probar entero sin configurar nada. Fuera de desarrollo hace falta
`EMAIL_HOST`, y si falta el proyecto no arranca: un fallo silencioso ahí es
gente esperando un mensaje que no se envía.

---

## Las pruebas

```bash
.venv/Scripts/python.exe manage.py test
```

Son **291** y tardan unos dos minutos. No tocan `db.sqlite3`: Django crea
una base aparte y la borra al terminar.

Algunas merecen que se sepa que existen, porque vigilan cosas que no se ven
cuando se rompen:

- **`apps/usuarios/tests_permisos.py`** declara, ruta por ruta, quién puede
  entrar, y falla si aparece una ruta sin declarar. No se puede añadir una
  pantalla sin decir quién la ve.
- **`apps/usuarios/tests_grupos.py`** comprueba que TODA vista con sesión
  declara `permission_required`, que cada cuenta está en el grupo de su rol
  y el CRUD de grupos y permisos.
- **`apps/usuarios/tests_pantallas.py`** abre todas las pantallas con sesión
  y comprueba que cargan. Una plantilla rota no rompe ninguna otra prueba: si
  es de una pantalla que se visita poco, aparece en la demostración.
- **`EtiquetasEnVariasLineasTests`** busca etiquetas de plantilla partidas en
  dos líneas. Django no las parsea: las imprime tal cual en la pantalla. Pasó
  de verdad, y el texto salía en la esquina de *todas* las pantallas.
- **`NadieSeQuedaFueraDeSuPropioInicioTests`** recorre los cinco roles y
  comprueba tres cosas: que ninguno recibe un 403 en la pantalla de inicio
  —a la que llegan todos al entrar—, que la barra no ofrece ninguna entrada
  que responda 403, y que la cuenta de solo lectura ve las listas enteras
  pero no puede escribir ni editar la cuenta de otra persona.

Las tres primeras encontraron fallos de verdad: una ruta sin declarar, un
panel que no pedía sesión y una cuenta de solo lectura que podía cambiarle
el nombre y el correo a cualquiera.

---

## Las herramientas

No son parte de la aplicación: son scripts para trabajar con ella.

| | |
|---|---|
| `cargar_campus.py` | Las doce universidades con sus coordenadas y sus dominios de correo, cada uno con la fuente donde se comprobó. No pisa lo que se haya puesto desde el Panel. |
| `sembrar_datos.py` | Las cinco cuentas de prueba y contenido para ver las pantallas llenas. |
| `generar_esquema_mysql.py` | `docs/esquema_mysql.sql` para dibujar el diagrama. |
| `auditar_permisos.py` | Recorre todas las rutas con una cuenta de cada rol y enseña qué responde cada una. Con esto se encontró que el panel no pedía sesión. |

---

## Quién puede qué

Cada rol es un **grupo de Django** con sus **permisos** (`apps/usuarios/roles.py`).
Al guardar una cuenta, entra sola en el grupo de su rol.

| Rol / grupo | Puede |
|---|---|
| **Estudiante** | reportar, viajar, acompañar, ver el mapa y los puntos de apoyo, avisar de que un punto está mal |
| **Administrador de campus** | lo anterior y, de **su** campus: el panel, los avisos, los puntos de apoyo, revisar reportes y la cola de correcciones |
| **Superadministrador** | lo anterior y, del sistema: los campus, las cuentas, y los **grupos y permisos** (Panel → Grupos / Permisos). Tiene acceso a `/admin/` |
| **Usuario externo** | quien no es de la comunidad: consultar campus, puntos de apoyo y avisos, y editar su propia ficha. Nada más |
| **Solo lectura** | ver **todo** el sistema, de todos los campus, sin poder agregar, modificar ni eliminar nada |

Los permisos de cada grupo se cambian desde la app (Panel → Grupos), y se
pueden crear grupos extra ("Brigada de seguridad") o dar permisos sueltos a
una cuenta desde su ficha.

Tres cerrojos, en este orden (`apps/usuarios/permisos.py`):

1. **`login_required`** en cada `urls.py` — sin sesión, a la pantalla de entrar.
2. **`permission_required`** en cada vista (`PermisoRequeridoMixin`) — sin el
   permiso, **403**: «esta pantalla existe y no es para tu cuenta».
3. **`get_queryset()`** — si la cosa es de otra persona o de otro campus,
   **404**: un 403 confirmaría que ese viaje existe, y quién viaja a dónde no
   se le filtra a quien no va en él. Ni siquiera a quien administra.

### Administrar y auditar no son lo mismo

Tener el permiso `view_` no basta para ver: el tercer cerrojo recorta además
por campus y por dueño. Una cuenta de solo lectura con todos los `view_`
acababa viendo lo mismo que un estudiante.

Lo que lo cambia es un cuarto permiso propio, **`auditar_sistema`**, que no
abre ningún `add_`, `change_` ni `delete_`: solo le dice a los filtros que a
esa cuenta la lista se le enseña entera.

Y es un permiso aparte de `administrar_campus` a propósito, porque ese
también abre acciones que **escriben** —dar por atendida una corrección, por
ejemplo—, y un rol que mira no puede llevar esa llave.

Por eso quien administra su campus **sigue sin ver los viajes de nadie**: los
viajes, las ubicaciones, los destinos guardados y las notificaciones solo se
abren con `auditar_sistema`. La administración gestiona el campus; la
auditoría mira el sistema y no toca nada.

La autorización está siempre en el servidor. Las plantillas esconden puertas
(`{% if perms.campus.add_campus %}`) para no ofrecer lo que no se puede
abrir; quien cierra con llave son las vistas.

`python manage.py createsuperuser` crea un **Superadministrador**.

---

## Lo que falta

Para que no haya que leerse el código para saberlo:

- **Cinco campus siguen sin dominio de correo**: TecNM Pachuca, Tec de
  Monterrey, La Salle, UPN y UPMH. No están puestos a propósito —no se
  encontró una fuente de esas universidades que confirmara el formato de su
  correo—, y un dominio equivocado cierra la puerta a toda una universidad.
  Se ponen desde Panel → Campus.
- **No hay puntos de apoyo reales.** Los tres que carga `sembrar_datos.py`
  se llaman «de demostración» en el nombre: decir «aquí hay una enfermería»
  es decirle a alguien que a las diez de la noche puede caminar hasta ahí y
  encontrar a una persona, y eso lo registra quien administra el campus,
  desde el mapa, porque es quien lo sabe.
- **Las coordenadas de UTVAM están sin confirmar.** Sobre la imagen de
  satélite, el punto que usa el sistema cae en terreno baldío junto al
  entronque. UTVAM no está mapeada en OpenStreetMap, así que hace falta que
  alguien del equipo señale cuál es la entrada.
- **Faltan once iconos** del juego de la marca: tache, palomita, advertencia,
  información, tendencia, cámara, salir y el logotipo reducido. Donde no hay,
  se usa un carácter o un SVG dibujado a mano.
- **No hay aviso de privacidad.** La aplicación guarda correo, teléfono,
  campus, los reportes con su foto y las posiciones de un viaje en curso;
  falta el documento que lo diga y explique cómo ejercer los derechos ARCO.

---

## Licencia

**MIT** — ver [`LICENSE`](LICENSE). Se puede usar, copiar y modificar citando
la autoría, que es lo que tiene sentido para un trabajo escolar del que otro
equipo pueda aprender algo.

El código de terceros mantiene la suya: Django y Leaflet son BSD, los datos
de OpenStreetMap son ODbL —por eso el mapa lleva su atribución a la vista, y
borrarla sería incumplirla— y las teselas las sirve Esri.
