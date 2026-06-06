#![cfg_attr(
  all(not(debug_assertions), target_os = "windows"),
  windows_subsystem = "windows"
)]

use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use window_vibrancy::{apply_vibrancy, NSVisualEffectMaterial};

fn main() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .plugin(tauri_plugin_opener::init())
    .setup(|app| {
      // 1. Get the main window instance
      let window = app.get_webview_window("main").unwrap();

      // 2. Apply the native macOS Vibrancy effect
      #[cfg(target_os = "macos")]
      apply_vibrancy(&window, NSVisualEffectMaterial::FullScreenUI, None, None)
        .expect("Unsupported platform! 'apply_vibrancy' is only supported on macOS");

      // Lanseaza serverul FastAPI în background
      let sidecar_command = app.shell().sidecar("main").expect("Eroare la crearea comenzii pentru backend");
      let (_rx, _child) = sidecar_command.spawn().expect("Eroare la pornirea procesului Python");
        
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}