use tauri::Manager;
use tauri_plugin_updater::UpdaterExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .build(),
        )
        .invoke_handler(tauri::generate_handler![check_update])
        .setup(|app| {
            // Spawn the Python backend as a sidecar process
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::ShellExt;
                let sidecar = handle.shell().sidecar("backend").unwrap()
                    .args(["--port", "8010"]);
                let (mut _rx, child) = sidecar.spawn().expect("Failed to spawn backend sidecar");
                handle.manage(BackendChild(std::sync::Mutex::new(Some(child))));
            });

            // Check for updates in background
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                // Wait for splash screen + window ready
                let wait = std::time::Duration::from_secs(8);
                tauri::async_runtime::spawn_blocking(move || std::thread::sleep(wait)).await.ok();

                let handle_clone = handle.clone();
                match check_for_updates(handle).await {
                    Ok(_) => {},
                    Err(e) => {
                        let err_msg = format!("{}", e);
                        log::warn!("Update check failed: {}", err_msg);
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

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/IM", "backend.exe"])
            .creation_flags(0x08000000)
            .output();
    }
}

async fn check_for_updates(handle: tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    log::info!("Checking for updates...");

    let updater = handle.updater()?;
    let update = updater.check().await?;

    if let Some(update) = update {
        let version = update.version.clone();
        log::info!("Update available: {}", version);

        // Use Tauri dialog plugin for a native OS dialog — reliable and blocking
        use tauri_plugin_dialog::{DialogExt, MessageDialogButtons};
        let user_said_yes = handle.dialog()
            .message(format!("Mise \u{00e0} jour v{} disponible.\n\nVoulez-vous mettre \u{00e0} jour maintenant ?", version))
            .title("Mise \u{00e0} jour ITManager")
            .buttons(MessageDialogButtons::OkCancelCustom("Mettre \u{00e0} jour".to_string(), "Plus tard".to_string()))
            .blocking_show();

        if !user_said_yes {
            log::info!("User declined update");
            return Ok(());
        }

        log::info!("User accepted update, starting download...");

        // Show progress overlay
        if let Some(window) = handle.get_webview_window("main") {
            let _ = window.eval(&format!(r#"
                (function() {{
                    var overlay = document.createElement('div');
                    overlay.id = '__update_overlay';
                    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.7);z-index:99999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(8px)';
                    overlay.innerHTML = '<div style="background:#1a1a2e;border-radius:16px;padding:40px;min-width:400px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.1)">' +
                        '<div style="font-size:40px;margin-bottom:16px">\u2B07\uFE0F</div>' +
                        '<div style="color:#fff;font-size:18px;font-weight:600;margin-bottom:8px">Mise \u00e0 jour v{}</div>' +
                        '<div id="__update_status" style="color:rgba(255,255,255,0.6);font-size:13px;margin-bottom:20px">T\u00e9l\u00e9chargement en cours...</div>' +
                        '<div style="background:rgba(255,255,255,0.1);border-radius:8px;height:8px;overflow:hidden;margin-bottom:12px">' +
                        '  <div id="__update_bar" style="height:100%;width:0%;background:linear-gradient(90deg,#4f46e5,#7c3aed);border-radius:8px;transition:width 0.3s ease"></div>' +
                        '</div>' +
                        '<div id="__update_pct" style="color:rgba(255,255,255,0.5);font-size:12px">0%</div>' +
                    '</div>';
                    document.body.appendChild(overlay);
                }})();
            "#, version));
        }

        // Backup before update
        log::info!("Creating pre-update backup...");
        let backup_client = reqwest::Client::new();
        match backup_client.post("http://localhost:8010/api/settings/backup/pre-update").send().await {
            Ok(resp) => log::info!("Pre-update backup: {}", resp.status()),
            Err(e) => log::warn!("Pre-update backup failed: {}", e),
        }

        // Download and install with progress
        let handle_dl = handle.clone();
        let mut downloaded: usize = 0;
        let install_result = update.download_and_install(
            move |chunk_length, content_length| {
                downloaded += chunk_length;
                if let Some(total) = content_length {
                    let pct = ((downloaded as f64 / total as f64) * 100.0).min(100.0) as u32;
                    let mb_down = downloaded as f64 / 1_048_576.0;
                    let mb_total = total as f64 / 1_048_576.0;
                    if let Some(window) = handle_dl.get_webview_window("main") {
                        let _ = window.eval(&format!(
                            "document.getElementById('__update_bar').style.width='{}%';\
                             document.getElementById('__update_pct').textContent='{:.1} Mo / {:.1} Mo ({}%)';"
                            , pct, mb_down, mb_total, pct));
                    }
                }
            },
            || {
                log::info!("Download finished, preparing install...");
            },
        ).await;

        match install_result {
            Ok(_) => {
                log::info!("Install succeeded, preparing restart...");

                // Show completion
                if let Some(window) = handle.get_webview_window("main") {
                    let _ = window.eval(
                        "document.getElementById('__update_status').textContent='Installation termin\u{00e9}e !';\
                         document.getElementById('__update_bar').style.width='100%';\
                         document.getElementById('__update_pct').textContent='Red\u{00e9}marrage dans 3 secondes...';"
                    );
                }

                // Kill backend before restart
                kill_backend(&handle);

                let delay = std::time::Duration::from_secs(3);
                tauri::async_runtime::spawn_blocking(move || std::thread::sleep(delay)).await.ok();

                log::info!("Restarting app now...");
                // Try restart, fallback to process::exit to let NSIS installer take over
                handle.restart();
                // If restart() didn't kill the process (shouldn't happen), force exit
                std::process::exit(0);
            }
            Err(e) => {
                log::error!("Update install failed: {}", e);
                if let Some(window) = handle.get_webview_window("main") {
                    let _ = window.eval(&format!(
                        "document.getElementById('__update_status').textContent='Erreur: {}';\
                         document.getElementById('__update_pct').textContent='Fermez et relancez manuellement.';\
                         document.getElementById('__update_bar').style.background='#ef4444';",
                        e.to_string().replace('\'', "\\'").replace('\n', " ")
                    ));
                }
                return Err(Box::new(e));
            }
        }
    } else {
        log::info!("No update available.");
        if let Some(window) = handle.get_webview_window("main") {
            let _ = window.eval("console.log('[Updater] App is up to date.')");
        }
    }
    Ok(())
}

#[tauri::command]
async fn check_update(handle: tauri::AppHandle) -> Result<String, String> {
    match check_for_updates(handle).await {
        Ok(_) => Ok("ok".to_string()),
        Err(e) => Err(format!("{}", e)),
    }
}

struct BackendChild(std::sync::Mutex<Option<tauri_plugin_shell::process::CommandChild>>);
