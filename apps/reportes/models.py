from django.db import models


class Reporte(models.Model):
    TIPOS = [
        ('robo', 'Robo'),
        ('acoso', 'Acoso'),
        ('iluminacion', 'Mala iluminación'),
        ('sospechoso', 'Persona sospechosa'),
        ('otro', 'Otro'),
    ]
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('verificado', 'Verificado'),
        ('rechazado', 'Rechazado'),
        ('resuelto', 'Resuelto'),
    ]
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, related_name='reportes')
    campus = models.ForeignKey('campus.Campus', on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    descripcion = models.TextField()
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.fecha_creacion:%d/%m/%Y}"


class ReporteConfirmacion(models.Model):
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name='confirmaciones')
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE)
    confirma = models.BooleanField(default=True)
    comentario = models.CharField(max_length=200, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Confirmación de reporte"
        verbose_name_plural = "Confirmaciones de reporte"
        unique_together = ('reporte', 'usuario')

    def __str__(self):
        return f"{self.usuario} -> reporte {self.reporte_id}"