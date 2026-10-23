/*
 * Cerrar el panel de la campana al tocar fuera o con Escape.
 *
 * QUE HACE Y QUE NO
 *     El panel es un <details>: abrirlo y cerrarlo con su propio boton ya lo
 *     hace el navegador. Esto solo anade lo que le falta a un <details> para
 *     portarse como un menu. Si este archivo no llega a cargarse, el panel
 *     sigue abriendose y cerrandose con la campana.
 */
(function () {
  'use strict';

  const SELECTOR = '[data-campana]';

  function abiertas() {
    return Array.from(document.querySelectorAll(SELECTOR)).filter((p) => p.open);
  }

  function cerrar(excepto) {
    abiertas().forEach((panel) => {
      if (panel !== excepto) panel.open = false;
    });
  }

  document.addEventListener('click', (evento) => {
    if (!evento.target.closest) return;

    // El velo esta DENTRO del <details> para poder pintarse solo cuando esta
    // abierto, pero para quien lo pulsa es "fuera": ahi se cierra.
    if (evento.target.classList.contains('campana__velo')) {
      cerrar(null);
      return;
    }

    cerrar(evento.target.closest(SELECTOR));
  });

  document.addEventListener('keydown', (evento) => {
    if (evento.key !== 'Escape') return;

    const habia = abiertas().length > 0;
    cerrar(null);

    // El foco vuelve a la campana: si se quedara donde estaba, quien navega
    // con teclado acabaria perdido a mitad de la pagina.
    if (habia) {
      const boton = document.querySelector(SELECTOR + ' > summary');
      if (boton) boton.focus();
    }
  });
})();
