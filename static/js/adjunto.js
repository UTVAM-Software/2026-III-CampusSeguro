/*
 * El area de "elige una foto o arrastrala aqui".
 *
 * NO SUSTITUYE AL CAMPO DE ARCHIVO, LO ENVUELVE
 *     El <input type="file"> de siempre sigue siendo el que viaja en el
 *     formulario. Este guion solo cambia cual de las dos versiones se ve y lo
 *     mueve dentro del area. Si el guion no carga, queda el campo normal y la
 *     foto se adjunta igual de bien.
 *
 * NO HAY BARRA DE PROGRESO, Y ES A PROPOSITO
 *     La foto no viaja al elegirla: viaja al enviar el formulario, con todo
 *     lo demas. Una barra aqui no estaria midiendo nada, solo dando vueltas
 *     para que pareciera que pasa algo.
 */
(function () {
  const caja = document.querySelector('[data-adjunto]');
  if (!caja) return;

  const sinJs = caja.querySelector('[data-sin-js]');
  const conJs = caja.querySelector('[data-con-js]');
  const campo = caja.querySelector('input[type="file"]');

  if (!sinJs || !conJs || !campo) return;

  const zona = conJs.querySelector('[data-zona]');
  const tarjeta = conJs.querySelector('[data-tarjeta]');
  const vista = conJs.querySelector('[data-vista]');
  const nombre = conJs.querySelector('[data-nombre]');
  const meta = conJs.querySelector('[data-meta]');
  const aviso = conJs.querySelector('[data-aviso]');

  // Lo mismo que comprueba el servidor. Aqui es solo para avisar antes, no
  // es la barrera: quien mande la peticion a mano se salta esto entero.
  const MAX_BYTES = 5 * 1024 * 1024;
  const TIPOS = ['image/jpeg', 'image/png', 'image/webp'];

  // El campo de archivo se mete dentro del area y se esconde: el que abre el
  // dialogo es el mismo que luego envia el archivo.
  zona.appendChild(campo);
  campo.classList.add('sr-only');

  sinJs.hidden = true;
  conJs.hidden = false;

  function pesar(bytes) {
    const megas = bytes / (1024 * 1024);
    return megas >= 1 ? megas.toFixed(1) + ' MB' : Math.round(bytes / 1024) + ' KB';
  }

  function avisar(texto) {
    aviso.textContent = texto;
    aviso.hidden = !texto;
  }

  function limpiar() {
    campo.value = '';
    if (vista.src) URL.revokeObjectURL(vista.src);
    vista.removeAttribute('src');
    tarjeta.hidden = true;
    zona.hidden = false;
    avisar('');
  }

  function mostrar(archivo) {
    if (!TIPOS.includes(archivo.type)) {
      limpiar();
      avisar('Ese formato no vale. Usa JPG, PNG o WEBP.');
      return;
    }

    if (archivo.size > MAX_BYTES) {
      limpiar();
      avisar('La foto no puede pasar de 5 MB.');
      return;
    }

    avisar('');
    vista.src = URL.createObjectURL(archivo);
    nombre.textContent = archivo.name;
    meta.textContent = pesar(archivo.size);
    zona.hidden = true;
    tarjeta.hidden = false;
  }

  zona.addEventListener('click', (e) => {
    // El propio campo ya abre el dialogo; sin esto se abriria dos veces.
    if (e.target !== campo) campo.click();
  });

  campo.addEventListener('change', () => {
    if (campo.files.length) mostrar(campo.files[0]);
  });

  conJs.querySelector('[data-cambiar]').onclick = () => campo.click();
  conJs.querySelector('[data-quitar]').onclick = limpiar;

  // Arrastrar y soltar. `DataTransfer` es lo que permite meter el archivo
  // soltado DENTRO del campo: sin eso, el formulario viajaria sin foto.
  ['dragenter', 'dragover'].forEach((evento) =>
    zona.addEventListener(evento, (e) => {
      e.preventDefault();
      zona.classList.add('adjunto__zona--encima');
    })
  );

  ['dragleave', 'drop'].forEach((evento) =>
    zona.addEventListener(evento, () => zona.classList.remove('adjunto__zona--encima'))
  );

  zona.addEventListener('drop', (e) => {
    e.preventDefault();

    const archivo = e.dataTransfer.files[0];
    if (!archivo) return;

    const datos = new DataTransfer();
    datos.items.add(archivo);
    campo.files = datos.files;

    mostrar(archivo);
  });
})();
