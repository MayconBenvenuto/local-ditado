// Local Ditado — shell desktop (Tauri 2).
//
// Responsabilidades do lado Rust (mínimas de propósito; a lógica vive no sidecar Python):
//   1. Subir o sidecar Python (`local-ditado-engine serve`) e ler a porta/token que ele
//      imprime no stdout como uma linha JSON.
//   2. Expor esse endereço para o frontend via o comando `get_server`.
//   3. Ícone de bandeja com "Abrir" e "Sair", e fechar a janela apenas a esconde.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    fs,
    net::{SocketAddr, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::Mutex,
    time::Duration,
};

use serde::{Deserialize, Serialize};
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager, State, WindowEvent,
};

#[derive(Default, Clone, Serialize)]
struct ServerInfo {
    host: String,
    port: u16,
    token: String,
    ready: bool,
    error: Option<String>,
}

#[derive(Deserialize)]
struct SidecarHello {
    host: String,
    port: u16,
    token: String,
}

#[derive(Default)]
struct RuntimeState {
    server: ServerInfo,
    sidecar: Option<Child>,
}

struct AppState(Mutex<RuntimeState>);

#[tauri::command]
fn get_server(state: State<AppState>) -> ServerInfo {
    let current = state.0.lock().unwrap().server.clone();
    if current.ready {
        return current;
    }
    read_server_file().unwrap_or(current)
}

fn server_file_path() -> Option<PathBuf> {
    std::env::var_os("APPDATA").map(|base| PathBuf::from(base).join("LocalDitado").join("server.json"))
}

fn can_reach(host: &str, port: u16) -> bool {
    let Ok(addr) = format!("{host}:{port}").parse::<SocketAddr>() else {
        return false;
    };
    TcpStream::connect_timeout(&addr, Duration::from_millis(250)).is_ok()
}

fn read_server_file() -> Option<ServerInfo> {
    let path = server_file_path()?;
    let raw = fs::read_to_string(path).ok()?;
    let hello = serde_json::from_str::<SidecarHello>(&raw).ok()?;
    if !can_reach(&hello.host, hello.port) {
        return None;
    }
    Some(ServerInfo {
        host: hello.host,
        port: hello.port,
        token: hello.token,
        ready: true,
        error: None,
    })
}

/// Locate the bundled sidecar executable. The onedir bundle lives at
/// `binaries/local-ditado-engine/`, which we try under both the installer's
/// resource directory and next to the running executable (dev / portable run).
fn find_sidecar(app: &tauri::AppHandle) -> Option<PathBuf> {
    let exe = if cfg!(windows) {
        "local-ditado-engine.exe"
    } else {
        "local-ditado-engine"
    };
    let relative = Path::new("binaries").join("local-ditado-engine").join(exe);

    let mut roots: Vec<PathBuf> = Vec::new();
    if let Ok(dir) = app.path().resource_dir() {
        roots.push(dir);
    }
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(dir) = exe_path.parent() {
            roots.push(dir.to_path_buf());
        }
    }
    roots
        .into_iter()
        .map(|root| root.join(&relative))
        .find(|candidate| candidate.exists())
}

fn spawn_sidecar(app: &tauri::AppHandle) {
    // Drop any stale server.json from a previous run. Until the fresh sidecar
    // writes a new one, `read_server_file` returns None instead of pointing the
    // frontend at a dead port (which would show a spurious "disconnected").
    if let Some(stale) = server_file_path() {
        let _ = fs::remove_file(stale);
    }

    let Some(path) = find_sidecar(app) else {
        eprintln!("Sidecar não encontrado no pacote.");
        let st = app.state::<AppState>();
        st.0.lock().unwrap().server.error =
            Some("sidecar não encontrado no pacote".to_string());
        return;
    };

    // We do not parse stdout: the sidecar advertises its host/port/token by
    // writing server.json (read by `read_server_file`). Discard stdio so a full
    // pipe buffer can never block the engine, and hide the console on Windows.
    let mut command = Command::new(&path);
    command
        .arg("serve")
        .env("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        .env("HF_HUB_DISABLE_XET", "1")
        .env("HF_HUB_VERBOSITY", "error")
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    match command.spawn() {
        Ok(child) => {
            app.state::<AppState>().0.lock().unwrap().sidecar = Some(child);
        }
        Err(e) => {
            eprintln!("Falha ao subir o sidecar: {e}");
            let st = app.state::<AppState>();
            st.0.lock().unwrap().server.error = Some(format!("falha ao iniciar sidecar: {e}"));
        }
    }
}

fn build_tray(app: &tauri::AppHandle) -> tauri::Result<()> {
    let open = MenuItem::with_id(app, "open", "Abrir", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Sair", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&open, &quit])?;

    TrayIconBuilder::new()
        .icon(app.default_window_icon().unwrap().clone())
        .menu(&menu)
        .tooltip("Local Ditado")
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open" => {
                if let Some(win) = app.get_webview_window("main") {
                    let _ = win.show();
                    let _ = win.set_focus();
                }
            }
            "quit" => app.exit(0),
            _ => {}
        })
        .build(app)?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState(Mutex::new(RuntimeState::default())))
        .invoke_handler(tauri::generate_handler![get_server])
        .setup(|app| {
            build_tray(app.handle())?;
            spawn_sidecar(app.handle());
            Ok(())
        })
        .on_window_event(|window, event| {
            // Fechar a janela apenas esconde — o serviço continua rodando na bandeja.
            if let WindowEvent::CloseRequested { api, .. } = event {
                window.hide().ok();
                api.prevent_close();
            }
        })
        .run(tauri::generate_context!())
        .expect("erro ao iniciar o Local Ditado");
}

fn main() {
    run();
}
