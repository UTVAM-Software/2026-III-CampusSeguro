from django.db import models
from django.urls import reverse
from django.utils import timezone


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

    # Dónde empieza y dónde termina, en el mapa. Sin esto un viaje son dos
    # textos: no hay nada que dibujar ni punto contra el que comparar la
    # ubicación que va guardando UbicacionViaje.
    #
    # Admiten vacío mientras no exista la pantalla que planifica el viaje, que
    # es la que las toma del mapa. Cuando esa pantalla llegue, pasan a ser
    # obligatorias.
    latitud_origen = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud_origen = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitud_destino = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud_destino = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    estado = models.CharField(max_length=20, choices=ESTADOS, default='en_curso')
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    # Hasta qué hora dura el acompañamiento. Pasada esa hora el viaje vence y
    # hay que avisar a quien acompaña: es la pieza que convierte "comparto mi
    # ubicación" en "alguien se entera si no llego".
    fecha_expiracion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.usuario}: {self.origen} -> {self.destino}"

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('viaje-detail', args=[self.pk])

    #: Con qué color se pinta cada estado en pantalla. Vive aquí, pegado a la
    #: lista de estados, para que añadir uno nuevo y olvidarse de su color sea
    #: difícil: las dos cosas se ven en la misma pantalla del editor.
    TONOS = {
        'en_curso': '',
        'llego_bien': 'exito',
        'cancelado': 'apagada',
        'alerta': 'alerta',
    }

    @property
    def tono_estado(self):
        return self.TONOS.get(self.estado, '')

    @property
    def esta_en_curso(self):
        return self.estado == 'en_curso'

    @property
    def minutos_restantes(self):
        """
        Cuanto falta para la hora limite, en minutos.

        Devuelve None cuando el viaje no tiene hora limite puesta, y la
        pantalla lo dice tal cual en vez de inventarse un numero. Un "45 min"
        que no sale de ningun dato es peor que no poner nada: quien acompana
        se queda esperando una alarma que no va a sonar.
        """
        if not self.fecha_expiracion:
            return None

        faltan = (self.fecha_expiracion - timezone.now()).total_seconds() / 60
        return max(0, int(faltan))

    @property
    def acompanantes_aceptados(self):
        """Los que dijeron que si. A los invitados todavia no se les ensena nada."""
        return self.acompanantes.filter(estado='aceptado')


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

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('acompanante-detail', args=[self.pk])

    #: Con qué color se pinta cada estado en pantalla. Vive aquí, pegado a la
    #: lista de estados, para que añadir uno nuevo y olvidarse de su color sea
    #: difícil: las dos cosas se ven en la misma pantalla del editor.
    TONOS = {
        'invitado': 'espera',
        'aceptado': 'exito',
        'rechazado': 'apagada',
    }

    @property
    def tono_estado(self):
        return self.TONOS.get(self.estado, '')


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

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('ubicacion-detail', args=[self.pk])


class DestinoGuardado(models.Model):
    """Un lugar que la persona guarda para no volver a buscarlo."""

    usuario = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.CASCADE, related_name='destinos'
    )
    etiqueta = models.CharField(max_length=40, help_text='Casa, Trabajo, Parada del 5…')

    # El nombre que tenía el lugar en el mapa cuando se guardó. Se conserva
    # aparte de la etiqueta para que dentro de un año se sepa a qué dirección
    # apunta "Casa".
    referencia = models.CharField(max_length=200, blank=True)

    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Destino guardado"
        verbose_name_plural = "Destinos guardados"
        ordering = ['etiqueta']
        # Dos destinos con la misma etiqueta no se podrían distinguir en una
        # lista. Va por usuario: que otra persona tenga su propia "Casa" es lo
        # normal.
        unique_together = ('usuario', 'etiqueta')

    def __str__(self):
        return self.etiqueta

    def get_absolute_url(self):
        """Su ficha. La usan los enlaces de las plantillas y Django al guardar."""
        return reverse('destino-detail', args=[self.pk])
