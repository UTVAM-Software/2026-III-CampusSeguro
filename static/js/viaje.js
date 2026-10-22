/*
 * Compartir la posicion mientras dura el viaje.
 *
 * QUE HACE CADA LADO
 *     Quien viaja: el navegador le pide permiso, y a partir de ahi manda su
 *     posicion al servidor cada medio minuto como mucho.
 *
 *     Quien acompana: pregunta cada medio minuto cuando fue la ultima
 *     posicion registrada, y lo escribe en pantalla.
 *
 * POR QUE PREGUNTANDO Y NO CON WEBSOCKETS
 *     Porque esto es lo que se ensena en clase, y para saber si alguien
 *     sigue en camino, preguntar cada treinta segundos sobra. Un socket
 *     abierto seria mas pieza que mantener a cambio de nada.
 *
 * LO QUE NO HACE
 *     Seguir en segundo plano. Si se cierra la pestana, deja de mandar. La
 *     pantalla lo dice, porque alguien podria estar contando con ello.
 */
(function () {
  'use strict';

  const nodo = document.getElementById('config-viaje');
  if (!nodo) return;

  let config;
  try {
    config = JSON.parse(nodo.textContent);
  } catch (e) {
    return;
  }

  if (!config.enCurso) return;

  const titulo = document.querySelector('[data-envio-titulo]');
  const texto = document.querySelector('[data-envio-texto]');
  if (!texto) return;

  const CADA = 30000;

  function decir(t, cuerpo) {
    if (titulo && t) titulo.textContent = t;
    texto.textContent = cuerpo;
  }

  function hace(segundos) {
    if (segundos < 60) return 'hace un momento';
    const minutos = Math.floor(segundos / 60);
    if (minutos < 60) return 'hace ' + minutos + ' min';
    return 'hace ' + Math.floor(minutos / 60) + ' h';
  }

  /* ----------------------------- Quien viaja ---------------------------- */

  function compartir() {
    if (!navigator.geolocation) {
      decir('Tu navegador no comparte ubicación',
            'Quien te acompaña no va a ver dónde estás.');
      return;
    }

    const csrf = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (!csrf) return;

    let ultimoEnvio = 0;

    function mandar(pos) {
      const ahora = Date.now();
      if (ahora - ultimoEnvio < CADA) return;
      ultimoEnvio = ahora;

      const datos = new FormData();
      datos.append('csrfmiddlewaretoken', csrf.value);
      datos.append('latitud', pos.coords.latitude.toFixed(6));
      datos.append('longitud', pos.coords.longitude.toFixed(6));

      fetch(config.urlPosicion, { method: 'POST', body: datos })
        .then((r) => {
          if (r.ok) decir('Compartiendo tu ubicación', 'Actualizada hace un momento.');
          else decir('No se pudo guardar tu ubicación', 'Lo intentamos de nuevo en un momento.');
        })
        .catch(() => {
          decir('Sin conexión', 'Tu ubicación no se está guardando ahora mismo.');
        });
    }

    navigator.geolocation.watchPosition(
      mandar,
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          decir('No diste permiso de ubicación',
                'Quien te acompaña no va a ver dónde estás.');
        } else {
          decir('No se pudo obtener tu ubicación',
                'Puede que no haya señal donde estás.');
        }
      },
      { enableHighAccuracy: true, maximumAge: 15000, timeout: 20000 }
    );
  }

  /* --------------------------- Quien acompana --------------------------- */

  function seguir() {
    function preguntar() {
      fetch(config.urlUltima, { headers: { 'X-Requested-With': 'fetch' } })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => {
          if (!d) return;

          if (!d.enCurso) {
            decir('El viaje terminó', 'Estado: ' + d.estado + '.');
            clearInterval(reloj);
            return;
          }

          if (d.hay) decir(null, 'Última posición registrada ' + hace(d.segundos) + '.');
          else decir(null, 'Todavía no hay ninguna posición registrada.');
        })
        .catch(() => {});
    }

    const reloj = setInterval(preguntar, CADA);
    preguntar();
  }

  if (config.esViajero) compartir();
  else seguir();
})();
