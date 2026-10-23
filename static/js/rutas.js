/*
 * Dibuja los caminos comparados sobre el mapa.
 *
 * Cada camino va de un color, y el mismo color lleva su tarjeta debajo: sin
 * eso, con dos lineas en pantalla no hay forma de saber cual es cual.
 *
 * NO PINTA UNO DE VERDE Y OTRO DE ROJO, Y ES A PROPOSITO
 *     Verde y rojo se leen como "seguro" y "peligroso", que es justo lo que
 *     estos datos no dicen. Son dos azules distintos: colores de
 *     identificacion, no de juicio.
 */
(function () {
  'use strict';

  const nodo = document.getElementById('datos-rutas');
  const lienzo = document.getElementById('mapa-rutas');

  if (!nodo || !lienzo || typeof L === 'undefined') return;

  let datos;
  try {
    datos = JSON.parse(nodo.textContent);
  } catch (e) {
    return;
  }

  if (!datos.caminos || !datos.caminos.length) return;

  const COLORES = ['#1976d2', '#0b3b61', '#5b6b7b'];

  const mapa = L.map(lienzo, { scrollWheelZoom: false });

  // La misma capa de fondo que el mapa del campus, y por el mismo motivo:
  // los servidores de teselas de OpenStreetMap no permiten que cualquier
  // aplicacion tire de ellos y nos devolvian 403. Ver static/js/mapa.js.
  window.CampusMapa.base(mapa);

  const capas = [];

  datos.caminos.forEach((camino, i) => {
    const linea = L.polyline(camino.puntos, {
      color: COLORES[i % COLORES.length],
      weight: 6,
      opacity: 0.85,
    }).addTo(mapa);

    linea.bindPopup(
      'Camino ' + camino.numero + '<br><small>' +
      camino.reportes + ' condiciones registradas cerca</small>'
    );
    capas.push(linea);
  });

  // Los dos extremos. Formas distintas entre si y distintas de las lineas:
  // quien no distingue bien los colores sigue viendo donde empieza y acaba.
  const salida = L.circleMarker([datos.origen.lat, datos.origen.lng], {
    radius: 9, fillColor: '#0f7a4f', fillOpacity: 1, color: '#ffffff', weight: 3,
  }).addTo(mapa).bindPopup('Sales de aquí');

  const llegada = L.marker([datos.destino.lat, datos.destino.lng], {
    icon: L.divIcon({
      className: '',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
      html: '<span class="pin-destino"></span>',
    }),
  }).addTo(mapa).bindPopup('Llegas aquí');

  capas.push(salida, llegada);

  mapa.fitBounds(L.featureGroup(capas).getBounds(), { padding: [40, 40] });

  // Un mapa creado dentro de un contenedor que todavia se estaba maquetando
  // se queda con el tamano equivocado y deja teselas grises.
  setTimeout(() => mapa.invalidateSize(), 200);
})();
