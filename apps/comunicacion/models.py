from django.db import models


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


class Aviso(models.Model):
    NIVELES = [
        ('info', 'Informativo'),
        ('precaucion', 'Precaución'),
        ('urgente', 'Urgente'),
    ]
    campus = models.ForeignKey('campus.Campus', on_delete=models.CASCADE)
    autor = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.CharField(max_length=100)
    contenido = models.TextField()
    nivel = models.CharField(max_length=20, choices=NIVELES, default='info')
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo