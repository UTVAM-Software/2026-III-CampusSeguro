"""
Formularios para administrar los grupos y permisos de Django desde la app.

Son los modelos que trae `django.contrib.auth`:

    Group       un grupo de cuentas con unos permisos ("Estudiante").
    Permission  una cosa concreta que se puede hacer ("Crear reporte").

Con esto el superadministrador los gestiona desde Campus Seguro, sin
depender del panel /admin/ de Django.
"""

from django import forms
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from .models import Usuario
from .roles import NOMBRES_GRUPOS_DE_ROL

#: Las apps cuyos permisos se pueden repartir desde la app. Se dejan fuera
#: los de admin, sesiones y contenttypes: son internos de Django y darlos no
#: tiene ningún efecto en Campus Seguro.
APPS_DEL_PROYECTO = ['campus', 'reportes', 'viajes', 'comunicacion', 'usuarios', 'auth']

#: Los cuatro permisos que Django crea solo para cada modelo.
ACCIONES = {'view': 'Ver', 'add': 'Crear', 'change': 'Editar', 'delete': 'Eliminar'}


def permisos_del_proyecto():
    """Los permisos que se pueden repartir, ordenados por modelo."""
    return (
        Permission.objects
        .filter(content_type__app_label__in=APPS_DEL_PROYECTO)
        .select_related('content_type')
        .order_by('content_type__app_label', 'content_type__model', 'codename')
    )


def es_de_django(permiso):
    """
    ¿Es uno de los cuatro que Django crea solo (view, add, change, delete)?

    Esos no se editan ni se borran desde la app: Django los volvería a crear
    en el siguiente `migrate`, y mientras tanto las vistas que los piden
    quedarían cerradas para todo el mundo.
    """
    accion = permiso.codename.split('_', 1)[0]
    return accion in ACCIONES and permiso.codename == f'{accion}_{permiso.content_type.model}'


#: Los permisos propios del sistema (Usuario.Meta.permissions). Tampoco se
#: editan ni se borran: el código los pide por su nombre.
PERMISOS_DEL_SISTEMA = {'administrar_campus', 'administrar_sistema'}


def es_editable(permiso):
    """Solo los permisos que se crearon desde la app."""
    return not es_de_django(permiso) and permiso.codename not in PERMISOS_DEL_SISTEMA


def describir_permiso(permiso):
    """'Crear' para los de Django (van debajo del nombre del modelo); su nombre para el resto."""
    if es_de_django(permiso):
        return ACCIONES[permiso.codename.split('_', 1)[0]]
    return permiso.name


class CampoPermisos(forms.ModelMultipleChoiceField):
    """Casillas de permisos, con etiquetas en español."""

    widget = forms.CheckboxSelectMultiple

    def __init__(self, **kwargs):
        kwargs.setdefault('queryset', permisos_del_proyecto())
        kwargs.setdefault('required', False)
        super().__init__(**kwargs)

    def label_from_instance(self, permiso):
        return describir_permiso(permiso)


def grupos_adicionales():
    """Los grupos que NO son de rol: los de rol los pone el campo `rol`."""
    return Group.objects.exclude(name__in=NOMBRES_GRUPOS_DE_ROL).order_by('name')


# --------------------------------------------------------------------------- #
# Grupos
# --------------------------------------------------------------------------- #

class GrupoForm(forms.ModelForm):
    """
    Crear o editar un grupo: su nombre, sus permisos y quién está en él.

    LOS TRES GRUPOS DE ROL
        Se les pueden cambiar los permisos -así se decide qué puede hacer un
        estudiante-, pero no el nombre ni los miembros: el nombre lo busca
        `Usuario.save()` y los miembros los pone el campo `rol` de cada cuenta.
    """

    permissions = CampoPermisos(label='Permisos')
    miembros = forms.ModelMultipleChoiceField(
        label='Cuentas en este grupo',
        queryset=Usuario.objects.order_by('nombre', 'apellidos'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']
        labels = {'name': 'Nombre del grupo'}
        help_texts = {'name': 'Por ejemplo: "Brigada de seguridad" o "Prefectura".'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.es_de_rol:
            self.fields['name'].disabled = True
            self.fields['name'].help_text = (
                'Es un grupo de rol: su nombre no se cambia. Quién está en él '
                'lo decide el campo "Rol" de cada cuenta.'
            )
            del self.fields['miembros']
        elif self.instance.pk:
            self.fields['miembros'].initial = self.instance.user_set.all()

    @property
    def es_de_rol(self):
        return bool(self.instance.pk) and self.instance.name in NOMBRES_GRUPOS_DE_ROL

    def clean_name(self):
        nombre = self.cleaned_data['name'].strip()

        if not self.es_de_rol and nombre in NOMBRES_GRUPOS_DE_ROL:
            raise forms.ValidationError('Ese nombre es de un grupo de rol. Elige otro.')

        return nombre

    def save(self, commit=True):
        grupo = super().save(commit=commit)

        if commit and 'miembros' in self.fields:
            grupo.user_set.set(self.cleaned_data['miembros'])

        return grupo


# --------------------------------------------------------------------------- #
# Permisos
# --------------------------------------------------------------------------- #

class PermisoForm(forms.ModelForm):
    """
    Crear o editar un permiso propio.

    Un permiso nuevo no hace nada por sí solo: sirve para repartirlo en
    grupos y para que una vista lo pida con `permission_required`. Por eso se
    escribe con un código (`codename`) que el programa pueda usar.
    """

    content_type = forms.ModelChoiceField(
        label='¿Sobre qué es?',
        queryset=ContentType.objects.filter(
            app_label__in=APPS_DEL_PROYECTO
        ).order_by('app_label', 'model'),
    )

    class Meta:
        model = Permission
        fields = ['name', 'codename', 'content_type']
        labels = {'name': 'Descripción', 'codename': 'Código'}
        help_texts = {
            'name': 'Lo que permite, en una frase. Ej.: "Puede exportar reportes".',
            'codename': (
                'En minúsculas y sin espacios. Ej.: exportar_reporte. '
                'Es el que se escribe en permission_required.'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content_type'].label_from_instance = (
            lambda ct: f'{ct.app_label} · {ct.name}'
        )

    def clean_codename(self):
        codigo = self.cleaned_data['codename'].strip().lower()

        if not codigo.replace('_', '').isalnum() or not codigo.isascii():
            raise forms.ValidationError('Solo letras sin acento, números y guion bajo.')

        accion = codigo.split('_', 1)[0]

        if accion in ACCIONES:
            raise forms.ValidationError(
                f'Los que empiezan por "{accion}_" los crea Django solo. Usa otra palabra.'
            )

        if codigo in PERMISOS_DEL_SISTEMA:
            raise forms.ValidationError('Ese código ya lo usa el sistema.')

        return codigo


# --------------------------------------------------------------------------- #
# Lo que el superadministrador ve al crear o editar una cuenta
# --------------------------------------------------------------------------- #

class AccesoFormMixin:
    """
    Añade a un formulario de cuenta los grupos adicionales y los permisos
    sueltos. Lo usan crear cuenta y editar cuenta, solo para la
    superadministración.
    """

    def configurar_acceso(self):
        if 'groups' in self.fields:
            self.fields['groups'] = forms.ModelMultipleChoiceField(
                label='Grupos adicionales',
                queryset=grupos_adicionales(),
                widget=forms.CheckboxSelectMultiple,
                required=False,
                help_text=(
                    'El grupo del rol se pone solo. Aquí van los demás, que '
                    'suman permisos.'
                ),
            )
            if self.instance.pk:
                self.fields['groups'].initial = self.instance.groups.exclude(
                    name__in=NOMBRES_GRUPOS_DE_ROL
                )

        if 'user_permissions' in self.fields:
            self.fields['user_permissions'] = CampoPermisos(
                label='Permisos sueltos',
                help_text='Solo para esta cuenta, además de los de sus grupos.',
            )
            if self.instance.pk:
                self.fields['user_permissions'].initial = self.instance.user_permissions.all()

    def guardar_acceso(self, usuario):
        """Grupos adicionales + el de su rol, y permisos sueltos."""
        if 'groups' in self.cleaned_data:
            de_rol = usuario.groups.filter(name__in=NOMBRES_GRUPOS_DE_ROL)
            usuario.groups.set([*de_rol, *self.cleaned_data['groups']])

        if 'user_permissions' in self.cleaned_data:
            usuario.user_permissions.set(self.cleaned_data['user_permissions'])

        usuario.sincronizar_grupo_de_rol()
