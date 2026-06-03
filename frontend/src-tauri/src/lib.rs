// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

use tauri::Manager;
use window_vibrancy::{apply_vibrancy, NSVisualEffectMaterial, NSVisualEffectState};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();
            
            // Force the window theme to Dark so the vibrancy is aggressively dark
            let _ = window.set_theme(Some(tauri::Theme::Dark));

            #[cfg(target_os = "macos")]
            apply_vibrancy(
                &window, 
                NSVisualEffectMaterial::HudWindow, 
                Some(NSVisualEffectState::Active), 
                None
            ).expect("Failed to apply native macOS vibrancy");

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
