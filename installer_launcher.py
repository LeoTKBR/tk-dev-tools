from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path


WINDOWS_HIDE_CONSOLE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _message_box(title: str, message: str, flags: int = 0) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, flags)
    except Exception:
        pass


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resource_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return _base_dir()


def _bundle_dir() -> Path | None:
    search_roots = (_resource_dir(), _base_dir())
    for root in search_roots:
        direct = root / "TKDevTools"
        if (direct / "TKDevTools.exe").exists():
            return direct

        dist_build = root / "dist" / "TKDevTools"
        if (dist_build / "TKDevTools.exe").exists():
            return dist_build

        if (root / "TKDevTools.exe").exists():
            return root

    return None


def _install_dir() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise RuntimeError("LOCALAPPDATA is not available.")
    return Path(local_appdata) / "TKDevTools" / "app"


def _copy_bundle(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
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
        raise RuntimeError("Failed to copy the application files.")


def _launch_installed_app() -> None:
    installed_exe = _install_dir() / "TKDevTools.exe"
    if not installed_exe.exists():
        raise RuntimeError("Installed executable not found.")

    subprocess.Popen(
        [str(installed_exe)],
        cwd=str(installed_exe.parent),
        creationflags=WINDOWS_HIDE_CONSOLE,
    )


def main() -> None:
    try:
        bundle = _bundle_dir()
        install_dir = _install_dir()

        if bundle is not None:
            _copy_bundle(bundle, install_dir)
        elif not (install_dir / "TKDevTools.exe").exists():
            raise RuntimeError("No local build was found to install.")

        _launch_installed_app()
    except Exception as exc:
        _message_box("TK Dev Tools", str(exc), 0x10)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
