from django.db import models
from django.urls import reverse


class Reporte(models.Model):
    # LAS CATEGORÍAS SON LAS DEL PROYECTO VIEJO, Y NO POR COPIAR
    #
    # Antes eran robo, acoso, mala iluminación, persona sospechosa y otro.
    # Dos problemas:
    #
    # 1. "Robo" y "acoso" nombran DELITOS. Esta aplicación no investiga nada
    #    ni comprueba nada: alguien escribe lo que vio y la comunidad lo
    #    confirma. Dejar que una pantalla diga "robo" en un sitio concreto es
    #    acusar, con el sello de la universidad delante y sin que nadie haya
    #    probado nada. "Persona sospechosa" es peor todavía: sospechosa para
    #    quien mira, y lo que acaba describiendo es cómo iba vestida.
    #
    # 2. Tres de las cinco salían con el mismo icono, porque el juego de Lady
    #    no trae dibujo para ninguna de las tres. Sí trae uno para cada una de
    #    estas ocho —alumbrado, obstaculo, situacion_registrada, accidente,
    #    acceso_bloqueado, fugas, obras, otros—, que es justo esta lista.
    #
    # Lo que se registra son CONDICIONES del camino, no culpables.
    TIPOS = [
        ('iluminacion', 'Iluminación'),
        ('obstaculo', 'Obstáculo'),
        ('situacion', 'Situación registrada'),
        ('accidente', 'Accidente'),
        ('acceso_bloqueado', 'Acceso bloqueado'),
        ('fuga', 'Fuga'),
        ('obras', 'Obras'),
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

    # Opcional a propósito: obligar a una foto dejaría fuera a quien reporta de
    # noche, de lejos o sin querer sacar el teléfono. ImageField comprueba que
    # el archivo sea de verdad una imagen y no un ejecutable con otro nombre.
    foto = models.ImageField(upload_to='reportes/', blank=True)

    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    #: El icono de cada tipo, de los que dibujo Lady. Uno distinto para cada
    #: uno: ya no hay tres categorias compartiendo dibujo.
    #:
    #: Vive aqui, pegado a la lista de tipos, y no en las plantillas: el tipo
    #: se pinta en cinco pantallas -inicio, mapa, lista, detalle y filtros- y
    #: un mapa por plantilla acabaria contradiciendose.
    ICONOS = {
        'iluminacion': 'alumbrado',
        'obstaculo': 'obstaculo',
        'situacion': 'situacion_registrada',
        'accidente': 'accidente',
        'acceso_bloqueado': 'acceso_bloqueado',
        'fuga': 'fugas',
        'obras': 'obras',
        'otro': 'otros',
    }

    @property
    def icono(self):
        return self.ICONOS.get(self.tipo, 'otros')

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.fecha_creacion:%d/%m/%Y}"

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('reporte-detail', args=[self.pk])

    #: Con qué color se pinta cada estado en pantalla. Vive aquí, pegado a la
    #: lista de estados, para que añadir uno nuevo y olvidarse de su color sea
    #: difícil: las dos cosas se ven en la misma pantalla del editor.
    TONOS = {
        'pendiente': 'espera',
        'verificado': 'exito',
        'rechazado': 'apagada',
        'resuelto': 'apagada',
    }

    @property
    def tono_estado(self):
        return self.TONOS.get(self.estado, '')


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

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('confirmacion-detail', args=[self.pk])
