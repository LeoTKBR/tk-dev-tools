from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen


REPO_OWNER = "LeoTKBR"
REPO_NAME = "tk-dev-tools"
REPO_FULL_NAME = f"{REPO_OWNER}/{REPO_NAME}"
RELEASE_API_URL = f"https://api.github.com/repos/{REPO_FULL_NAME}/releases/latest"
APP_EXE_NAME = "TKDevTools.exe"
APP_INSTALL_ROOT = "TKDevTools"
WINDOWS_HIDE_CONSOLE = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_ASSET_NAME_RE = re.compile(r"(?i)(?:^|[^a-z0-9])tk[-_ ]?dev[-_ ]?tools(?:[^a-z0-9]|$)")


def _message_box(title: str, message: str, flags: int = 0) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, flags)
    except Exception:
        pass


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _install_dir() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise RuntimeError("LOCALAPPDATA is not available.")
    return Path(local_appdata) / APP_INSTALL_ROOT / "app"


def _state_file() -> Path:
    return _install_dir() / ".release-tag"


def _http_get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "TK-Dev-Tools-Launcher"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "TK-Dev-Tools-Launcher"})
    with urlopen(request, timeout=60) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.read())


def _latest_release() -> dict:
    return _http_get_json(RELEASE_API_URL)


def _select_release_asset(release: dict) -> dict:
    assets = release.get("assets", [])
    if not assets:
        raise RuntimeError(
            "No release assets were found on GitHub. "
            "Publish a release asset containing the TK Dev Tools build."
        )

    preferred = []
    for asset in assets:
        name = str(asset.get("name", ""))
        lower = name.lower()
        if "launcher" in lower:
            continue
        if not _ASSET_NAME_RE.search(name):
            continue
        preferred.append(asset)

    if not preferred:
        preferred = [asset for asset in assets if "launcher" not in str(asset.get("name", "")).lower()]

    zip_assets = [asset for asset in preferred if str(asset.get("name", "")).lower().endswith((".zip", ".7z"))]
    if zip_assets:
        return zip_assets[0]

    exe_assets = [asset for asset in preferred if str(asset.get("name", "")).lower().endswith(".exe")]
    if exe_assets:
        return exe_assets[0]

    return preferred[0]


def _mirror_directory(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    command = [
        "robocopy",
        str(source),
        str(destination),
        "/MIR",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS",
        "/NP",
        "/R:2",
        "/W:1",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=WINDOWS_HIDE_CONSOLE,
    )
    if completed.returncode >= 8:
        raise RuntimeError("Failed to copy the application files from the GitHub release.")


def _find_exe_root(extracted_root: Path) -> Path:
    candidates = list(extracted_root.rglob(APP_EXE_NAME))
    if not candidates:
        raise RuntimeError(f"{APP_EXE_NAME} was not found in the downloaded release.")
    return candidates[0].parent


def _install_from_release() -> str:
    release = _latest_release()
    tag = str(release.get("tag_name") or "")
    asset = _select_release_asset(release)
    asset_name = str(asset.get("name") or "release-asset")
    download_url = str(asset.get("browser_download_url") or "")
    if not download_url:
        raise RuntimeError(f"The selected asset '{asset_name}' does not have a download URL.")

    install_dir = _install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    temp_root = Path(tempfile.mkdtemp(prefix="tk-dev-tools-launcher-"))
    try:
        asset_path = temp_root / asset_name
        _http_download(download_url, asset_path)

        if asset_path.suffix.lower() == ".zip":
            extract_dir = temp_root / "extract"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(asset_path) as archive:
                archive.extractall(extract_dir)
            source_root = _find_exe_root(extract_dir)
            _mirror_directory(source_root, install_dir)
        elif asset_path.suffix.lower() == ".exe":
            shutil.copy2(asset_path, install_dir / APP_EXE_NAME)
        else:
            raise RuntimeError(
                f"Unsupported release asset format: {asset_name}. "
                "Use a .zip bundle or a standalone .exe release asset."
            )

        _state_file().write_text(tag, encoding="utf-8")
        return tag
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _launch_installed_app() -> None:
    installed_exe = _install_dir() / APP_EXE_NAME
    if not installed_exe.exists():
        raise RuntimeError("Installed TK Dev Tools executable was not found after installation.")

    subprocess.Popen(
        [str(installed_exe)],
        cwd=str(installed_exe.parent),
        creationflags=WINDOWS_HIDE_CONSOLE,
    )


def _needs_update(latest_tag: str) -> bool:
    state = _state_file()
    if not state.exists():
        return True
    try:
        current_tag = state.read_text(encoding="utf-8").strip()
    except OSError:
        return True
    return current_tag != latest_tag


def main() -> None:
    try:
        release = _latest_release()
        latest_tag = str(release.get("tag_name") or "")
        if _needs_update(latest_tag):
            _install_from_release()
        elif not (_install_dir() / APP_EXE_NAME).exists():
            _install_from_release()

        _launch_installed_app()
    except Exception as exc:
        _message_box("TK Dev Tools", str(exc), 0x10)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
