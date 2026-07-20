const API_PREFIX = "/api";
const TOKEN_KEY = "plog_access_token";
const REFRESH_KEY = "plog_refresh_token";
const ADMIN_KEY = "plog_user_admin";

let currentPage = 1;
let currentTotalPages = 1;
let currentController = null;

document.addEventListener("DOMContentLoaded", function () {
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
  const select = document.getElementById("protocolo");
  if (!select) return [];
  return Array.from(select.selectedOptions, (option) => option.value);
}

function buildUrl(page = 1) {
  const pageSize = document.getElementById("pageSize")?.value || "100";
  const ip = document.getElementById("ip")?.value.trim() || "";
  const porta = document.getElementById("porta")?.value.trim() || "";
  const day = document.getElementById("day")?.value || "";
  const dayEnd = document.getElementById("dayEnd")?.value || "";
  const protocolos = getSelectedProtocols();
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
  if (!requireAuth()) return;

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
