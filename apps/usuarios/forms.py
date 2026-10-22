from django import forms
from django.contrib.auth.password_validation import validate_password

from .formularios_grupos import AccesoFormMixin
from .models import Usuario


class RegistroForm(forms.ModelForm):
    """
    Crear una cuenta uno mismo.

    EL ROL NO SE ELIGE AQUÍ, Y ES LO MÁS IMPORTANTE DE ESTE ARCHIVO
        `rol` no está en `fields`. Quien se registra queda como estudiante,
        que es lo que pone el modelo por omisión. Si el rol se pudiera
        mandar en el formulario, cualquiera se registraría como
        administrador: no hace falta ni saber programar, basta con añadir un
        campo a mano antes de enviar.

        Lo mismo con `activo`: quien se registra no decide si su cuenta está
        habilitada.

    LA CONTRASEÑA SE PIDE DOS VECES
        Una errata al escribirla dejaría a alguien fuera de su propia cuenta
        sin manera de saber qué escribió.
    """

    password = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput, strip=False,
    )
    password2 = forms.CharField(
        label="Repite la contraseña", widget=forms.PasswordInput, strip=False,
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellidos', 'correo', 'telefono', 'campus']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # "Elige tu campus" en vez del "---------" de Django. La primera
        # opcion de una lista es la que mas gente deja puesta, y un guion no
        # dice que haya que elegir algo.
        self.fields['campus'].empty_label = 'Elige tu campus'

    def clean_correo(self):
        # En minúsculas: si no, Ana@x.edu y ana@x.edu serían dos cuentas y el
        # unique=True de la columna no lo impediría.
        correo = self.cleaned_data['correo'].strip().lower()

        if Usuario.objects.filter(correo=correo).exists():
            raise forms.ValidationError('Ya hay una cuenta con ese correo.')

        return correo

    def clean(self):
        """
        El correo tiene que ser del campus que se eligió.

        POR QUÉ IMPORTA
            Sin esto, cualquiera con una cuenta de Gmail se registra en
            cualquier universidad y ve los reportes de esa comunidad: dónde
            hay mala iluminación, por dónde pasa la gente, a qué hora.
            Pertenecer al campus es lo único que da derecho a ver eso.

            Se comprueba contra los dominios que tiene registrados ESE campus
            -`Campus.dominios_correo`-, no contra una lista escrita aquí: la
            administración los pone y los cambia sin tocar el código.

        UN CAMPUS SIN DOMINIOS NO FILTRA
            Y es a propósito: si vacío significara "nadie puede registrarse",
            añadir este campo habría cerrado el registro en todas las
            universidades a la vez. El panel avisa de cuáles están sin poner.
        """
        datos = super().clean()
        correo, campus = datos.get('correo'), datos.get('campus')

        if correo and campus and not campus.admite_correo(correo):
            dominios = ', '.join('@' + d for d in campus.dominios)
            self.add_error(
                'correo',
                f'Para {campus} hace falta un correo {dominios}.',
            )

        clave, repetida = datos.get('password'), datos.get('password2')

        if clave and repetida and clave != repetida:
            self.add_error('password2', 'Las dos contraseñas no coinciden.')

        return datos

    def clean_password(self):
        clave = self.cleaned_data['password']

        # Las reglas de AUTH_PASSWORD_VALIDATORS: largo mínimo, que no sea una
        # de las más usadas del mundo, que no sea solo números y que no se
        # parezca al correo o al nombre.
        validate_password(clave)

        return clave



    def save(self, commit=True):
        usuario = super().save(commit=False)

        # set_password cifra con Argon2id. Asignar `usuario.password` a secas
        # guardaría la contraseña en claro en la base.
        usuario.set_password(self.cleaned_data['password'])

        if commit:
            usuario.save()

        return usuario


class UsuarioAdminForm(AccesoFormMixin, RegistroForm):
    """
    El superadmin crea cuentas: lo mismo que el registro
    (contraseña cifrada y validada), más el rol, si está activa, y sus
    grupos adicionales y permisos sueltos.
    """

    class Meta(RegistroForm.Meta):
        fields = RegistroForm.Meta.fields + [
            'rol', 'activo', 'groups', 'user_permissions',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configurar_acceso()

    def save(self, commit=True):
        usuario = super().save(commit=commit)

        if commit:
            self.guardar_acceso(usuario)

        return usuario


class CuentaForm(AccesoFormMixin, forms.ModelForm):
    """
    La base del formulario de editar cuenta. Los campos los decide la vista
    según quién edita (ver UsuarioUpdateView); si están `groups` o
    `user_permissions`, salen como casillas.
    """

    class Meta:
        model = Usuario
        fields = ['nombre', 'apellidos', 'correo', 'telefono']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configurar_acceso()
