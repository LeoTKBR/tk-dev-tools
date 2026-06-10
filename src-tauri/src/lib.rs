use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use rayon::prelude::*;
use rayon::ThreadPoolBuilder;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager};
use tauri::window::Color;

mod core_types;
mod dat;
mod generation;
mod spr;

use core_types::Client;
use dat::DatManager;
use generation::{build_item_frames, build_jobs, collect_used_sprite_ids, is_blank_frame, save_gif};
use spr::SpriteManager;

const GITHUB_REPO_FULL_NAME: &str = "LeoTKBR/tk-dev-tools";
const GITHUB_REPO_URL: &str = "https://github.com/LeoTKBR/tk-dev-tools";

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct ArchitectureItem {
    title: &'static str,
    description: &'static str,
    details: [&'static str; 4],
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct AppOverview {
    app_name: &'static str,
    tagline: &'static str,
    current_phase: &'static str,
    next_target: &'static str,
    modules: [ArchitectureItem; 3],
    workstreams: [ArchitectureItem; 3],
    principles: [&'static str; 4],
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct GenerateRequest {
    client_version: u32,
    spr_path: String,
    dat_path: String,
    output_dir: String,
    only_pickable: bool,
    use_range: bool,
    start_id: Option<u32>,
    end_id: Option<u32>,
    frame_delay_ms: u32,
    workers: u32,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct GenerateSummary {
    total_jobs: usize,
    written_files: Vec<String>,
    skipped_blank: usize,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct IntegrityFileReport {
    path: String,
    status: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct IntegrityReport {
    repo: String,
    default_branch: String,
    checked_files: usize,
    matches: usize,
    changed: usize,
    missing: usize,
    repaired: usize,
    files: Vec<IntegrityFileReport>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct GenerationEvent {
    kind: String,
    message: String,
    done: Option<usize>,
    total: Option<usize>,
    output_id: Option<u32>,
    output_file: Option<String>,
}

#[tauri::command]
fn get_app_overview() -> AppOverview {
    AppOverview {
        app_name: "TK Dev Tools",
        tagline: "A Rust + React + Tauri foundation for the Python tool suite.",
        current_phase: "Architecture scaffold",
        next_target: "Port the GIF Generator core into Rust.",
        modules: [
            ArchitectureItem {
                title: "Core",
                description: "Binary parsing, sprite decoding, frame assembly, integrity checks.",
                details: ["DAT parser", "SPR parser", "GIF renderer", "Integrity verifier"],
            },
            ArchitectureItem {
                title: "Shell",
                description: "Tauri commands and app state that connect the UI to Rust.",
                details: ["Typed commands", "Progress events", "File dialogs", "Open-folder actions"],
            },
            ArchitectureItem {
                title: "UI",
                description: "React workspace for the generator and future admin tools.",
                details: ["Hero dashboard", "Generator workspace", "Log panel", "Extensible tabs"],
            },
        ],
        workstreams: [
            ArchitectureItem {
                title: "Phase 1",
                description: "Recreate the current Python feature set with clear boundaries.",
                details: ["Project shell", "App identity", "Architecture map", "Command contract"],
            },
            ArchitectureItem {
                title: "Phase 2",
                description: "Move the GIF generator logic to Rust without changing the workflow.",
                details: ["File parsing", "Rendering pipeline", "Background jobs", "Progress reporting"],
            },
            ArchitectureItem {
                title: "Phase 3",
                description: "Add the remaining tools and polish the product for daily use.",
                details: ["More tabs", "Persistent settings", "Better packaging", "Release workflow"],
            },
        ],
        principles: [
            "Keep the current workflow recognizable for existing users.",
            "Move reusable logic into Rust and keep the UI declarative.",
            "Expose only the commands the front end needs.",
            "Design for future tools, not just the first generator.",
        ],
    }
}

#[tauri::command]
fn select_spr_file() -> Option<String> {
    rfd::FileDialog::new()
        .add_filter("Tibia SPR", &["spr"])
        .pick_file()
        .map(|path| path.to_string_lossy().to_string())
}

#[tauri::command]
fn select_dat_file() -> Option<String> {
    rfd::FileDialog::new()
        .add_filter("Tibia DAT", &["dat"])
        .pick_file()
        .map(|path| path.to_string_lossy().to_string())
}

#[tauri::command]
fn select_output_dir() -> Option<String> {
    rfd::FileDialog::new()
        .pick_folder()
        .map(|path| path.to_string_lossy().to_string())
}

#[derive(Deserialize)]
struct RepoInfo {
    default_branch: String,
}

#[derive(Deserialize)]
struct CommitInfo {
    commit: CommitDetails,
}

#[derive(Deserialize)]
struct CommitDetails {
    tree: TreePointer,
}

#[derive(Deserialize)]
struct TreePointer {
    sha: String,
}

#[derive(Deserialize)]
struct TreeInfo {
    tree: Vec<TreeEntry>,
    truncated: bool,
}

#[derive(Deserialize)]
struct TreeEntry {
    path: String,
    #[serde(rename = "type")]
    entry_type: String,
}

fn read_local_bytes(path: &Path) -> Option<Vec<u8>> {
    fs::read(path).ok()
}

fn http_client() -> Result<reqwest::blocking::Client, String> {
    reqwest::blocking::Client::builder()
        .user_agent("TK-Dev-Tools/1.0")
        .build()
        .map_err(|err| err.to_string())
}

fn get_remote_json<T: serde::de::DeserializeOwned>(client: &reqwest::blocking::Client, url: &str) -> Result<T, String> {
    client
        .get(url)
        .send()
        .and_then(|response| response.error_for_status())
        .map_err(|err| err.to_string())?
        .json::<T>()
        .map_err(|err| err.to_string())
}

fn get_remote_bytes(client: &reqwest::blocking::Client, url: &str) -> Result<Vec<u8>, String> {
    client
        .get(url)
        .send()
        .and_then(|response| response.error_for_status())
        .map_err(|err| err.to_string())?
        .bytes()
        .map_err(|err| err.to_string())
        .map(|bytes| bytes.to_vec())
}

fn derive_output_root(dat_path: &Path, spr_path: &Path) -> Result<PathBuf, String> {
    let base_dir = dat_path
        .parent()
        .or_else(|| spr_path.parent())
        .ok_or_else(|| "Unable to determine output directory from DAT/SPR paths".to_string())?;
    Ok(base_dir.join("generate").join("gifs"))
}

fn integrity_root(app: &AppHandle) -> Result<PathBuf, String> {
    let root = app
        .path()
        .app_local_data_dir()
        .map_err(|err| err.to_string())?
        .join("integrity-cache");
    fs::create_dir_all(&root).map_err(|err| err.to_string())?;
    Ok(root)
}

fn fetch_remote_blobs(
    client: &reqwest::blocking::Client,
    repo_full_name: &str,
    branch: &str,
) -> Result<Vec<TreeEntry>, String> {
    let commit_url = format!("https://api.github.com/repos/{}/commits/{}", repo_full_name, branch);
    let commit_info: CommitInfo = get_remote_json(client, &commit_url)?;
    let tree_url = format!(
        "https://api.github.com/repos/{}/git/trees/{}?recursive=1",
        repo_full_name,
        commit_info.commit.tree.sha
    );
    let tree_info: TreeInfo = get_remote_json(client, &tree_url)?;

    if tree_info.truncated {
        return Err("Remote repository tree was truncated by GitHub".to_string());
    }

    Ok(tree_info
        .tree
        .into_iter()
        .filter(|entry| entry.entry_type == "blob")
        .collect())
}

#[tauri::command]
async fn generate_gifs(app: AppHandle, request: GenerateRequest) -> Result<GenerateSummary, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let emit = |event: GenerationEvent| {
            let _ = app.emit("generation://event", event);
        };

        let client = Client::new(request.client_version);
        let dat_path = PathBuf::from(&request.dat_path);
        let spr_path = PathBuf::from(&request.spr_path);
        let output_dir = if request.output_dir.trim().is_empty() {
            derive_output_root(&dat_path, &spr_path)?
        } else {
            PathBuf::from(&request.output_dir)
        };

        emit(GenerationEvent {
            kind: "log".to_string(),
            message: format!("Client version: {}", request.client_version),
            done: None,
            total: None,
            output_id: None,
            output_file: None,
        });
        emit(GenerationEvent {
            kind: "log".to_string(),
            message: "Loading DAT...".to_string(),
            done: None,
            total: None,
            output_id: None,
            output_file: None,
        });

        let mut dat = DatManager::new(Client::new(request.client_version));
        dat.load_dat(&dat_path)?;

        emit(GenerationEvent {
            kind: "log".to_string(),
            message: "DAT loaded".to_string(),
            done: None,
            total: None,
            output_id: None,
            output_file: None,
        });

        let start_id = if request.use_range { request.start_id } else { None };
        let end_id = if request.use_range { request.end_id } else { None };
        let jobs = build_jobs(&dat, request.only_pickable, start_id, end_id);
        if jobs.is_empty() {
            return Err("No items matched the selected filters.".to_string());
        }

        emit(GenerationEvent {
            kind: "log".to_string(),
            message: format!("Found {} item(s)", jobs.len()),
            done: None,
            total: Some(jobs.len()),
            output_id: None,
            output_file: None,
        });
        emit(GenerationEvent {
            kind: "log".to_string(),
            message: "Loading SPR...".to_string(),
            done: None,
            total: None,
            output_id: None,
            output_file: None,
        });

        let used_sprite_ids = collect_used_sprite_ids(&dat, &jobs);
        let mut sprites = SpriteManager::new(client);
        sprites.load_spr(&spr_path, Some(&used_sprite_ids))?;

        emit(GenerationEvent {
            kind: "log".to_string(),
            message: format!("Loaded SPR with {} used sprite(s)", used_sprite_ids.len()),
            done: None,
            total: None,
            output_id: None,
            output_file: None,
        });

        let total = jobs.len();
        let progress = Arc::new(AtomicUsize::new(0));
        let worker_count = request.workers.max(1) as usize;
        let pool = ThreadPoolBuilder::new()
            .num_threads(worker_count)
            .build()
            .map_err(|err| err.to_string())?;

        #[derive(Debug)]
        struct JobOutcome {
            output_file: Option<String>,
            skipped_blank: bool,
        }

        let app_handle = app.clone();
        let outcomes = pool.install(|| {
            jobs.par_iter()
                .map(|(output_id, client_id)| -> Result<JobOutcome, String> {
                    let thing = dat
                        .get_item(*client_id)
                        .ok_or_else(|| format!("Missing DAT item {}", client_id))?;
                    let (frames, durations) = build_item_frames(thing, &sprites, request.frame_delay_ms)?;
                    if frames.is_empty() || frames.iter().all(is_blank_frame) {
                        let done = progress.fetch_add(1, Ordering::SeqCst) + 1;
                        let _ = app_handle.emit(
                            "generation://event",
                            GenerationEvent {
                                kind: "progress".to_string(),
                                message: format!("Skipped blank item {}", output_id),
                                done: Some(done),
                                total: Some(total),
                                output_id: Some(*output_id),
                                output_file: None,
                            },
                        );
                        return Ok(JobOutcome {
                            output_file: None,
                            skipped_blank: true,
                        });
                    }

                    let out_file = output_dir.join("items").join(format!("{}.gif", output_id));
                    save_gif(&frames, &out_file, &durations)?;
                    let out_file_string = out_file.to_string_lossy().to_string();
                    let done = progress.fetch_add(1, Ordering::SeqCst) + 1;
                    let _ = app_handle.emit(
                        "generation://event",
                        GenerationEvent {
                            kind: "progress".to_string(),
                            message: format!("Done {}", output_id),
                            done: Some(done),
                            total: Some(total),
                            output_id: Some(*output_id),
                            output_file: Some(out_file_string.clone()),
                        },
                    );
                    Ok(JobOutcome {
                        output_file: Some(out_file_string),
                        skipped_blank: false,
                    })
                })
                .collect::<Vec<_>>()
        });

        let mut written_files = Vec::new();
        let mut skipped_blank = 0usize;
        for outcome in outcomes {
            let outcome = outcome?;
            if outcome.skipped_blank {
                skipped_blank += 1;
            }
            if let Some(path) = outcome.output_file {
                written_files.push(path);
            }
        }

        emit(GenerationEvent {
            kind: "done".to_string(),
            message: format!("Finished in {}", output_dir.to_string_lossy()),
            done: Some(total),
            total: Some(total),
            output_id: None,
            output_file: Some(output_dir.to_string_lossy().to_string()),
        });

        Ok(GenerateSummary {
            total_jobs: total,
            written_files,
            skipped_blank,
        })
    })
    .await
    .map_err(|err| err.to_string())?
}

#[tauri::command]
async fn check_integrity(app: AppHandle) -> Result<IntegrityReport, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let client = http_client()?;
        let repo_url = format!("https://api.github.com/repos/{}", GITHUB_REPO_FULL_NAME);
        let repo_info: RepoInfo = get_remote_json(&client, &repo_url)?;
        let blobs = fetch_remote_blobs(&client, GITHUB_REPO_FULL_NAME, &repo_info.default_branch)?;
        let checked_files = blobs.len();
        let local_root = integrity_root(&app)?;

        let mut files = Vec::new();
        let mut matches = 0usize;
        let mut changed = 0usize;
        let mut missing = 0usize;
        let mut repaired = 0usize;

        for entry in blobs {
            let relative_path = entry.path;
            let local_path = local_root.join(&relative_path);
            let local_bytes = read_local_bytes(&local_path);
            let raw_url = format!(
                "https://raw.githubusercontent.com/{}/{}/{}",
                GITHUB_REPO_FULL_NAME,
                repo_info.default_branch,
                relative_path.as_str()
            );
            let remote_bytes = get_remote_bytes(&client, &raw_url);

            match (local_bytes, remote_bytes) {
                (Some(local), Ok(remote)) if local == remote => {
                    matches += 1;
                    files.push(IntegrityFileReport {
                        path: relative_path.clone(),
                        status: "match".to_string(),
                    });
                }
                (Some(_), Ok(remote)) => {
                    changed += 1;
                    if let Some(parent) = local_path.parent() {
                        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
                    }
                    fs::write(local_path, &remote).map_err(|err| err.to_string())?;
                    repaired += 1;
                    files.push(IntegrityFileReport {
                        path: relative_path.clone(),
                        status: "repaired".to_string(),
                    });
                }
                (None, Ok(remote)) => {
                    missing += 1;
                    if let Some(parent) = local_path.parent() {
                        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
                    }
                    fs::write(local_path, &remote).map_err(|err| err.to_string())?;
                    repaired += 1;
                    files.push(IntegrityFileReport {
                        path: relative_path.clone(),
                        status: "repaired".to_string(),
                    });
                }
                (_, Err(err)) => {
                    files.push(IntegrityFileReport {
                        path: relative_path,
                        status: format!("error: {}", err),
                    });
                }
            }
        }

        Ok(IntegrityReport {
            repo: GITHUB_REPO_URL.to_string(),
            default_branch: repo_info.default_branch,
            checked_files,
            matches,
            changed,
            missing,
            repaired,
            files,
        })
    })
    .await
    .map_err(|err| err.to_string())?
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            if let Some(main_window) = app.get_webview_window("main") {
                let _ = main_window.set_background_color(Some(Color(10, 8, 9, 255)));
                if let Ok(decoded_icon) = image::load_from_memory(include_bytes!("../../public/icon.png")) {
                    let icon = tauri::image::Image::new_owned(
                        decoded_icon.to_rgba8().into_raw(),
                        decoded_icon.width(),
                        decoded_icon.height(),
                    );
                    let _ = main_window.set_icon(icon);
                }
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_app_overview,
            select_spr_file,
            select_dat_file,
            select_output_dir,
            generate_gifs,
            check_integrity
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
