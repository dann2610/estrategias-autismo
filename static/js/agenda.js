// Creador de agendas visuales. Todo ocurre en el navegador: no se envían datos al servidor.
(function () {
  "use strict";
  var data = JSON.parse(document.getElementById("pictos").textContent);
  var byId = {}; data.forEach(function (p) { byId[p.id] = p; });
  var grid = document.getElementById("banco-grid");
  var list = document.getElementById("lista");
  var empty = document.getElementById("vacia");
  var title = document.getElementById("titulo-agenda");
  var status = document.getElementById("estado");
  var sheet = document.getElementById("hoja");
  var search = document.getElementById("buscar-picto");
  var MAX = 12;
  var steps = []; // {id, label}
  var currentCat = "";

  var TEMPLATES = {
    manana: ["Despertar", "Ir al baño", "Vestirse", "Desayunar", "Cepillarse los dientes", "Preparar la mochila", "Ir a la escuela"],
    noche: ["Comer", "Bañarse", "Cepillarse los dientes", "Leer un cuento", "Dormir"],
    escuela: ["Ir a la escuela", "Jugar", "Esperar", "Lavarse las manos", "Comer", "Volver a casa"]
  };

  function say(msg) { status.textContent = msg; }

  function renderBank() {
    var q = (search.value || "").trim().toLowerCase();
    grid.innerHTML = "";
    data.filter(function (p) {
      return (!currentCat || p.cat === currentCat) && (!q || p.label.toLowerCase().indexOf(q) !== -1);
    }).forEach(function (p) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "picto-card";
      b.setAttribute("aria-label", "Agregar " + p.label);
      var img = document.createElement("img"); img.src = p.src; img.alt = "";
      b.appendChild(img); b.appendChild(document.createTextNode(p.label));
      b.addEventListener("click", function () { add(p.id); });
      grid.appendChild(b);
    });
    if (!grid.children.length) { grid.innerHTML = "<p class='text-soft'>No hay pictogramas con esa búsqueda.</p>"; }
  }

  function save() {
    var state = { t: title.value, s: steps };
    try { localStorage.setItem("agenda-visual", JSON.stringify(state)); } catch (e) { /* almacenamiento no disponible */ }
  }

  function iconButton(icon, label, handler) {
    var b = document.createElement("button");
    b.type = "button"; b.setAttribute("aria-label", label); b.title = label;
    b.innerHTML = "<i class='bi bi-" + icon + "' aria-hidden='true'></i>";
    b.addEventListener("click", handler);
    return b;
  }

  function renderList() {
    list.innerHTML = "";
    steps.forEach(function (s, i) {
      var p = byId[s.id]; if (!p) { return; }
      var li = document.createElement("li");
      var img = document.createElement("img"); img.src = p.src; img.alt = "";
      var input = document.createElement("input");
      input.value = s.label; input.maxLength = 40;
      input.setAttribute("aria-label", "Texto del paso " + (i + 1));
      input.addEventListener("input", function () { s.label = input.value; save(); });
      var tools = document.createElement("span"); tools.className = "tools";
      tools.appendChild(iconButton("arrow-up", "Subir paso " + (i + 1), function () { move(i, -1); }));
      tools.appendChild(iconButton("arrow-down", "Bajar paso " + (i + 1), function () { move(i, 1); }));
      tools.appendChild(iconButton("x-lg", "Quitar paso " + (i + 1), function () { remove(i); }));
      li.appendChild(img); li.appendChild(input); li.appendChild(tools);
      list.appendChild(li);
    });
    empty.hidden = steps.length > 0;
    save();
  }

  function add(id) {
    if (steps.length >= MAX) { say("La agenda admite hasta " + MAX + " pasos."); return; }
    steps.push({ id: id, label: byId[id].label });
    renderList(); say("Agregado: " + byId[id].label + ". La agenda tiene " + steps.length + " pasos.");
  }
  function move(i, d) {
    var j = i + d; if (j < 0 || j >= steps.length) { return; }
    var t = steps[i]; steps[i] = steps[j]; steps[j] = t;
    renderList(); say("Paso movido a la posición " + (j + 1) + ".");
    var btn = list.children[j] && list.children[j].querySelectorAll("button")[d < 0 ? 0 : 1];
    if (btn) { btn.focus(); }
  }
  function remove(i) {
    var label = steps[i].label; steps.splice(i, 1);
    renderList(); say("Quitado: " + label + ".");
  }
  function loadTemplate(name) {
    steps = [];
    TEMPLATES[name].forEach(function (label) {
      var p = data.find(function (x) { return x.label.toLowerCase() === label.toLowerCase(); });
      if (p) { steps.push({ id: p.id, label: p.label }); }
    });
    var names = { manana: "Rutina de la mañana", noche: "Rutina de la noche", escuela: "Un día en la escuela" };
    title.value = names[name];
    renderList(); say("Plantilla cargada: " + names[name] + ".");
  }

  document.querySelectorAll("[data-cat]").forEach(function (b) {
    b.addEventListener("click", function () {
      currentCat = b.getAttribute("data-cat");
      document.querySelectorAll("[data-cat]").forEach(function (x) {
        x.classList.toggle("btn-area", x === b); x.classList.toggle("btn-soft", x !== b);
      });
      renderBank();
    });
  });
  document.querySelectorAll("[data-template]").forEach(function (b) {
    b.addEventListener("click", function () { loadTemplate(b.getAttribute("data-template")); });
  });
  search.addEventListener("input", renderBank);
  title.addEventListener("input", save);
  document.getElementById("imprimir").addEventListener("click", function () { window.print(); });
  document.getElementById("limpiar").addEventListener("click", function () { steps = []; renderList(); say("Agenda vacía."); });
  var orient = document.getElementById("orientacion");
  orient.addEventListener("click", function () {
    var h = sheet.classList.toggle("horizontal");
    orient.setAttribute("aria-pressed", h ? "true" : "false");
    orient.textContent = h ? "Ver en vertical" : "Ver en horizontal";
  });

  try {
    var saved = JSON.parse(localStorage.getItem("agenda-visual") || "null");
    if (saved && Array.isArray(saved.s)) {
      steps = saved.s.filter(function (s) { return byId[s.id]; });
      if (saved.t) { title.value = saved.t; }
    }
  } catch (e) { steps = []; }
  renderBank(); renderList();
})();
