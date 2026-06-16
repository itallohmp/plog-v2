const API_PREFIX = "/api";
let currentPage = 1;
let currentTotalPages = 1;
let currentController = null;

document.addEventListener("DOMContentLoaded", function () {
  setDefaultDate();
  renderPagination(1, 1);

  const form = document.getElementById("filterForm");
  const btn = document.getElementById("btnBuscar");

  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      buscarLogs(1);
    });
  } else if (btn) {
    btn.addEventListener("click", () => buscarLogs(1));
  }
});

function setDefaultDate() {
  const day = document.getElementById("day");
  if (day && !day.value) {
    day.value = new Date().toISOString().slice(0, 10);
  }
}

function buildUrl(page = 1) {
  const pageSize = document.getElementById("pageSize")?.value || "100";
  const ip = document.getElementById("ip")?.value.trim() || "";
  const porta = document.getElementById("porta")?.value.trim() || "";
  const day = document.getElementById("day")?.value || "";
  const horaDe = document.getElementById("horaDe")?.value.trim() || "";
  const horaAte = document.getElementById("horaAte")?.value.trim() || "";

  if (!day) {
    throw new Error("Selecione uma data para buscar.");
  }

  const params = new URLSearchParams();
  params.set("data", day);
  params.set("pagina", String(page));
  params.set("tamanho_pagina", String(pageSize));

  if (ip) params.set("ip", ip);
  if (porta) params.set("porta", porta);
  if (horaDe) params.set("hora_de", horaDe);
  if (horaAte) params.set("hora_ate", horaAte);

  return `${API_PREFIX}/flows?${params.toString()}`;
}

function clearTable() {
  const tbody = document.querySelector("#tabelaLogs tbody");
  if (tbody) tbody.innerHTML = "";
}

function appendRow(obj) {
  const tbody = document.querySelector("#tabelaLogs tbody");
  if (!tbody) return;

  const data = obj.data || "-";
  const evento = obj.evento || "-";
  const protocolo = obj.protocolo || "-";
  const origem = obj.origem || "-";
  const nat = obj.nat || "-";
  const blocoPortas = obj.bloco_portas || obj.porta_origem || obj.porta_destino || "-";
  const destino = obj.destino || "-";
  const roteador = obj.roteador || obj.destino_final || "-";

  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${escapeHtml(data)}</td>
    <td>${escapeHtml(evento)}</td>
    <td>${escapeHtml(protocolo)}</td>
    <td>${escapeHtml(origem)}</td>
    <td>${escapeHtml(nat)}</td>
    <td>${escapeHtml(blocoPortas)}</td>
    <td>${escapeHtml(destino)}</td>
    <td>${escapeHtml(roteador)}</td>
  `;
  tbody.appendChild(tr);
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderPagination(page, totalPages) {
  currentPage = page;
  currentTotalPages = totalPages || 1;

  const pagination = document.getElementById("pagination");
  if (!pagination) return;

  const prevDisabled = page <= 1 ? "disabled" : "";
  const nextDisabled = page >= currentTotalPages ? "disabled" : "";

  pagination.innerHTML = `
    <span>Página ${page} de ${currentTotalPages}</span>
    <button id="btnPrev" type="button" ${prevDisabled}>Anterior</button>
    <button id="btnNext" type="button" ${nextDisabled}>Próxima</button>
  `;

  const btnPrev = document.getElementById("btnPrev");
  const btnNext = document.getElementById("btnNext");

  if (btnPrev) {
    btnPrev.addEventListener("click", () => {
      if (page > 1) buscarLogs(page - 1);
    });
  }

  if (btnNext) {
    btnNext.addEventListener("click", () => {
      if (page < currentTotalPages) buscarLogs(page + 1);
    });
  }
}

async function buscarLogs(page = 1) {
  if (currentController) {
    currentController.abort();
    currentController = null;
  }

  clearTable();

  const summaryEl = document.getElementById("resultSummary");
  const btn = document.getElementById("btnBuscar");
  setStatus("Carregando...", "loading");
  if (summaryEl) summaryEl.textContent = "Buscando flows no servidor...";
  if (btn) btn.disabled = true;

  let url;
  try {
    url = buildUrl(page);
  } catch (err) {
    setStatus(err.message, "error");
    if (summaryEl) summaryEl.textContent = "Ajuste os filtros e tente novamente.";
    renderEmptyRow(err.message);
    if (btn) btn.disabled = false;
    return;
  }

  currentController = new AbortController();
  const signal = currentController.signal;

  try {
    const resp = await fetch(url, {
      signal,
      headers: { Accept: "application/json" },
    });

    const text = await resp.text();
    let payload = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch (e) {
      console.warn("Resposta não-JSON:", e, text);
    }

    if (!resp.ok) {
      const message = formatError(payload, resp.status);
      setStatus(message, "error");
      renderEmptyRow(message);
      if (summaryEl) summaryEl.textContent = "Não foi possível carregar os flows.";
      return;
    }

    const registros = Array.isArray(payload?.registros) ? payload.registros : [];
    for (const obj of registros) {
      appendRow(obj);
    }

    const total = payload?.total ?? registros.length;
    const totalPaginas = payload?.total_paginas ?? 1;
    renderPagination(page, totalPaginas);

    if (registros.length === 0) {
      renderEmptyRow("Nenhum flow encontrado para os filtros informados.");
      setStatus("Nenhum resultado", "empty");
      if (summaryEl) summaryEl.textContent = "Tente outra data, IP, porta ou hora.";
    } else {
      setStatus(`${registros.length} flows nesta página`, "success");
      if (summaryEl) {
        summaryEl.textContent = `Mostrando ${registros.length} de ${total} resultado(s) — página ${page} de ${totalPaginas}.`;
      }
    }
  } catch (err) {
    if (err.name === "AbortError") {
      setStatus("Busca cancelada.", "empty");
    } else {
      setStatus("Erro ao buscar flows.", "error");
      renderEmptyRow("Erro ao buscar flows.");
      console.error("Erro no fetch:", err);
    }
  } finally {
    currentController = null;
    if (btn) btn.disabled = false;
  }
}

function formatError(payload, status) {
  if (payload && payload.erro) {
    if (payload.detalhes && typeof payload.detalhes === "string") {
      return `${payload.erro}: ${payload.detalhes}`;
    }
    return payload.erro;
  }
  return `Erro ${status}`;
}

function renderEmptyRow(message) {
  const tbody = document.querySelector("#tabelaLogs tbody");
  if (!tbody) return;
  tbody.innerHTML = `
    <tr class="empty_row">
      <td colspan="8">${escapeHtml(message)}</td>
    </tr>
  `;
}

function setStatus(message, state = "default") {
  const statusEl = document.getElementById("status");
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.dataset.state = state;
}
