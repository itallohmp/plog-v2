const API_PREFIX = "/api";
const TOKEN_KEY = "plog_access_token";
const REFRESH_KEY = "plog_refresh_token";
const ADMIN_KEY = "plog_user_admin";

let currentPage = 1;
let currentTotalPages = 1;
let currentController = null;

const THEME_KEY = "plog_theme";

// Aplica o tema (dark = preto neutro) marcando o <html>. O CSS reage a
// [data-theme="dark"]. Um script inline no <head> de cada página já aplica o
// tema salvo antes da 1a pintura (sem flash); aqui só tratamos a troca.
function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "dark") root.setAttribute("data-theme", "dark");
  else root.removeAttribute("data-theme");
}

function initThemeToggle() {
  const btn = document.getElementById("themeToggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const dark =
      document.documentElement.getAttribute("data-theme") === "dark";
    const proximo = dark ? "light" : "dark";
    try {
      localStorage.setItem(THEME_KEY, proximo);
    } catch (e) {
      /* localStorage indisponível: aplica só nesta navegação */
    }
    applyTheme(proximo);
    btn.setAttribute("aria-pressed", String(proximo === "dark"));
  });
  btn.setAttribute(
    "aria-pressed",
    String(document.documentElement.getAttribute("data-theme") === "dark")
  );
}

document.addEventListener("DOMContentLoaded", function () {
  // Toggle de tema roda em qualquer página que tenha o botão (home, consulta).
  initThemeToggle();

  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    initLoginPage();
    return;
  }

  const filterForm = document.getElementById("filterForm");
  if (filterForm) {
    if (!requireAuth()) return;
    initPlogPage();
  }
});

function initPlogPage() {
  initLogoutButtons();
  loadAdminNav();
  setDefaultDate();
  renderPagination(1, 1);

  const filterForm = document.getElementById("filterForm");
  filterForm.addEventListener("submit", (event) => {
    event.preventDefault();
    buscarLogs(1);
  });

  document.getElementById("btnExport")?.addEventListener("click", exportarCSV);

  // Selo de "Mais filtros": mostra quantos protocolos/estados estão marcados,
  // para que filtros ativos sejam visíveis mesmo com a seção recolhida.
  document
    .querySelectorAll('input[name="protocolo"], input[name="status"]')
    .forEach((cb) => cb.addEventListener("change", atualizarSeloMaisFiltros));
  atualizarSeloMaisFiltros();
}

function atualizarSeloMaisFiltros() {
  const badge = document.getElementById("moreFiltersCount");
  if (!badge) return;
  const n = document.querySelectorAll(
    'input[name="protocolo"]:checked, input[name="status"]:checked'
  ).length;
  if (n > 0) {
    badge.textContent = `${n} ativo${n > 1 ? "s" : ""}`;
    badge.hidden = false;
  } else {
    badge.hidden = true;
  }
}

async function loadAdminNav() {
  const navItem = document.getElementById("adminNavItem");
  if (!navItem) return;

  try {
    const resp = await fetchWithAuth(`${API_PREFIX}/auth/me`);
    const user = await parseJsonResponse(resp);

    if (!resp.ok) return;

    setUserAdmin(Boolean(user?.admin));
    navItem.hidden = !user?.admin;
  } catch (err) {
    console.error("Erro ao verificar perfil:", err);
  }
}

function setUserAdmin(isAdmin) {
  localStorage.setItem(ADMIN_KEY, isAdmin ? "1" : "0");
}

function isUserAdmin() {
  return localStorage.getItem(ADMIN_KEY) === "1";
}

function initLogoutButtons() {
  document.querySelectorAll("[data-logout]").forEach((button) => {
    button.addEventListener("click", handleLogout);
  });
}

async function handleLogout(event) {
  event.preventDefault();

  const button = event.currentTarget;
  if (button) button.disabled = true;

  try {
    const token = getAccessToken();
    if (token) {
      await fetch(`${API_PREFIX}/auth/logout`, {
        method: "POST",
        headers: authHeaders(),
      });
    }
  } catch (err) {
    console.error("Erro no logout:", err);
  } finally {
    clearTokens();
    window.location.href = "/index.html";
  }
}

function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

function setTokens(accessToken, refreshToken) {
  localStorage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_KEY, refreshToken);
  }
}

function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(ADMIN_KEY);
}

function authHeaders(extra = {}) {
  const headers = { Accept: "application/json", ...extra };
  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

function requireAuth() {
  if (!getAccessToken()) {
    window.location.href = "/login.html";
    return false;
  }
  return true;
}

function initLoginPage() {
  if (getAccessToken()) {
    window.location.href = "/plog.html";
    return;
  }

  const form = document.getElementById("loginForm");
  const togglePassword = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("password");

  if (togglePassword && passwordInput) {
    togglePassword.addEventListener("click", () => {
      const isHidden = passwordInput.type === "password";
      passwordInput.type = isHidden ? "text" : "password";
      togglePassword.textContent = isHidden ? "Ocultar" : "Mostrar";
      togglePassword.setAttribute("aria-pressed", String(isHidden));
      togglePassword.setAttribute("aria-label", isHidden ? "Ocultar senha" : "Mostrar senha");
    });
  }

  form.addEventListener("submit", handleLogin);
}

function showLoginMessage(message, state = "error") {
  const messageEl = document.getElementById("loginMessage");
  if (!messageEl) return;

  messageEl.hidden = false;
  messageEl.textContent = message;
  messageEl.dataset.state = state;
}

function hideLoginMessage() {
  const messageEl = document.getElementById("loginMessage");
  if (!messageEl) return;
  messageEl.hidden = true;
  messageEl.textContent = "";
  delete messageEl.dataset.state;
}

async function handleLogin(event) {
  event.preventDefault();
  hideLoginMessage();

  const username = document.getElementById("username")?.value.trim();
  const password = document.getElementById("password")?.value || "";
  const submitBtn = document.getElementById("btnLogin");

  if (!username || !password) {
    showLoginMessage("Informe usuário e senha.");
    return;
  }

  if (submitBtn) submitBtn.disabled = true;

  try {
    const resp = await fetch(`${API_PREFIX}/auth/login`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, senha: password }),
    });

    const payload = await parseJsonResponse(resp);

    if (!resp.ok) {
      const detail = extractErrorDetail(payload);
      showLoginMessage(detail || "Não foi possível entrar. Tente novamente.");
      return;
    }

    setTokens(payload.access_token, payload.refresh_token);
    setUserAdmin(Boolean(payload.admin));
    window.location.href = "/plog.html";
  } catch (err) {
    console.error("Erro no login:", err);
    showLoginMessage("Erro de conexão com o servidor.");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

async function refreshAccessToken() {
  const token = getRefreshToken();
  if (!token) return false;

  try {
    const resp = await fetch(`${API_PREFIX}/auth/refresh`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!resp.ok) return false;

    const payload = await parseJsonResponse(resp);
    if (!payload?.access_token) return false;

    setTokens(payload.access_token, payload.refresh_token);
    setUserAdmin(Boolean(payload.admin));
    return true;
  } catch (err) {
    console.error("Erro ao renovar token:", err);
    return false;
  }
}

async function fetchWithAuth(url, options = {}) {
  const requestOptions = {
    ...options,
    headers: authHeaders(options.headers || {}),
  };

  let resp = await fetch(url, requestOptions);

  if (resp.status !== 401) {
    return resp;
  }

  const refreshed = await refreshAccessToken();
  if (!refreshed) {
    clearTokens();
    window.location.href = "/login.html";
    return resp;
  }

  return fetch(url, {
    ...options,
    headers: authHeaders(options.headers || {}),
  });
}

async function parseJsonResponse(resp) {
  const text = await resp.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (err) {
    console.warn("Resposta não-JSON:", err, text);
    return null;
  }
}

function extractErrorDetail(payload) {
  if (!payload) return null;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
    return payload.detail[0].msg;
  }
  if (payload.erro) return payload.erro;
  return null;
}

function setDefaultDate() {
  const day = document.getElementById("day");
  if (day && !day.value) {
    day.value = new Date().toISOString().slice(0, 10);
  }
}

function getSelectedProtocols() {
  return Array.from(
    document.querySelectorAll('input[name="protocolo"]:checked'),
    (checkbox) => checkbox.value
  );
}

function getSelectedStatus() {
  return Array.from(
    document.querySelectorAll('input[name="status"]:checked'),
    (checkbox) => checkbox.value
  );
}

function buildUrl(page = 1, pageSizeOverride) {
  const pageSize =
    pageSizeOverride || document.getElementById("pageSize")?.value || "100";
  const ip = document.getElementById("ip")?.value.trim() || "";
  const porta = document.getElementById("porta")?.value.trim() || "";
  const day = document.getElementById("day")?.value || "";
  const dayEnd = document.getElementById("dayEnd")?.value || "";
  const protocolos = getSelectedProtocols();
  const estados = getSelectedStatus();
  const horaDe = document.getElementById("horaDe")?.value.trim() || "";
  const horaAte = document.getElementById("horaAte")?.value.trim() || "";

  if (!day) {
    throw new Error("Selecione uma data para buscar.");
  }

  if (dayEnd && dayEnd < day) {
    throw new Error("A data final deve ser maior ou igual à data inicial.");
  }

  const params = new URLSearchParams();
  params.set("data", day);
  params.set("pagina", String(page));
  params.set("tamanho_pagina", String(pageSize));

  if (dayEnd && dayEnd !== day) params.set("data_fim", dayEnd);
  // Um parametro "protocolo" por protocolo marcado; nenhum marcado = todos.
  for (const protocolo of protocolos) params.append("protocolo", protocolo);
  // Idem para o estado da sessao (aberta/fechada).
  for (const estado of estados) params.append("status", estado);
  if (ip) params.set("ip", ip);
  if (porta) params.set("porta", porta);
  if (horaDe) params.set("hora_de", horaDe);
  if (horaAte) params.set("hora_ate", horaAte);

  return `${API_PREFIX}/flows?${params.toString()}`;
}

// Descreve os filtros ativos para carimbar o arquivo exportado (auditoria).
function descreverFiltros() {
  const g = (id) => document.getElementById(id)?.value?.trim() || "";
  const partes = [`data=${g("day")}`];
  if (g("dayEnd")) partes.push(`data_fim=${g("dayEnd")}`);
  if (g("ip")) partes.push(`ip=${g("ip")}`);
  if (g("porta")) partes.push(`porta=${g("porta")}`);
  const protos = getSelectedProtocols();
  if (protos.length) partes.push(`protocolo=${protos.join("+")}`);
  const estados = getSelectedStatus();
  if (estados.length) partes.push(`estado=${estados.join("+")}`);
  if (g("horaDe")) partes.push(`hora_de=${g("horaDe")}`);
  if (g("horaAte")) partes.push(`hora_ate=${g("horaAte")}`);
  return partes.join("; ");
}

function csvCell(valor) {
  const s = valor === null || valor === undefined ? "" : String(valor);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function montarCsv(registros, meta) {
  const linhas = [
    "# PLog — Exportacao de sessoes NAT",
    `# Gerado em: ${new Date().toISOString()}`,
    `# Filtros: ${descreverFiltros()}`,
    `# Total exportado: ${registros.length}${
      meta.truncado ? ` (TRUNCADO no limite de ${meta.paginasLidas} paginas)` : ""
    }`,
    "",
  ];
  const cols = [
    "Status", "Abertura", "Fechamento", "Duracao",
    "Protocolo", "Origem", "NAT", "Bloco Portas", "Roteador",
  ];
  linhas.push(cols.map(csvCell).join(","));
  for (const r of registros) {
    linhas.push(
      [
        r.status, r.abertura || r.data, r.fechamento, r.duracao,
        r.protocolo, r.origem, r.nat, r.bloco_portas, r.roteador,
      ].map(csvCell).join(",")
    );
  }
  return linhas.join("\r\n");
}

function baixarCsv(csv) {
  // BOM para o Excel reconhecer UTF-8.
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const a = document.createElement("a");
  a.href = url;
  a.download = `plog-flows-${stamp}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// Exporta TODAS as sessoes dos filtros atuais (nao so a pagina visivel),
// paginando a API, com carimbo de filtros + timestamp para uso auditavel.
async function exportarCSV() {
  if (!requireAuth()) return;

  const btn = document.getElementById("btnExport");
  const summaryEl = document.getElementById("resultSummary");

  try {
    buildUrl(1, 1000); // valida os filtros (lanca se data ausente/invalida)
  } catch (err) {
    setStatus(err.message, "error");
    if (summaryEl) summaryEl.textContent = err.message;
    return;
  }

  const rotuloOriginal = btn ? btn.textContent : "";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Exportando…";
  }
  setStatus("Exportando…", "loading");

  const MAX_PAGINAS = 100; // teto de seguranca (~100k linhas)
  const todas = [];
  let pagina = 1;
  let totalPaginas = 1;

  try {
    do {
      const resp = await fetchWithAuth(buildUrl(pagina, 1000));
      const payload = await parseJsonResponse(resp);
      if (!resp.ok) {
        throw new Error(formatError(payload, resp.status));
      }
      const regs = Array.isArray(payload?.registros) ? payload.registros : [];
      todas.push(...regs);
      totalPaginas = payload?.total_paginas ?? 1;
      pagina += 1;
    } while (pagina <= totalPaginas && pagina <= MAX_PAGINAS);

    const truncado = totalPaginas > MAX_PAGINAS;
    baixarCsv(montarCsv(todas, { truncado, paginasLidas: MAX_PAGINAS }));
    setStatus(`${todas.length} sessões exportadas`, "success");
    if (summaryEl) {
      summaryEl.textContent = `Exportadas ${todas.length} sessões${
        truncado ? " (truncado no limite de segurança)" : ""
      }.`;
    }
  } catch (err) {
    setStatus("Erro ao exportar.", "error");
    if (summaryEl) summaryEl.textContent = `Falha na exportação: ${err.message}`;
    console.error("Erro na exportação:", err);
  } finally {
    if (btn) {
      btn.textContent = rotuloOriginal;
      btn.disabled = todas.length === 0;
    }
  }
}

function clearTable() {
  const tbody = document.querySelector("#tabelaLogs tbody");
  if (tbody) tbody.innerHTML = "";
}

const STATUS_ROTULO = {
  aberta: "Aberta",
  fechada: "Fechada",
  indefinida: "Indefinida",
};

function formatTimestamp(valor) {
  if (!valor) return "-";
  // ISO "2026-07-15T18:48:41.045" -> "2026-07-15 18:48:41"
  return String(valor).replace("T", " ").slice(0, 19);
}

function statusBadge(obj) {
  const status = obj.status || "indefinida";
  const rotulo = STATUS_ROTULO[status] || status;
  let titulo = "";
  if (status === "aberta" && obj.verificado_ate) {
    titulo = `Sem fechamento até ${obj.verificado_ate}`;
  } else if (status === "fechada" && obj.parcial) {
    titulo = "Abertura anterior ao período consultado";
  }
  const marca = obj.parcial ? " session_badge--parcial" : "";
  const attrTitulo = titulo ? ` title="${escapeHtml(titulo)}"` : "";
  return `<span class="session_badge${marca}" data-state="${escapeHtml(status)}"${attrTitulo}>${escapeHtml(rotulo)}</span>`;
}

function appendRow(obj) {
  const tbody = document.querySelector("#tabelaLogs tbody");
  if (!tbody) return;

  const abertura = formatTimestamp(obj.abertura || obj.data);
  const fechamento = formatTimestamp(obj.fechamento);
  const duracao = obj.duracao || "-";
  const protocolo = obj.protocolo || "-";
  const origem = obj.origem || "-";
  const nat = obj.nat || "-";
  const blocoPortas = obj.bloco_portas || obj.porta_origem || obj.porta_destino || "-";
  const roteador = obj.roteador || obj.destino_final || "-";

  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${statusBadge(obj)}</td>
    <td>${escapeHtml(abertura)}</td>
    <td>${escapeHtml(fechamento)}</td>
    <td>${escapeHtml(duracao)}</td>
    <td>${escapeHtml(protocolo)}</td>
    <td>${escapeHtml(origem)}</td>
    <td>${escapeHtml(nat)}</td>
    <td>${escapeHtml(blocoPortas)}</td>
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
  if (!requireAuth()) return;

  if (currentController) {
    currentController.abort();
    currentController = null;
  }

  clearTable();
  resetPanorama();
  resetAnomalias();

  const summaryEl = document.getElementById("resultSummary");
  const btn = document.getElementById("btnBuscar");
  setStatus("Carregando...", "loading");
  if (summaryEl) summaryEl.textContent = "Buscando flows no servidor...";
  if (btn) btn.disabled = true;
  const btnExport = document.getElementById("btnExport");
  if (btnExport) btnExport.disabled = true;

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
    const resp = await fetchWithAuth(url, { signal });
    const payload = await parseJsonResponse(resp);

    if (resp.status === 401) {
      setStatus("Sessão expirada. Redirecionando...", "error");
      renderEmptyRow("Faça login novamente para continuar.");
      return;
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

    // Exportar só faz sentido quando há resultados.
    const btnExport = document.getElementById("btnExport");
    if (btnExport) btnExport.disabled = registros.length === 0;

    if (registros.length === 0) {
      renderEmptyRow("Nenhum flow encontrado para os filtros informados.");
      setStatus("Nenhum resultado", "empty");
      if (summaryEl) summaryEl.textContent = "Tente outra data, IP, porta ou hora.";
      resetPanorama();
      resetAnomalias();
    } else {
      setStatus(`${registros.length} flows nesta página`, "success");
      if (summaryEl) {
        summaryEl.textContent = `Mostrando ${registros.length} de ${total} resultado(s) — página ${page} de ${totalPaginas}.`;
      }
      atualizarPanorama(payload?.resumo);
      atualizarAnomalias(payload?.anomalias);
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
  const detail = extractErrorDetail(payload);
  if (detail) return detail;

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
      <td colspan="9">${escapeHtml(message)}</td>
    </tr>
  `;
}

// Volta o panorama ao estado vazio (sem busca ou sem resultados).
function resetPanorama() {
  const empty = document.getElementById("dashEmpty");
  const body = document.getElementById("dashBody");
  if (empty) empty.hidden = false;
  if (body) body.hidden = true;
}

// Preenche o painel a partir do resumo agregado que vem na resposta de /flows.
// O resumo cobre TODAS as sessões do filtro (não apenas a página exibida):
// total, quebra aberta/fechada/indefinida, duração média e protocolos.
function atualizarPanorama(resumo) {
  const empty = document.getElementById("dashEmpty");
  const body = document.getElementById("dashBody");
  if (!empty || !body) return;

  if (!resumo || !resumo.total) {
    resetPanorama();
    return;
  }

  const total = resumo.total;
  const abertas = resumo.abertas || 0;
  const fechadas = resumo.fechadas || 0;
  const indefinidas = resumo.indefinidas || 0;

  const setText = (id, valor) => {
    const el = document.getElementById(id);
    if (el) el.textContent = valor;
  };
  setText("kpiTotal", total);
  setText("kpiAbertas", abertas);
  setText("kpiFechadas", fechadas);
  setText("kpiDuracao", resumo.duracao_media || "—");
  setText("legAberta", abertas);
  setText("legFechada", fechadas);
  setText("legIndef", indefinidas);

  // Rosca aberto x fechado. Indefinidas ficam fora da proporção (o gráfico é
  // só sobre aberto/fechado), mas continuam contadas na nota da legenda.
  const base = abertas + fechadas;
  const ring = document.getElementById("donutRing");
  if (ring) {
    if (base > 0) {
      const pctAberta = (abertas / base) * 100;
      ring.style.background =
        `conic-gradient(#22c55e 0 ${pctAberta}%, #ef4444 ${pctAberta}% 100%)`;
      ring.setAttribute(
        "aria-label",
        `${abertas} aberta(s) e ${fechadas} fechada(s)`
      );
    } else {
      ring.style.background = "conic-gradient(#e5e7eb 0 100%)";
      ring.setAttribute("aria-label", "Sem sessões abertas ou fechadas");
    }
  }
  setText("donutValue", base);

  const indefWrap = document.getElementById("legIndefWrap");
  if (indefWrap) indefWrap.hidden = indefinidas === 0;

  // Quebra por protocolo: TCP/UDP/ICMP primeiro, demais em seguida; só os > 0.
  const proto = resumo.por_protocolo || {};
  const protoEl = document.getElementById("dashProto");
  if (protoEl) {
    const ordem = ["TCP", "UDP", "ICMP"];
    const partes = [];
    for (const nome of ordem) {
      if (proto[nome]) partes.push(`${nome} ${proto[nome]}`);
    }
    for (const nome of Object.keys(proto)) {
      if (!ordem.includes(nome) && proto[nome]) partes.push(`${nome} ${proto[nome]}`);
    }
    protoEl.textContent = partes.join("  ·  ");
    protoEl.hidden = partes.length === 0;
  }

  empty.hidden = true;
  body.hidden = false;
}

function setStatus(message, state = "default") {
  // O feedback de estado vive no resumo de resultados (aria-live), que ganha
  // um dot colorido por estado. A mensagem detalhada é definida separadamente.
  const summaryEl = document.getElementById("resultSummary");
  if (!summaryEl) return;
  summaryEl.dataset.state = state;
}

// ── Anomalias: seção do dashboard, alimentada pela resposta de /flows ──

// Esconde a seção (sem busca, sem resultados ou erro).
function resetAnomalias() {
  const section = document.getElementById("anomaliaSection");
  if (section) section.hidden = true;
}

// Preenche a seção a partir de payload.anomalias, que vem junto da consulta.
// Sempre aparece após uma busca: mostra o ranking dos maiores consumidores de
// blocos (mesmo sem anomalia) e destaca os que passam do limiar. Só fica oculta
// se a resposta não trouxer o campo (backend antigo/sem restart).
function atualizarAnomalias(anomalias) {
  const section = document.getElementById("anomaliaSection");
  const summary = document.getElementById("anomSummary");
  if (!section) return;
  if (!anomalias) {
    resetAnomalias();
    return;
  }

  section.hidden = false;
  const itens = Array.isArray(anomalias.itens) ? anomalias.itens : [];
  renderAnomalias(itens, anomalias.limiar);

  if (summary) {
    const lim = anomalias.limiar;
    if (anomalias.total_ips > 0) {
      summary.textContent =
        `${anomalias.total_ips} IP(s) acima do limiar (${lim}) — investigar. Maiores consumidores no ranking.`;
    } else if (itens.length) {
      summary.textContent =
        `Nenhum IP acima do limiar (${lim}). Maiores consumidores de blocos abaixo.`;
    } else {
      summary.textContent =
        "Nenhum IP com blocos concorrentes acima do normal (1 por protocolo).";
    }
  }
}

function renderAnomaliaEmpty(message) {
  const tbody = document.querySelector("#tabelaAnomalias tbody");
  if (tbody) {
    tbody.innerHTML =
      `<tr class="empty_row"><td colspan="8">${escapeHtml(message)}</td></tr>`;
  }
}

// Célula de protocolo: pico em destaque, abertos em número menor.
function protoCell(p) {
  if (!p || (!p.pico && !p.abertas)) return '<span class="proto_zero">—</span>';
  return `<b>${p.pico || 0}</b> <span class="ab">${p.abertas || 0}</span>`;
}

function severidade(pico, limiar) {
  if (pico >= limiar * 2) return " sev--alto";
  if (pico >= limiar) return " sev--medio";
  return "";
}

function renderAnomalias(itens, limiar) {
  const tbody = document.querySelector("#tabelaAnomalias tbody");
  if (!tbody) return;
  if (!itens.length) {
    renderAnomaliaEmpty("Nenhum IP com blocos concorrentes acima do normal.");
    return;
  }
  const lim = limiar || 6;
  tbody.innerHTML = itens
    .map(
      (a) => `
    <tr>
      <td class="mono">${escapeHtml(a.origem)}</td>
      <td>${protoCell(a.tcp)}</td>
      <td>${protoCell(a.udp)}</td>
      <td>${protoCell(a.icmp)}</td>
      <td><span class="pico_total${severidade(a.total_pico, lim)}">${a.total_pico}</span></td>
      <td class="mono">${a.total_abertas}</td>
      <td class="mono">${escapeHtml(a.nat || "-")}</td>
      <td class="mono">${escapeHtml(a.roteador || "-")}</td>
    </tr>`
    )
    .join("");
}
