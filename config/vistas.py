"""
El inicio.

Era un `TemplateView` sin datos: un menú con un botón por sección. Ahora
enseña lo que esa persona necesita ver al abrir la aplicación —si tiene un
viaje en curso, qué avisó el campus, qué se ha reportado cerca— y deja el
menú completo para abajo.

CADA BLOQUE TRAE DATOS DE VERDAD O SU HUECO
    Ninguno inventa contenido para que la pantalla se vea llena. Si no hay
    reportes, lo dice; si no hay puntos de apoyo, lo dice. Una pantalla que
    finge tener datos es peor que una vacía: quien la mira se fía.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView

from apps.campus.models import Campus, Correccion, PuntoApoyo
from apps.comunicacion.models import Aviso, Notificacion
from apps.reportes.models import Reporte
from apps.usuarios.permisos import PermisoRequeridoMixin
from apps.viajes.models import Viaje, ViajeAcompanante
from config.fechas import hace


class InicioView(PermisoRequeridoMixin, LoginRequiredMixin, TemplateView):
    permission_required = 'reportes.view_reporte'
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        campus = usuario.campus

        contexto["viaje_en_curso"] = (
            Viaje.objects.filter(usuario=usuario, estado="en_curso").first()
        )

        # Los viajes que esta persona acompaña también están activos: dejarlos
        # fuera sería no enseñarle que alguien cuenta con ella ahora mismo.
        contexto["acompanamientos"] = (
            ViajeAcompanante.objects
            .filter(acompanante=usuario, estado="aceptado", viaje__estado="en_curso")
            .select_related("viaje", "viaje__usuario")
        )

        hoy = timezone.localdate()

        # Vigente es: activo y sin fecha de fin, o con una que todavía no pasó.
        # Un aviso caducado en la pantalla de inicio es información falsa.
        contexto["avisos"] = (
            Aviso.objects
            .filter(campus=campus, activo=True)
            .filter(Q(fecha_expiracion__isnull=True) | Q(fecha_expiracion__gte=hoy))
            .order_by("-fecha_publicacion")[:2]
            if campus else []
        )

        contexto["reportes"] = (
            Reporte.objects
            .filter(campus=campus)
            .select_related("usuario")
            .order_by("-fecha_creacion")[:3]
            if campus else []
        )

        contexto["puntos"] = (
            PuntoApoyo.objects.filter(campus=campus, activo=True)[:3] if campus else []
        )

        contexto["sin_leer"] = Notificacion.objects.filter(
            usuario=usuario, leida=False
        ).count()

        return contexto


class MapaView(PermisoRequeridoMixin, LoginRequiredMixin, TemplateView):
    """
    El mapa del campus: dónde se ha registrado qué, y dónde hay ayuda.

    LO QUE EL MAPA NO DICE
        No pinta zonas seguras ni zonas peligrosas, y no las va a pintar. Lo
        que hay son condiciones que alguien registró en un punto concreto y
        una fecha concreta. Colorear un barrio de rojo sería afirmar algo que
        este sistema no sabe, y de paso señalar a quien vive ahí.

    EL FILTRO VA EN LA DIRECCIÓN
        `?categoria=obras&categoria=fuga`. Así un filtro puesto se puede
        compartir o guardar, y el botón de atrás del navegador lo deshace. Si
        viviera solo en JavaScript, ninguna de las dos cosas funcionaría.

        Las categorías que llegan se cruzan con las que existen: cualquier
        otra cosa se tira, para que escribir una categoría inventada en la
        dirección no cambie lo que se ve.
    """

    permission_required = 'reportes.view_reporte'
    template_name = "mapa.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        campus = usuario.campus

        validas = {valor for valor, _ in Reporte.TIPOS}
        activas = [c for c in self.request.GET.getlist("categoria") if c in validas]

        reportes = (
            Reporte.objects.filter(campus=campus).select_related("usuario")
            if campus else Reporte.objects.none()
        )

        if activas:
            reportes = reportes.filter(tipo__in=activas)

        reportes = list(reportes.order_by("-fecha_creacion"))
        puntos = list(
            PuntoApoyo.objects.filter(campus=campus, activo=True) if campus else []
        )

        contexto.update(
            campus=campus,
            categorias=Reporte.TIPOS,
            categorias_activas=activas,
            reportes=reportes,
            puntos=puntos,
            datos_mapa=self.datos_del_mapa(campus, reportes, puntos),
        )
        return contexto

    @staticmethod
    def datos_del_mapa(campus, reportes, puntos):
        """
        Lo que el mapa necesita, como datos y no como JavaScript escrito a
        mano dentro de la plantilla: va por `json_script`, que escapa lo que
        escribió la comunidad. Una descripción con `</script>` dentro
        reventaría la página -o algo peor- si se pegara en crudo.

        El centro es el del campus. Casi nunca se usa: cuando hay algo que
        enseñar, el guion encuadra todos los marcadores. Solo manda cuando el
        mapa está vacío.
        """
        centro = (
            {"lat": float(campus.latitud), "lng": float(campus.longitud)}
            if campus else None
        )

        return {
            "centro": centro,
            "reportes": [
                {
                    "id": r.pk,
                    "lat": float(r.latitud),
                    "lng": float(r.longitud),
                    "tipo": r.get_tipo_display(),
                    "estado": r.estado,
                    "estadoTexto": r.get_estado_display(),
                    "descripcion": r.descripcion,
                    # Sin el cuándo, lo de anoche y lo de hace medio año son
                    # el mismo punto en la pantalla.
                    "cuando": hace(r.fecha_creacion),
                }
                for r in reportes
            ],
            "puntos": [
                {
                    "lat": float(p.latitud),
                    "lng": float(p.longitud),
                    "nombre": p.nombre,
                    "tipo": p.get_tipo_display(),
                    # "Aquí hay una enfermería" es media verdad si cierra a
                    # las nueve y son las once.
                    "horario": p.horario,
                }
                for p in puntos
            ],
        }


class PanelView(PermisoRequeridoMixin, TemplateView):
    """
    El panel de quien administra: que hay registrado y que espera respuesta.

    LO QUE ESTA PANTALLA NO HACE
        No predice nada. Compara dos periodos y lo dice con esas palabras: un
        aumento puede significar que pasan mas cosas, o simplemente que mas
        gente esta usando Campus Seguro. Presentar eso como una prevision
        seria inventar una capacidad que este sistema no tiene.

    SOLO EL CAMPUS DE QUIEN MIRA
        Las cifras salen de los reportes de su campus. Un panel con los
        numeros de todas las universidades no le sirve para nada a quien
        administra una, y de paso diria cuantas hay y como les va.
    """

    permission_required = 'usuarios.administrar_campus'
    template_name = "panel.html"

    #: Cuantos dias compara la tendencia contra los mismos de antes.
    DIAS = 7

    #: A cuantos decimales se redondean las coordenadas para agrupar zonas.
    #: Tres decimales son unos 110 m: una esquina, no un edificio concreto.
    DECIMALES = 3

    def get_context_data(self, **kwargs):
        from collections import Counter
        from datetime import timedelta

        contexto = super().get_context_data(**kwargs)
        campus = self.request.user.campus
        reportes = Reporte.objects.filter(campus=campus) if campus else Reporte.objects.none()

        ahora = timezone.now()
        corte = ahora - timedelta(days=self.DIAS)
        corte_previo = corte - timedelta(days=self.DIAS)

        por_estado = Counter(reportes.values_list("estado", flat=True))

        contexto["campus"] = campus
        contexto["resumen"] = {
            "total": sum(por_estado.values()),
            "pendientes": por_estado.get("pendiente", 0),
            "verificados": por_estado.get("verificado", 0),
            "recientes": reportes.filter(fecha_creacion__gte=ahora - timedelta(days=1)).count(),
        }
        contexto["estados"] = [
            (etiqueta, por_estado.get(valor, 0)) for valor, etiqueta in Reporte.ESTADOS
        ]
        contexto["categorias"] = self.por_categoria(reportes)
        contexto["tendencia"] = self.tendencia(reportes, corte, corte_previo)
        contexto["zonas"] = self.zonas(reportes)

        # Lo que espera una respuesta. Es lo unico de esta pantalla sobre lo
        # que se puede ACTUAR, asi que lleva enlace a cada reporte.
        contexto["pendientes"] = (
            reportes.filter(estado="pendiente")
            .select_related("usuario")
            .order_by("-fecha_creacion")[:5]
        )

        # Los campus que todavia no restringen el correo.
        #
        # Un campus sin dominios admite a cualquiera con un Gmail, y eso no
        # se nota desde ninguna pantalla: el registro funciona igual. Si no
        # se avisa aqui, se queda asi para siempre sin que nadie se entere.
        contexto["campus_sin_dominio"] = Campus.objects.filter(
            dominios_correo=""
        ).order_by("nombre")

        # Lo que la comunidad avisa que esta mal en los puntos de apoyo.
        # Junto a los reportes pendientes porque es lo mismo: cosas que
        # esperan una decision de quien administra.
        contexto["correcciones"] = Correccion.objects.filter(
            atendida=False, punto__campus=campus
        ).count()

        return contexto

    @staticmethod
    def por_categoria(reportes):
        """Cuantos hay de cada tipo, y que parte del total son."""
        from collections import Counter

        cuenta = Counter(reportes.values_list("tipo", flat=True))
        total = sum(cuenta.values())

        return [
            {
                "etiqueta": etiqueta,
                "total": cuenta.get(valor, 0),
                # Sin reportes el porcentaje seria una division por cero. Y
                # una barra al 0% es informacion: "de esto no hay".
                "porcentaje": round(cuenta.get(valor, 0) * 100 / total) if total else 0,
            }
            for valor, etiqueta in Reporte.TIPOS
        ]

    def tendencia(self, reportes, corte, corte_previo):
        """
        Los de esta semana contra los de la anterior.

        `variacion` es None cuando antes no habia ninguno: un aumento del
        "infinito por ciento" porque se pasa de cero a uno no dice nada.
        """
        actual = reportes.filter(fecha_creacion__gte=corte).count()
        previo = reportes.filter(
            fecha_creacion__gte=corte_previo, fecha_creacion__lt=corte
        ).count()

        return {
            "dias": self.DIAS,
            "actual": actual,
            "previo": previo,
            "variacion": round((actual - previo) * 100 / previo) if previo else None,
            "sube": actual > previo,
            "baja": actual < previo,
        }

    def zonas(self, reportes):
        """
        Donde se juntan varios reportes, agrupando por coordenada redondeada.

        Solo las que acumulan mas de uno: una zona con un reporte no es una
        concentracion, es un reporte.

        NO ES UNA ZONA PELIGROSA, Y LA PANTALLA LO DICE
            Es donde la gente ha registrado mas cosas. Puede ser el sitio por
            donde pasa mas gente, o donde hay mas luz para ver lo que pasa.
        """
        from collections import Counter

        cuenta = Counter(
            (round(float(lat), self.DECIMALES), round(float(lng), self.DECIMALES))
            for lat, lng in reportes.values_list("latitud", "longitud")
        )

        return [
            {"latitud": lat, "longitud": lng, "total": total}
            for (lat, lng), total in cuenta.most_common(5)
            if total > 1
        ]
