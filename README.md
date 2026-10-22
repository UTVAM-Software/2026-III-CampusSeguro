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

## Arrancarlo

Hace falta **Python 3.10 o superior**. No hace falta Node, ni MySQL, ni
ninguna clave de ningún servicio.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
cp .env.example .env
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py runserver 8001
```

En Linux o macOS, `.venv/bin/python` en vez de `.venv/Scripts/python.exe`.

**El `cp .env.example .env` no es opcional.** Sin `.env`, `DEBUG` queda
apagado, y con `DEBUG` apagado el proyecto exige un servidor de correo y no
arranca: sin correo nadie puede recuperar su contraseña, y esa pantalla
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
coordenadas. El segundo crea las cuentas de prueba y un poco de contenido.

### Cuentas de prueba

Las crea `sembrar_datos.py`. **Todas con la misma contraseña**, que está
escrita en ese archivo (`CLAVE_DE_PRUEBA`):

| Correo | Rol | Para ver |
|---|---|---|
| `lady@gmail.com` | Estudiante | el día a día |
| `admin@gmail.com` | Administrador de campus | panel, avisos, puntos de apoyo |
| `alexis@gmail.com` | Superadministrador | además, campus y cuentas |

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

Son **257** y tardan unos tres minutos. No tocan `db.sqlite3`: Django crea
una base aparte y la borra al terminar.

Tres merecen que se sepa que existen, porque vigilan cosas que no se ven
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

---

## Las herramientas

No son parte de la aplicación: son scripts para trabajar con ella.

| | |
|---|---|
| `cargar_campus.py` | Las doce universidades con sus coordenadas. Se puede correr las veces que haga falta. |
| `sembrar_datos.py` | Cuentas de prueba y contenido para ver las pantallas llenas. |
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

La autorización está siempre en el servidor. Las plantillas esconden puertas
(`{% if perms.campus.add_campus %}`) para no ofrecer lo que no se puede
abrir; quien cierra con llave son las vistas.

`python manage.py createsuperuser` crea un **Superadministrador**.

---

## Lo que falta

Para que no haya que leerse el código para saberlo:

- **Los doce campus no tienen dominio de correo configurado**, así que la
  restricción al correo institucional está montada pero apagada. El panel lo
  avisa.
- **No hay ningún punto de apoyo cargado.** El formulario deja señalarlos en
  el mapa; hay que registrarlos.
- **Faltan once iconos** del juego de la marca: tache, palomita, advertencia,
  información, tendencia, cámara, salir y el logotipo reducido. Donde no hay,
  se usa un carácter o un SVG dibujado a mano.
