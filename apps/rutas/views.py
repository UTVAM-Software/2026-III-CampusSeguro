"""
Comparar dos caminos por lo que la comunidad ha registrado en ellos.

LO QUE ESTA PANTALLA DICE Y LO QUE NO
    Dice: "por este camino hay 4 condiciones registradas en los últimos 30
    días, y por este otro 1".

    No dice cuál es seguro. No puntúa. No predice. Un camino sin reportes
    puede no tener ninguno porque no pasa nadie por ahí —que es justo lo
    contrario de lo que un número bajo parecería significar—, y la pantalla
    lo advierte con esas palabras.

    Por eso no hay un índice de 0 a 100: un solo número invita a leerse como
    nota de seguridad, por mucho que la letra pequeña diga otra cosa.
"""

from django.utils import timezone
from django.views.generic import FormView

from apps.campus.models import PuntoApoyo
from apps.reportes.models import Reporte
from apps.viajes.models import DestinoGuardado

from .forms import ConsultarRutaForm
from .geo import distancia_a_ruta_metros
from .osrm import ServicioNoDisponible, rutas
from apps.usuarios.permisos import PermisoRequeridoMixin


class ConsultarRutaView(PermisoRequeridoMixin, FormView):
    """
    La sesión la pide `login_required` en urls.py, como todas las demás de
    este proyecto. Un solo mecanismo y en un solo sitio: con unas vistas
    usando el decorador y otras el mixin, mirar el urls.py ya no basta para
    saber qué está cerrado, y hay una prueba que lo mira ahí.
    """

    permission_required = 'reportes.view_reporte'
    template_name = 'rutas/consultar.html'
    form_class = ConsultarRutaForm

    #: A qué distancia del camino deja de contar un reporte. 150 m es como
    #: una cuadra y media: lo que se ve desde la acera. Más lejos y entrarían
    #: cosas de calles por las que no se va a pasar.
    CERCA_METROS = 150

    #: Cuánto hacia atrás se mira. Una lámpara fundida hace ocho meses
    #: seguramente ya se arregló, y contarla diría algo falso del camino de
    #: hoy.
    DIAS = 30

    def get(self, request, *args, **kwargs):
        # Con las coordenadas en la direccion, la consulta se puede compartir
        # y el boton de atras funciona. Sin ellas, el formulario vacio.
        if request.GET:
            formulario = self.get_form()

            if formulario.is_valid():
                return self.render_to_response(
                    self.get_context_data(form=formulario, **self.comparar(formulario))
                )

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Los sitios que esta persona guardó. Aquí sirven de verdad: un
        # toque pone las coordenadas, que es lo que esta pantalla necesita y
        # lo más incómodo de conseguir.
        ctx['destinos'] = DestinoGuardado.objects.filter(usuario=self.request.user)
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        if self.request.method == 'GET' and self.request.GET:
            kwargs['data'] = self.request.GET

        return kwargs

    def comparar(self, formulario):
        """Los caminos y lo que hay registrado cerca de cada uno."""
        origen, destino = formulario.coordenadas()

        try:
            caminos = rutas(origen, destino)
        except ServicioNoDisponible as fallo:
            # Se dice que el servicio no respondio. Dibujar una linea recta
            # en su lugar daria un recuento sobre un camino que no existe, y
            # con aspecto de valido.
            return {'fallo': str(fallo), 'origen': origen, 'destino': destino}

        desde = timezone.now() - timezone.timedelta(days=self.DIAS)
        reportes = list(
            Reporte.objects
            .filter(campus=self.request.user.campus, fecha_creacion__gte=desde)
            .exclude(estado='rechazado')
            .select_related('usuario')
        )
        puntos = list(
            PuntoApoyo.objects.filter(campus=self.request.user.campus, activo=True)
        )

        comparadas = [
            {
                **camino,
                'numero': numero,
                'reportes': self.cerca(camino['puntos'], reportes),
                'apoyos': len(self.cerca(camino['puntos'], puntos)),
            }
            for numero, camino in enumerate(caminos, start=1)
        ]

        return {
            'caminos': comparadas,
            'origen': origen,
            'destino': destino,
            'dias': self.DIAS,
            'metros': self.CERCA_METROS,
            # Para el guion que dibuja las lineas sobre el mapa.
            'datos_rutas': {
                'origen': {'lat': origen[0], 'lng': origen[1]},
                'destino': {'lat': destino[0], 'lng': destino[1]},
                'caminos': [
                    {
                        'numero': c['numero'],
                        'puntos': [[lat, lng] for lat, lng in c['puntos']],
                        'reportes': len(c['reportes']),
                    }
                    for c in comparadas
                ],
            },
        }

    def cerca(self, camino, registros):
        """Los que caen a menos de `CERCA_METROS` del recorrido."""
        return [
            r for r in registros
            if distancia_a_ruta_metros(
                (float(r.latitud), float(r.longitud)), camino
            ) <= self.CERCA_METROS
        ]
