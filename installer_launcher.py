from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen
import zipfile


REPO_OWNER = "LeoTKBR"
REPO_NAME = "tk-dev-tools"
REPO_BRANCH = "main"
REPO_FULL_NAME = f"{REPO_OWNER}/{REPO_NAME}"
REPO_API_COMMIT_URL = f"https://api.github.com/repos/{REPO_FULL_NAME}/commits/{REPO_BRANCH}"
REPO_ZIP_URL = f"https://github.com/{REPO_FULL_NAME}/archive/refs/heads/{REPO_BRANCH}.zip"
PYTHON_INSTALLER_ID = "9NQ7512CXL7T"
INSTALL_ROOT_NAME = "TKDevTools"
WINDOWS_HIDE_CONSOLE = getattr(subprocess, "CREATE_NO_WINDOW", 0)

REQUIRED_FILES = (
    "launcher.py",
    "bootstrap_ui.py",
    "dependency_bootstrap.py",
    "qt_ui.py",
    "core_types.py",
    "dat_core.py",
    "generation_core.py",
    "spr_core.py",
    "icon.png",
    "loading.png",
)


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
    return Path(local_appdata) / INSTALL_ROOT_NAME / "app"


def _state_file() -> Path:
    return _install_dir() / ".repo-sha"


def _http_get_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "TK-Dev-Tools-Launcher"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def _http_download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "TK-Dev-Tools-Launcher"})
    with urlopen(request, timeout=60) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.read())


def _find_python_command() -> list[str] | None:
    for candidate in (["python"], ["py", "-3"]):
        try:
            completed = subprocess.run(
                [*candidate, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                creationflags=WINDOWS_HIDE_CONSOLE,
            )
            if completed.returncode == 0:
                return candidate
        except FileNotFoundError:
            continue
    return None


def _ensure_python() -> None:
    if _find_python_command() is not None:
        return

    winget = shutil.which("winget")
    if winget is None:
        raise RuntimeError("Python is missing and WinGet is not available.")

    install_command = [
        winget,
        "install",
        PYTHON_INSTALLER_ID,
        "-e",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ]
    completed = subprocess.run(
        install_command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=WINDOWS_HIDE_CONSOLE,
    )
    if completed.returncode != 0:
        raise RuntimeError("Failed to install the Python runtime manager.")

    if _find_python_command() is None:
        raise RuntimeError("Python is still unavailable after installation.")


def _remote_commit() -> str:
    payload = json.loads(_http_get_text(REPO_API_COMMIT_URL))
    sha = str(payload.get("sha") or "")
    if not sha:
        raise RuntimeError("Failed to read the latest repository commit from GitHub.")
    return sha


def _files_present(base: Path) -> bool:
    return all((base / filename).exists() for filename in REQUIRED_FILES)


def _sync_repository() -> None:
    remote_commit = _remote_commit()
    install_dir = _install_dir()
    local_commit = _state_file().read_text(encoding="utf-8").strip() if _state_file().exists() else ""

    if local_commit == remote_commit and _files_present(install_dir):
        return

    temp_root = Path(tempfile.mkdtemp(prefix="tk-dev-tools-launcher-"))
    try:
        zip_path = temp_root / "repo.zip"
        extract_dir = temp_root / "extract"
        _http_download(REPO_ZIP_URL, zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)

        source_dir = next(extract_dir.glob(f"{REPO_NAME}-*"), None)
        if source_dir is None:
            raise RuntimeError("Could not locate the extracted repository folder.")

        install_dir.mkdir(parents=True, exist_ok=True)
        for item in source_dir.rglob("*"):
            relative = item.relative_to(source_dir)
            destination = install_dir / relative
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, destination)

        _state_file().write_text(remote_commit, encoding="utf-8")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _launch_installed_launcher() -> None:
    python_cmd = _find_python_command()
    if python_cmd is None:
        raise RuntimeError("Python is not available for launching the project.")

    launcher = _install_dir() / "launcher.py"
    if not launcher.exists():
        raise RuntimeError("launcher.py was not found in the installed project files.")

    subprocess.Popen(
        [*python_cmd, str(launcher)],
        cwd=str(_install_dir()),
        creationflags=WINDOWS_HIDE_CONSOLE,
    )


def main() -> None:
    try:
        _ensure_python()
        _sync_repository()
        _launch_installed_launcher()
    except Exception as exc:
        _message_box("TK Dev Tools", str(exc), 0x10)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
