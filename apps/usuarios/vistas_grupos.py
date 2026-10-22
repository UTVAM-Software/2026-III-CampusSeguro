"""
CRUD de los grupos y permisos de Django, desde la app (Punto 4 de la tarea).

Todas piden un permiso de `auth` -el que corresponde a lo que hacen- y solo
lo tiene el grupo "Superadministrador". Quien no lo tenga recibe 403.
"""

from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.db.models import Count
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView,
)

from .formularios_grupos import (
    GrupoForm, PermisoForm, describir_permiso, es_de_django, es_editable,
    permisos_del_proyecto,
)
from .permisos import PermisoRequeridoMixin
from .roles import NOMBRES_GRUPOS_DE_ROL


# --------------------------------------------------------------------------- #
# Grupos
# --------------------------------------------------------------------------- #

class GrupoListView(PermisoRequeridoMixin, ListView):
    permission_required = 'auth.view_group'
    model = Group
    template_name = 'usuarios/grupo_list.html'

    def get_queryset(self):
        return Group.objects.annotate(
            num_miembros=Count('user', distinct=True),
            num_permisos=Count('permissions', distinct=True),
        ).order_by('name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['grupos_de_rol'] = NOMBRES_GRUPOS_DE_ROL
        return ctx


class GrupoDetailView(PermisoRequeridoMixin, DetailView):
    permission_required = 'auth.view_group'
    model = Group
    template_name = 'usuarios/grupo_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        grupo = self.object
        ctx['es_de_rol'] = grupo.name in NOMBRES_GRUPOS_DE_ROL
        ctx['miembros'] = grupo.user_set.order_by('nombre', 'apellidos')
        ctx['permisos'] = agrupar_por_modelo(
            grupo.permissions.select_related('content_type').order_by(
                'content_type__app_label', 'content_type__model', 'codename'
            )
        )
        return ctx


class GrupoCreateView(PermisoRequeridoMixin, CreateView):
    permission_required = 'auth.add_group'
    model = Group
    form_class = GrupoForm
    template_name = 'usuarios/grupo_form.html'

    def get_success_url(self):
        messages.success(self.request, f'Grupo "{self.object}" creado.')
        return reverse('grupo-detail', args=[self.object.pk])


class GrupoUpdateView(PermisoRequeridoMixin, UpdateView):
    permission_required = 'auth.change_group'
    model = Group
    form_class = GrupoForm
    template_name = 'usuarios/grupo_form.html'

    def get_success_url(self):
        messages.success(self.request, 'Cambios guardados.')
        return reverse('grupo-detail', args=[self.object.pk])


class GrupoDeleteView(PermisoRequeridoMixin, DeleteView):
    """
    Los tres grupos de rol no se borran: sin ellos, nadie tendría permisos.
    No están en el queryset, así que su dirección de borrar responde 404.
    """

    permission_required = 'auth.delete_group'
    model = Group
    template_name = 'usuarios/grupo_confirm_delete.html'
    success_url = reverse_lazy('grupo-list')

    def get_queryset(self):
        return Group.objects.exclude(name__in=NOMBRES_GRUPOS_DE_ROL)


# --------------------------------------------------------------------------- #
# Permisos
# --------------------------------------------------------------------------- #

def agrupar_por_modelo(permisos):
    """[(nombre del modelo, [(permiso, etiqueta), ...]), ...] para las plantillas."""
    grupos = []

    for permiso in permisos:
        titulo = f'{permiso.content_type.app_label} · {permiso.content_type.name}'

        if not grupos or grupos[-1][0] != titulo:
            grupos.append((titulo, []))

        grupos[-1][1].append((permiso, describir_permiso(permiso)))

    return grupos


class PermisoListView(PermisoRequeridoMixin, ListView):
    permission_required = 'auth.view_permission'
    model = Permission
    template_name = 'usuarios/permiso_list.html'

    def get_queryset(self):
        return permisos_del_proyecto()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['por_modelo'] = agrupar_por_modelo(ctx['object_list'])
        return ctx


class PermisoDetailView(PermisoRequeridoMixin, DetailView):
    permission_required = 'auth.view_permission'
    model = Permission
    template_name = 'usuarios/permiso_detail.html'

    def get_queryset(self):
        return permisos_del_proyecto()

    def get_context_data(self, **kwargs):
        from .models import Usuario

        ctx = super().get_context_data(**kwargs)
        permiso = self.object
        ctx['etiqueta'] = describir_permiso(permiso)
        ctx['de_django'] = es_de_django(permiso)
        ctx['editable'] = es_editable(permiso)
        ctx['grupos'] = permiso.group_set.order_by('name')
        ctx['cuentas'] = Usuario.objects.filter(user_permissions=permiso).order_by('nombre')
        return ctx


class PermisosEditablesMixin:
    """
    Solo los permisos creados desde la app se editan o borran. Los de Django
    y los del sistema responden 404: el código los pide por su nombre.
    """

    def get_queryset(self):
        editables = [p.pk for p in permisos_del_proyecto() if es_editable(p)]
        return Permission.objects.filter(pk__in=editables)


class PermisoCreateView(PermisoRequeridoMixin, CreateView):
    permission_required = 'auth.add_permission'
    model = Permission
    form_class = PermisoForm
    template_name = 'usuarios/permiso_form.html'

    def get_success_url(self):
        messages.success(self.request, f'Permiso "{self.object.name}" creado.')
        return reverse('permiso-detail', args=[self.object.pk])


class PermisoUpdateView(PermisoRequeridoMixin, PermisosEditablesMixin, UpdateView):
    permission_required = 'auth.change_permission'
    model = Permission
    form_class = PermisoForm
    template_name = 'usuarios/permiso_form.html'

    def get_success_url(self):
        messages.success(self.request, 'Cambios guardados.')
        return reverse('permiso-detail', args=[self.object.pk])


class PermisoDeleteView(PermisoRequeridoMixin, PermisosEditablesMixin, DeleteView):
    permission_required = 'auth.delete_permission'
    model = Permission
    template_name = 'usuarios/permiso_confirm_delete.html'
    success_url = reverse_lazy('permiso-list')
