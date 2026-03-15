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
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill the backend when the window is closed
                if let Some(state) = window.try_state::<BackendChild>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(child) = guard.take() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

async fn check_for_updates(handle: tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let update = handle.updater()?.check().await?;
    if let Some(update) = update {
        log::info!("Update available: {}", update.version);

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

        log::info!("Update installed, restart required");
    }
    Ok(())
}

struct BackendChild(std::sync::Mutex<Option<tauri_plugin_shell::process::CommandChild>>);
