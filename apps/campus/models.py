from django.db import models


class Campus(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True)
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Campus"

    def __str__(self):
        return self.nombre


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

    class Meta:
        verbose_name = "Punto de apoyo"
        verbose_name_plural = "Puntos de apoyo"

    def __str__(self):
        return self.nombre