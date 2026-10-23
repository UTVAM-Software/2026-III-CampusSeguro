from django import forms


class ConsultarRutaForm(forms.Form):
    """
    De dónde a dónde.

    Las cuatro coordenadas van escondidas y las rellenan los botones de
    ubicación, igual que en un reporte. Lo que se escribe es la dirección; lo
    que viaja son números.
    """

    origen = forms.CharField(
        label='¿De dónde sales?', max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Ej. UTVAM, Tizayuca'}),
    )
    latitud_origen = forms.DecimalField(
        max_digits=9, decimal_places=6, widget=forms.HiddenInput()
    )
    longitud_origen = forms.DecimalField(
        max_digits=9, decimal_places=6, widget=forms.HiddenInput()
    )

    destino = forms.CharField(
        label='¿A dónde vas?', max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Ej. Paradero de Los Héroes'}),
    )
    latitud_destino = forms.DecimalField(
        max_digits=9, decimal_places=6, widget=forms.HiddenInput()
    )
    longitud_destino = forms.DecimalField(
        max_digits=9, decimal_places=6, widget=forms.HiddenInput()
    )

    def clean(self):
        datos = super().clean()

        # Comprobar el rango aqui y no solo confiar en el formulario: estas
        # coordenadas acaban dentro de una direccion que sale del servidor.
        for campo in ('latitud_origen', 'latitud_destino'):
            valor = datos.get(campo)
            if valor is not None and not (-90 <= valor <= 90):
                self.add_error(campo, 'Latitud fuera de rango.')

        for campo in ('longitud_origen', 'longitud_destino'):
            valor = datos.get(campo)
            if valor is not None and not (-180 <= valor <= 180):
                self.add_error(campo, 'Longitud fuera de rango.')

        return datos

    def coordenadas(self):
        """Los dos puntos, como (lat, lng) en float."""
        d = self.cleaned_data
        return (
            (float(d['latitud_origen']), float(d['longitud_origen'])),
            (float(d['latitud_destino']), float(d['longitud_destino'])),
        )
