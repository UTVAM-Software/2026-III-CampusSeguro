from django.db import models


class Usuario(models.Model):
    ROLES = [
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
        ('administrativo', 'Administrativo'),
        ('seguridad', 'Seguridad'),
        ('admin', 'Administrador'),
    ]
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    correo = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15, blank=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='estudiante')
    campus = models.ForeignKey('campus.Campus', on_delete=models.PROTECT)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellidos}"