from django import forms
from django.utils import timezone
from .models import Aviso


class AvisoForm(forms.ModelForm):
    class Meta:
        model = Aviso
        fields = '__all__'
        widgets = {
            'fecha_expiracion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bloquea días pasados en el calendario
        self.fields['fecha_expiracion'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_fecha_expiracion(self):
        fecha = self.cleaned_data.get('fecha_expiracion')
        if fecha and fecha < timezone.localdate():
            raise forms.ValidationError('No puedes elegir una fecha pasada.')
        return fecha