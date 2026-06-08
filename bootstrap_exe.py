from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from PySide6 import QtCore, QtGui, QtWidgets

from bootstrap_ui import apply_bootstrap_theme


REPO_OWNER = "LeoTKBR"
REPO_NAME = "tk-dev-tools"
REPO_BRANCH = "main"
REPO_FULL_NAME = f"{REPO_OWNER}/{REPO_NAME}"
REPO_URL = f"https://github.com/{REPO_FULL_NAME}"
REPO_API_COMMIT_URL = f"https://api.github.com/repos/{REPO_FULL_NAME}/commits/{REPO_BRANCH}"
REPO_ZIP_URL = f"https://github.com/{REPO_FULL_NAME}/archive/refs/heads/{REPO_BRANCH}.zip"
PYTHON_INSTALLER_ID = "9NQ7512CXL7T"
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

WINDOWS_HIDE_CONSOLE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def tools_dir() -> Path:
    return app_base_dir() / "tools"


def local_state_file() -> Path:
    return tools_dir() / ".repo-sha"


def bootstrap_icon_path() -> Path | None:
    candidates = (
        app_base_dir() / "_internal" / "icon.png",
        app_base_dir() / "icon.png",
        app_base_dir() / "tools" / "icon.png",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_bootstrap_icon() -> QtGui.QIcon:
    icon_path = bootstrap_icon_path()
    if icon_path is None:
        return QtGui.QIcon()
    return QtGui.QIcon(str(icon_path))


def http_get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "TK-Dev-Tools-Bootstrap"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def http_download(url: str, destination: Path) -> None:
    request = Request(url, headers={"User-Agent": "TK-Dev-Tools-Bootstrap"})
    with urlopen(request, timeout=60) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.read())


def find_python_command() -> list[str] | None:
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


def launch_launcher() -> None:
    python_cmd = find_python_command()
    if python_cmd is None:
        raise RuntimeError("Python is not available for launching the project.")

    launcher = tools_dir() / "launcher.py"
    if not launcher.exists():
        raise RuntimeError("launcher.py was not found inside the tools folder.")

    subprocess.Popen(
        [*python_cmd, str(launcher)],
        cwd=str(tools_dir()),
        creationflags=WINDOWS_HIDE_CONSOLE,
    )


class BootstrapWorker(QtCore.QObject):
    status_changed = QtCore.Signal(str)
    log_line = QtCore.Signal(str)
    progress_mode_changed = QtCore.Signal(bool)
    finished = QtCore.Signal(bool, str)

    def run(self):
        try:
            self.status_changed.emit("Checking repository...")
            self.ensure_repository()
            self.status_changed.emit("Checking Python runtime...")
            self.ensure_python()
            self.progress_mode_changed.emit(False)
            self.finished.emit(True, "Ready. Press Open Tools to continue.")
        except Exception as exc:
            self.progress_mode_changed.emit(False)
            self.finished.emit(False, str(exc))

    def log(self, message: str):
        self.log_line.emit(message)

    def ensure_repository(self):
        remote_commit = http_get_json(REPO_API_COMMIT_URL)["sha"]
        base = tools_dir()
        state = local_state_file()
        local_commit = state.read_text(encoding="utf-8").strip() if state.exists() else ""
        files_present = all((base / filename).exists() for filename in REQUIRED_FILES)

        if local_commit == remote_commit and files_present:
            self.log("Repository is already up to date.")
            return

        self.log("Updating repository files from GitHub...")
        temp_root = Path(tempfile.mkdtemp(prefix="tk-dev-tools-bootstrap-"))
        try:
            zip_path = temp_root / "repo.zip"
            extract_dir = temp_root / "extract"
            http_download(REPO_ZIP_URL, zip_path)
            shutil.unpack_archive(str(zip_path), str(extract_dir))

            source_dir = next(extract_dir.glob(f"{REPO_NAME}-*"), None)
            if source_dir is None:
                raise RuntimeError("Could not locate the extracted repository folder.")

            base.mkdir(parents=True, exist_ok=True)
            for item in source_dir.rglob("*"):
                relative = item.relative_to(source_dir)
                destination = base / relative
                if item.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, destination)

            state.write_text(remote_commit, encoding="utf-8")
            self.log("Repository updated successfully.")
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def ensure_python(self):
        python_cmd = find_python_command()
        if python_cmd is not None:
            self.log(f"Python found: {' '.join(python_cmd)}")
            return

        winget = shutil.which("winget")
        if winget is None:
            raise RuntimeError("Python is missing and WinGet is not available.")

        self.log("Python is missing. Installing the Python runtime manager through WinGet...")
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
            self.log(completed.stdout.strip())
        if completed.returncode != 0:
            raise RuntimeError("Failed to install the Python runtime manager.")

        python_cmd = find_python_command()
        if python_cmd is None:
            raise RuntimeError("Python is still unavailable after installation.")

        self.log(f"Python is now available: {' '.join(python_cmd)}")

class BootstrapWindow(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        icon = load_bootstrap_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)
        self.setWindowTitle("TK Dev Tools Bootstrap")
        self.setMinimumSize(820, 540)

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
            "Checking the local environment, syncing the project files, and preparing the launcher."
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
            launch_launcher()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "TK Dev Tools", str(exc))
            self.status_label.setText("Ready. Press Open Tools to continue.")
            self.open_tools_button.setEnabled(True)
            return

        QtCore.QTimer.singleShot(200, QtWidgets.QApplication.instance().quit)

    def _on_finished(self, success: bool, message: str):
        self.status_label.setText(message)
        if success:
            self._set_progress_mode(False)
            self.open_tools_button.setEnabled(True)
        else:
            self._set_progress_mode(False)
            QtWidgets.QMessageBox.critical(self, "TK Dev Tools", message)


def main():
    app = QtWidgets.QApplication(sys.argv)
    apply_bootstrap_theme(app)
    icon = load_bootstrap_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = BootstrapWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
