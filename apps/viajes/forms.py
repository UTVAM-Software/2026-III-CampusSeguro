from django import forms
from django.utils import timezone
from .models import Viaje

FORMATO = '%Y-%m-%dT%H:%M'


class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        # `usuario` fuera: de quién es el viaje lo pone la vista desde la
        # sesión. Si estuviera aquí, sería una lista desplegable con todas las
        # personas del sistema para elegir a nombre de quién viajas.
        exclude = ['usuario']
        widgets = {
            'fecha_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format=FORMATO),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bloquea fechas pasadas en el calendario
        self.fields['fecha_fin'].widget.attrs['min'] = timezone.localtime().strftime(FORMATO)

    def clean_fecha_fin(self):
        fin = self.cleaned_data.get('fecha_fin')
        if fin and fin < timezone.now():
            raise forms.ValidationError('No puedes elegir una fecha pasada.')
        return fin

class AcompananteForm(forms.ModelForm):
    """
    Invitar a alguien a acompañarte.

    NO TE PUEDES INVITAR A TI MISMA
        Salía en la pantalla de viajes como "Te invitaron a acompañar:
        GUADALUPE SOLIS" en tu propio viaje. Además de absurdo, no significa
        nada: acompañar sirve para que otra persona vea dónde vas, y tú ya lo
        sabes.

        Se comprueba en los dos sitios: la lista no te ofrece, y `clean` lo
        rechaza aunque llegue por una petición escrita a mano.

    EL ESTADO NO SE ELIGE AL INVITAR
        Una invitación nace invitada. Si quien invita pudiera marcarla como
        aceptada, bastaría con invitarte para dar por hecho que aceptaste —y
        aceptar es justo lo que abre tu ubicación—. La responde quien la
        recibe, en `ResponderInvitacionView`.
    """

    class Meta:
        from .models import ViajeAcompanante

        model = ViajeAcompanante
        fields = ['viaje', 'acompanante']

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

        if usuario is not None:
            from apps.usuarios.models import Usuario

            self.fields['viaje'].queryset = Viaje.objects.filter(usuario=usuario)
            self.fields['acompanante'].queryset = (
                Usuario.objects.filter(activo=True).exclude(pk=usuario.pk)
            )

    def clean(self):
        datos = super().clean()
        viaje, acompanante = datos.get('viaje'), datos.get('acompanante')

        if viaje and acompanante and viaje.usuario_id == acompanante.pk:
            raise forms.ValidationError('No puedes invitarte a tu propio viaje.')

        return datos


class DestinoGuardadoForm(forms.ModelForm):
    """
    Un lugar que se guarda para no volver a buscarlo.

    `usuario` NO es un campo: lo pone la vista desde la sesión. Si estuviera
    aquí, sería una lista con todas las personas del sistema para elegir a
    quién le guardas un destino —y con ello, dónde vive—.

    Las coordenadas van escondidas y las rellena el selector de ubicación,
    igual que en un reporte: teclear 20.122877 a mano es pedir una errata.
    """

    class Meta:
        from .models import DestinoGuardado

        model = DestinoGuardado
        fields = ['etiqueta', 'referencia', 'latitud', 'longitud']
        labels = {
            'etiqueta': '¿Cómo lo vas a llamar?',
            'referencia': 'La dirección, para acordarte',
        }
        help_texts = {
            'etiqueta': 'Casa, Trabajo, Parada del 5… Es lo que verás al planificar.',
            # Se guarda aparte de la etiqueta para que dentro de un ano se
            # sepa a que direccion apunta "Casa".
            'referencia': 'Opcional. Se guarda para saber a qué sitio apunta.',
        }
        widgets = {
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_etiqueta(self):
        """
        Dos "Casa" en la misma lista no se podrían distinguir al elegir.

        La base ya lo impide -`unique_together`-, pero `usuario` no está en
        el formulario, así que Django no puede comprobarlo por su cuenta:
        reventaba con un IntegrityError, que es una página de error en vez de
        un mensaje debajo del campo.
        """
        from .models import DestinoGuardado

        etiqueta = (self.cleaned_data.get('etiqueta') or '').strip()

        if not etiqueta or self.usuario is None:
            return etiqueta

        repetidos = DestinoGuardado.objects.filter(
            usuario=self.usuario, etiqueta__iexact=etiqueta
        ).exclude(pk=self.instance.pk)

        if repetidos.exists():
            raise forms.ValidationError(f'Ya tienes un destino llamado «{etiqueta}».')

        return etiqueta
