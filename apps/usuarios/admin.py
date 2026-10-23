"""
Las cuentas en el panel /admin/ de Django.

La app ya tiene sus propias pantallas para cuentas, grupos y permisos (Punto 4
de la tarea); esto es el respaldo. Entra quien tiene `is_staff`: la
superadministración.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm

from .models import Usuario


class UsuarioCreationForm(AdminUserCreationForm):
    """El de Django pide `username`; esta cuenta se crea con el correo."""

    class Meta:
        model = Usuario
        fields = ['correo', 'nombre', 'campus', 'rol']


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # El UserAdmin de Django espera `username`, `first_name` y `email`. Aquí
    # se entra con `correo`, así que se le dice qué campos tiene este modelo.
    add_form = UsuarioCreationForm
    ordering = ['correo']
    list_display = ['correo', 'nombre', 'apellidos', 'rol', 'campus', 'activo', 'is_staff']
    list_filter = ['rol', 'activo', 'is_staff', 'groups', 'campus']
    search_fields = ['correo', 'nombre', 'apellidos']
    filter_horizontal = ['groups', 'user_permissions']

    fieldsets = [
        (None, {'fields': ['correo', 'password']}),
        ('Datos', {'fields': ['nombre', 'apellidos', 'telefono', 'foto', 'campus']}),
        ('Acceso', {'fields': ['rol', 'activo', 'is_staff', 'is_superuser', 'groups', 'user_permissions']}),
        ('Fechas', {'fields': ['last_login', 'fecha_registro']}),
    ]
    readonly_fields = ['last_login', 'fecha_registro']
    add_fieldsets = [
        (None, {
            'classes': ['wide'],
            'fields': ['correo', 'nombre', 'campus', 'rol', 'password1', 'password2'],
        }),
    ]
