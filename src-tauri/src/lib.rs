use tauri::Manager;
use tauri_plugin_updater::UpdaterExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .setup(|app| {
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

            // Check for updates in background
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                // Wait 5 seconds for the window to be ready
                let five_secs = std::time::Duration::from_secs(5);
                tauri::async_runtime::spawn_blocking(move || std::thread::sleep(five_secs)).await.ok();

                let handle_clone = handle.clone();
                match check_for_updates(handle).await {
                    Ok(_) => {},
                    Err(e) => {
                        let err_msg = format!("{}", e);
                        log::warn!("Update check failed: {}", err_msg);
                        // Show error in webview for debugging
                        if let Some(window) = handle_clone.get_webview_window("main") {
                            let _ = window.eval(&format!(
                                "console.error('Update check error: {}')",
                                err_msg.replace('\'', "\\'").replace('\n', " ")
                            ));
                        }
                    }
                }
            });

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
    log::info!("Checking for updates...");

    let updater = handle.updater()?;
    let update = updater.check().await?;

    if let Some(update) = update {
        log::info!("Update available: {}", update.version);

        // Show a confirm dialog via JavaScript
        if let Some(window) = handle.get_webview_window("main") {
            let version = update.version.clone();
            let _ = window.eval(&format!(
                "alert('Mise à jour disponible : v{}')",
                version
            ));
        }

        // Kill backend before update to release file locks
        kill_backend(&handle);

        // Download and install the update
        let mut downloaded: usize = 0;
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
        log::info!("No update available - app is up to date.");
        // Debug: show in console
        if let Some(window) = handle.get_webview_window("main") {
            let _ = window.eval("console.log('[Updater] No update available - app is up to date.')");
        }
    }
    Ok(())
}

struct BackendChild(std::sync::Mutex<Option<tauri_plugin_shell::process::CommandChild>>);
