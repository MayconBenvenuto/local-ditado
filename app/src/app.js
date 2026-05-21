// Frontend do Local Ditado. Conversa com o sidecar Python (FastAPI + WebSocket).
// Descobre o endereço do sidecar via Tauri (comando `get_server`) ou via ?api= no dev.

const state = { base: null, ws: null, config: {} };

async function discoverServer() {
  // 1) Override de desenvolvimento: ?api=http://127.0.0.1:8000
  const params = new URLSearchParams(location.search);
  if (params.get("api")) return params.get("api");

  // 2) Via Tauri: o shell em Rust lê a porta do sidecar e expõe em get_server.
  if (window.__TAURI__?.core?.invoke) {
    for (let i = 0; i < 60; i++) {
      try {
        const info = await window.__TAURI__.core.invoke("get_server");
        if (info && info.ready) return `http://${info.host}:${info.port}`;
      } catch (_) { /* ainda subindo */ }
      await new Promise((r) => setTimeout(r, 500));
    }
  }
  return null;
}

async function api(path, options = {}) {
  const res = await fetch(state.base + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.status === 204 ? null : res.json();
}

function setConn(ok, text) {
  document.getElementById("conn-dot").className = "dot " + (ok ? "on" : "off");
  document.getElementById("conn-text").textContent = text;
}

// ---------------------------- WebSocket de eventos ----------------------------
function connectWs() {
  const url = state.base.replace("http", "ws") + "/ws";
  state.ws = new WebSocket(url);
  state.ws.onopen = () => setConn(true, "conectado");
  state.ws.onclose = () => { setConn(false, "desconectado"); setTimeout(connectWs, 1500); };
  state.ws.onmessage = (ev) => handleEvent(JSON.parse(ev.data));
}

function handleEvent({ event, payload }) {
  if (event === "level") {
    document.getElementById("meter-fill").style.width = Math.round(payload.level * 100) + "%";
  } else if (event === "recording_started") {
    setDictating(true, "gravando…");
  } else if (event === "transcribing") {
    setDictating(false, "transcrevendo…");
  } else if (event === "result") {
    document.getElementById("meter-fill").style.width = "0%";
    setDictating(false, "pronto");
    if (!payload.empty) {
      document.getElementById("last-result").textContent = payload.text || "(vazio)";
      if (location.hash === "#history") loadHistory();
    }
  } else if (event === "error") {
    setDictating(false, "erro: " + payload.message);
  } else if (event === "ready") {
    document.getElementById("stat-engine").textContent = `${payload.engine}/${payload.model}`;
  }
}

function setDictating(recording, status) {
  const btn = document.getElementById("btn-dictate");
  btn.classList.toggle("recording", recording);
  btn.textContent = recording ? "Parar" : "Ditar agora";
  document.getElementById("dictate-status").textContent = status;
}

// ---------------------------- Navegação ----------------------------
function showView(name) {
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + name));
  if (name === "history") loadHistory();
  if (name === "diagnostics") loadDiagnostics();
  if (name === "models") loadModels();
}

document.querySelectorAll(".nav-item").forEach((b) =>
  b.addEventListener("click", () => showView(b.dataset.view))
);

// ---------------------------- Dashboard ----------------------------
document.getElementById("btn-dictate").addEventListener("click", () => api("/api/toggle", { method: "POST" }));

async function loadStatus() {
  try {
    const s = await api("/api/status");
    if (s.engine) document.getElementById("stat-engine").textContent = `${s.engine}/${s.model}`;
    document.getElementById("stat-profile").textContent = s.profile || "—";
  } catch (_) {}
}

// ---------------------------- Configurações ----------------------------
async function loadConfig() {
  const cfg = await api("/api/config");
  state.config = cfg;
  const profs = await api("/api/profiles");
  const profSel = document.getElementById("cfg-profile");
  profSel.innerHTML = profs.profiles.map((p) => `<option value="${p}">${p}</option>`).join("");
  profSel.value = cfg.active_profile;

  const devs = await api("/api/devices");
  const devSel = document.getElementById("cfg-device");
  devSel.innerHTML = `<option value="">Padrão do sistema</option>` +
    devs.devices.map((d) => `<option value="${d.name}">${d.name}</option>`).join("");
  if (cfg.device_name) devSel.value = cfg.device_name;

  document.getElementById("cfg-model").value = cfg.whisper_model || "auto";
  document.getElementById("cfg-language").value = cfg.language || "pt";
  document.getElementById("cfg-hotkey").value = cfg.hotkey || "ctrl+alt+d";
  document.getElementById("cfg-silence").value = cfg.silence_seconds ?? 1.5;
  document.getElementById("cfg-vad").checked = (cfg.vad || "silero") === "silero";
  document.getElementById("cfg-denoise").checked = !!cfg.denoise;
  document.getElementById("cfg-voice").checked = cfg.voice_commands !== false;
  document.getElementById("cfg-cap").checked = cfg.capitalize !== false;
  document.getElementById("cfg-paste").checked = cfg.auto_paste !== false;
  document.getElementById("cfg-sound").checked = cfg.feedback_sound !== false;
  document.getElementById("cfg-rec").checked = !!cfg.save_recordings;
  document.getElementById("cfg-hotwords").value = cfg.hotwords || "";
  document.getElementById("stat-hotkey").textContent = cfg.hotkey || "ctrl+alt+d";

  const auto = await api("/api/autostart");
  document.getElementById("cfg-autostart").checked = auto.enabled;
}

document.getElementById("btn-save").addEventListener("click", async () => {
  const patch = {
    active_profile: document.getElementById("cfg-profile").value,
    device_name: document.getElementById("cfg-device").value || null,
    whisper_model: document.getElementById("cfg-model").value,
    language: document.getElementById("cfg-language").value,
    hotkey: document.getElementById("cfg-hotkey").value,
    silence_seconds: parseFloat(document.getElementById("cfg-silence").value),
    vad: document.getElementById("cfg-vad").checked ? "silero" : "rms",
    denoise: document.getElementById("cfg-denoise").checked,
    voice_commands: document.getElementById("cfg-voice").checked,
    capitalize: document.getElementById("cfg-cap").checked,
    auto_paste: document.getElementById("cfg-paste").checked,
    feedback_sound: document.getElementById("cfg-sound").checked,
    save_recordings: document.getElementById("cfg-rec").checked,
  };
  const status = document.getElementById("save-status");
  status.textContent = "salvando…";
  await api("/api/config", { method: "POST", body: JSON.stringify(patch) });
  await api("/api/autostart", { method: "POST", body: JSON.stringify({ enabled: document.getElementById("cfg-autostart").checked }) });
  status.textContent = "salvo ✓ (motor recarregando se necessário)";
  loadStatus();
});

// ---------------------------- Dicionário ----------------------------
function renderDict() {
  const dict = state.config.dictionary || {};
  document.getElementById("dict-body").innerHTML = Object.entries(dict)
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>→</td><td>${esc(v)}</td><td><button class="del" data-k="${esc(k)}">×</button></td></tr>`)
    .join("");
  document.querySelectorAll(".del").forEach((b) =>
    b.addEventListener("click", async () => {
      const dict = { ...(state.config.dictionary || {}) };
      delete dict[b.dataset.k];
      state.config = await api("/api/config", { method: "POST", body: JSON.stringify({ dictionary: dict }) });
      renderDict();
    })
  );
}

document.getElementById("dict-add").addEventListener("click", async () => {
  const from = document.getElementById("dict-from").value.trim();
  const to = document.getElementById("dict-to").value.trim();
  if (!from || !to) return;
  const dict = { ...(state.config.dictionary || {}), [from]: to };
  state.config = await api("/api/config", { method: "POST", body: JSON.stringify({ dictionary: dict }) });
  document.getElementById("dict-from").value = "";
  document.getElementById("dict-to").value = "";
  renderDict();
});

document.getElementById("btn-save-hotwords").addEventListener("click", async () => {
  state.config = await api("/api/config", {
    method: "POST",
    body: JSON.stringify({ hotwords: document.getElementById("cfg-hotwords").value }),
  });
});

// ---------------------------- Histórico ----------------------------
async function loadHistory() {
  const { entries } = await api("/api/history?limit=100");
  document.getElementById("history-list").innerHTML = entries.length
    ? entries.map((e) => `<div class="hist-item"><div>${esc(e.text)}</div>
        <div class="hist-meta">${e.ts || ""} · ${e.model || ""} · ${e.elapsed ?? "?"}s</div></div>`).join("")
    : `<p class="muted">Sem histórico ainda.</p>`;
}
document.getElementById("btn-clear-history").addEventListener("click", async () => {
  await api("/api/history", { method: "DELETE" });
  loadHistory();
});

// ---------------------------- Diagnóstico / Modelos ----------------------------
async function loadDiagnostics() {
  document.getElementById("diag-output").textContent = "carregando…";
  const d = await api("/api/diagnostics");
  document.getElementById("diag-output").textContent = JSON.stringify(d, null, 2);
}
document.getElementById("btn-refresh-diag").addEventListener("click", loadDiagnostics);

async function loadModels() {
  const d = await api("/api/diagnostics");
  const r = d.resolved_engine || {};
  document.getElementById("models-info").textContent =
    `Resolvido para este hardware: modelo=${r.model}, device=${r.device}, precisão=${r.compute_type}. ` +
    `GPU CUDA: ${d.hardware?.has_cuda ? "sim" : "não"} (VRAM ${d.hardware?.vram_mb}MB).`;
}

function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

// ---------------------------- Boot ----------------------------
(async function boot() {
  setConn(false, "procurando sidecar…");
  state.base = await discoverServer();
  if (!state.base) { setConn(false, "sidecar não encontrado"); return; }
  try {
    await loadConfig();
    await loadStatus();
    renderDict();
    connectWs();
    setConn(true, "conectado");
  } catch (e) {
    setConn(false, "erro: " + e.message);
  }
})();
