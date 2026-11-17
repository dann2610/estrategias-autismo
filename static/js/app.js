// Comportamientos mínimos. No hay scripts en línea por la política de seguridad de contenido.
(function () {
  "use strict";
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) { e.preventDefault(); }
    });
  });
  document.querySelectorAll("form.filters select").forEach(function (sel) {
    sel.addEventListener("change", function () { sel.form.submit(); });
  });
  document.querySelectorAll("[data-print]").forEach(function (btn) {
    btn.addEventListener("click", function () { window.print(); });
  });
})();

// Carrusel de la portada: botón de pausa y respeto a «reducir movimiento».
(function () {
  "use strict";
  var el = document.getElementById("carruselInicio");
  if (!el || !window.bootstrap) { return; }
  var carousel = bootstrap.Carousel.getOrCreateInstance(el);
  var btn = el.querySelector("[data-carousel-toggle]");
  var paused = false;
  function setPaused(p) {
    paused = p;
    if (p) { carousel.pause(); } else { carousel.cycle(); }
    if (btn) {
      btn.setAttribute("aria-pressed", p ? "true" : "false");
      btn.querySelector("i").className = p ? "bi bi-play-fill" : "bi bi-pause-fill";
      btn.querySelector(".visually-hidden").textContent = p ? "Reanudar el carrusel" : "Pausar el carrusel";
    }
  }
  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setPaused(true); }
  if (btn) { btn.addEventListener("click", function () { setPaused(!paused); }); }
  el.addEventListener("mouseleave", function () { if (paused) { carousel.pause(); } });
})();
