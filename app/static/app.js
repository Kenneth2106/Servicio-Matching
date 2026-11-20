(function () {
  var config = window.STUDYMATCH_CONFIG || {};
  var form = document.getElementById('filters-form');
  var clearButton = document.getElementById('clear-filters');
  var modalityFilter = document.getElementById('modality-filter');
  var levelFilter = document.getElementById('level-filter');
  var matchList = document.getElementById('match-list');
  var feedback = document.getElementById('feedback');
  var resultCount = document.getElementById('result-count');
  var sessionStatus = document.getElementById('session-status');
  var sessionIndicator = document.getElementById('session-indicator');
  var submitButton = form.querySelector('button[type="submit"]');
  var token = null;
  var usuarioId = null;
  var currentRequest = null;

  function mostrarMensaje(texto, error) {
    feedback.textContent = texto;
    feedback.classList.toggle('is-error', Boolean(error));
    feedback.classList.remove('is-hidden');
  }

  function limpiarResultados() {
    matchList.replaceChildren();
    resultCount.textContent = '— resultados';
  }

  function crearElemento(tag, className, texto) {
    var elemento = document.createElement(tag);
    if (className) elemento.className = className;
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  function iniciales(nombre) {
    return nombre.split(/\s+/).filter(Boolean).slice(0, 2)
      .map(function (parte) { return parte.charAt(0); }).join('').toUpperCase() || 'SM';
  }

  function renderizarMatches(coincidencias) {
    matchList.replaceChildren();
    coincidencias.forEach(function (coincidencia) {
      var tarjeta = crearElemento('article', 'match-card');
      var parteSuperior = crearElemento('div', 'card-top');
      var persona = crearElemento('div', 'person');
      var avatar = crearElemento('span', 'avatar', iniciales(coincidencia.nombre_match));
      var datosPersona = crearElemento('div');
      var nombre = crearElemento('h3', '', coincidencia.nombre_match);
      var id = crearElemento('p', '', 'Estudiante · Match #' + coincidencia.match_id);
      var score = crearElemento('div', 'score', Number(coincidencia.porcentaje_match).toFixed(0) + '%');
      var scoreLabel = crearElemento('span', 'score-label', 'compatibilidad');
      var divider = crearElemento('div', 'card-divider');
      var skillRow = crearElemento('div', 'skill-row');
      var skillLabel = crearElemento('span', 'skill-label', 'Puede ayudarte con');
      var skillTag = crearElemento('span', 'skill-tag', coincidencia.habilidad);

      score.appendChild(scoreLabel);
      datosPersona.append(nombre, id);
      persona.append(avatar, datosPersona);
      parteSuperior.append(persona, score);
      skillRow.append(skillLabel, skillTag);
      tarjeta.append(parteSuperior, divider, skillRow);

      if (coincidencia.compatibilidad_parcial) {
        tarjeta.appendChild(crearElemento(
          'p', 'partial-note', 'Disponibilidad no evaluada temporalmente.'
        ));
      }
      matchList.appendChild(tarjeta);
    });
    resultCount.textContent = coincidencias.length + (coincidencias.length === 1
      ? ' resultado'
      : ' resultados');
  }

  function baseApi() {
    var base = typeof config.matchingApiBase === 'string'
      ? config.matchingApiBase.trim().replace(/\/+$/, '')
      : '';
    if (!base) return null;
    return base;
  }

  async function cargarMatches() {
    if (!token || !usuarioId) {
      limpiarResultados();
      mostrarMensaje('Esperando una sesión válida del sistema.');
      return;
    }

    var apiBase = baseApi();
    if (!apiBase) {
      limpiarResultados();
      mostrarMensaje(
        'Falta configurar STUDYMATCH_MATCHING_API_BASE con la ruta del Matching en el API Gateway.',
        true
      );
      return;
    }

    if (currentRequest) currentRequest.abort();
    currentRequest = new AbortController();
    var controller = currentRequest;
    var url = new URL(apiBase + '/' + encodeURIComponent(usuarioId), window.location.href);
    if (modalityFilter.value) url.searchParams.set('modalidad', modalityFilter.value);
    if (levelFilter.value) url.searchParams.set('nivel_minimo', levelFilter.value);

    submitButton.disabled = true;
    limpiarResultados();
    mostrarMensaje('Buscando estudiantes compatibles...');

    try {
      var respuesta = await fetch(url.toString(), {
        method: 'GET',
        headers: { Authorization: 'Bearer ' + token },
        signal: controller.signal
      });

      if (controller !== currentRequest) return;
      if (respuesta.status === 401) {
        window.StudyMatch.sesionInvalida();
        token = null;
        usuarioId = null;
        limpiarResultados();
        mostrarMensaje('La sesión venció. Volviendo al sistema para iniciar sesión.', true);
        sessionStatus.textContent = 'Sesión inválida';
        sessionIndicator.classList.remove('is-ready');
        return;
      }

      var datos = await respuesta.json();
      if (respuesta.status === 404 && datos.error === 'sin_coincidencias') {
        renderizarMatches([]);
        mostrarMensaje('No encontramos matches con estos filtros. Prueba otra combinación.');
        return;
      }
      if (!respuesta.ok) {
        throw new Error(datos.detalle || datos.error || 'No se pudieron cargar las coincidencias.');
      }

      var coincidencias = Array.isArray(datos.coincidencias) ? datos.coincidencias : [];
      if (controller !== currentRequest) return;
      renderizarMatches(coincidencias);
      if (coincidencias.length) {
        feedback.classList.add('is-hidden');
      } else {
        mostrarMensaje('No encontramos matches con estos filtros. Prueba otra combinación.');
      }
    } catch (error) {
      if (error.name === 'AbortError') return;
      limpiarResultados();
      mostrarMensaje(
        error instanceof TypeError
          ? 'No fue posible conectar con el API Gateway. Revisa la URL y su configuración CORS.'
          : error.message,
        true
      );
    } finally {
      if (controller === currentRequest) {
        currentRequest = null;
        submitButton.disabled = false;
      }
    }
  }

  form.addEventListener('submit', function (evento) {
    evento.preventDefault();
    cargarMatches();
  });

  clearButton.addEventListener('click', function () {
    modalityFilter.value = '';
    levelFilter.value = '';
    if (token && usuarioId) cargarMatches();
  });

  window.addEventListener('studymatch:sesion', function () {
    token = window.StudyMatch.token();
    usuarioId = window.StudyMatch.usuarioId();
    sessionIndicator.classList.toggle('is-ready', Boolean(token && usuarioId));
    sessionStatus.textContent = token && usuarioId
      ? 'Sesión conectada'
      : 'Sesión recibida, pero incompleta';
    if (token && usuarioId) {
      cargarMatches();
    } else {
      limpiarResultados();
      mostrarMensaje('No se recibió un token o usuario_id válido. Revisa el mensaje SESION.', true);
    }
  });

  window.addEventListener('studymatch:cerrar', function () {
    if (currentRequest) currentRequest.abort();
    currentRequest = null;
    token = null;
    usuarioId = null;
    limpiarResultados();
    mostrarMensaje('Sesión cerrada. Tus coincidencias se limpiaron.');
    sessionStatus.textContent = 'Sesión cerrada';
    sessionIndicator.classList.remove('is-ready');
  });
})();
