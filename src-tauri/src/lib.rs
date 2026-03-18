use tauri::Manager;
use tauri_plugin_updater::UpdaterExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Spawn the Python backend as a sidecar process
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::ShellExt;
                let sidecar = handle.shell().sidecar("backend").unwrap()
                    .args(["--port", "8010"]);
                let (mut _rx, child) = sidecar.spawn().expect("Failed to spawn backend sidecar");

                // Store the child process so it gets killed when the app exits
                handle.manage(BackendChild(std::sync::Mutex::new(Some(child))));
            });

            // Check for updates in background (only in release builds)
            if !cfg!(debug_assertions) {
                let handle = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    if let Err(e) = check_for_updates(handle).await {
                        log::warn!("Update check failed: {}", e);
                    }
                });
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            match event {
                tauri::RunEvent::WindowEvent {
                    event: tauri::WindowEvent::CloseRequested { .. },
                    ..
                } => {
                    kill_backend(app_handle);
                }
                tauri::RunEvent::Exit => {
                    kill_backend(app_handle);
                }
                _ => {}
            }
        });
}

fn kill_backend(handle: &tauri::AppHandle) {
    if let Some(state) = handle.try_state::<BackendChild>() {
        if let Ok(mut guard) = state.0.lock() {
            if let Some(child) = guard.take() {
                log::info!("Killing backend process...");
                let _ = child.kill();
            }
        }
    }

    // Fallback: force kill any remaining backend.exe via taskkill (Windows)
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/IM", "backend.exe"])
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .output();
    }
}

async fn check_for_updates(handle: tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    // Small delay to let the window load
    std::thread::sleep(std::time::Duration::from_secs(3));

    log::info!("Checking for updates...");
    let update = handle.updater()?.check().await?;
    if let Some(update) = update {
        log::info!("Update available: {}", update.version);

        // Show a dialog to the user
        let window = handle.get_webview_window("main").unwrap();
        let version = update.version.clone();
        let _ = window.eval(&format!(
            r#"
            (function() {{
                if (confirm('Une mise à jour est disponible (v{}).\n\nVoulez-vous la télécharger et l\'installer maintenant ?')) {{
                    document.title = 'Mise à jour en cours...';
                    window.__tauriUpdateAccepted = true;
                }} else {{
                    window.__tauriUpdateAccepted = false;
                }}
            }})()
            "#,
            version
        ));

        // Wait a moment for user response
        std::thread::sleep(std::time::Duration::from_secs(1));

        // Kill backend before update to release file locks
        kill_backend(&handle);

        // Download and install the update
        let mut downloaded = 0;
        update.download_and_install(
            |chunk_length, content_length| {
                downloaded += chunk_length;
                log::info!("Downloaded {} / {:?}", downloaded, content_length);
            },
            || {
                log::info!("Download finished, installing...");
            },
        ).await?;

        log::info!("Update installed, restarting...");
        handle.restart();
    } else {
        log::info!("No update available.");
    }
    Ok(())
}

struct BackendChild(std::sync::Mutex<Option<tauri_plugin_shell::process::CommandChild>>);
