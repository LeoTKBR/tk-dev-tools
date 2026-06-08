from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from PySide6 import QtCore, QtGui, QtWidgets

from bootstrap_ui import apply_bootstrap_theme


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


def _resource_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return _base_dir()


def _icon_path() -> Path | None:
    candidates = (
        _resource_dir() / "icon.png",
        _base_dir() / "icon.png",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _install_dir() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise RuntimeError("LOCALAPPDATA is not available.")
    return Path(local_appdata) / INSTALL_ROOT_NAME / "app"


def _state_file() -> Path:
    return _install_dir() / ".repo-sha"


def _http_get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "TK-Dev-Tools-Launcher"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


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


def _ensure_python(log) -> None:
    python_cmd = _find_python_command()
    if python_cmd is not None:
        log(f"Python found: {' '.join(python_cmd)}")
        return

    winget = shutil.which("winget")
    if winget is None:
        raise RuntimeError("Python is missing and WinGet is not available.")

    log("Python is missing. Installing Python through WinGet...")
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
    if completed.stdout:
        log(completed.stdout.strip())
    if completed.returncode != 0:
        raise RuntimeError("Failed to install the Python runtime manager.")

    python_cmd = _find_python_command()
    if python_cmd is None:
        raise RuntimeError("Python is still unavailable after installation.")

    log(f"Python is now available: {' '.join(python_cmd)}")


def _get_remote_commit() -> str:
    payload = _http_get_json(REPO_API_COMMIT_URL)
    sha = str(payload.get("sha") or "")
    if not sha:
        raise RuntimeError("Failed to read the latest repository commit from GitHub.")
    return sha


def _files_present(base: Path) -> bool:
    return all((base / filename).exists() for filename in REQUIRED_FILES)


def _sync_repository(log) -> None:
    remote_commit = _get_remote_commit()
    install_dir = _install_dir()
    state_file = _state_file()
    local_commit = state_file.read_text(encoding="utf-8").strip() if state_file.exists() else ""
    files_present = _files_present(install_dir)

    if local_commit == remote_commit and files_present:
        log("Repository is already up to date.")
        return

    log("Updating repository files from GitHub...")
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

        state_file.write_text(remote_commit, encoding="utf-8")
        log("Repository updated successfully.")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _launcher_path() -> Path:
    return _install_dir() / "launcher.py"


def _open_tools(log) -> None:
    python_cmd = _find_python_command()
    if python_cmd is None:
        raise RuntimeError("Python is not available for launching the project.")

    launcher = _launcher_path()
    if not launcher.exists():
        raise RuntimeError("launcher.py was not found in the installed project files.")

    log("Opening the installed launcher...")
    subprocess.Popen(
        [*python_cmd, str(launcher)],
        cwd=str(_install_dir()),
        creationflags=WINDOWS_HIDE_CONSOLE,
    )


class BootstrapWorker(QtCore.QObject):
    status_changed = QtCore.Signal(str)
    log_line = QtCore.Signal(str)
    progress_mode_changed = QtCore.Signal(bool)
    finished = QtCore.Signal(bool, str)

    def log(self, message: str):
        self.log_line.emit(message)

    @QtCore.Slot()
    def run(self):
        try:
            self.progress_mode_changed.emit(True)
            self.status_changed.emit("Checking Python runtime...")
            _ensure_python(self.log)

            self.status_changed.emit("Syncing repository from GitHub...")
            _sync_repository(self.log)

            self.status_changed.emit("Ready.")
            self.progress_mode_changed.emit(False)
            self.finished.emit(True, "Ready. Press Open Tools to continue.")
        except Exception as exc:
            self.progress_mode_changed.emit(False)
            self.finished.emit(False, str(exc))


class BootstrapWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        icon = QtGui.QIcon(str(_icon_path())) if _icon_path() else QtGui.QIcon()
        if not icon.isNull():
            self.setWindowIcon(icon)

        self.setWindowTitle("TK Dev Tools Bootstrap")
        self.setMinimumSize(860, 560)
        self._thread: QtCore.QThread | None = None
        self._worker: BootstrapWorker | None = None

        self._build_ui()
        self._start_worker()

    def _build_ui(self):
        apply_bootstrap_theme(QtWidgets.QApplication.instance())

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QtWidgets.QFrame()
        header.setObjectName("HeaderCard")
        header_layout = QtWidgets.QVBoxLayout(header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(6)

        title = QtWidgets.QLabel("Preparing TK Dev Tools")
        title.setObjectName("Title")
        subtitle = QtWidgets.QLabel(
            "Checking the local environment, installing what is missing, and syncing the project from GitHub."
        )
        subtitle.setObjectName("Hint")
        subtitle.setWordWrap(True)
        self.status_label = QtWidgets.QLabel("Starting...")
        self.status_label.setObjectName("Status")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_layout.addWidget(self.status_label)

        content = QtWidgets.QFrame()
        content.setObjectName("ContentCard")
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(16, 14, 16, 14)
        content_layout.setSpacing(10)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)

        content_layout.addWidget(self.progress)
        content_layout.addWidget(self.log_text, 1)

        footer = QtWidgets.QHBoxLayout()
        footer.addStretch(1)
        self.open_tools_button = QtWidgets.QPushButton("Open Tools")
        self.open_tools_button.setEnabled(False)
        self.open_tools_button.clicked.connect(self._open_tools)
        footer.addWidget(self.open_tools_button)

        layout.addWidget(header)
        layout.addWidget(content, 1)
        layout.addLayout(footer)

    def _start_worker(self):
        self._thread = QtCore.QThread(self)
        self._worker = BootstrapWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.status_changed.connect(self.status_label.setText)
        self._worker.log_line.connect(self._append_log)
        self._worker.progress_mode_changed.connect(self._set_progress_mode)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _append_log(self, text: str):
        self.log_text.append(text)
        self.log_text.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def _set_progress_mode(self, busy: bool):
        self.progress.setRange(0, 0 if busy else 1)
        if not busy:
            self.progress.setValue(1)

    def _open_tools(self):
        try:
            self.status_label.setText("Opening Tools...")
            self.open_tools_button.setEnabled(False)
            _open_tools(self._append_log)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "TK Dev Tools", str(exc))
            self.status_label.setText("Ready. Press Open Tools to continue.")
            self.open_tools_button.setEnabled(True)
            return

        QtCore.QTimer.singleShot(200, QtWidgets.QApplication.instance().quit)

    def _on_finished(self, success: bool, message: str):
        self.status_label.setText(message)
        self._set_progress_mode(False)
        if success:
            self.open_tools_button.setEnabled(True)
        else:
            QtWidgets.QMessageBox.critical(self, "TK Dev Tools", message)


def main():
    app = QtWidgets.QApplication(sys.argv)
    apply_bootstrap_theme(app)
    icon = _icon_path()
    if icon is not None:
        app.setWindowIcon(QtGui.QIcon(str(icon)))
    window = BootstrapWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
