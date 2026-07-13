const API_BASE = "/api/v1";
const WS_URL = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws/dashboard";

const state = {
  signals: [],
  operations: [],
  scans: [],
};

let capitalChart = null;

// ---------------- Clock ----------------
function tickClock() {
  const el = document.getElementById("clock");
  el.textContent = new Date().toLocaleTimeString("pt-BR");
}
setInterval(tickClock, 1000);
tickClock();

// ---------------- REST calls ----------------
async function fetchJSON(path) {
  try {
    const res = await fetch(API_BASE + path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("Erro ao buscar", path, err);
    return null;
  }
}

async function loadSignals() {
  const data = await fetchJSON("/signals");
  if (data) {
    state.signals = data;
    renderSignals();
    renderHeatmap();
  }
}

async function loadOperations() {
  const data = await fetchJSON("/operations?limit=20");
  if (data) {
    state.operations = data;
    renderOperationsTable();
  }
}

async function loadLatestScan() {
  const data = await fetchJSON("/signals/latest-scan");
  if (data) {
    state.scans = data;
    renderScanTable();
  }
}

async function loadStatistics() {
  const data = await fetchJSON("/statistics?days=30");
  if (data) renderKPIs(data);
}

async function loadMarketStatus() {
  const data = await fetchJSON("/pairs/EURUSD/status");
  const pill = document.getElementById("market-status");
  if (!data) return;
  pill.classList.toggle("online", data.market_open);
  pill.classList.toggle("offline", !data.market_open);
  pill.innerHTML = `<span class="dot"></span> Mercado ${data.market_open ? "Aberto" : "Fechado"}`;
}

// ---------------- Rendering ----------------
function renderSignals() {
  const container = document.getElementById("signal-cards");
  if (!state.signals.length) {
    container.innerHTML = `<div class="empty-state">Aguardando sinais do scanner…</div>`;
    return;
  }

  container.innerHTML = state.signals
    .map((s) => {
      const dirClass = s.direction === "BUY" ? "buy" : "sell";
      return `
      <div class="signal-card ${dirClass === "buy" ? "" : "sell"}">
        <div class="signal-card-top">
          <span class="signal-symbol">${s.symbol}</span>
          <span class="signal-direction ${dirClass}">${s.direction}</span>
        </div>
        <div class="signal-grid">
          <span class="label">Entrada</span><span class="value">${fmt(s.entry_price)}</span>
          <span class="label">Stop</span><span class="value">${fmt(s.stop_loss)}</span>
          <span class="label">Take</span><span class="value">${fmt(s.take_profit)}</span>
          <span class="label">RR</span><span class="value">${s.risk_reward.toFixed(1)}:1</span>
          <span class="label">Probabilidade</span><span class="value">${s.probability}%</span>
          <span class="label">Tempo</span><span class="value">${s.expected_duration_minutes} min</span>
        </div>
        <div class="iqs-badge">
          <span>${s.status} · ${s.timeframe}</span>
          <span class="iqs-score">IQS ${s.iqs_score.toFixed(0)}</span>
        </div>
        <button class="mark-traded-btn" onclick="markAsTraded(${s.id}, '${s.symbol}', ${s.entry_price})">
          Marcar como Operado
        </button>
      </div>`;
    })
    .join("");
}

async function markAsTraded(signalId, symbol, defaultEntryPrice) {
  const lotInput = window.prompt(`${symbol} — Tamanho do lote (ex: 0.10):`, "0.10");
  if (lotInput === null) return;
  const lotSize = parseFloat(lotInput.replace(",", "."));
  if (!lotSize || lotSize <= 0) {
    alert("Tamanho de lote inválido.");
    return;
  }

  const priceInput = window.prompt(
    `${symbol} — Preço de entrada real (deixe como está para usar o preço sugerido):`,
    String(defaultEntryPrice)
  );
  if (priceInput === null) return;
  const entryPrice = parseFloat(priceInput.replace(",", "."));

  try {
    const res = await fetch(`${API_BASE}/operations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        signal_id: signalId,
        lot_size: lotSize,
        entry_price: entryPrice || null,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || `HTTP ${res.status}`);
    }
    await loadOperations();
    alert(`Operação em ${symbol} registrada. O sistema vai fechar ela sozinho quando atingir Take Profit ou Stop Loss.`);
  } catch (err) {
    alert(`Não foi possível registrar a operação: ${err.message}`);
  }
}

function renderHeatmap() {
  const container = document.getElementById("heatmap");
  if (!state.signals.length) {
    container.innerHTML = `<div class="empty-state">Sem dados suficientes.</div>`;
    return;
  }
  container.innerHTML = state.signals
    .map((s) => {
      const intensity = Math.min(1, s.iqs_score / 100);
      const color = s.direction === "BUY"
        ? `rgba(0,217,192,${0.15 + intensity * 0.5})`
        : `rgba(255,93,93,${0.15 + intensity * 0.5})`;
      return `
      <div class="heat-cell" style="background:${color}">
        <div class="heat-symbol">${s.symbol}</div>
        <div class="heat-score mono">${s.iqs_score.toFixed(0)}</div>
      </div>`;
    })
    .join("");
}

const STATUS_LABELS = {
  CONFIRMADO: "Confirmado",
  PREPARANDO: "Preparando",
  DESCARTADO: "Descartado",
  SEM_DADOS: "Sem dados",
  LIMITE_ATINGIDO: "Limite atingido",
  ERRO: "Erro",
};

function renderScanTable() {
  const tbody = document.getElementById("scan-table-body");
  if (!state.scans.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-row">Aguardando primeiro scan…</td></tr>`;
    return;
  }
  tbody.innerHTML = state.scans
    .map((s) => {
      const statusClass = s.status === "CONFIRMADO" ? "pl-positive"
        : s.status === "DESCARTADO" ? "pl-negative" : "";
      const iqsText = s.iqs_score != null ? s.iqs_score.toFixed(0) : "—";
      const updated = s.scanned_at ? new Date(s.scanned_at).toLocaleTimeString("pt-BR") : "—";
      return `
      <tr>
        <td>${s.symbol}</td>
        <td>${s.timeframe}</td>
        <td>${s.direction}</td>
        <td>${iqsText}</td>
        <td class="${statusClass}">${STATUS_LABELS[s.status] || s.status}</td>
        <td style="font-family: var(--font-body); font-size: 12px;">${s.reason || "—"}</td>
        <td>${updated}</td>
      </tr>`;
    })
    .join("");
}

function renderOperationsTable() {
  const tbody = document.getElementById("ops-table-body");
  if (!state.operations.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-row">Sem operações registradas ainda.</td></tr>`;
    return;
  }
  tbody.innerHTML = state.operations
    .map((op) => {
      const plClass = (op.profit_loss ?? 0) >= 0 ? "pl-positive" : "pl-negative";
      const plText = op.profit_loss != null ? op.profit_loss.toFixed(2) : "—";
      return `
      <tr>
        <td>${op.symbol}</td>
        <td>${op.direction}</td>
        <td>${fmt(op.entry_price)}</td>
        <td>${op.exit_price != null ? fmt(op.exit_price) : "—"}</td>
        <td>${op.result}</td>
        <td class="${plClass}">${plText}</td>
        <td>${new Date(op.opened_at).toLocaleString("pt-BR")}</td>
      </tr>`;
    })
    .join("");
}

function renderKPIs(stats) {
  document.getElementById("kpi-winrate").textContent = `${stats.win_rate.toFixed(1)}%`;
  document.getElementById("kpi-pf").textContent = stats.profit_factor.toFixed(2);
  document.getElementById("kpi-expectancy").textContent = stats.expectancy.toFixed(2);
  document.getElementById("kpi-drawdown").textContent = stats.max_drawdown.toFixed(2);
  document.getElementById("kpi-net").textContent = stats.net_result.toFixed(2);
  renderCapitalChart(stats.capital_curve || []);
}

function renderCapitalChart(curve) {
  const ctx = document.getElementById("capital-chart");
  const labels = curve.map((_, i) => i);

  if (capitalChart) {
    capitalChart.data.labels = labels;
    capitalChart.data.datasets[0].data = curve;
    capitalChart.update();
    return;
  }

  capitalChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Capital",
        data: curve,
        borderColor: "#00d9c0",
        backgroundColor: "rgba(0,217,192,0.08)",
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8b95a7" }, grid: { color: "#232a3a" } },
        y: { ticks: { color: "#8b95a7" }, grid: { color: "#232a3a" } },
      },
    },
  });
}

function fmt(value) {
  return Number(value).toFixed(5);
}

// ---------------- WebSocket ----------------
function connectWebSocket() {
  const ws = new WebSocket(WS_URL);
  const pill = document.getElementById("ws-status");

  ws.onopen = () => {
    pill.classList.add("online");
    pill.classList.remove("offline");
    pill.innerHTML = `<span class="dot"></span> Tempo real conectado`;
  };

  ws.onclose = () => {
    pill.classList.remove("online");
    pill.classList.add("offline");
    pill.innerHTML = `<span class="dot"></span> Reconectando...`;
    setTimeout(connectWebSocket, 3000);
  };

  ws.onerror = () => ws.close();

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.event === "new_signal") {
        state.signals = [msg.data, ...state.signals].slice(0, 40);
        renderSignals();
        renderHeatmap();
      }
      if (msg.event === "operation_update") {
        loadOperations();
      }
      if (msg.event === "statistics_update") {
        loadStatistics();
      }
    } catch (err) {
      console.error("Mensagem WS inválida", err);
    }
  };
}

// ---------------- Bootstrap ----------------
async function init() {
  await Promise.all([loadSignals(), loadOperations(), loadStatistics(), loadMarketStatus(), loadLatestScan()]);
  connectWebSocket();
  setInterval(loadMarketStatus, 30000);
  setInterval(loadLatestScan, 20000);
  await setupBacktestForm();
}

// ---------------- Backtest ----------------
let backtestChart = null;
let backtestRunResults = {}; // symbol -> result

async function setupBacktestForm() {
  const pairsData = await fetchJSON("/pairs");
  const container = document.getElementById("bt-pairs");
  if (pairsData && pairsData.symbols) {
    container.innerHTML = pairsData.symbols
      .map(
        (s, i) => `
      <label class="backtest-pair-chip ${i === 0 ? "checked" : ""}">
        <input type="checkbox" value="${s}" ${i === 0 ? "checked" : ""} onchange="this.parentElement.classList.toggle('checked', this.checked)" />
        ${s}
      </label>`
      )
      .join("");
  }

  const presetSelect = document.getElementById("bt-preset");
  presetSelect.addEventListener("change", () => {
    const isCustom = presetSelect.value === "custom";
    document.getElementById("bt-start-field").style.display = isCustom ? "flex" : "none";
    document.getElementById("bt-end-field").style.display = isCustom ? "flex" : "none";
  });

  const today = new Date();
  const monthAgo = new Date(today);
  monthAgo.setMonth(monthAgo.getMonth() - 1);
  document.getElementById("bt-end").value = today.toISOString().slice(0, 10);
  document.getElementById("bt-start").value = monthAgo.toISOString().slice(0, 10);

  document.getElementById("backtest-form").addEventListener("submit", runBacktest);
}

function resolvePeriod() {
  const preset = document.getElementById("bt-preset").value;
  const end = new Date();
  if (preset === "custom") {
    return {
      start: document.getElementById("bt-start").value,
      end: document.getElementById("bt-end").value,
    };
  }
  const start = new Date();
  start.setDate(start.getDate() - parseInt(preset, 10));
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

async function runBacktest(event) {
  event.preventDefault();
  const button = event.target.querySelector(".backtest-run-btn");
  const statusEl = document.getElementById("backtest-status");
  const summaryWrap = document.getElementById("backtest-summary-wrap");
  const resultsEl = document.getElementById("backtest-results");

  const symbols = Array.from(document.querySelectorAll("#bt-pairs input:checked")).map((i) => i.value);
  const timeframe = document.getElementById("bt-timeframe").value;
  const capital = parseFloat(document.getElementById("bt-capital").value) || 10000;
  const { start: startDate, end: endDate } = resolvePeriod();

  if (!symbols.length || !startDate || !endDate) {
    statusEl.textContent = "Selecione ao menos um par e um período válido.";
    return;
  }

  button.disabled = true;
  resultsEl.style.display = "none";
  summaryWrap.style.display = "none";
  backtestRunResults = {};
  const summaryBody = document.getElementById("backtest-summary-body");
  summaryBody.innerHTML = "";

  for (let i = 0; i < symbols.length; i++) {
    const symbol = symbols[i];
    statusEl.textContent = `Rodando ${symbol} (${i + 1}/${symbols.length})… candles históricas reais, pode levar alguns segundos.`;
    try {
      const res = await fetch(`${API_BASE}/backtest/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          timeframe,
          start_date: `${startDate}T00:00:00Z`,
          end_date: `${endDate}T23:59:59Z`,
          initial_capital: capital,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.message || `HTTP ${res.status}`);
      }
      const result = await res.json();
      backtestRunResults[symbol] = result;
      appendSummaryRow(symbol, result);
    } catch (err) {
      appendSummaryRow(symbol, null, err.message);
    }
  }

  button.disabled = false;
  summaryWrap.style.display = "block";
  statusEl.textContent = `Backtest concluído para ${symbols.length} par(es). Toque numa linha para ver o detalhe.`;
}

function appendSummaryRow(symbol, result, errorMessage) {
  const summaryBody = document.getElementById("backtest-summary-body");
  const row = document.createElement("tr");

  if (!result) {
    row.innerHTML = `
      <td>${symbol}</td>
      <td colspan="6" class="pl-negative">Erro: ${errorMessage || "falha desconhecida"}</td>`;
    summaryBody.appendChild(row);
    return;
  }

  const netClass = result.net_result >= 0 ? "pl-positive" : "pl-negative";
  row.innerHTML = `
    <td>${symbol}</td>
    <td>${result.signals_evaluated}</td>
    <td>${result.total_operations}</td>
    <td>${result.win_rate.toFixed(1)}%</td>
    <td>${result.profit_factor.toFixed(2)}</td>
    <td class="${netClass}">${result.net_result.toFixed(2)}</td>
    <td>${result.max_drawdown.toFixed(2)}</td>
  `;
  row.addEventListener("click", () => showBacktestDetail(symbol));
  summaryBody.appendChild(row);
}

function showBacktestDetail(symbol) {
  const result = backtestRunResults[symbol];
  if (!result) return;

  document.getElementById("backtest-detail-title").textContent = `Detalhe — ${symbol}`;
  renderBacktestResults(result);
  document.getElementById("backtest-results").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderBacktestResults(result) {
  const resultsEl = document.getElementById("backtest-results");
  resultsEl.style.display = "block";

  const kpiRow = document.getElementById("backtest-kpi-row");
  const netClass = result.net_result >= 0 ? "pl-positive" : "pl-negative";
  kpiRow.innerHTML = `
    <div class="kpi-card">
      <div class="kpi-label">Win Rate</div>
      <div class="kpi-value mono">${result.win_rate.toFixed(1)}%</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Profit Factor</div>
      <div class="kpi-value mono">${result.profit_factor.toFixed(2)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Resultado Líquido</div>
      <div class="kpi-value mono ${netClass}">${result.net_result.toFixed(2)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Drawdown Máx.</div>
      <div class="kpi-value mono">${result.max_drawdown.toFixed(2)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Capital Final</div>
      <div class="kpi-value mono">${result.final_capital.toFixed(2)}</div>
    </div>
  `;

  renderBacktestChart(result.capital_curve);

  const tbody = document.getElementById("backtest-trades-body");
  if (!result.trades.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-row">Nenhum sinal confirmado no período selecionado.</td></tr>`;
    return;
  }
  tbody.innerHTML = result.trades
    .map((t) => {
      const plClass = t.profit_loss >= 0 ? "pl-positive" : "pl-negative";
      return `
      <tr>
        <td>${t.direction}</td>
        <td>${fmt(t.entry_price)}</td>
        <td>${fmt(t.exit_price)}</td>
        <td>${t.result}</td>
        <td class="${plClass}">${t.profit_loss.toFixed(2)}</td>
        <td>${t.iqs_score.toFixed(0)}</td>
        <td>${new Date(t.opened_at).toLocaleString("pt-BR")}</td>
      </tr>`;
    })
    .join("");
}

function renderBacktestChart(curve) {
  const ctx = document.getElementById("backtest-chart");
  const labels = curve.map((_, i) => i);

  if (backtestChart) {
    backtestChart.data.labels = labels;
    backtestChart.data.datasets[0].data = curve;
    backtestChart.update();
    return;
  }

  backtestChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Capital",
        data: curve,
        borderColor: "#ffb454",
        backgroundColor: "rgba(255,180,84,0.08)",
        fill: true,
        tension: 0.25,
        pointRadius: 0,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8b95a7" }, grid: { color: "#232a3a" } },
        y: { ticks: { color: "#8b95a7" }, grid: { color: "#232a3a" } },
      },
    },
  });
}

init();
