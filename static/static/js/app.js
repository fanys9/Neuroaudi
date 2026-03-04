/**
 * Interfaz web — Experimento de audio NeuroAudi
 * Flujo: Iniciar → Prueba activa (captura A/D) → Detener prueba.
 * Captura de teclado exclusivamente en JavaScript (addEventListener keydown).
 * Comunicación con backend Flask vía fetch.
 */

(function () {
  'use strict';

  const API_BASE = '';

  const ESTADOS_UI = {
    listo: 'Listo',
    ejecutando: 'Ejecutando',
    respuesta_registrada: 'Respuesta registrada',
    detenido: 'Prueba detenida'
  };

  const DEBOUNCE_MS = 400;

  const selectors = {
    nombre: document.getElementById('nombre'),
    errorNombre: document.getElementById('error-nombre'),
    instrucciones: document.getElementById('instrucciones'),
    respuestaFeedback: document.getElementById('respuesta-feedback'),
    estadoIndicator: document.getElementById('estado-indicator'),
    btnIniciar: document.getElementById('btn-iniciar'),
    btnDetener: document.getElementById('btn-detener')
  };

  let estadoBackend = 'listo';
  let tecladoBloqueado = false;
  let timeoutRespuestaRegistrada = null;

  /**
   * Actualiza el indicador visual de estado y las clases CSS.
   */
  function actualizarEstado(estado) {
    const el = selectors.estadoIndicator;
    if (!el) return;
    el.textContent = ESTADOS_UI[estado] || estado;
    el.className = 'estado-indicator estado-' + (estado === 'ejecutando' ? 'ejecutando' : estado === 'detenido' ? 'detenido' : estado === 'respuesta_registrada' ? 'respuesta-registrada' : 'listo');
  }

  /**
   * Muestra u oculta la zona de instrucciones (A/D) según si la prueba está activa.
   */
  function setInstruccionesVisible(visible) {
    if (selectors.instrucciones) {
      selectors.instrucciones.hidden = !visible;
    }
  }

  /**
   * Muestra confirmación visual "Respuesta registrada" durante un breve tiempo.
   */
  function mostrarRespuestaRegistrada() {
    if (timeoutRespuestaRegistrada) clearTimeout(timeoutRespuestaRegistrada);
    if (selectors.respuestaFeedback) {
      selectors.respuestaFeedback.textContent = 'Respuesta registrada';
      selectors.respuestaFeedback.hidden = false;
    }
    actualizarEstado('respuesta_registrada');
    timeoutRespuestaRegistrada = setTimeout(function () {
      if (estadoBackend === 'ejecutando') {
        actualizarEstado('ejecutando');
      }
      if (selectors.respuestaFeedback) {
        selectors.respuestaFeedback.hidden = true;
      }
      timeoutRespuestaRegistrada = null;
    }, 600);
  }

  function mostrarErrorNombre(mensaje) {
    const el = selectors.errorNombre;
    if (!el) return;
    el.textContent = mensaje || '';
    el.hidden = !mensaje;
  }

  /**
   * Sincroniza botones e instrucciones con el estado del backend.
   */
  function aplicarEstadoUI(estado) {
    estadoBackend = estado;
    actualizarEstado(estado);

    const activa = estado === 'ejecutando';
    if (selectors.btnIniciar) selectors.btnIniciar.disabled = activa;
    if (selectors.btnDetener) selectors.btnDetener.disabled = !activa;
    setInstruccionesVisible(activa);

    if (estado === 'detenido') {
      setInstruccionesVisible(false);
      if (selectors.respuestaFeedback) selectors.respuestaFeedback.hidden = true;
    }
  }

  /**
   * Consulta el estado actual al backend y actualiza la UI.
   */
  function refrescarEstado() {
    fetch(API_BASE + '/api/estado')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        aplicarEstadoUI(data.estado || 'listo');
      })
      .catch(function () {
        aplicarEstadoUI('listo');
      });
  }

  /**
   * Envía una respuesta (A = izquierda, D = derecha) al backend.
   * Evita dobles envíos con bloqueo temporal.
   */
  function enviarRespuesta(respuesta) {
    if (estadoBackend !== 'ejecutando' || tecladoBloqueado) return;

    tecladoBloqueado = true;
    var nombre = (selectors.nombre && selectors.nombre.value || '').trim();

    fetch(API_BASE + '/api/respuesta', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nombre: nombre,
        respuesta: respuesta,
        timestamp: new Date().toISOString()
      })
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (result) {
        if (result.ok) {
          mostrarRespuestaRegistrada();
        }
      })
      .catch(function () {})
      .finally(function () {
        setTimeout(function () { tecladoBloqueado = false; }, DEBOUNCE_MS);
      });
  }

  /**
   * Listener de teclado: solo A y D mientras la prueba está activa.
   */
  function onKeyDown(e) {
    if (estadoBackend !== 'ejecutando') return;
    if (e.repeat) return;

    var key = e.key.toUpperCase();
    if (key === 'A') {
      e.preventDefault();
      enviarRespuesta('left');
    } else if (key === 'D') {
      e.preventDefault();
      enviarRespuesta('right');
    }
  }

  function iniciarPrueba() {
    var nombre = (selectors.nombre && selectors.nombre.value || '').trim();
    mostrarErrorNombre('');

    if (!nombre) {
      mostrarErrorNombre('Ingrese el nombre del participante.');
      if (selectors.nombre) selectors.nombre.focus();
      return;
    }

    if (selectors.btnIniciar) selectors.btnIniciar.disabled = true;

    fetch(API_BASE + '/api/iniciar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nombre: nombre })
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, status: res.status, data: data }; }); })
      .then(function (result) {
        if (result.ok) {
          aplicarEstadoUI('ejecutando');
        } else {
          if (selectors.btnIniciar) selectors.btnIniciar.disabled = false;
          mostrarErrorNombre(result.data.error || 'No se pudo iniciar la prueba.');
        }
      })
      .catch(function () {
        if (selectors.btnIniciar) selectors.btnIniciar.disabled = false;
        mostrarErrorNombre('Error de conexión. Compruebe que el servidor esté en marcha.');
      });
  }

  function detenerPrueba() {
    if (selectors.btnDetener) selectors.btnDetener.disabled = true;

    fetch(API_BASE + '/api/detener', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        aplicarEstadoUI(data.estado || 'detenido');
      })
      .catch(function () {
        aplicarEstadoUI('detenido');
        if (selectors.btnDetener) selectors.btnDetener.disabled = false;
      });
  }

  // Eventos de botones
  if (selectors.btnIniciar) selectors.btnIniciar.addEventListener('click', iniciarPrueba);
  if (selectors.btnDetener) selectors.btnDetener.addEventListener('click', detenerPrueba);

  // Enter en el campo nombre inicia la prueba
  if (selectors.nombre) {
    selectors.nombre.addEventListener('input', function () { mostrarErrorNombre(''); });
    selectors.nombre.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') iniciarPrueba();
    });
  }

  // Captura de teclado global (solo A/D durante prueba activa)
  document.addEventListener('keydown', onKeyDown, false);

  refrescarEstado();
})();
