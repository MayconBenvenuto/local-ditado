// Local Ditado — shell desktop (Tauri 2).
//
// Responsabilidades do lado Rust (mínimas de propósito; a lógica vive no sidecar Python):
//   1. Subir o sidecar Python (`local-ditado-engine serve`) e ler a porta/token que ele
//      imprime no stdout como uma linha JSON.
//   2. Expor esse endereço para o frontend via o comando `get_server`.
//   3. Ícone de bandeja com "Abrir" e "Sair", e fechar a janela apenas a esconde.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;

use serde::{Deserialize, Serialize};
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager, State, WindowEvent,
};
use tauri_plugin_shell::process::CommandEvent;
use tauri_plugin_shell::ShellExt;

#[derive(Default, Clone, Serialize)]
struct ServerInfo {
    host: String,
    port: u16,
    token: String,
    ready: bool,
}

#[derive(Deserialize)]
struct SidecarHello {
    host: String,
    port: u16,
    token: String,
}

struct AppState(Mutex<ServerInfo>);

#[tauri::command]
fn get_server(state: State<AppState>) -> ServerInfo {
    state.0.lock().unwrap().clone()
}

fn spawn_sidecar(app: &tauri::AppHandle) {
    let sidecar = match app.shell().sidecar("local-ditado-engine") {
        Ok(cmd) => cmd.args(["serve"]),
        Err(e) => {
            eprintln!("Falha ao localizar o sidecar: {e}");
            return;
        }
    };
    let (mut rx, _child) = match sidecar.spawn() {
        Ok(pair) => pair,
        Err(e) => {
            eprintln!("Falha ao subir o sidecar: {e}");
            return;
        }
    };

    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            if let CommandEvent::Stdout(line) = event {
                if let Ok(hello) = serde_json::from_slice::<SidecarHello>(&line) {
                    let st = handle.state::<AppState>();
                    let mut info = st.0.lock().unwrap();
                    *info = ServerInfo {
                        host: hello.host,
                        port: hello.port,
                        token: hello.token,
                        ready: true,
                    };
                }
            }
        }
    });
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
        .plugin(tauri_plugin_shell::init())
        .manage(AppState(Mutex::new(ServerInfo::default())))
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
