let currentAdminId = null;

document.addEventListener("DOMContentLoaded", function () {
  const painelApp = document.getElementById("painelApp");
  if (!painelApp) return;

  if (!requireAuth()) return;
  initPainelPage();
});

async function initPainelPage() {
  initLogoutButtons();

  const allowed = await requireAdmin();
  if (!allowed) return;

  const form = document.getElementById("createUserForm");
  form.addEventListener("submit", handleCreateUser);

  const usersTable = document.getElementById("usersTable");
  usersTable.addEventListener("click", handleUserTableClick);

  await loadUsers();
}

async function requireAdmin() {
  try {
    const resp = await fetchWithAuth(`${API_PREFIX}/auth/me`);
    const user = await parseJsonResponse(resp);

    if (resp.status === 403 || !user?.admin) {
      window.location.href = "/plog.html";
      return false;
    }

    currentAdminId = user.id;
    setUserAdmin(true);
    return true;
  } catch (err) {
    console.error("Erro ao verificar permissões:", err);
    window.location.href = "/plog.html";
    return false;
  }
}

async function loadUsers() {
  const summaryEl = document.getElementById("usersSummary");
  setPainelStatus("Carregando usuários...", "loading");

  try {
    const resp = await fetchWithAuth(`${API_PREFIX}/auth/usuarios`);
    const payload = await parseJsonResponse(resp);

    if (resp.status === 403) {
      window.location.href = "/plog.html";
      return;
    }

    if (!resp.ok) {
      const message = extractErrorDetail(payload) || "Não foi possível carregar os usuários.";
      renderUsersEmpty(message);
      if (summaryEl) summaryEl.textContent = message;
      setPainelStatus("Erro ao carregar", "error");
      return;
    }

    const users = Array.isArray(payload) ? payload : [];
    renderUsers(users);
    if (summaryEl) {
      summaryEl.textContent = `${users.length} usuário(s) cadastrado(s).`;
    }
    setPainelStatus("Painel pronto", "success");
  } catch (err) {
    console.error("Erro ao listar usuários:", err);
    renderUsersEmpty("Erro ao carregar usuários.");
    if (summaryEl) summaryEl.textContent = "Erro ao carregar usuários.";
    setPainelStatus("Erro ao carregar", "error");
  }
}

function renderUsers(users) {
  const tbody = document.querySelector("#usersTable tbody");
  if (!tbody) return;

  if (users.length === 0) {
    renderUsersEmpty("Nenhum usuário cadastrado.");
    return;
  }

  tbody.innerHTML = users
    .map((user) => {
      const isSelf = user.id === currentAdminId;
      const statusClass = user.ativo ? "table_btn--active" : "table_btn--inactive";
      const statusLabel = user.ativo ? "Ativo" : "Inativo";
      const toggleLabel = user.ativo ? "Desativar" : "Ativar";

      return `
        <tr>
          <td>${escapeHtml(user.id)}</td>
          <td>${escapeHtml(user.username)}</td>
          <td>${escapeHtml(user.email)}</td>
          <td>${user.admin ? "Sim" : "Não"}</td>
          <td>
            <span class="user_status ${statusClass}">${statusLabel}</span>
          </td>
          <td>
            <div class="user_actions">
              <button
                type="button"
                class="table_btn table_btn--toggle"
                data-action="toggle-ativo"
                data-user-id="${user.id}"
                ${isSelf ? "disabled title=\"Não é possível alterar a própria conta\"" : ""}
              >
                ${toggleLabel}
              </button>
              <button
                type="button"
                class="table_btn table_btn--danger"
                data-action="remove-user"
                data-user-id="${user.id}"
                data-username="${escapeHtml(user.username)}"
                ${isSelf ? "disabled title=\"Não é possível remover a própria conta\"" : ""}
              >
                Remover
              </button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderUsersEmpty(message) {
  const tbody = document.querySelector("#usersTable tbody");
  if (!tbody) return;
  tbody.innerHTML = `
    <tr class="empty_row">
      <td colspan="6">${escapeHtml(message)}</td>
    </tr>
  `;
}

async function handleUserTableClick(event) {
  const button = event.target.closest("[data-action]");
  if (!button || button.disabled) return;

  const userId = Number(button.dataset.userId);
  const action = button.dataset.action;

  if (action === "toggle-ativo") {
    await toggleUserStatus(userId, button);
    return;
  }

  if (action === "remove-user") {
    await removeUser(userId, button.dataset.username, button);
  }
}

async function toggleUserStatus(userId, button) {
  hidePainelMessage();
  button.disabled = true;
  setPainelStatus("Atualizando status...", "loading");

  try {
    const resp = await fetchWithAuth(`${API_PREFIX}/auth/usuarios/${userId}/ativo`, {
      method: "PATCH",
      headers: authHeaders(),
    });
    const payload = await parseJsonResponse(resp);

    if (!resp.ok) {
      const message = extractErrorDetail(payload) || "Não foi possível alterar o status.";
      showPainelMessage(message);
      setPainelStatus("Erro ao atualizar", "error");
      return;
    }

    showPainelMessage(
      `Usuário ${payload.ativo ? "ativado" : "desativado"} com sucesso.`,
      "success"
    );
    setPainelStatus("Status atualizado", "success");
    await loadUsers();
  } catch (err) {
    console.error("Erro ao alterar status:", err);
    showPainelMessage("Erro de conexão com o servidor.");
    setPainelStatus("Erro ao atualizar", "error");
  } finally {
    button.disabled = false;
  }
}

async function removeUser(userId, username, button) {
  const confirmed = window.confirm(`Remover o usuário "${username}"? Esta ação não pode ser desfeita.`);
  if (!confirmed) return;

  hidePainelMessage();
  button.disabled = true;
  setPainelStatus("Removendo usuário...", "loading");

  try {
    const resp = await fetchWithAuth(`${API_PREFIX}/auth/usuarios/${userId}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    const payload = await parseJsonResponse(resp);

    if (!resp.ok) {
      const message = extractErrorDetail(payload) || "Não foi possível remover o usuário.";
      showPainelMessage(message);
      setPainelStatus("Erro ao remover", "error");
      return;
    }

    showPainelMessage(payload?.message || "Usuário removido com sucesso.", "success");
    setPainelStatus("Usuário removido", "success");
    await loadUsers();
  } catch (err) {
    console.error("Erro ao remover usuário:", err);
    showPainelMessage("Erro de conexão com o servidor.");
    setPainelStatus("Erro ao remover", "error");
  } finally {
    button.disabled = false;
  }
}

async function handleCreateUser(event) {
  event.preventDefault();
  hidePainelMessage();

  const username = document.getElementById("newUsername")?.value.trim();
  const email = document.getElementById("newEmail")?.value.trim();
  const senha = document.getElementById("newPassword")?.value || "";
  const admin = document.getElementById("newAdmin")?.checked || false;
  const submitBtn = document.getElementById("btnCreateUser");

  if (!username || !email || !senha) {
    showPainelMessage("Preencha usuário, e-mail e senha.");
    return;
  }

  if (submitBtn) submitBtn.disabled = true;
  setPainelStatus("Cadastrando...", "loading");

  try {
    const resp = await fetchWithAuth(`${API_PREFIX}/auth/registrar`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, email, senha, admin }),
    });

    const payload = await parseJsonResponse(resp);

    if (!resp.ok) {
      const message = extractErrorDetail(payload) || "Não foi possível cadastrar o usuário.";
      showPainelMessage(message);
      setPainelStatus("Erro no cadastro", "error");
      return;
    }

    event.target.reset();
    showPainelMessage("Usuário cadastrado com sucesso.", "success");
    setPainelStatus("Usuário cadastrado", "success");
    await loadUsers();
  } catch (err) {
    console.error("Erro ao cadastrar usuário:", err);
    showPainelMessage("Erro de conexão com o servidor.");
    setPainelStatus("Erro no cadastro", "error");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

function showPainelMessage(message, state = "error") {
  const messageEl = document.getElementById("painelMessage");
  if (!messageEl) return;
  messageEl.hidden = false;
  messageEl.textContent = message;
  messageEl.dataset.state = state;
}

function hidePainelMessage() {
  const messageEl = document.getElementById("painelMessage");
  if (!messageEl) return;
  messageEl.hidden = true;
  messageEl.textContent = "";
  delete messageEl.dataset.state;
}

function setPainelStatus(message, state = "default") {
  const statusEl = document.getElementById("painelStatus");
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.dataset.state = state;
}
