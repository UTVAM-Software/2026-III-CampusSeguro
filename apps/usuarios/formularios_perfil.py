"""
Los formularios de la pantalla de perfil.

Van aparte de `forms.py` —que es de entrar y registrarse— porque son otra
conversación: allí no sabemos quién eres todavía, aquí sí, y lo que se edita
son tus propios datos.

LO QUE SE PUEDE CAMBIAR Y LO QUE NO
    Tu foto y tu teléfono. El nombre, el correo y el campus se ven pero no se
    tocan: el correo identifica la cuenta y el campus decide qué reportes y
    qué avisos ves, así que dejar que cada quien se cambie el suyo sería
    dejarle elegir de qué universidad quiere ver las cosas.
"""

import re
from io import BytesIO
from uuid import uuid4

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile

from .models import Usuario

#: Lo que vale como teléfono: números, espacios, guiones, paréntesis y el +
#: de delante. No se valida "que exista" —no se puede sin llamar— sino que no
#: lleve nada raro.
TELEFONO = re.compile(r'^[0-9+\-\s()]{7,15}$')

#: Lo que se acepta como foto. Los mismos que admite un reporte: si el
#: navegador puede enseñarlos, Pillow puede abrirlos.
TIPOS_FOTO = {'image/jpeg', 'image/png', 'image/webp'}


def reducir(imagen):
    """
    Deja la foto en un cuadrado de `LADO_FOTO_PERFIL` píxeles.

    SE RECORTA, NO SE DEFORMA
        Una foto apaisada estirada a cuadrado deja a la persona con la cara
        ancha. `ImageOps.fit` recorta por los lados y conserva el centro.

    SE RESPETA LA ORIENTACIÓN DEL TELÉFONO
        `exif_transpose` aplica el giro que graba la cámara en los datos del
        archivo. Sin esto, las fotos verticales de muchos móviles salen
        tumbadas 90 grados.

    Devuelve siempre un JPEG. Se pierde la transparencia, que en una foto de
    perfil no es pérdida ninguna, y a cambio pesa bastante menos.
    """
    from PIL import Image, ImageOps

    lado = settings.LADO_FOTO_PERFIL

    foto = ImageOps.exif_transpose(Image.open(imagen))
    foto = ImageOps.fit(foto.convert('RGB'), (lado, lado), method=Image.LANCZOS)

    memoria = BytesIO()
    foto.save(memoria, format='JPEG', quality=85, optimize=True)
    memoria.seek(0)

    # El nombre va al azar y no "perfil.jpg": la carpeta de medios se sirve
    # tal cual, así que un nombre previsible es una dirección que cualquiera
    # puede probar para mirar la foto de otra persona.
    return InMemoryUploadedFile(
        memoria, 'ImageField', f'{uuid4().hex}.jpg', 'image/jpeg',
        memoria.getbuffer().nbytes, None,
    )


class DatosPerfilForm(forms.ModelForm):
    """Tu foto y tu teléfono. Nada más: lo demás no es tuyo para cambiarlo."""

    class Meta:
        model = Usuario
        fields = ['foto', 'telefono']
        labels = {'foto': 'Foto de perfil', 'telefono': 'Teléfono'}
        help_texts = {
            'foto': 'JPG, PNG o WEBP, hasta 2 MB. Se guarda recortada en cuadrado.',
            # Lo que dice aquí es lo que de verdad hace el sistema, ni más ni
            # menos: quien escriba su número tiene derecho a saber quién lo va
            # a ver antes de escribirlo.
            'telefono': (
                'Solo lo ven las personas que aceptaron acompañarte, y solo '
                'mientras un viaje tuyo está en curso. Puedes dejarlo vacío.'
            ),
        }
        widgets = {
            'telefono': forms.TextInput(attrs={
                'type': 'tel', 'inputmode': 'tel', 'autocomplete': 'tel',
                'placeholder': '771 123 4567',
            }),
            'foto': forms.ClearableFileInput(attrs={
                'accept': 'image/jpeg,image/png,image/webp',
            }),
        }

    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()

        if telefono and not TELEFONO.match(telefono):
            raise ValidationError('El teléfono tiene caracteres que no son válidos.')

        return telefono

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')

        # Sin foto nueva no hay nada que revisar: `foto` trae entonces lo que
        # ya estaba guardado, que no es un archivo recién subido.
        if not foto or not hasattr(foto, 'content_type'):
            return foto

        if foto.size > settings.FOTO_PERFIL_MAX_BYTES:
            limite = settings.FOTO_PERFIL_MAX_BYTES // (1024 * 1024)
            raise ValidationError(f'La foto no puede pasar de {limite} MB.')

        if foto.content_type not in TIPOS_FOTO:
            raise ValidationError('Ese formato no vale. Usa JPG, PNG o WEBP.')

        try:
            return reducir(foto)
        except Exception:
            # Pillow revienta con un archivo que no es una imagen de verdad,
            # aunque el navegador haya dicho que sí: el tipo que manda el
            # navegador es lo que el navegador DICE, no lo que el archivo es.
            raise ValidationError('No pudimos leer esa imagen. Prueba con otra.')

    def save(self, commit=True):
        """
        Guardar, borrando la foto anterior si llegó una nueva.

        Sin esto, cada cambio de foto deja la anterior ocupando disco para
        siempre y sin nada que la nombre: basura que solo crece.
        """
        anterior = Usuario.objects.get(pk=self.instance.pk).foto

        usuario = super().save(commit=commit)

        if anterior and anterior.name != getattr(usuario.foto, 'name', None):
            anterior.delete(save=False)

        return usuario
