/* studymatch-integracion.js — protocolo StudyMatch v1. */
(function () {
  var config = window.STUDYMATCH_CONFIG || {};
  var ORIGEN_STUDYMATCH = config.frontendOrigin || 'http://localhost:4200';
  var token = null;
  var usuarioId = null;
  var parametros = {};
  var ultimo = 0;

  function enviar(tipo, extra) {
    if (window.parent === window) return;
    var mensaje = { app: 'studymatch', v: 1, tipo: tipo };
    for (var clave in (extra || {})) {
      if (Object.prototype.hasOwnProperty.call(extra, clave)) {
        mensaje[clave] = extra[clave];
      }
    }
    window.parent.postMessage(mensaje, ORIGEN_STUDYMATCH);
  }

  window.addEventListener('message', function (evento) {
    if (evento.origin !== ORIGEN_STUDYMATCH || evento.source !== window.parent) return;
    var mensaje = evento.data;
    if (!mensaje || mensaje.app !== 'studymatch' || mensaje.v !== 1) return;

    if (mensaje.tipo === 'SESION') {
      token = typeof mensaje.token === 'string' && mensaje.token ? mensaje.token : null;
      usuarioId = Number.isSafeInteger(mensaje.usuario_id) && mensaje.usuario_id > 0
        ? mensaje.usuario_id
        : null;
      parametros = mensaje.parametros && typeof mensaje.parametros === 'object'
        && !Array.isArray(mensaje.parametros)
        ? mensaje.parametros
        : {};
      window.dispatchEvent(new CustomEvent('studymatch:sesion', { detail: mensaje }));
    }

    if (mensaje.tipo === 'CERRAR_SESION') {
      token = null;
      usuarioId = null;
      parametros = {};
      window.dispatchEvent(new Event('studymatch:cerrar'));
    }
  });

  ['pointerdown', 'pointermove', 'keydown', 'scroll', 'touchstart'].forEach(function (nombre) {
    window.addEventListener(nombre, function () {
      var ahora = Date.now();
      if (token && ahora - ultimo > 5000) {
        ultimo = ahora;
        enviar('ACTIVIDAD');
      }
    }, { passive: true, capture: true });
  });

  window.StudyMatch = {
    token: function () { return token; },
    usuarioId: function () { return usuarioId; },
    parametros: function () { return JSON.parse(JSON.stringify(parametros)); },
    sesionInvalida: function () { enviar('SESION_INVALIDA'); }
  };

  enviar('LISTO');
})();
