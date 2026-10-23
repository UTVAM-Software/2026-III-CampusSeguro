from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.templatetags.static import static

from .models import Reporte, ReporteConfirmacion


class SelectConIconos(forms.Select):
    """
    Un <select> cuyas opciones llevan la direccion de su icono.

    El cajon que sustituye al desplegable (static/js/selector.js) la lee de
    `data-icono`. Va en un widget y no escrita en la plantilla porque el mapa
    de iconos vive en el modelo, pegado a la lista de tipos: asi anadir un
    tipo nuevo y olvidarse de su icono es dificil.
    """

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )

        icono = Reporte.ICONOS.get(str(value))

        if icono:
            opcion['attrs']['data-icono'] = static(f'img/iconos/{icono}.png')

        return opcion

#: Lo mínimo que tiene que decir una descripción para servirle a alguien.
#: "si" o "x" no sitúan nada ni dicen qué pasó, y el reporte acaba en el mapa
#: ocupando un punto sin contar nada.
MINIMO_DESCRIPCION = 10


class ReporteForm(forms.ModelForm):
    """
    Registrar una condición del camino.

    LO QUE NO ESTÁ AQUÍ
        `usuario` y `campus` los pone la vista desde la sesión. Mientras
        fueron campos del formulario, cualquiera podía firmar un reporte a
        nombre de otra persona o soltarlo en un campus que no es el suyo.

        `estado` tampoco: un reporte nace pendiente y lo verifica la
        comunidad con sus confirmaciones. Elegir "verificado" al crearlo
        sería saltarse justo lo que da valor al dato.

    LAS COORDENADAS VAN ESCONDIDAS
        Las rellena el selector de ubicación —el botón de "usar mi ubicación"
        o la búsqueda de una dirección—. Teclear 20.122877 a mano es pedir
        una errata que deja el punto en otra calle, y un reporte mal situado
        es peor que ninguno.
    """

    class Meta:
        model = Reporte
        fields = ['tipo', 'descripcion', 'latitud', 'longitud', 'foto']
        labels = {
            'tipo': '¿Qué tipo de situación es?',
            'descripcion': 'Descripción',
            'foto': 'Fotografía (opcional)',
        }
        help_texts = {
            'descripcion': (
                f'Describe qué viste y dónde, con al menos '
                f'{MINIMO_DESCRIPCION} caracteres.'
            ),
            'foto': 'JPG, PNG o WEBP, hasta 5 MB.',
        }
        widgets = {
            'tipo': SelectConIconos(),
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
            'foto': forms.ClearableFileInput(attrs={
                'accept': 'image/jpeg,image/png,image/webp',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # "Elige una categoría" en vez del "---------" de Django: la primera
        # opción de un desplegable es la que más gente deja puesta, y un
        # guion no dice que haya que elegir algo.
        self.fields['tipo'].choices = (
            [('', 'Elige una categoría')] + list(Reporte.TIPOS)
        )

    def clean_descripcion(self):
        descripcion = (self.cleaned_data.get('descripcion') or '').strip()

        if len(descripcion) < MINIMO_DESCRIPCION:
            raise ValidationError(
                f'Cuenta un poco más: al menos {MINIMO_DESCRIPCION} caracteres.'
            )

        return descripcion

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')

        # Sin foto nueva no hay nada que revisar: llega lo que ya estaba
        # guardado, que no es un archivo recién subido.
        if not foto or not hasattr(foto, 'content_type'):
            return foto

        if foto.size > settings.FOTO_REPORTE_MAX_BYTES:
            limite = settings.FOTO_REPORTE_MAX_BYTES // (1024 * 1024)
            raise ValidationError(f'La foto no puede pasar de {limite} MB.')

        # El tipo que manda el navegador es lo que el navegador DICE. El
        # ImageField de Django además abre el archivo y comprueba que sea una
        # imagen de verdad, así que entre los dos no pasa un ejecutable con
        # otro nombre.
        if foto.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
            raise ValidationError('Ese formato no vale. Usa JPG, PNG o WEBP.')

        return foto


class ConfirmacionForm(forms.ModelForm):
    """
    Responder si un reporte es cierto.

    `usuario` NO es un campo. Quien responde es quien tiene la sesión abierta,
    y lo pone la vista. Mientras fue un desplegable, bastaba con elegir otro
    nombre para votar por esa persona —tantas veces como gente hubiera en el
    campus—, y las confirmaciones son justo lo que decide si un reporte se da
    por bueno.

    La lista de reportes también se recorta: solo los del campus de quien
    responde, y nunca los suyos. Eso ya lo impedía `clean`, pero una lista que
    ofrece lo que luego se rechaza hace perder el tiempo.
    """

    class Meta:
        model = ReporteConfirmacion
        fields = ['reporte', 'confirma', 'comentario']

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

        if usuario is not None:
            self.fields['reporte'].queryset = (
                Reporte.objects
                .filter(campus=usuario.campus)
                .exclude(usuario=usuario)
            )

    def clean(self):
        datos = super().clean()
        reporte = datos.get('reporte')

        if reporte and self.usuario and reporte.usuario_id == self.usuario.pk:
            raise forms.ValidationError('La persona que hizo el reporte no puede confirmarlo.')

        return datos
