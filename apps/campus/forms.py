"""Los formularios de campus y puntos de apoyo."""

from django import forms
from django.templatetags.static import static

from .models import Correccion, PuntoApoyo


class SelectConIconos(forms.Select):
    """
    Un <select> cuyas opciones llevan la direccion de su icono.

    El cajon que sustituye al desplegable (static/js/selector.js) la lee de
    `data-icono`. Es el mismo truco que en los reportes, y vive aqui y no en
    un sitio comun porque cada uno mira SU mapa de iconos: el de este modelo
    esta en `PuntoApoyo.ICONOS`, pegado a su lista de tipos.
    """

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )

        icono = PuntoApoyo.ICONOS.get(str(value))

        if icono:
            opcion['attrs']['data-icono'] = static(f'img/iconos/{icono}.png')

        return opcion


class PuntoApoyoForm(forms.ModelForm):
    """
    Registrar un punto de apoyo: donde hay ayuda dentro del campus.

    LAS COORDENADAS VAN ESCONDIDAS
        Las rellena el selector de ubicacion. Es lo mismo que en un reporte y
        por lo mismo: teclear 20.122877 a mano deja la enfermeria en otra
        calle, y aqui el error manda a alguien a caminar hasta un sitio donde
        no hay nada.
    """

    class Meta:
        model = PuntoApoyo
        fields = [
            'campus', 'nombre', 'tipo', 'descripcion',
            'horario', 'latitud', 'longitud', 'activo',
        ]
        labels = {
            'nombre': 'Nombre',
            'tipo': '¿Qué tipo de punto es?',
            'descripcion': 'Descripción',
            'horario': 'Horario',
            'activo': 'Está disponible',
        }
        help_texts = {
            'nombre': 'Como lo conoce la gente del campus. Ej. "Enfermería del edificio C".',
            'horario': 'Ej. "Lunes a viernes, 8:00 a 20:00". Déjalo vacío si no lo sabes.',
            # Lo que de verdad hace la casilla, no lo que parece: un punto
            # dado de baja desaparece de la lista y del mapa.
            'activo': (
                'Si lo quitas, deja de salir en la lista y en el mapa. Mandar '
                'a alguien a un módulo cerrado es peor que no enseñárselo.'
            ),
        }
        widgets = {
            'tipo': SelectConIconos(),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['campus'].empty_label = 'Elige el campus'
        self.fields['tipo'].choices = (
            [('', 'Elige un tipo')] + list(PuntoApoyo.TIPOS)
        )


class CorreccionForm(forms.ModelForm):
    """
    Avisar de que un punto de apoyo está mal.

    `punto` y `usuario` NO son campos: el punto lo dice la dirección y el
    usuario la sesión. Si estuvieran aquí, cualquiera podría avisar de un
    punto de otro campus a nombre de otra persona.
    """

    class Meta:
        model = Correccion
        fields = ['motivo', 'comentario']
        labels = {
            'motivo': '¿Qué está mal?',
            'comentario': 'Cuéntanos (opcional)',
        }
        help_texts = {
            'comentario': (
                'Lo que viste. Esto lo lee quien administra el campus para '
                'corregirlo.'
            ),
        }
        widgets = {
            'comentario': forms.Textarea(attrs={
                'rows': 2, 'placeholder': 'Ej. Lleva cerrada desde el mes pasado.',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['motivo'].choices = (
            [('', 'Elige qué está mal')] + list(Correccion.MOTIVOS)
        )
