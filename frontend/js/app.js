// Configuração básica do endpoint.
// Como o Nginx serve o frontend e proxy para o backend na mesma porta (80),
// podemos usar caminhos relativos para que funcione perfeitamente localmente e na VPS.
const API_URL = "";

let clicksHistoryChart = null;
let clicksDistributionChart = null;
let latestDashboardStats = null;
let adminPlatesCache = [];
const DEVICE_TYPES = ["display", "cartao", "tag", "pulseira", "outro"];

function normalizeOptional(value) {
    const str = (value ?? "").toString().trim();
    return str === "" ? null : str;
}

function normalizeDeviceType(value) {
    const normalized = normalizeOptional(value);
    if (!normalized) return null;
    const lower = normalized.toLowerCase();
    return DEVICE_TYPES.includes(lower) ? lower : lower;
}

function escapeHtml(value) {
    return (value ?? "")
        .toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function deviceDisplayName(device) {
    const custom = normalizeOptional(device.nome_exibicao);
    return custom || `Dispositivo #${device.id_placa}`;
}

function deviceTypeLabel(device) {
    const labels = {
        display: "Display",
        cartao: "Cartão",
        tag: "Tag",
        pulseira: "Pulseira",
        outro: "Outro"
    };
    const type = normalizeDeviceType(device.tipo_dispositivo);
    return labels[type] || "Não definido";
}

function dashFallback(value) {
    return normalizeOptional(value) || "-";
}

function deviceStatsFor(idPlaca) {
    return latestDashboardStats?.placas_stats?.find(item => Number(item.id_placa) === Number(idPlaca)) || {
        frente_cliques: 0,
        verso_cliques: 0,
        total_cliques: 0
    };
}

function versoDestinationLabel(device) {
    if (normalizeOptional(device.pix_chave)) return "Pix";
    const link = normalizeOptional(device.link_verso);
    if (!link) return "Não configurado";
    const lower = link.toLowerCase();
    if (lower.includes("wa.me") || lower.includes("whatsapp")) return "WhatsApp";
    if (lower.includes("cardapio") || lower.includes("menu")) return "Cardápio";
    return "Link do verso";
}

function frenteDestinationLabel(device) {
    return normalizeOptional(device.link_frente) ? "Avaliação Google" : "Não configurado";
}

function formatAccessCount(value) {
    const count = Number(value || 0);
    return count === 1 ? "1 acesso" : `${count} acessos`;
}

function recordingUrl(idPlaca, lado) {
    return `${window.location.origin}/r/${idPlaca}/${lado}`;
}

async function copyTextToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
    }

    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
}

function showFeedback(element, message, type = "success") {
    element.style.display = "block";
    if (type === "success") {
        element.style.backgroundColor = "rgba(16, 185, 129, 0.1)";
        element.style.color = "#10b981";
        element.style.border = "1px solid rgba(16, 185, 129, 0.25)";
    } else {
        element.style.backgroundColor = "rgba(244, 63, 94, 0.1)";
        element.style.color = "#f43f5e";
        element.style.border = "1px solid rgba(244, 63, 94, 0.25)";
    }
    element.textContent = message;
}

// Inicialização do APP
document.addEventListener("DOMContentLoaded", () => {
    checkSession();
    setupEventListeners();
});

// Verifica se existe sessão ativa
function checkSession() {
    const token = localStorage.getItem("nfc_token");
    const establishmentName = localStorage.getItem("nfc_establishment_name");
    const isAdmin = localStorage.getItem("nfc_is_admin") === "true";

    if (token) {
        if (isAdmin) {
            showScreen("superadmin-screen");
            loadSuperAdminData();
        } else {
            showScreen("dashboard-screen");
            document.getElementById("user-establishment-name").textContent = establishmentName;
            loadDashboardData();
        }
    } else {
        showScreen("login-screen");
    }
}

// Transição suave entre telas
function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(screen => {
        screen.classList.remove("active");
    });

    const activeScreen = document.getElementById(screenId);
    if (activeScreen) {
        activeScreen.classList.add("active");
    }
}

// Configura os ouvintes de eventos da página
function setupEventListeners() {
    // Form de Login
    const loginForm = document.getElementById("login-form");
    if (loginForm) {
        loginForm.addEventListener("submit", handleLogin);
    }

    // Botão de Logout comerciante
    const btnLogout = document.getElementById("btn-logout");
    if (btnLogout) {
        btnLogout.addEventListener("click", handleLogout);
    }

    // Botão de Logout admin
    const btnLogoutSuper = document.getElementById("btn-logout-super");
    if (btnLogoutSuper) {
        btnLogoutSuper.addEventListener("click", handleLogout);
    }

    // Form de Cadastro de Comerciante
    const formCadastro = document.getElementById("form-cadastro-comerciante");
    if (formCadastro) {
        formCadastro.addEventListener("submit", handleCadastroComerciante);
    }

    const formVinculo = document.getElementById("form-vincular-dispositivo");
    if (formVinculo) {
        formVinculo.addEventListener("submit", handleVincularDispositivo);
    }
}

// Lógica de Login
async function handleLogin(e) {
    e.preventDefault();
    const docInput = document.getElementById("login-doc").value.trim();
    const pwdInput = document.getElementById("login-pwd").value;
    const submitBtn = document.getElementById("login-submit");
    const errorBox = document.getElementById("login-error");
    const errorText = document.getElementById("error-text");

    // Limpar erros e colocar estado de carregamento
    errorBox.classList.add("hidden");
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Entrando...`;

    try {
        const response = await fetch(`${API_URL}/api/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                documento: docInput,
                senha: pwdInput
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Erro ao fazer login. Verifique seus dados.");
        }

        // Salvar dados no LocalStorage
        localStorage.setItem("nfc_token", data.access_token);
        localStorage.setItem("nfc_establishment_name", data.nome_estabelecimento);
        localStorage.setItem("nfc_is_admin", data.is_admin ? "true" : "false");

        // Limpar inputs de login
        document.getElementById("login-doc").value = "";
        document.getElementById("login-pwd").value = "";

        // Direcionar de acordo com perfil
        if (data.is_admin) {
            showScreen("superadmin-screen");
            loadSuperAdminData();
        } else {
            document.getElementById("user-establishment-name").textContent = data.nome_estabelecimento;
            showScreen("dashboard-screen");
            loadDashboardData();
        }

    } catch (err) {
        errorText.textContent = err.message;
        errorBox.classList.remove("hidden");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Acessar Painel</span> <i class="fa-solid fa-arrow-right"></i>`;
    }
}

// Lógica de Logout
function handleLogout() {
    localStorage.removeItem("nfc_token");
    localStorage.removeItem("nfc_establishment_name");
    localStorage.removeItem("nfc_is_admin");
    showScreen("login-screen");
}

// Carregar todos os dados do dashboard
async function loadDashboardData() {
    const token = localStorage.getItem("nfc_token");
    if (!token) return;

    try {
        // Executar chamadas em paralelo
        const [statsResponse, placasResponse] = await Promise.all([
            fetch(`${API_URL}/api/admin/dashboard`, {
                headers: { "Authorization": `Bearer ${token}` }
            }),
            fetch(`${API_URL}/api/admin/placas`, {
                headers: { "Authorization": `Bearer ${token}` }
            })
        ]);

        if (statsResponse.status === 401 || placasResponse.status === 401) {
            // Token expirado ou inválido
            handleLogout();
            return;
        }

        const statsData = await statsResponse.json();
        const placasData = await placasResponse.json();

        if (!statsResponse.ok) {
            throw new Error(statsData.detail || "Erro ao carregar os indicadores do painel.");
        }
        if (!placasResponse.ok) {
            throw new Error(placasData.detail || "Erro ao carregar seus dispositivos.");
        }

        latestDashboardStats = statsData;
        updateMetrics(statsData);
        renderCharts(statsData);
        renderPlatesGrid(placasData);

    } catch (err) {
        console.error("Erro ao carregar dados do painel:", err);
        const grid = document.getElementById("plates-grid");
        if (grid) {
            grid.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation" style="font-size: 32px; color: var(--color-rose);"></i>
                    <p>${escapeHtml(err.message)}</p>
                </div>
            `;
        }
    }
}

// Atualizar cards de métricas
function updateMetrics(stats) {
    document.getElementById("stat-total-plates").textContent = stats.total_placas;
    document.getElementById("stat-total-clicks").textContent = stats.total_cliques;
    document.getElementById("stat-today-clicks").textContent = stats.cliques_hoje;
}

// Formatar data em string amigável (Ex: "Ter, 19 Mai")
function formatLabelDate(dateStr) {
    const parts = dateStr.split('-');
    if (parts.length !== 3) return dateStr;
    const date = new Date(parts[0], parts[1] - 1, parts[2]);
    const options = { weekday: 'short', day: 'numeric', month: 'short' };
    let formatted = date.toLocaleDateString('pt-BR', options);
    // Capitalizar primeira letra
    formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);
    return formatted.replace('.', '');
}

// Renderizar gráficos com Chart.js
function renderCharts(stats) {
    const ctxHistory = document.getElementById("clicksHistoryChart").getContext("2d");
    const ctxDistribution = document.getElementById("clicksDistributionChart").getContext("2d");

    // Destruir gráficos anteriores para evitar duplicações/erros ao recarregar
    if (clicksHistoryChart) clicksHistoryChart.destroy();
    if (clicksDistributionChart) clicksDistributionChart.destroy();

    // Dados de acesso diários
    const labels = stats.historico_cliques_diarios.map(d => formatLabelDate(d.data));
    const dataTotal = stats.historico_cliques_diarios.map(d => d.frente + d.verso);

    // Gráfico 1: barras simples para leitura rápida da semana
    clicksHistoryChart = new Chart(ctxHistory, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total de acessos',
                    data: dataTotal,
                    borderColor: '#06b6d4',
                    backgroundColor: 'rgba(6, 182, 212, 0.72)',
                    borderWidth: 0,
                    borderRadius: 8,
                    maxBarThickness: 44
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false,
                    labels: {
                        color: '#475569',
                        font: { family: 'Outfit', size: 12 }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: { family: 'Outfit', size: 13, weight: 'bold' },
                    bodyFont: { family: 'Outfit', size: 13 },
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(15, 23, 42, 0.06)' },
                    ticks: { color: '#475569', font: { family: 'Outfit' } }
                },
                y: {
                    grid: { color: 'rgba(15, 23, 42, 0.06)' },
                    ticks: {
                        color: '#475569',
                        font: { family: 'Outfit' },
                        precision: 0
                    },
                    min: 0
                }
            }
        }
    });

    // Gráfico 2: proporção por destino percebido pelo comerciante
    const totalFrente = stats.frente_cliques;
    const totalVerso = stats.verso_cliques;

    // Se não houver cliques, exibe valores neutros mockados para visual não ficar quebrado
    const noClicks = totalFrente === 0 && totalVerso === 0;
    const doughnutData = noClicks ? [1, 1] : [totalFrente, totalVerso];
    const doughnutColors = noClicks ? ['rgba(15, 23, 42, 0.08)', 'rgba(15, 23, 42, 0.04)'] : ['#0284c7', '#059669'];
    const doughnutLabels = noClicks ? ['Sem acessos na avaliação', 'Sem acessos no verso'] : ['Avaliação Google', 'Cardápio / WhatsApp / Pix'];

    clicksDistributionChart = new Chart(ctxDistribution, {
        type: 'doughnut',
        data: {
            labels: doughnutLabels,
            datasets: [{
                data: doughnutData,
                backgroundColor: doughnutColors,
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#475569',
                        font: { family: 'Outfit', size: 12 },
                        padding: 16
                    }
                },
                tooltip: {
                    enabled: !noClicks,
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleFont: { family: 'Outfit', size: 13 },
                    bodyFont: { family: 'Outfit', size: 13 },
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12
                }
            },
            cutout: '75%'
        }
    });
}

// Renderizar listagem de dispositivos
function renderPlatesGrid(dispositivos) {
    const grid = document.getElementById("plates-grid");
    grid.innerHTML = "";

    if (dispositivos.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-tablet-button" style="font-size: 32px; color: var(--text-muted);"></i>
                <p>Nenhum dispositivo cadastrado para o seu estabelecimento.</p>
            </div>
        `;
        return;
    }

    dispositivos.forEach(dispositivo => {
        const card = document.createElement("div");
        card.className = "plate-card glass";
        card.tabIndex = 0;

        const host = window.location.origin;
        const urlFrente = `${host}/r/${dispositivo.id_placa}/frente`;
        const urlVerso = `${host}/r/${dispositivo.id_placa}/verso`;
        const friendlyName = deviceDisplayName(dispositivo);
        const tipoDispositivo = deviceTypeLabel(dispositivo);
        const localUso = dashFallback(dispositivo.local_uso);
        const lojaUnidade = dashFallback(dispositivo.loja_unidade);
        const responsavel = dashFallback(dispositivo.responsavel);
        const statusLabel = dispositivo.status_ativa ? "Ativo" : "Suspenso";
        const stats = deviceStatsFor(dispositivo.id_placa);
        const frenteLabel = frenteDestinationLabel(dispositivo);
        const versoLabel = versoDestinationLabel(dispositivo);

        card.innerHTML = `
            <div class="device-card-head">
                <div class="device-icon"><i class="fa-solid fa-tablet-screen-button"></i></div>
                <span class="status-pill ${dispositivo.status_ativa ? "active" : "suspended"}">${statusLabel}</span>
            </div>
            <h3>${escapeHtml(friendlyName)}</h3>
            <p>ID físico #${dispositivo.id_placa}</p>
            <div class="device-destinations">
                <div class="destination-row">
                    <span><i class="fa-brands fa-google"></i> ${escapeHtml(frenteLabel)}</span>
                    <strong>${formatAccessCount(stats.frente_cliques)}</strong>
                </div>
                <div class="destination-row">
                    <span><i class="fa-solid fa-arrow-turn-down"></i> ${escapeHtml(versoLabel)}</span>
                    <strong>${formatAccessCount(stats.verso_cliques)}</strong>
                </div>
            </div>
            <div class="device-card-meta">
                <span><i class="fa-solid fa-layer-group"></i>${escapeHtml(tipoDispositivo)}</span>
                <span><i class="fa-solid fa-location-dot"></i>${escapeHtml(localUso)}</span>
                <span><i class="fa-solid fa-store"></i>${escapeHtml(lojaUnidade)}</span>
                <span><i class="fa-solid fa-user"></i>${escapeHtml(responsavel)}</span>
            </div>
            <div class="plate-actions">
                <a href="${urlFrente}" target="_blank" class="btn-test" title="Testar redirecionamento da Frente">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> Frente
                </a>
                <a href="${urlVerso}" target="_blank" class="btn-test" title="Testar redirecionamento do Verso">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> Verso
                </a>
                <button type="button" class="btn-test btn-configure">
                    <i class="fa-solid fa-pen-to-square"></i> Editar destinos
                </button>
                <button type="button" class="btn-test btn-delete-plate" onclick="deleteOwnDevice(${dispositivo.id_placa})">
                    <i class="fa-solid fa-trash"></i> Excluir
                </button>
            </div>
        `;

        card.addEventListener("click", () => openDeviceConfigModal(dispositivo));
        card.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openDeviceConfigModal(dispositivo);
            }
        });
        card.querySelectorAll("a, button").forEach(element => {
            element.addEventListener("click", (event) => {
                event.stopPropagation();
                if (element.classList.contains("btn-configure")) {
                    openDeviceConfigModal(dispositivo);
                }
            });
        });

        grid.appendChild(card);
    });
}

function deviceConfigFormHtml(dispositivo) {
    const isPix = !!(dispositivo.pix_chave && dispositivo.pix_chave.trim() !== "");
    const tipoSelecionado = normalizeDeviceType(dispositivo.tipo_dispositivo) || "";

    return `
        <form class="plate-form modal-device-form" data-id="${dispositivo.id_placa}">
            <section class="form-panel">
                <div class="form-panel-header">
                    <i class="fa-solid fa-route"></i>
                    <div>
                        <h4>Destinos da plaquinha</h4>
                        <p>Defina para onde o cliente vai ao tocar na frente ou no verso.</p>
                    </div>
                </div>
                <div class="form-grid">
                    <div class="form-group span-2">
                        <label for="frente-${dispositivo.id_placa}">Frente: Avaliação Google</label>
                        <div class="form-input-wrapper">
                            <i class="fa-brands fa-google"></i>
                            <input type="url" id="frente-${dispositivo.id_placa}" placeholder="Ex: https://goo.gl/maps/..." value="${escapeHtml(dispositivo.link_frente || "")}">
                        </div>
                    </div>
                    <div class="form-group span-2">
                        <label for="verso-type-${dispositivo.id_placa}">Verso da plaquinha</label>
                        <div class="form-select-wrapper">
                            <select id="verso-type-${dispositivo.id_placa}" onchange="toggleVersoMode(${dispositivo.id_placa})">
                                <option value="link" ${!isPix ? "selected" : ""}>Abrir cardápio, WhatsApp ou outro link</option>
                                <option value="pix" ${isPix ? "selected" : ""}>Gerar Pix na hora</option>
                            </select>
                        </div>
                    </div>
                    <div id="section-link-${dispositivo.id_placa}" class="form-group span-2 ${isPix ? "hidden" : ""}">
                        <label for="verso-${dispositivo.id_placa}">Link do verso</label>
                        <div class="form-input-wrapper">
                            <i class="fa-solid fa-link"></i>
                            <input type="url" id="verso-${dispositivo.id_placa}" placeholder="Ex: link do cardápio, WhatsApp ou página de pagamento" value="${escapeHtml(dispositivo.link_verso || "")}">
                        </div>
                    </div>
                </div>
            </section>

            <section class="form-panel">
                <div class="form-panel-header">
                    <i class="fa-solid fa-id-card-clip"></i>
                    <div>
                        <h4>Identificação</h4>
                        <p>Ajuda a reconhecer essa plaquinha no painel.</p>
                    </div>
                </div>
                <div class="form-grid">
                    <div class="form-group span-2">
                        <label for="nome-exibicao-${dispositivo.id_placa}">Nome da plaquinha</label>
                        <div class="form-input-wrapper">
                            <i class="fa-solid fa-tag"></i>
                            <input type="text" id="nome-exibicao-${dispositivo.id_placa}" maxlength="120" placeholder="Ex: Placa Caixa 1 - Loja Centro" value="${escapeHtml(dispositivo.nome_exibicao || "")}">
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="tipo-dispositivo-${dispositivo.id_placa}">Tipo</label>
                        <div class="form-select-wrapper">
                            <select id="tipo-dispositivo-${dispositivo.id_placa}">
                                <option value="" ${tipoSelecionado === "" ? "selected" : ""}>Não definido</option>
                                <option value="display" ${tipoSelecionado === "display" ? "selected" : ""}>Display</option>
                                <option value="cartao" ${tipoSelecionado === "cartao" ? "selected" : ""}>Cartão</option>
                                <option value="tag" ${tipoSelecionado === "tag" ? "selected" : ""}>Tag</option>
                                <option value="pulseira" ${tipoSelecionado === "pulseira" ? "selected" : ""}>Pulseira</option>
                                <option value="outro" ${tipoSelecionado === "outro" ? "selected" : ""}>Outro</option>
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="responsavel-${dispositivo.id_placa}">Responsável</label>
                        <div class="form-input-wrapper">
                            <i class="fa-solid fa-user"></i>
                            <input type="text" id="responsavel-${dispositivo.id_placa}" maxlength="120" placeholder="Ex: Equipe Caixa" value="${escapeHtml(dispositivo.responsavel || "")}">
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="local-uso-${dispositivo.id_placa}">Local de uso</label>
                        <div class="form-input-wrapper">
                            <i class="fa-solid fa-location-dot"></i>
                            <input type="text" id="local-uso-${dispositivo.id_placa}" maxlength="120" placeholder="Ex: Caixa 1" value="${escapeHtml(dispositivo.local_uso || "")}">
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="loja-unidade-${dispositivo.id_placa}">Loja/Unidade</label>
                        <div class="form-input-wrapper">
                            <i class="fa-solid fa-store"></i>
                            <input type="text" id="loja-unidade-${dispositivo.id_placa}" maxlength="120" placeholder="Ex: Loja Centro" value="${escapeHtml(dispositivo.loja_unidade || "")}">
                        </div>
                    </div>
                    <div class="form-group span-2">
                        <label for="observacao-${dispositivo.id_placa}">Observação</label>
                        <div class="form-input-wrapper">
                            <i class="fa-solid fa-note-sticky"></i>
                            <textarea id="observacao-${dispositivo.id_placa}" maxlength="500" placeholder="Ex: Display principal de avaliação Google">${escapeHtml(dispositivo.observacao || "")}</textarea>
                        </div>
                    </div>
                </div>
            </section>

            <section id="section-pix-${dispositivo.id_placa}" class="form-panel ${!isPix ? "hidden" : ""}">
                <div class="form-panel-header">
                    <i class="fa-brands fa-pix"></i>
                    <div>
                        <h4>Pix</h4>
                        <p>Cobrança local no verso do dispositivo.</p>
                    </div>
                </div>
                <div class="form-grid">
                    <div class="form-group span-2">
                        <label for="pix-chave-${dispositivo.id_placa}">Chave Pix</label>
                        <div class="form-input-wrapper">
                            <i class="fa-brands fa-pix"></i>
                            <input type="text" id="pix-chave-${dispositivo.id_placa}" placeholder="CPF, CNPJ, e-mail, celular ou chave aleatória" value="${escapeHtml(dispositivo.pix_chave || "")}">
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="pix-tipo-${dispositivo.id_placa}">Tipo de valor</label>
                        <div class="form-select-wrapper">
                            <select id="pix-tipo-${dispositivo.id_placa}" onchange="togglePixType(${dispositivo.id_placa})">
                                <option value="aberto" ${dispositivo.pix_tipo_valor === "aberto" ? "selected" : ""}>Cliente digita o valor</option>
                                <option value="fixo" ${dispositivo.pix_tipo_valor === "fixo" ? "selected" : ""}>Valor fixo</option>
                            </select>
                        </div>
                    </div>
                    <div id="section-pix-valor-${dispositivo.id_placa}" class="form-group ${dispositivo.pix_tipo_valor !== "fixo" ? "hidden" : ""}">
                        <label for="pix-valor-${dispositivo.id_placa}">Valor fixo (R$)</label>
                        <div class="form-input-wrapper">
                            <i class="fa-solid fa-dollar-sign"></i>
                            <input type="number" step="0.01" min="0.01" id="pix-valor-${dispositivo.id_placa}" placeholder="Ex: 40.00" value="${dispositivo.pix_valor_fixo || ""}">
                        </div>
                    </div>
                </div>
            </section>

            <div class="modal-actions">
                <button type="button" class="btn-secondary-action" onclick="closeDeviceConfigModal()">Cancelar</button>
                <button type="submit" class="btn-save">
                    <i class="fa-solid fa-floppy-disk"></i> Salvar alterações
                </button>
            </div>
        </form>
    `;
}

function openDeviceConfigModal(dispositivo, isAdmin) {
    closeDeviceConfigModal();

    const modal = document.createElement("div");
    modal.id = "device-config-modal";
    modal.className = "modal-backdrop";
    modal.innerHTML = `
        <div class="device-modal" role="dialog" aria-modal="true" aria-labelledby="device-modal-title">
            <div class="modal-header">
                <div>
                    <span class="modal-kicker">Dispositivo Smart Flow #${dispositivo.id_placa}</span>
                    <h2 id="device-modal-title">${escapeHtml(deviceDisplayName(dispositivo))}</h2>
                </div>
                <button type="button" class="modal-close" onclick="closeDeviceConfigModal()" aria-label="Fechar">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            <div class="modal-body">
                ${deviceConfigFormHtml(dispositivo)}
            </div>
        </div>
    `;

    modal.addEventListener("click", (event) => {
        if (event.target === modal) closeDeviceConfigModal();
    });

    document.body.appendChild(modal);
    document.body.classList.add("modal-open");

    const form = modal.querySelector(".plate-form");
    form.addEventListener("submit", (event) => handleSavePlate(event, dispositivo.id_placa, !!isAdmin));
    modal.querySelector("input, select, textarea")?.focus();
}

function closeDeviceConfigModal() {
    const modal = document.getElementById("device-config-modal");
    if (modal) modal.remove();
    document.body.classList.remove("modal-open");
}

window.closeDeviceConfigModal = closeDeviceConfigModal;

// Salvar personalização, links e configurações do Pix do dispositivo
async function handleSavePlate(e, idPlaca, isAdmin) {
    e.preventDefault();
    const token = localStorage.getItem("nfc_token");
    if (!token) return;

    const form = e.target;
    const saveBtn = form.querySelector(".btn-save");
    const nomeExibicao = normalizeOptional(document.getElementById(`nome-exibicao-${idPlaca}`).value);
    const tipoDispositivo = normalizeDeviceType(document.getElementById(`tipo-dispositivo-${idPlaca}`).value);
    const localUso = normalizeOptional(document.getElementById(`local-uso-${idPlaca}`).value);
    const lojaUnidade = normalizeOptional(document.getElementById(`loja-unidade-${idPlaca}`).value);
    const responsavel = normalizeOptional(document.getElementById(`responsavel-${idPlaca}`).value);
    const observacao = normalizeOptional(document.getElementById(`observacao-${idPlaca}`).value);
    const inputFrente = document.getElementById(`frente-${idPlaca}`).value.trim();

    // Obter comportamento do verso
    const versoType = document.getElementById(`verso-type-${idPlaca}`).value;

    let linkVerso = null;
    let pixChave = null;
    let pixTipoValor = null;
    let pixValorFixo = null;

    if (versoType === "link") {
        linkVerso = document.getElementById(`verso-${idPlaca}`).value.trim();
        // pixChave, pixTipoValor e pixValorFixo ficam null (limpando o Pix)
    } else {
        pixChave = document.getElementById(`pix-chave-${idPlaca}`).value.trim();
        pixTipoValor = document.getElementById(`pix-tipo-${idPlaca}`).value;

        if (!pixChave) {
            alert("Para ativar o Pix Local, digite uma Chave Pix válida.");
            return;
        }

        if (pixTipoValor === "fixo") {
            const rawVal = document.getElementById(`pix-valor-${idPlaca}`).value;
            pixValorFixo = parseFloat(rawVal) || null;
            if (!pixValorFixo || pixValorFixo <= 0) {
                alert("Para o tipo Valor Fixo, digite um valor maior que zero.");
                return;
            }
        } else {
            pixTipoValor = "aberto";
        }
    }

    // Estado visual de carregamento
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Salvando...`;

    try {
        const endpoint = isAdmin ? `${API_URL}/api/admin/super/placas/${idPlaca}` : `${API_URL}/api/admin/placas/${idPlaca}`;
        const response = await fetch(endpoint, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                nome_exibicao: nomeExibicao,
                tipo_dispositivo: tipoDispositivo,
                local_uso: localUso,
                loja_unidade: lojaUnidade,
                responsavel: responsavel,
                observacao: observacao,
                link_frente: inputFrente || null,
                link_verso: linkVerso || null,
                pix_chave: pixChave || null,
                pix_tipo_valor: pixTipoValor || null,
                pix_valor_fixo: pixValorFixo
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Erro ao salvar as configurações do dispositivo.");
        }

        // Sucesso visual
        saveBtn.classList.add("success");
        saveBtn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Salvo com Sucesso!`;

        // Atualizar estatísticas do dashboard silenciosamente em segundo plano
        setTimeout(async () => {
            if (isAdmin) {
                saveBtn.classList.remove("success");
                saveBtn.disabled = false;
                saveBtn.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Salvar alterações`;
                closeDeviceConfigModal();
                loadSuperAdminData();
                return;
            }

            const statsResp = await fetch(`${API_URL}/api/admin/dashboard`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (statsResp.ok) {
                const statsData = await statsResp.json();
                updateMetrics(statsData);
                renderCharts(statsData);
            }

            // Restaurar botão original após 2.5s
            saveBtn.classList.remove("success");
            saveBtn.disabled = false;
            saveBtn.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Salvar alterações`;
            closeDeviceConfigModal();
            loadDashboardData();
        }, 2000);

    } catch (err) {
        alert(err.message);
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Salvar alterações`;
    }
}

// Excluir um dispositivo do comerciante logado
window.deleteOwnDevice = async function(idPlaca) {
    const token = localStorage.getItem("nfc_token");
    if (!token) return;

    const confirma = confirm(`Excluir o dispositivo #${idPlaca}?\nO histórico de cliques também será apagado. Essa ação não pode ser desfeita.`);
    if (!confirma) return;

    try {
        const response = await fetch(`${API_URL}/api/admin/placas/${idPlaca}`, {
            method: "DELETE",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || "Erro ao excluir o dispositivo.");
        }

        loadDashboardData();
    } catch (err) {
        alert(err.message);
    }
};

// Funções globais de toggle para elementos interativos dos dispositivos
window.toggleVersoMode = function(idPlaca) {
    const versoType = document.getElementById(`verso-type-${idPlaca}`).value;
    const linkSection = document.getElementById(`section-link-${idPlaca}`);
    const pixSection = document.getElementById(`section-pix-${idPlaca}`);

    if (versoType === "link") {
        linkSection.classList.remove("hidden");
        pixSection.classList.add("hidden");
    } else {
        linkSection.classList.add("hidden");
        pixSection.classList.remove("hidden");
    }
};

window.togglePixType = function(idPlaca) {
    const pixType = document.getElementById(`pix-tipo-${idPlaca}`).value;
    const valueSection = document.getElementById(`section-pix-valor-${idPlaca}`);

    if (pixType === "fixo") {
        valueSection.classList.remove("hidden");
    } else {
        valueSection.classList.add("hidden");
    }
};

// --- LOGICA DO SUPERADMIN ---

async function loadSuperAdminData() {
    const token = localStorage.getItem("nfc_token");
    if (!token) return;

    try {
        const response = await fetch(`${API_URL}/api/admin/super/comerciantes`, {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            handleLogout();
            return;
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Erro ao obter lista de comerciantes.");
        }

        adminPlatesCache = data.flatMap(comerciante => comerciante.placas || []);
        renderSuperTable(data);
    } catch (err) {
        console.error("Erro ao carregar dados do admin:", err);
    }
}

window.openAdminPlateModal = function(idPlaca) {
    const placa = adminPlatesCache.find(p => p.id_placa === idPlaca);
    if (!placa) {
        alert("Dispositivo não encontrado. Recarregue a lista.");
        return;
    }
    openDeviceConfigModal(placa, true);
};

window.deleteAdminPlate = async function(idPlaca) {
    const token = localStorage.getItem("nfc_token");
    if (!token) return;

    const confirma = confirm(`Excluir o dispositivo #${idPlaca}?\nO histórico de cliques também será apagado. Essa ação não pode ser desfeita.`);
    if (!confirma) return;

    try {
        const response = await fetch(`${API_URL}/api/admin/super/placas/${idPlaca}`, {
            method: "DELETE",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || "Erro ao excluir o dispositivo.");
        }

        loadSuperAdminData();
    } catch (err) {
        alert(err.message);
    }
};

function renderSuperTable(comerciantes) {
    const tbody = document.getElementById("comerciantes-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (comerciantes.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="padding: 24px; text-align: center; color: #a1a1aa;">Nenhum comerciante cadastrado.</td></tr>`;
        return;
    }

    comerciantes.forEach(comerciante => {
        const tr = document.createElement("tr");

        if (comerciante.placas.length === 0) {
            tr.innerHTML = `
                <td style="padding: 12px 16px; font-weight: 600; color: white;">${escapeHtml(comerciante.nome_estabelecimento)}</td>
                <td style="padding: 12px 16px; color: #a1a1aa;">${escapeHtml(comerciante.documento)}</td>
                <td style="padding: 12px 16px; color: #71717a; font-style: italic;">Nenhum dispositivo</td>
                <td style="padding: 12px 16px; text-align: center; color: #71717a;">-</td>
            `;
        } else {
            const dispositivosHtml = comerciante.placas.map(placa => {
                const nomeAmigavel = deviceDisplayName(placa);
                const tipo = deviceTypeLabel(placa);
                const status = placa.status_ativa ? "Ativo" : "Suspenso";
                const frenteUrl = recordingUrl(placa.id_placa, "frente");
                const versoUrl = recordingUrl(placa.id_placa, "verso");
                return `
                    <div class="admin-device-row">
                        <strong>${escapeHtml(nomeAmigavel)}</strong>
                        <span>ID físico: #${placa.id_placa}</span>
                        <span>Tipo: ${escapeHtml(tipo)}</span>
                        <span>Status: ${status}</span>
                        <div class="recording-links">
                            <div class="recording-link-row">
                                <span>Frente</span>
                                <code>${escapeHtml(frenteUrl)}</code>
                                <button type="button" class="btn-copy-link" onclick="copyRecordingLink('${escapeHtml(frenteUrl)}', this)">
                                    <i class="fa-regular fa-copy"></i> Copiar
                                </button>
                            </div>
                            <div class="recording-link-row">
                                <span>Verso</span>
                                <code>${escapeHtml(versoUrl)}</code>
                                <button type="button" class="btn-copy-link" onclick="copyRecordingLink('${escapeHtml(versoUrl)}', this)">
                                    <i class="fa-regular fa-copy"></i> Copiar
                                </button>
                            </div>
                        </div>
                        <div class="admin-device-actions">
                            <button type="button" class="btn-edit-plate" onclick="openAdminPlateModal(${placa.id_placa})">
                                <i class="fa-solid fa-pen-to-square"></i> Editar
                            </button>
                            <button type="button" class="btn-delete-plate" onclick="deleteAdminPlate(${placa.id_placa})">
                                <i class="fa-solid fa-trash"></i> Excluir
                            </button>
                        </div>
                    </div>
                `;
            }).join("");

            const statusHtml = comerciante.placas.map(placa => {
                const isChecked = placa.status_ativa ? "checked" : "";
                const status = placa.status_ativa ? "Ativo" : "Suspenso";
                return `
                    <div class="admin-status-row">
                        <span>#${placa.id_placa}</span>
                        <label class="switch">
                            <input type="checkbox" ${isChecked} onchange="togglePlateStatus(${placa.id_placa}, this.checked)">
                            <span class="slider"></span>
                        </label>
                        <span>${status}</span>
                    </div>
                `;
            }).join("");

            tr.innerHTML = `
                <td style="padding: 12px 16px; font-weight: 600; color: white;">${escapeHtml(comerciante.nome_estabelecimento)}</td>
                <td style="padding: 12px 16px; color: #a1a1aa;">${escapeHtml(comerciante.documento)}</td>
                <td style="padding: 12px 16px; color: white;">${dispositivosHtml}</td>
                <td style="padding: 12px 16px; text-align: center;">${statusHtml}</td>
            `;
        }

        tbody.appendChild(tr);
    });
}

window.togglePlateStatus = async function(idPlaca, statusAtiva) {
    const token = localStorage.getItem("nfc_token");
    if (!token) return;

    try {
        const response = await fetch(`${API_URL}/api/admin/super/placas/${idPlaca}/status`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                status_ativa: statusAtiva
            })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Erro ao alterar status do dispositivo.");
        }

        loadSuperAdminData();
    } catch (err) {
        alert(err.message);
        loadSuperAdminData();
    }
};

window.copyRecordingLink = async function(url, button) {
    const originalHtml = button.innerHTML;
    try {
        await copyTextToClipboard(url);
        button.classList.add("copied");
        button.innerHTML = `<i class="fa-solid fa-circle-check"></i> Copiado`;
        setTimeout(() => {
            button.classList.remove("copied");
            button.innerHTML = originalHtml;
        }, 1800);
    } catch (err) {
        alert("Não consegui copiar automaticamente. Selecione o link e copie manualmente.");
    }
};

async function handleCadastroComerciante(e) {
    e.preventDefault();
    const token = localStorage.getItem("nfc_token");
    if (!token) return;

    const docInput = document.getElementById("super-documento").value.trim();
    const estabInput = document.getElementById("super-estabelecimento").value.trim();
    const senhaInput = document.getElementById("super-senha").value;
    const placaInputVal = document.getElementById("super-placa").value.trim();

    const saveBtn = document.getElementById("btn-save-comerciante");
    const feedback = document.getElementById("cadastro-feedback");

    feedback.style.display = "none";
    feedback.className = "";

    saveBtn.disabled = true;
    saveBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Cadastrando...`;

    const tipoDispositivo = document.getElementById("super-tipo-dispositivo")?.value || null;
    const payload = {
        documento: docInput,
        nome_estabelecimento: estabInput,
        senha: senhaInput,
        id_placa: placaInputVal ? parseInt(placaInputVal) : null
    };
    if (tipoDispositivo) {
        payload.tipo_dispositivo = tipoDispositivo;
    }

    try {
        const response = await fetch(`${API_URL}/api/admin/super/comerciantes`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Erro ao cadastrar comerciante.");
        }

        const successMessage = data.detail || "Dispositivo vinculado com sucesso. O comerciante poderá personalizar nome, local, loja, responsável e destinos pelo painel dele.";
        showFeedback(feedback, successMessage);

        document.getElementById("form-cadastro-comerciante").reset();
        loadSuperAdminData();

    } catch (err) {
        showFeedback(feedback, err.message, "error");
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<span>Cadastrar Comerciante</span> <i class="fa-solid fa-save"></i>`;
    }
}

async function handleVincularDispositivo(e) {
    e.preventDefault();
    const token = localStorage.getItem("nfc_token");
    if (!token) return;

    const documento = document.getElementById("vinculo-documento").value.trim();
    const idPlaca = document.getElementById("vinculo-placa").value.trim();
    const tipoDispositivo = document.getElementById("vinculo-tipo-dispositivo")?.value || null;
    const saveBtn = document.getElementById("btn-vincular-dispositivo");
    const feedback = document.getElementById("vinculo-feedback");

    feedback.style.display = "none";
    feedback.className = "";

    const payload = {
        dono_documento: documento,
        id_placa: parseInt(idPlaca)
    };
    if (tipoDispositivo) {
        payload.tipo_dispositivo = tipoDispositivo;
    }

    saveBtn.disabled = true;
    saveBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Vinculando...`;

    try {
        const response = await fetch(`${API_URL}/api/admin/super/placas`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Erro ao vincular dispositivo.");
        }

        showFeedback(feedback, "Dispositivo vinculado com sucesso. O comerciante poderá personalizar nome, local, loja, responsável e destinos pelo painel dele.");
        document.getElementById("form-vincular-dispositivo").reset();
        loadSuperAdminData();
    } catch (err) {
        showFeedback(feedback, err.message, "error");
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `<span>Adicionar Dispositivo</span> <i class="fa-solid fa-link"></i>`;
    }
}
