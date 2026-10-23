/*
 * Poner unas coordenadas sin escribirlas a mano.
 *
 * Lo escribió Lady dentro del formulario de reporte. Está aquí para que
 * cualquier pantalla con un par de campos de latitud y longitud pueda usarlo:
 * lo necesitan los reportes, los puntos de apoyo y la comparación de rutas, y
 * escribir 20.122877 a mano es pedir una errata que deja el punto en otra
 * calle.
 *
 * VARIOS EN LA MISMA PANTALLA
 *     La comparación de rutas tiene dos: origen y destino. Cada caja dice de
 *     qué par es con `data-par="origen"`, y entonces busca los campos
 *     `id_latitud_origen` y `id_longitud_origen`. Sin `data-par` usa
 *     `id_latitud` y `id_longitud`, que es el caso de siempre.
 *
 * SI NO HAY CAMPOS, NO HACE NADA
 *     Se carga en varias pantallas; en las que no los tengan sale por la
 *     puerta sin tocar nada.
 */
(function () {
  function montar(caja) {
    const par = caja.dataset.par ? '_' + caja.dataset.par : '';
    const lat = document.getElementById('id_latitud' + par);
    const lng = document.getElementById('id_longitud' + par);

    if (!lat || !lng) return;

    const estado = caja.querySelector('[data-estado]');
    const titulo = caja.querySelector('[data-titulo]');
    const buscador = caja.querySelector('[data-buscador]');
    const direccion = caja.querySelector('[data-direccion]');

    if (!estado) return;

    // Se rellenan desde aquí. Dejarlos escribibles invita a teclear un número
    // a ojo, y un punto mal situado es peor que ninguno.
    lat.readOnly = lng.readOnly = true;

    // La caja nace escondida cuando es el bloque suelto que se inyecta en un
    // formulario genérico (`_selector_ubicacion.html`): hay que colocarla y
    // destaparla. Cuando ya viene escrita en su sitio, no se toca.
    if (caja.hidden) {
      const hueco = lat.closest('p, div.campo, div');
      if (hueco) hueco.before(caja);
      caja.hidden = false;
    }

    function poner(la, lo, texto) {
      lat.value = Number(la).toFixed(6);
      lng.value = Number(lo).toFixed(6);

      if (titulo) titulo.textContent = 'Ubicación lista';

      estado.textContent = texto + ' · ';

      const enlace = document.createElement('a');
      enlace.href = `https://www.google.com/maps?q=${lat.value},${lng.value}`;
      enlace.target = '_blank';
      enlace.rel = 'noopener';
      enlace.textContent = 'Ver en el mapa';
      estado.appendChild(enlace);
    }

    // Si los campos ya vienen con algo -la consulta llega por la direccion,
    // o el formulario volvio con un error-, la caja lo dice. Sin esto ponia
    // "sin ubicacion" teniendo una, que es lo que mas confunde.
    if (lat.value && lng.value) poner(lat.value, lng.value, 'Ubicación elegida');

    montarMapa(caja, lat, lng, poner);

    // Los destinos guardados, si la pantalla los ofrece. Un toque y las
    // coordenadas quedan puestas, que es justo para lo que se guardaron.
    caja.querySelectorAll('[data-destino-guardado]').forEach((boton) => {
      boton.onclick = () =>
        poner(boton.dataset.lat, boton.dataset.lng, boton.dataset.etiqueta);
    });

    const miUbicacion = caja.querySelector('[data-mi-ubicacion]');

    if (miUbicacion) {
      miUbicacion.onclick = () => {
        estado.textContent = 'Obteniendo tu ubicación...';
        navigator.geolocation.getCurrentPosition(
          (pos) => poner(pos.coords.latitude, pos.coords.longitude, 'Ubicación actual'),
          () => {
            estado.textContent =
              'No se pudo obtener tu ubicación. Prueba escribiendo la dirección.';
          }
        );
      };
    }

    if (!buscador || !direccion) return;

    const abrir = caja.querySelector('[data-otra-direccion]');

    if (abrir) {
      abrir.onclick = () => {
        buscador.hidden = !buscador.hidden;
        if (!buscador.hidden) direccion.focus();
      };
    }

    function buscar() {
      const q = direccion.value.trim();
      if (!q) return;

      estado.textContent = 'Buscando...';

      // Nominatim es el buscador de OpenStreetMap. Limitado a México para que
      // "Juárez" no devuelva una calle de Buenos Aires.
      fetch(
        `https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=mx&q=${encodeURIComponent(q)}`,
        { referrerPolicy: 'strict-origin-when-cross-origin' }
      )
        .then((r) => r.json())
        .then((d) => {
          if (!d.length) {
            estado.textContent = 'No encontré esa dirección. Intenta ser más específica.';
            return;
          }
          poner(d[0].lat, d[0].lon, d[0].display_name);
        })
        .catch(() => {
          estado.textContent = 'No se pudo buscar la dirección.';
        });
    }

    const boton = caja.querySelector('[data-buscar]');
    if (boton) boton.onclick = buscar;

    // Enter busca, en vez de enviar el formulario a medio llenar.
    direccion.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        buscar();
      }
    });
  }

  /**
   * El mapa para señalar el punto con el dedo.
   *
   * POR QUÉ HACE FALTA, ADEMÁS DE LOS OTROS DOS BOTONES
   *     "Usar mi ubicación actual" sirve si estás delante del sitio. Buscar
   *     la dirección sirve para una calle.
   *
   *     Pero una caseta de vigilancia, una enfermería o una lámpara fundida
   *     no tienen dirección propia: están DENTRO del campus, y Nominatim no
   *     sabe nada de ellas. Para eso hace falta poder señalar en el mapa.
   *
   * SE APAGA SOLO SI NO HAY LEAFLET
   *     La caja del mapa nace escondida y solo se destapa si la librería
   *     está. Si no carga, quedan los dos botones de siempre.
   */
  function montarMapa(caja, lat, lng, poner) {
    const hueco = caja.querySelector('[data-mapa-ubicacion]');

    if (!hueco || typeof L === 'undefined' || !window.CampusMapa) return;

    const centro = (hueco.dataset.centro || '').split(',').map(Number);
    const tiene = lat.value && lng.value;

    const punto = tiene
      ? [Number(lat.value), Number(lng.value)]
      : (centro.length === 2 && centro.every((n) => !isNaN(n)) ? centro : [19.8637, -98.982]);

    hueco.closest('.lienzo').hidden = false;

    const mapa = L.map(hueco, { scrollWheelZoom: false }).setView(punto, tiene ? 17 : 16);
    window.CampusMapa.base(mapa);

    // El marcador solo existe cuando hay punto elegido. Uno puesto de
    // entrada en el centro del mapa seria un punto que nadie eligio y que
    // viaja igual si no se toca nada.
    let marca = tiene ? L.marker(punto, { draggable: true }).addTo(mapa) : null;

    function colocar(donde) {
      if (marca) {
        marca.setLatLng(donde);
      } else {
        marca = L.marker(donde, { draggable: true }).addTo(mapa);
        marca.on('dragend', () => {
          const p = marca.getLatLng();
          poner(p.lat, p.lng, 'Señalado en el mapa');
        });
      }
      poner(donde.lat, donde.lng, 'Señalado en el mapa');
    }

    if (marca) {
      marca.on('dragend', () => {
        const p = marca.getLatLng();
        poner(p.lat, p.lng, 'Señalado en el mapa');
      });
    }

    mapa.on('click', (e) => colocar(e.latlng));

    // Un mapa creado dentro de un contenedor que todavia se estaba maquetando
    // se queda con el tamano equivocado y deja teselas grises.
    setTimeout(() => mapa.invalidateSize(), 200);
  }

  document.querySelectorAll('[data-ubicacion]').forEach(montar);
})();
