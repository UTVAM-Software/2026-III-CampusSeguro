from django import forms
from django.utils import timezone
from .models import Viaje

FORMATO = '%Y-%m-%dT%H:%M'


class ViajeForm(forms.ModelForm):
    """
    Planificar un viaje.

    LOS CAMPOS VAN ESCRITOS A MANO
        `exclude` no significa "todos menos uno": significa "todos los que el
        modelo tenga hoy y todos los que gane después". Con la lista escrita,
        un campo nuevo no se cuela solo en esta pantalla.

    QUÉ NO ESTÁ
        `estado` lo mueven los botones del detalle, que pasan por
        `Viaje.cerrar()` y borran por dónde pasaste; pedirlo aquí abría una
        segunda forma de cerrar un viaje que no borraba nada. `fecha_fin` es
        cuándo terminó: la pone el sistema al cerrarlo.
    """

    class Meta:
        model = Viaje
        # `usuario` fuera: de quién es el viaje lo pone la vista desde la
        # sesión. Si estuviera aquí, sería una lista desplegable con todas las
        # personas del sistema para elegir a nombre de quién viajas.
        fields = [
            'origen', 'destino',
            'latitud_origen', 'longitud_origen',
            'latitud_destino', 'longitud_destino',
            'fecha_expiracion',
        ]
        labels = {
            'fecha_expiracion': 'Hora límite',
        }
        help_texts = {
            'fecha_expiracion': (
                'Hasta qué hora quieres que te acompañen. Si no has '
                'confirmado que llegaste, es la hora a la que quien te '
                'acompaña debería preocuparse.'
            ),
        }
        widgets = {
            'fecha_expiracion': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format=FORMATO
            ),
            # Las rellena el mapa, igual que en la comparación de caminos.
            # Nadie se sabe su latitud, y una errata al teclearla deja el
            # viaje empezando en otra calle.
            'latitud_origen': forms.HiddenInput(),
            'longitud_origen': forms.HiddenInput(),
            'latitud_destino': forms.HiddenInput(),
            'longitud_destino': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bloquea fechas pasadas en el calendario
        self.fields['fecha_expiracion'].widget.attrs['min'] = (
            timezone.localtime().strftime(FORMATO)
        )

    def clean_fecha_expiracion(self):
        limite = self.cleaned_data.get('fecha_expiracion')

        # Una hora límite que ya pasó nace vencida
        if limite and limite < timezone.now():
            raise forms.ValidationError('No puedes elegir una fecha pasada.')

        return limite


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
