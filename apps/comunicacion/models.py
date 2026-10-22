from django.db import models
from django.urls import reverse


class Notificacion(models.Model):
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, related_name='notificaciones')
    titulo = models.CharField(max_length=100)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('notificacion-detail', args=[self.pk])


class Aviso(models.Model):
    NIVELES = [
        ('info', 'Informativo'),
        ('precaucion', 'Precaución'),
        ('urgente', 'Urgente'),
    ]

    #: Con qué color se pinta cada estado en pantalla. Vive aquí, pegado a la
    #: lista de estados, para que añadir uno nuevo y olvidarse de su color sea
    #: difícil: las dos cosas se ven en la misma pantalla del editor.
    TONOS = {
        'info': '',
        'precaucion': 'espera',
        'urgente': 'alerta',
    }

    @property
    def tono_nivel(self):
        return self.TONOS.get(self.nivel, '')
    campus = models.ForeignKey('campus.Campus', on_delete=models.CASCADE)
    autor = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.CharField(max_length=100)
    contenido = models.TextField()
    nivel = models.CharField(max_length=20, choices=NIVELES, default='info')
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    @property
    def esta_vigente(self):
        """
        Si este aviso sigue valiendo hoy.

        El inicio ya filtraba por esto para no ensenar avisos caducados, pero
        la condicion vivia dentro de la consulta de esa pantalla. Aqui la ve
        tambien el detalle, que es donde hace falta decir "esto caduco" en vez
        de ensenarlo como si fuera de hoy.
        """
        from django.utils import timezone

        if not self.activo:
            return False

        return (
            self.fecha_expiracion is None
            or self.fecha_expiracion >= timezone.localdate()
        )

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('aviso-detail', args=[self.pk])
