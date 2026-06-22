// Frontend do Local Ditado. Conversa com o sidecar Python (FastAPI + WebSocket).
// Descobre o endereço do sidecar via Tauri (comando `get_server`) ou via ?api= no dev.

const DEFAULT_PROFILES = ["equilibrado", "precisao", "rapido"];
const state = { base: null, ws: null, config: {} };

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeBase(url) {
  return String(url || "").replace(/\/+$/, "");
}

async function discoverServer({ preferQuery = true } = {}) {
  // 1) Override de desenvolvimento: ?api=http://127.0.0.1:8000
  const params = new URLSearchParams(location.search);
  if (preferQuery && params.get("api")) return normalizeBase(params.get("api"));

  // 2) Via Tauri: o shell em Rust lê a porta do sidecar e expõe em get_server.
  if (window.__TAURI__?.core?.invoke) {
    for (let i = 0; ; i++) {
      try {
        const info = await window.__TAURI__.core.invoke("get_server");
        if (info?.error) {
          setConn(false, info.error);
          return null;
        }
        if (info && info.ready) return normalizeBase(`http://${info.host}:${info.port}`);
      } catch (_) { /* ainda subindo */ }
      if (i === 60) setConn(false, "sidecar iniciando…");
      if (i === 180) setConn(false, "sidecar ainda carregando…");
      await sleep(500);
    }
  }
  return null;
}

async function readJson(res, path) {
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${path}: ${text.slice(0, 120)}`);
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch (error) {
    error.nonJsonResponse = true;
    error.message = `resposta não-JSON de ${res.url || path}: ${text.trim().slice(0, 80)}`;
    throw error;
  }
}

async function api(path, options = {}, retry = true) {
  if (!state.base) {
    state.base = await discoverServer({ preferQuery: false });
  }
  if (!state.base) {
    setConn(false, "sidecar não conectado");
    throw new Error("sidecar não conectado");
  }
  let res;
  try {
    res = await fetch(state.base + path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (error) {
    // A network-level failure ("Failed to fetch") means the cached base is stale —
    // the sidecar picks a new ephemeral port on each launch. Re-discover and retry.
    if (!retry || !window.__TAURI__?.core?.invoke) throw error;
    const rediscovered = await discoverServer({ preferQuery: false });
    if (!rediscovered) throw error;
    state.base = rediscovered;
    return api(path, options, false);
  }
  try {
    return await readJson(res, path);
  } catch (error) {
    if (!retry || !error.nonJsonResponse || !window.__TAURI__?.core?.invoke) throw error;
    const rediscovered = await discoverServer({ preferQuery: false });
    if (!rediscovered || rediscovered === state.base) throw error;
    state.base = rediscovered;
    return api(path, options, false);
  }
}

function setConn(ok, text) {
  document.getElementById("conn-dot").className = "dot " + (ok ? "on" : "off");
  document.getElementById("conn-text").textContent = text;
}

// ---------------------------- WebSocket de eventos ----------------------------
async function connectWs() {
  // The sidecar picks a fresh ephemeral port on each launch, so on every
  // (re)connect we re-discover the address instead of reusing a stale port.
  state.base = await discoverServer({ preferQuery: false });
  if (!state.base) { setTimeout(connectWs, 1500); return; }
  const url = state.base.replace(/^http/, "ws") + "/ws";
  state.ws = new WebSocket(url);
  state.ws.onopen = () => setConn(true, "conectado");
  state.ws.onerror = () => { try { state.ws.close(); } catch (_) { /* ignore */ } };
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
  if (name === "settings") loadConfig();
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
function setSelectOptions(select, options, selectedValue = "") {
  select.replaceChildren();
  for (const option of options) {
    const el = document.createElement("option");
    el.value = option.value;
    el.textContent = option.label;
    select.appendChild(el);
  }
  select.value = selectedValue;
}

async function loadConfig() {
  const cfg = await api("/api/config");
  state.config = cfg;

  const profSel = document.getElementById("cfg-profile");
  setSelectOptions(
    profSel,
    DEFAULT_PROFILES.map((p) => ({ value: p, label: p })),
    cfg.active_profile || "equilibrado"
  );

  const profs = await api("/api/profiles");
  const profiles = Array.isArray(profs.profiles) && profs.profiles.length
    ? profs.profiles
    : DEFAULT_PROFILES;
  if (!profiles.includes(cfg.active_profile)) profiles.unshift(cfg.active_profile);
  setSelectOptions(profSel, profiles.map((p) => ({ value: p, label: p })), cfg.active_profile);

  const devSel = document.getElementById("cfg-device");
  setSelectOptions(devSel, [{ value: "", label: "Padrão do sistema" }], cfg.device_name || "");

  const devs = await api("/api/devices");
  const devices = (devs.devices || []).map((d) => ({
    value: d.name,
    label: `${d.name} (${Math.round(d.default_sample_rate)} Hz)`,
  }));
  setSelectOptions(
    devSel,
    [{ value: "", label: "Padrão do sistema" }, ...devices],
    cfg.device_name || ""
  );
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
  const silenceSeconds = parseFloat(document.getElementById("cfg-silence").value);
  const patch = {
    active_profile: document.getElementById("cfg-profile").value,
    device_name: document.getElementById("cfg-device").value || null,
    whisper_model: document.getElementById("cfg-model").value || "auto",
    language: document.getElementById("cfg-language").value || "pt",
    hotkey: document.getElementById("cfg-hotkey").value.trim() || "ctrl+alt+d",
    silence_seconds: Number.isFinite(silenceSeconds) ? silenceSeconds : 1.5,
    vad: document.getElementById("cfg-vad").checked ? "silero" : "rms",
    denoise: document.getElementById("cfg-denoise").checked,
    voice_commands: document.getElementById("cfg-voice").checked,
    capitalize: document.getElementById("cfg-cap").checked,
    auto_paste: document.getElementById("cfg-paste").checked,
    feedback_sound: document.getElementById("cfg-sound").checked,
    save_recordings: document.getElementById("cfg-rec").checked,
  };
  const status = document.getElementById("save-status");
  const button = document.getElementById("btn-save");
  button.disabled = true;
  status.textContent = "salvando…";
  try {
    state.config = await api("/api/config", { method: "POST", body: JSON.stringify(patch) });
    await api("/api/autostart", { method: "POST", body: JSON.stringify({ enabled: document.getElementById("cfg-autostart").checked }) });
    status.textContent = "salvo ✓ (motor recarregando se necessário)";
    loadStatus();
  } catch (e) {
    status.textContent = "erro ao salvar: " + e.message;
  } finally {
    button.disabled = false;
  }
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
  try {
    state.base = await discoverServer();
    if (!state.base) { setConn(false, "sidecar não encontrado"); return; }
    await loadConfig();
    await loadStatus();
    renderDict();
    connectWs();
    setConn(true, "conectado");
  } catch (e) {
    setConn(false, "erro: " + e.message);
  }
})();
