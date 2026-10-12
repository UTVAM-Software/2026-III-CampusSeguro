from django.db import models


class Viaje(models.Model):
    ESTADOS = [
        ('en_curso', 'En curso'),
        ('llego_bien', 'Llegó bien'),
        ('cancelado', 'Cancelado'),
        ('alerta', 'Alerta'),
    ]
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, related_name='viajes')
    origen = models.CharField(max_length=150)
    destino = models.CharField(max_length=150)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='en_curso')
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.usuario}: {self.origen} -> {self.destino}"


class ViajeAcompanante(models.Model):
    ESTADOS = [
        ('invitado', 'Invitado'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
    ]
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='acompanantes')
    acompanante = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, related_name='acompanamientos')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='invitado')

    class Meta:
        verbose_name = "Acompañante de viaje"
        verbose_name_plural = "Acompañantes de viaje"
        unique_together = ('viaje', 'acompanante')

    def __str__(self):
        return f"{self.acompanante} en viaje {self.viaje_id}"


class UbicacionViaje(models.Model):
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name='ubicaciones')
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ubicación de viaje"
        verbose_name_plural = "Ubicaciones de viaje"

    def __str__(self):
        return f"Viaje {self.viaje_id} - {self.fecha_registro:%H:%M}"