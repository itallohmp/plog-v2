const API_PREFIX = "/api";
let currentPage = 1;
let currentTotalPages = 1;
let currentController = null;

document.addEventListener("DOMContentLoaded", function () {
  setDefaultDate();
  renderPagination(1, 1);
  const btn = document.getElementById("btnBuscar");
  const form = document.getElementById("filterForm");

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

  if (!ip && !porta) {
    throw new Error("Informe um IP ou uma porta para buscar.");
  }

  const params = new URLSearchParams();
  params.set("pagina", String(page));
  params.set("tamanho_pagina", String(pageSize));

  if (ip) params.set("ip", ip);
  if (porta) params.set("porta", porta);

  if (day) {
    const [year, month, dayPart] = day.split("-");
    if (year) params.set("ano", year);
    if (month) params.set("mes", month.padStart(2, "0"));
    if (dayPart) params.set("dia", dayPart.padStart(2, "0"));
  }

  return `${API_PREFIX}/logs/filter?${params.toString()}`;
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
  const nextDisabled = page >= totalPages ? "disabled" : "";

  pagination.innerHTML = `
    <span>Página ${page} de ${totalPages || 1}</span>
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
      if (page < totalPages) buscarLogs(page + 1);
    });
  }
}

async function buscarLogs(page = 1) {
  if (currentController) {
    currentController.abort();
    currentController = null;
  }

  clearTable();

  const statusEl = document.getElementById("status");
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

  console.log("URL chamada:", url);

  currentController = new AbortController();
  const signal = currentController.signal;

  try {
    const resp = await fetch(url, {
      signal,
      headers: {
        "Accept": "application/x-ndjson"
      }
    });

    if (!resp.ok) {
      const text = await resp.text();
      console.error("Resposta não OK:", resp.status, text);

      let message = `Erro ${resp.status}`;

      try {
        const json = JSON.parse(text);
        if (json.erro) {
          message = json.detalhes ? `${json.erro}: ${json.detalhes}` : json.erro;
        }
      } catch {
      }

      setStatus(message, "error");
      renderEmptyRow(message);
      if (summaryEl) summaryEl.textContent = "Não foi possível carregar os flows.";
      return;
    }

    if (!resp.body) {
      setStatus("Resposta sem corpo.", "error");
      renderEmptyRow("Resposta sem corpo.");
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let receivedCount = 0;

    const pageSize = parseInt(document.getElementById("pageSize")?.value || "100", 10);
    let totalPagesGuess = page;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        try {
          const obj = JSON.parse(trimmed);
          appendRow(obj);
          receivedCount++;
          if (receivedCount % 25 === 0) {
            setStatus(`${receivedCount} flows recebidos...`, "loading");
          }
        } catch (e) {
          console.warn("Erro ao parsear linha NDJSON:", e, trimmed);
        }
      }
    }

    // processa sobra final do buffer
    if (buffer.trim()) {
      try {
        const obj = JSON.parse(buffer.trim());
        appendRow(obj);
        receivedCount++;
      } catch (e) {
        console.warn("Erro ao parsear buffer final:", e, buffer);
      }
    }

    if (receivedCount < pageSize) {
      totalPagesGuess = page;
    } else {
      totalPagesGuess = page + 1;
    }

    renderPagination(page, totalPagesGuess);

    if (receivedCount === 0) {
      renderEmptyRow("Nenhum flow encontrado para os filtros informados.");
      setStatus("Nenhum resultado", "empty");
      if (summaryEl) summaryEl.textContent = "Tente outro IP, porta ou data.";
    } else {
      setStatus(`${receivedCount} flows recebidos`, "success");
      if (summaryEl) {
        summaryEl.textContent = `Mostrando ${receivedCount} resultado(s) da página ${page}.`;
      }
    }
  } catch (err) {
    if (err.name === "AbortError") {
      setStatus("Busca cancelada.", "empty");
      console.log("Fetch abortado.");
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