from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from dependency_bootstrap import REQUIRED_REQUIREMENTS, RequirementStatus, get_missing_requirements


APP_DIR = Path(__file__).resolve().parent
APP_ICON_PATH = APP_DIR / "icon.png"


def apply_bootstrap_theme(app: QtWidgets.QApplication):
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QWidget {
            background-color: #18181c;
            color: #eaeaea;
        }
        QDialog {
            background-color: #18181c;
        }
        QFrame#HeaderCard, QFrame#ContentCard {
            background-color: #1d1d22;
            border: 1px solid #31313a;
            border-radius: 10px;
        }
        QLabel#Title {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
        }
        QLabel#Status {
            color: #9dc5ff;
            font-weight: 600;
        }
        QLabel#Hint {
            color: #b7bcc8;
        }
        QTextEdit {
            background-color: #111114;
            border: 1px solid #34343d;
            border-radius: 6px;
            padding: 6px 8px;
            color: #eaeaea;
        }
        QProgressBar {
            border: 1px solid #34343d;
            border-radius: 6px;
            background-color: #111114;
            text-align: center;
            height: 18px;
        }
        QProgressBar::chunk {
            border-radius: 5px;
            background-color: #4a90e2;
        }
        QPushButton {
            background-color: #2b2f38;
            border: 1px solid #3a3f49;
            border-radius: 6px;
            padding: 7px 12px;
        }
        QPushButton:hover {
            background-color: #353b46;
        }
        QPushButton:pressed {
            background-color: #1f232a;
        }
        QPushButton:disabled {
            background-color: #22242a;
            color: #777777;
        }
        """
    )


class DependencyInstallerWorker(QtCore.QObject):
    status_changed = QtCore.Signal(str)
    log_line = QtCore.Signal(str)
    progress_mode_changed = QtCore.Signal(bool)
    finished = QtCore.Signal(bool, str)

    def __init__(self, requirements: list[RequirementStatus]):
        super().__init__()
        self._requirements = requirements
        self._process: subprocess.Popen | None = None

    def _log_requirement_summary(self, requirement: RequirementStatus):
        if requirement.installed_version is None:
            self.log_line.emit(f"- {requirement.requirement} is not installed")
        else:
            self.log_line.emit(
                f"- {requirement.name} {requirement.installed_version} does not satisfy {requirement.requirement}"
            )

    @QtCore.Slot()
    def run(self):
        try:
            if not self._requirements:
                self.finished.emit(True, "All dependencies are already installed.")
                return

            self.status_changed.emit("Checking required packages...")
            for requirement in self._requirements:
                self._log_requirement_summary(requirement)

            self.status_changed.emit("Downloading and installing missing packages...")
            self.progress_mode_changed.emit(True)

            command = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--progress-bar",
                "off",
                *[requirement.requirement for requirement in self._requirements],
            ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            self._process = process

            assert process.stdout is not None
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    self.log_line.emit(line)

            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"pip exited with code {return_code}")

            still_missing = get_missing_requirements(REQUIRED_REQUIREMENTS)
            if still_missing:
                missing_names = ", ".join(requirement.requirement for requirement in still_missing)
                raise RuntimeError(f"Installation finished, but these packages are still missing: {missing_names}")

            self.finished.emit(True, "Dependencies installed successfully.")
        except Exception as exc:
            self.finished.emit(False, str(exc))
        finally:
            self._process = None
            self.progress_mode_changed.emit(False)


class DependencyBootstrapWindow(QtWidgets.QDialog):
    completed = QtCore.Signal(bool)
    open_tools_requested = QtCore.Signal()

    def __init__(self, requirements: list[RequirementStatus] | None = None):
        super().__init__()
        self._requirements = requirements if requirements is not None else get_missing_requirements(REQUIRED_REQUIREMENTS)
        self._thread: QtCore.QThread | None = None
        self._worker: DependencyInstallerWorker | None = None

        if APP_ICON_PATH.exists():
            self.setWindowIcon(QtGui.QIcon(str(APP_ICON_PATH)))

        self.setWindowTitle("TK Dev Tools Setup")
        self.setMinimumSize(820, 520)
        self.setModal(True)

        self.header_card = QtWidgets.QFrame()
        self.header_card.setObjectName("HeaderCard")

        self.title_label = QtWidgets.QLabel("Preparing TK Dev Tools")
        self.title_label.setObjectName("Title")

        self.subtitle_label = QtWidgets.QLabel(
            "Checking the local environment, installing anything that is missing, and then launching the main app."
        )
        self.subtitle_label.setObjectName("Hint")
        self.subtitle_label.setWordWrap(True)

        self.summary_label = QtWidgets.QLabel(self._build_requirement_summary())
        self.summary_label.setObjectName("Hint")
        self.summary_label.setWordWrap(True)

        header_layout = QtWidgets.QVBoxLayout(self.header_card)
        header_layout.setContentsMargins(16, 14, 16, 14)
        header_layout.setSpacing(6)
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        header_layout.addWidget(self.summary_label)

        self.content_card = QtWidgets.QFrame()
        self.content_card.setObjectName("ContentCard")

        self.status_label = QtWidgets.QLabel("Starting...")
        self.status_label.setObjectName("Status")

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(True)

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)

        content_layout = QtWidgets.QVBoxLayout(self.content_card)
        content_layout.setContentsMargins(16, 14, 16, 14)
        content_layout.setSpacing(10)
        content_layout.addWidget(self.status_label)
        content_layout.addWidget(self.progress_bar)
        content_layout.addWidget(self.log_text, 1)

        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self._quit_application)

        self.open_tools_button = QtWidgets.QPushButton("Open tools")
        self.open_tools_button.setEnabled(False)
        self.open_tools_button.clicked.connect(self._request_open_tools)

        footer = QtWidgets.QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.open_tools_button)
        footer.addWidget(self.close_button)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.header_card)
        layout.addWidget(self.content_card, 1)
        layout.addLayout(footer)

        self._start_worker()

    def _start_worker(self):
        self._thread = QtCore.QThread(self)
        self._worker = DependencyInstallerWorker(self._requirements)
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

    def _append_log(self, line: str):
        self.log_text.append(line)
        self.log_text.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def _set_progress_mode(self, busy: bool):
        self.progress_bar.setRange(0, 0 if busy else 1)
        if not busy:
            self.progress_bar.setValue(1)

    def _build_requirement_summary(self) -> str:
        if not self._requirements:
            return "No dependencies are missing."

        lines = ["The following packages will be installed or updated:"]
        lines.extend(f"- {requirement.requirement}" for requirement in self._requirements)
        return "\n".join(lines)

    def _request_open_tools(self):
        self.open_tools_requested.emit()

    def _quit_application(self):
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.quit()
        else:
            self.close()

    def _on_finished(self, success: bool, message: str):
        self._set_progress_mode(False)
        if success:
            self.status_label.setText(f"{message} Press Open tools to continue.")
        else:
            self.status_label.setText(message)
        self.open_tools_button.setEnabled(success)
        self.close_button.setEnabled(True)
        self.completed.emit(success)

    def closeEvent(self, event):
        if self.close_button.isEnabled():
            event.accept()
            return

        event.ignore()
        QtWidgets.QMessageBox.information(self, "Please wait", "The setup is still running.")
