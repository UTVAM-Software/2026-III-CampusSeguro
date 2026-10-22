from django.urls import path

from .views import (
    UsuarioListView, UsuarioDetailView, UsuarioCreateView,
    UsuarioUpdateView, UsuarioDeleteView,
    EntrarView, SalirView, RegistroView,
)
from .vistas_perfil import PerfilView, CerrarOtrasSesionesView, CambiarClaveView
from .vistas_clave import (
    PedirClaveView, ClaveEnviadaView, NuevaClaveView, ClaveListaView,
)
from .vistas_grupos import (
    GrupoListView, GrupoDetailView, GrupoCreateView, GrupoUpdateView,
    GrupoDeleteView, PermisoListView, PermisoDetailView, PermisoCreateView,
    PermisoUpdateView, PermisoDeleteView,
)
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # Estas tres NO llevan login_required, y es evidente por que: son las que
    # sirven para conseguir la sesion. Pedirla aqui seria pedir la llave para
    # poder recoger la llave.
    path('entrar/', EntrarView.as_view(), name='entrar'),
    path('salir/', SalirView.as_view(), name='salir'),
    path('registro/', RegistroView.as_view(), name='registro'),

    # Recuperar la contrasena. Tampoco llevan login_required, y por lo mismo:
    # quien llega aqui es justo quien no puede entrar.
    path('clave/', PedirClaveView.as_view(), name='clave-pedir'),
    path('clave/enviada/', ClaveEnviadaView.as_view(), name='clave-enviada'),
    path('clave/nueva/<uidb64>/<token>/', NuevaClaveView.as_view(), name='clave-nueva'),
    path('clave/lista/', ClaveListaView.as_view(), name='clave-lista'),

    # El perfil: tu propia cuenta. No lleva <pk> a proposito -la vista
    # devuelve request.user-, asi que no existe la pregunta de si alguien
    # puede editar a otra persona desde aqui.
    path('perfil/', login_required(PerfilView.as_view()), name='perfil'),
    path('perfil/contrasena/', login_required(CambiarClaveView.as_view()), name='cambiar-clave'),
    path('perfil/sesiones/', login_required(CerrarOtrasSesionesView.as_view()), name='cerrar-otras-sesiones'),

    path('usuarios/', login_required(UsuarioListView.as_view()), name='usuario-list'),
    path('usuarios/<int:pk>/', login_required(UsuarioDetailView.as_view()), name='usuario-detail'),
    path('usuarios/create/', login_required(UsuarioCreateView.as_view()), name='usuario-create'),
    path('usuarios/<int:pk>/update/', login_required(UsuarioUpdateView.as_view()), name='usuario-update'),
    path('usuarios/<int:pk>/delete/', login_required(UsuarioDeleteView.as_view()), name='usuario-delete'),

    # Grupos y permisos de Django (Punto 4). Todas piden un permiso de
    # `auth` que solo tiene la superadministracion.
    path('grupos/', login_required(GrupoListView.as_view()), name='grupo-list'),
    path('grupos/<int:pk>/', login_required(GrupoDetailView.as_view()), name='grupo-detail'),
    path('grupos/create/', login_required(GrupoCreateView.as_view()), name='grupo-create'),
    path('grupos/<int:pk>/update/', login_required(GrupoUpdateView.as_view()), name='grupo-update'),
    path('grupos/<int:pk>/delete/', login_required(GrupoDeleteView.as_view()), name='grupo-delete'),

    path('permisos/', login_required(PermisoListView.as_view()), name='permiso-list'),
    path('permisos/<int:pk>/', login_required(PermisoDetailView.as_view()), name='permiso-detail'),
    path('permisos/create/', login_required(PermisoCreateView.as_view()), name='permiso-create'),
    path('permisos/<int:pk>/update/', login_required(PermisoUpdateView.as_view()), name='permiso-update'),
    path('permisos/<int:pk>/delete/', login_required(PermisoDeleteView.as_view()), name='permiso-delete'),
]
