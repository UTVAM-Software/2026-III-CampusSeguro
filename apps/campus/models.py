from django.db import models
from django.urls import reverse


class Campus(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    activo = models.BooleanField(default=True)

    # Con qué correo se entra a este campus.
    #
    # Varios separados por coma, porque casi ninguna universidad tiene uno
    # solo: suele haber el del personal y el del alumnado
    # ("uaeh.edu.mx, alumno.uaeh.edu.mx").
    #
    # VACÍO QUIERE DECIR "SIN RESTRICCIÓN", Y ES A PROPÓSITO
    #     Si vacío significara "no se admite nadie", poner este campo habría
    #     dejado el registro cerrado en todos los campus a la vez hasta que
    #     alguien los rellenara uno por uno. Un campo nuevo no puede apagar
    #     la aplicación.
    #
    #     El precio es que un campus sin dominio no filtra nada. El panel lo
    #     dice para que no se quede así sin que nadie se entere.
    dominios_correo = models.CharField(
        'dominios de correo', max_length=200, blank=True,
        help_text=(
            'Separados por coma. Solo se podrán registrar correos de estos '
            'dominios. Déjalo vacío para no restringir.'
        ),
    )

    @property
    def dominios(self):
        """La lista limpia, en minúsculas y sin el arroba si alguien lo puso."""
        return [
            d.strip().lower().lstrip('@')
            for d in self.dominios_correo.split(',')
            if d.strip()
        ]

    def admite_correo(self, correo):
        """
        Si este correo puede registrarse en este campus.

        Sin dominios configurados admite cualquiera. El subdominio cuenta:
        `alumno.uaeh.edu.mx` no entra por `uaeh.edu.mx` si no se puso
        también, porque "acaba en" dejaría pasar `uaeh.edu.mx.otracosa.com`.
        """
        if not self.dominios:
            return True

        _, _, dominio = (correo or '').strip().lower().rpartition('@')

        return dominio in self.dominios

    class Meta:
        verbose_name_plural = "Campus"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('campus-detail', args=[self.pk])


class PuntoApoyo(models.Model):
    TIPOS = [
        ('caseta', 'Caseta de vigilancia'),
        ('enfermeria', 'Enfermería'),
        ('modulo', 'Módulo de ayuda'),
        ('boton', 'Botón de emergencia'),
    ]
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    descripcion = models.TextField(blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    horario = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)

    #: El icono de cada tipo.
    ICONOS = {
        'caseta': 'escudo',
        'enfermeria': 'puntos_apoyo',
        'modulo': 'puntos_apoyo',
        'boton': 'ondas_concentricas',
    }

    @property
    def icono(self):
        return self.ICONOS.get(self.tipo, 'puntos_apoyo')

    class Meta:
        verbose_name = "Punto de apoyo"
        verbose_name_plural = "Puntos de apoyo"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('punto-detail', args=[self.pk])

class Correccion(models.Model):
    """
    Alguien avisa de que un punto de apoyo está mal.

    POR QUÉ ESTO Y NO DEJAR QUE CUALQUIERA EDITE EL PUNTO
        Un punto de apoyo es una afirmación de la institución: decir "aquí
        hay una enfermería" es decirle a alguien que a las diez de la noche
        puede caminar hasta ahí y encontrar a una persona. Si eso lo pudiera
        escribir cualquiera, la primera broma manda a alguien a un edificio
        vacío justo cuando más lo necesita.

        Un reporte es distinto: es "yo vi esto", lo firma quien lo escribe y
        la comunidad lo confirma o lo niega. Un punto de apoyo no se
        confirma, se da por cierto.

        Así que la comunidad AVISA y la administración CORRIGE. Se aprovecha
        que la gente ve las cosas sin dejar que las invente.

    LO QUE ESTO NO CAMBIA
        El punto no se toca solo. Un aviso no lo da de baja ni le cambia el
        horario: lo pone en la cola de quien administra, y esa persona
        decide. Que diez avisos lo cerraran automáticamente sería una forma
        de borrar la enfermería del mapa poniéndose de acuerdo diez personas.
    """

    MOTIVOS = [
        ('cerrado', 'Ya no está o está cerrado'),
        ('horario', 'El horario no coincide'),
        ('ubicacion', 'No está donde dice el mapa'),
        ('otro', 'Otra cosa'),
    ]

    punto = models.ForeignKey(
        PuntoApoyo, on_delete=models.CASCADE, related_name='correcciones'
    )
    usuario = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.CASCADE, related_name='correcciones'
    )
    motivo = models.CharField(max_length=20, choices=MOTIVOS)
    comentario = models.CharField(max_length=300, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    # Mientras esté en False sale en la cola del panel. No se borra al
    # atenderlo: saber que ese punto dio problemas tres veces en un mes es
    # justo lo que hace falta para decidir darlo de baja.
    atendida = models.BooleanField(default=False)
    fecha_atendida = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Corrección de punto de apoyo'
        verbose_name_plural = 'Correcciones de puntos de apoyo'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.punto}: {self.get_motivo_display()}"

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('correccion-detail', args=[self.pk])

    #: Con qué color se pinta cada motivo. Vive aquí, pegado a la lista.
    TONOS = {
        'cerrado': 'alerta',
        'horario': 'espera',
        'ubicacion': 'espera',
        'otro': '',
    }

    @property
    def tono_motivo(self):
        return self.TONOS.get(self.motivo, '')
