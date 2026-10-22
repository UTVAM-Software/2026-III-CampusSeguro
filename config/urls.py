"""
Las direcciones del proyecto.

AQUÍ SOLO VIVEN LAS QUE NO SON DE NINGUNA APP
    El inicio, el mapa y el panel: pantallas que juntan datos de varias
    —reportes, viajes, puntos de apoyo— y que por eso no pertenecen a una.
    Todo lo demás se incluye desde su app.

TODAS LLEVAN `login_required`, TAMBIÉN LAS DE AQUÍ
    Es el único mecanismo del proyecto para pedir sesión, y está en un solo
    sitio a propósito: con unas vistas usando el decorador y otras un mixin,
    mirar el urls.py ya no basta para saber qué está cerrado.

    Hubo un rato en que el panel se quedó sin él. Como `SoloAdminMixin`
    preguntaba `request.user.es_admin` y una visita sin sesión es un
    `AnonymousUser` —que no tiene ese atributo—, la pantalla respondía un 500
    en vez de mandar a entrar. Lo encontró herramientas/auditar_permisos.py.

    La prueba `TodasLasPuertasTests` recorre este archivo y los de las apps y
    falla si aparece una vista sin decorador.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from django.views.generic import TemplateView

from .vistas import InicioView, MapaView, PanelView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Con `login_required`, igual que todas las de las apps. Inicio y mapa ya
    # lo pedian por su cuenta -LoginRequiredMixin-, pero el panel NO: una
    # visita sin sesion llegaba hasta el mixin de administracion y lo
    # reventaba con un 500.
    #
    # Un solo mecanismo y en un solo sitio: con unas vistas usando el
    # decorador y otras el mixin, mirar el urls.py ya no basta para saber que
    # esta cerrado. Y hay una prueba que lo mira ahi.
    path('', login_required(InicioView.as_view()), name='index'),
    path('mapa/', login_required(MapaView.as_view()), name='mapa'),
    path('panel/', login_required(PanelView.as_view()), name='panel'),
    path('', include('apps.campus.urls')),
    path('', include('apps.usuarios.urls')),
    path('', include('apps.reportes.urls')),
    path('', include('apps.viajes.urls')),
    path('', include('apps.comunicacion.urls')),
    path('', include('apps.rutas.urls')),
]

# Las fotos subidas, solo en desarrollo. En produccion las sirve el servidor
# web, nunca Django: esta linea no hace nada con DEBUG apagado.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Y las pantallas de error, para poder verlas mientras se trabajan: con
    # DEBUG encendido Django ensena su pagina amarilla de depuracion y estas no
    # salen nunca. Fuera de desarrollo estas rutas no existen.
    urlpatterns += [
        path(f'error/{codigo}/', TemplateView.as_view(template_name=f'{codigo}.html'))
        for codigo in (400, 403, 404, 500)
    ]
