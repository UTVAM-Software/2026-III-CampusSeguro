/*
 * Elegir una opcion en un cajon, en vez de en un desplegable del sistema.
 *
 * QUE SUSTITUYE
 *     Al <select> de siempre, que lo dibuja el sistema operativo: ignora la
 *     tipografia, los bordes y los colores del proyecto, y no puede pintar el
 *     icono de cada opcion. En un telefono sale una rueda minuscula en la que
 *     "Acceso bloqueado" y "Accidente" se distinguen mal.
 *
 * QUIEN MANDA SIGUE SIENDO EL <select>
 *     Se queda en el formulario y es el que viaja. Esto lo esconde, dibuja un
 *     boton y un cajon con las opciones, y al elegir le escribe el valor y
 *     dispara su `change`, para que cualquier otro codigo se entere igual que
 *     si se hubiera usado el desplegable de siempre.
 *
 *     Si este archivo no llega a cargarse, queda el <select> normal y se
 *     elige igual de bien.
 *
 * POR QUE <dialog> Y NO UN DIV
 *     `showModal()` da hecho lo que una ventana a mano siempre olvida: el
 *     foco queda atrapado dentro mientras esta abierta, Escape la cierra, el
 *     resto de la pagina queda inerte para los lectores de pantalla y el
 *     fondo oscurecido es `::backdrop`.
 */
(function () {
  'use strict';

  /* La flecha del boton. Va aqui y no en el CSS para que herede el color. */
  const FLECHA =
    '<svg class="selector__flecha" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="m6 9 6 6 6-6"/></svg>';

  /* La misma mascara que `_icono.html`: del PNG solo se usa la silueta y el
     color lo pone el texto de alrededor. */
  function icono(opcion) {
    if (!opcion.dataset.icono) return '';

    return (
      '<span class="icono" style="--icono: url(' + opcion.dataset.icono + ')" aria-hidden="true"></span>'
    );
  }

  function elegibles(campo) {
    return Array.from(campo.options).filter((o) => o.value !== '');
  }

  function montar(caja) {
    const campo = caja.querySelector('select');
    if (!campo) return;

    const sinJs = caja.querySelector('[data-sin-js]');
    const etiqueta = sinJs && sinJs.querySelector('label');
    const ayuda = sinJs && sinJs.querySelector('.campo__ayuda');
    const errores = sinJs ? [...sinJs.querySelectorAll('.campo__error')] : [];
    const titulo = etiqueta ? etiqueta.textContent.trim() : 'Elige una opción';
    const opciones = elegibles(campo);

    if (sinJs) sinJs.hidden = true;

    // Se rehace el campo con su etiqueta y su ayuda, para que quien use un
    // lector de pantalla oiga lo mismo que antes.
    const contenedor = document.createElement('div');
    contenedor.className = 'campo';

    if (etiqueta) {
      const copia = etiqueta.cloneNode(true);
      copia.removeAttribute('for');
      contenedor.appendChild(copia);
    }

    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'selector__boton';
    boton.setAttribute('aria-haspopup', 'dialog');
    boton.disabled = opciones.length === 0;

    const cajon = document.createElement('dialog');
    cajon.className = 'cajon';
    cajon.innerHTML =
      '<span class="cajon__asa" aria-hidden="true"></span>' +
      '<h2 class="cajon__titulo"></h2>' +
      '<ul class="cajon__lista"></ul>';
    cajon.querySelector('.cajon__titulo').textContent = titulo;

    const lista = cajon.querySelector('.cajon__lista');

    function pintarBoton() {
      const elegida = campo.options[campo.selectedIndex];
      const vacio = !elegida || elegida.value === '';

      boton.classList.toggle('selector__boton--vacio', vacio);
      boton.innerHTML =
        '<span class="selector__elegido">' + (vacio ? '' : icono(elegida)) + '</span>' + FLECHA;

      // El texto por separado: asi no hay forma de que un nombre con `<` o
      // `&` dentro se cuele como HTML.
      boton.firstChild.appendChild(document.createTextNode(elegida ? elegida.text : ''));
    }

    function marcar() {
      lista.querySelectorAll('button').forEach((b) => {
        b.setAttribute('aria-pressed', b.dataset.valor === campo.value ? 'true' : 'false');
      });
    }

    function elegir(valor) {
      campo.value = valor;
      campo.dispatchEvent(new Event('change', { bubbles: true }));
      pintarBoton();
      marcar();
      cajon.close();
    }

    opciones.forEach((opcion) => {
      const fila = document.createElement('li');
      const eleccion = document.createElement('button');

      eleccion.type = 'button';
      eleccion.className = 'cajon__opcion';
      eleccion.dataset.valor = opcion.value;
      eleccion.innerHTML =
        icono(opcion) +
        '<span class="cajon__texto"></span>' +
        '<span class="cajon__marca" aria-hidden="true">✓</span>';
      eleccion.querySelector('.cajon__texto').textContent = opcion.text;
      eleccion.addEventListener('click', () => elegir(opcion.value));

      fila.appendChild(eleccion);
      lista.appendChild(fila);
    });

    boton.addEventListener('click', () => {
      marcar();
      cajon.showModal();
    });

    // Pulsar fuera del cajon lo cierra. El <dialog> ocupa solo su caja, asi
    // que un clic con coordenadas fuera de ella es un clic en el fondo.
    cajon.addEventListener('click', (evento) => {
      if (evento.target !== cajon) return;

      const r = cajon.getBoundingClientRect();
      const dentro =
        evento.clientX >= r.left && evento.clientX <= r.right &&
        evento.clientY >= r.top && evento.clientY <= r.bottom;

      if (!dentro) cajon.close();
    });

    contenedor.appendChild(boton);
    contenedor.appendChild(campo);
    campo.classList.add('sr-only');
    campo.tabIndex = -1;

    if (ayuda) contenedor.appendChild(ayuda);
    errores.forEach((e) => contenedor.appendChild(e));

    contenedor.appendChild(cajon);
    caja.appendChild(contenedor);

    pintarBoton();
  }

  document.querySelectorAll('[data-selector]').forEach(montar);
})();
