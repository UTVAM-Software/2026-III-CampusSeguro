/**
 * El mapa del campus, sobre OpenStreetMap con Leaflet.
 *
 * POR QUE OPENSTREETMAP Y NO GOOGLE MAPS
 *     Google Maps Platform exige tarjeta de credito y facturacion activa. Sin
 *     eso la API degrada el mapa y lo marca de agua. OpenStreetMap no pide
 *     clave ni tarjeta.
 *
 * LO QUE ESTE MAPA NO DIBUJA
 *     Zonas seguras ni zonas peligrosas. Lo que hay son puntos: alguien
 *     registro una condicion en un sitio y una fecha. Pintar un barrio de
 *     rojo seria afirmar algo que este sistema no sabe, y de paso senalar a
 *     quien vive ahi.
 */
(function () {
  "use strict";

  /**
   * La capa de fondo del mapa.
   *
   * POR QUE NO tile.openstreetmap.org
   *     Porque nos bloqueaba. Los servidores de teselas de OpenStreetMap los
   *     pagan voluntarios y su politica de uso no permite que cualquier
   *     aplicacion tire de ellos: devolvian un 403 con una tesela que lo
   *     decia -"App is not following the tile usage policy"- y el mapa salia
   *     empapelado de avisos amarillos.
   *
   *     Las teselas de CARTO estan hechas con los mismos datos de
   *     OpenStreetMap y si se ofrecen para esto. La atribucion va a los dos,
   *     que es lo que piden las dos licencias.
   *
   * LA ATRIBUCION NO ES DECORATIVA
   *     La obligan las licencias. Leaflet la pinta sola a partir de esta
   *     opcion; borrarla es incumplirlas.
   */
  function base(mapa) {
    return L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
      {
        maxZoom: 19,
        attribution:
          'Teselas: <a href="https://www.esri.com/">Esri</a> · ' +
          'Búsqueda y rutas: &copy; colaboradores de ' +
          '<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }
    ).addTo(mapa);
  }

  window.CampusMapa = { base: base };

  /** Los datos que dejo Django con json_script. Null si no hay o no se leen. */
  function leerDatos(id) {
    var nodo = document.getElementById(id);
    if (!nodo) return null;

    try {
      return JSON.parse(nodo.textContent);
    } catch (e) {
      return null;
    }
  }

  /**
   * Escapa texto antes de meterlo en un popup.
   *
   * Las descripciones las escribe la comunidad, y dentro de un popup salen
   * del autoescapado de las plantillas de Django: aqui se construye HTML a
   * mano, asi que hay que escaparlo a mano.
   */
  function escapar(texto) {
    var div = document.createElement("div");
    div.textContent = texto == null ? "" : String(texto);
    return div.innerHTML;
  }

  /**
   * El color de cada estado, leido de las variables `--estado-*` de la hoja
   * de estilos. De ahi salen tambien los cuadritos de la leyenda: con una
   * copia aqui, cambiar un color dejaria la leyenda diciendo una cosa y el
   * mapa pintando otra. Se leen una sola vez y no por marcador.
   */
  var GRIS_DE_RESERVA = "#5b6b7b";
  var colores = null;

  function colorDeEstado(estado) {
    if (colores === null) {
      var raiz = getComputedStyle(document.documentElement);
      colores = {};
      ["pendiente", "verificado", "resuelto", "rechazado"].forEach(function (nombre) {
        colores[nombre] = raiz.getPropertyValue("--estado-" + nombre).trim();
      });
    }

    return colores[estado] || GRIS_DE_RESERVA;
  }

  function marcadorReporte(reporte) {
    return L.circleMarker([reporte.lat, reporte.lng], {
      radius: 9,
      fillColor: colorDeEstado(reporte.estado),
      fillOpacity: 0.95,
      color: "#ffffff",
      weight: 2,
    });
  }

  function marcadorPunto(punto) {
    // Cuadrado frente al circulo de los reportes: quien no distingue bien los
    // colores sigue viendo cual es cual.
    return L.marker([punto.lat, punto.lng], {
      icon: L.divIcon({
        className: "",
        iconSize: [16, 16],
        iconAnchor: [8, 8],
        html: '<span class="pin-punto"></span>',
      }),
    });
  }

  /**
   * Con la fecha: sin ella, un bache de anoche y uno de hace medio ano son el
   * mismo punto en la pantalla.
   */
  function popupReporte(reporte) {
    return (
      "<strong>" + escapar(reporte.tipo) + "</strong><br>" +
      "<small>" + escapar(reporte.estadoTexto) +
      (reporte.cuando ? " · Registrado " + escapar(reporte.cuando) : "") +
      "</small>" +
      "<p>" + escapar(reporte.descripcion) + "</p>" +
      '<a href="/reportes/' + encodeURIComponent(reporte.id) + '/">Ver detalle</a>'
    );
  }

  /**
   * Con el horario: "aqui hay una enfermeria" es media verdad si cierra a las
   * nueve y son las once. Sin horario registrado se dice que no lo hay, que
   * no es lo mismo que estar abierto.
   */
  function popupPunto(punto) {
    return (
      "<strong>" + escapar(punto.nombre) + "</strong><br>" +
      "<small>" + escapar(punto.tipo) + "</small>" +
      "<p>" + (punto.horario
        ? escapar(punto.horario)
        : "Sin horario registrado") + "</p>"
    );
  }

  function iniciar() {
    var datos = leerDatos("datos-mapa");
    var lienzo = document.getElementById("mapa-lienzo");

    if (!datos || !datos.centro || !lienzo || typeof L === "undefined") return;

    var mapa = L.map(lienzo, {
      center: [datos.centro.lat, datos.centro.lng],
      zoom: 16,
      // No secuestra el scroll de la pagina: quien baja con la rueda quiere
      // seguir leyendo, no alejar el mapa.
      scrollWheelZoom: false,
    });

    base(mapa);

    // La leyenda nace escondida en la plantilla: hay mapa, asi que ya tiene
    // algo que explicar.
    var leyenda = document.querySelector("[data-leyenda]");
    if (leyenda) leyenda.hidden = false;

    var capas = [];

    (datos.reportes || []).forEach(function (reporte) {
      capas.push(marcadorReporte(reporte).bindPopup(popupReporte(reporte)).addTo(mapa));
    });

    (datos.puntos || []).forEach(function (punto) {
      capas.push(marcadorPunto(punto).bindPopup(popupPunto(punto)).addTo(mapa));
    });

    // Encuadra todo lo que hay que ver. Sin esto, con los reportes repartidos
    // por el campus algunos quedarian fuera de la vista inicial.
    if (capas.length > 0) {
      // Con un solo marcador el encuadre no tiene area y se iria al zoom
      // maximo: la pantalla entera seria una manzana y no se sabria donde
      // esta eso. 16 deja ver el barrio alrededor.
      mapa.fitBounds(L.featureGroup(capas).getBounds(), {
        padding: [40, 40],
        maxZoom: 16,
      });
    }

    // Un mapa creado dentro de un contenedor que todavia se estaba maquetando
    // se queda con el tamano equivocado y deja teselas grises.
    setTimeout(function () {
      mapa.invalidateSize();
    }, 200);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
