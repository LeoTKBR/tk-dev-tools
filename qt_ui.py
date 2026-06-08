from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Empty, Queue
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from PySide6 import QtCore, QtGui, QtWidgets

from core_types import Client
from dat_core import DatManager
from generation_core import ProgressEvent, build_item_frames, build_jobs, collect_used_sprite_ids, is_blank_frame, save_gif
from spr_core import SpriteManager


APP_DIR = Path(__file__).resolve().parent
APP_ICON_PATH = APP_DIR / "icon.png"
LOADING_IMAGE_PATH = APP_DIR / "loading.png"
GITHUB_REPO_OWNER = "LeoTKBR"
GITHUB_REPO_NAME = "tk-dev-tools"
GITHUB_REPO_FULL_NAME = f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_REPO_FULL_NAME}"
DISCORD_LINKS = {
    "Canary": "https://discord.gg/gvTj5sh9Mp",
    "TK Dev": "https://discord.gg/rj97H4JD3k",
}


def _http_get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "TK-Dev-Tools/1.0"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_get_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "TK-Dev-Tools/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read()


def _git_blob_sha_for_bytes(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def _git_blob_sha_for_file(path: Path) -> str:
    return _git_blob_sha_for_bytes(path.read_bytes())


def apply_dark_theme(app: QtWidgets.QApplication):
    app.setStyle("Fusion")

    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(24, 24, 28))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(235, 235, 235))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(18, 18, 20))
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(32, 32, 36))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor(20, 20, 20))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(235, 235, 235))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(40, 40, 46))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(235, 235, 235))
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(255, 80, 80))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(74, 144, 226))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(96, 172, 255))
    palette.setColor(QtGui.QPalette.ColorRole.LinkVisited, QtGui.QColor(164, 131, 255))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QWidget {
            background-color: #18181c;
            color: #eaeaea;
            selection-background-color: #4a90e2;
            selection-color: #ffffff;
        }
        QMainWindow::separator {
            background: #2b2b31;
            width: 1px;
            height: 1px;
        }
        QTabWidget::pane {
            border: 1px solid #31313a;
            top: -1px;
            background-color: #1d1d22;
        }
        QTabBar::tab {
            background: #23232a;
            border: 1px solid #31313a;
            border-bottom: none;
            padding: 4px 10px;
            margin-right: 4px;
            color: #d6d6d6;
            min-width: 92px;
            min-height: 22px;
            font-size: 10px;
        }
        QTabBar::tab:selected {
            background: #1d1d22;
            color: #ffffff;
        }
        QTabBar::tab:hover:!selected {
            background: #2c2c33;
        }
        QGroupBox {
            border: 1px solid #31313a;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 10px;
            background-color: #1d1d22;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
            color: #f0f0f0;
        }
        QLineEdit, QSpinBox, QTextEdit {
            background-color: #111114;
            border: 1px solid #34343d;
            border-radius: 6px;
            padding: 6px 8px;
            selection-background-color: #4a90e2;
        }
        QSpinBox {
            padding-right: 24px;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            width: 0px;
            border: none;
            background: transparent;
        }
        QLineEdit:disabled, QSpinBox:disabled, QTextEdit:disabled {
            background-color: #24242a;
            color: #8c8c94;
            border: 1px solid #3a3a43;
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
        QToolButton {
            background-color: #2b2f38;
            border: 1px solid #3a3f49;
            border-radius: 6px;
            padding: 7px 12px;
        }
        QToolButton:hover {
            background-color: #353b46;
        }
        QToolButton:pressed {
            background-color: #1f232a;
        }
        QToolButton::menu-indicator {
            image: none;
            width: 0px;
        }
        QFrame#TopBar {
            background-color: #1d1d22;
            border: 1px solid #31313a;
            border-radius: 10px;
        }
        QLabel#TopBarLabel {
            color: #9dc5ff;
            font-size: 11px;
            font-weight: 600;
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
        QCheckBox, QLabel {
            color: #eaeaea;
        }
        QCheckBox:disabled, QLabel:disabled {
            color: #7b7b82;
        }
        QLabel#ToolTitle {
            color: #9dc5ff;
            font-size: 12px;
            font-weight: 600;
            padding: 2px 0 4px 0;
        }
        QScrollBar:vertical {
            background: #1a1a1f;
            width: 12px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #3a3f49;
            min-height: 24px;
            border-radius: 4px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        """
    )


def load_app_icon() -> QtGui.QIcon:
    if APP_ICON_PATH.exists():
        return QtGui.QIcon(str(APP_ICON_PATH))
    return QtGui.QIcon()


def show_splash_then_start(app: QtWidgets.QApplication, on_finished):
    if not LOADING_IMAGE_PATH.exists():
        on_finished()
        return

    pixmap = QtGui.QPixmap(str(LOADING_IMAGE_PATH))
    if pixmap.isNull():
        on_finished()
        return

    splash = QtWidgets.QSplashScreen(
        pixmap,
        QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.SplashScreen,
    )
    splash.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
    splash.setStyleSheet("background: transparent;")
    splash.setMask(pixmap.mask())

    screen = app.primaryScreen()
    if screen is not None:
        geometry = screen.availableGeometry()
        splash.move(
            geometry.center().x() - splash.width() // 2,
            geometry.center().y() - splash.height() // 2,
        )

    opacity = QtWidgets.QGraphicsOpacityEffect(splash)
    splash.setGraphicsEffect(opacity)
    opacity.setOpacity(0.0)

    fade_in = QtCore.QPropertyAnimation(opacity, b"opacity", splash)
    fade_in.setDuration(450)
    fade_in.setStartValue(0.0)
    fade_in.setEndValue(1.0)
    fade_in.setEasingCurve(QtCore.QEasingCurve.Type.InOutQuad)

    hold = QtCore.QPauseAnimation(500, splash)

    fade_out = QtCore.QPropertyAnimation(opacity, b"opacity", splash)
    fade_out.setDuration(350)
    fade_out.setStartValue(1.0)
    fade_out.setEndValue(0.0)
    fade_out.setEasingCurve(QtCore.QEasingCurve.Type.InOutQuad)

    sequence = QtCore.QSequentialAnimationGroup(splash)
    sequence.addAnimation(fade_in)
    sequence.addAnimation(hold)
    sequence.addAnimation(fade_out)

    def finish_splash():
        splash.close()
        on_finished()

    sequence.finished.connect(finish_splash)
    splash.show()
    splash.raise_()
    sequence.start()

    app._splash_window = splash
    app._splash_animation = sequence


class ItemImageFramesWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TK Dev Tools")
        self.resize(980, 760)

        self.client_version_spin = QtWidgets.QSpinBox()
        self.client_version_spin.setRange(740, 1100)
        self.client_version_spin.setValue(1100)

        self.spr_edit = QtWidgets.QLineEdit()
        self.dat_edit = QtWidgets.QLineEdit()
        self.output_edit = QtWidgets.QLineEdit()

        self.only_pickable_check = QtWidgets.QCheckBox("Only pickable items")
        self.only_pickable_check.setChecked(False)

        self.use_range_check = QtWidgets.QCheckBox("Use ID range")
        self.use_range_check.setChecked(False)
        self.use_range_check.toggled.connect(self._toggle_range_inputs)

        self.range_start_spin = QtWidgets.QSpinBox()
        self.range_start_spin.setRange(100, 999999)
        self.range_start_spin.setValue(100)

        self.range_end_spin = QtWidgets.QSpinBox()
        self.range_end_spin.setRange(100, 999999)
        self.range_end_spin.setValue(1100)

        self.delay_spin = QtWidgets.QSpinBox()
        self.delay_spin.setRange(10, 1000)
        self.delay_spin.setValue(100)

        self.workers_spin = QtWidgets.QSpinBox()
        self.workers_spin.setRange(1, 32)
        self.workers_spin.setValue(max(1, min(4, os.cpu_count() or 2)))

        self.status_label = QtWidgets.QLabel("Ready")
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)

        self.log_enabled = False
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)

        self.top_bar = QtWidgets.QFrame()
        self.top_bar.setObjectName("TopBar")
        self.toggle_log_button = QtWidgets.QPushButton("Enable log")
        self.toggle_log_button.clicked.connect(self.toggle_log_visibility)

        self.about_button = QtWidgets.QPushButton("About")
        self.about_button.clicked.connect(self.show_about_dialog)

        self.discord_button = QtWidgets.QToolButton()
        self.discord_button.setText("Discord")
        self.discord_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.discord_menu = QtWidgets.QMenu(self.discord_button)
        for label, url in DISCORD_LINKS.items():
            action = self.discord_menu.addAction(label)
            action.triggered.connect(lambda checked=False, link=url: self.open_external_url(link))
        self.discord_button.setMenu(self.discord_menu)

        self.integrity_button = QtWidgets.QPushButton("Check integrity")
        self.integrity_button.clicked.connect(self.check_integrity)

        self.start_button = QtWidgets.QPushButton("Generate GIFs")
        self.open_button = QtWidgets.QPushButton("Open Output")
        self.start_button.clicked.connect(self.start_generation)
        self.open_button.clicked.connect(self.open_output)

        self.tool_tabs = QtWidgets.QTabWidget()
        self.tool_tabs.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.tool_tabs.currentChanged.connect(self._on_tool_tab_changed)
        self.tool_title_label = QtWidgets.QLabel()
        self.tool_title_label.setObjectName("ToolTitle")

        self._queue: Queue[ProgressEvent] = Queue()
        self._worker: threading.Thread | None = None
        self._integrity_worker: threading.Thread | None = None
        self._loading_mode = False

        self._build_ui()

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.poll_queue)
        self._timer.start(100)

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        top_bar_layout = QtWidgets.QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(12, 10, 12, 10)
        top_bar_layout.setSpacing(8)

        title_block = QtWidgets.QVBoxLayout()
        title_block.setSpacing(0)
        title = QtWidgets.QLabel("TK Dev Tools")
        title_font = title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        subtitle = QtWidgets.QLabel("A toolkit to make an OTAdmin's daily work easier")
        subtitle.setObjectName("TopBarLabel")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        top_bar_layout.addLayout(title_block)
        top_bar_layout.addStretch(1)
        top_bar_layout.addWidget(self.toggle_log_button)
        top_bar_layout.addWidget(self.about_button)
        top_bar_layout.addWidget(self.discord_button)
        top_bar_layout.addWidget(self.integrity_button)
        root_layout.addWidget(self.top_bar)

        root_layout.addWidget(self.tool_title_label)

        generator_tab = QtWidgets.QWidget()
        generator_layout = QtWidgets.QVBoxLayout(generator_tab)
        generator_layout.setContentsMargins(0, 0, 0, 0)
        generator_layout.setSpacing(10)

        form = QtWidgets.QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)

        self._add_row(form, 0, "Client Version", self.client_version_spin)
        self._add_path_row(form, 1, "SPR File", self.spr_edit)
        self._add_path_row(form, 2, "DAT File", self.dat_edit)
        self._add_path_row(form, 3, "Output Folder", self.output_edit, directory=True)
        generator_layout.addLayout(form)

        options_box = QtWidgets.QGroupBox("Options")
        options_layout = QtWidgets.QGridLayout(options_box)
        options_layout.setHorizontalSpacing(10)
        options_layout.setVerticalSpacing(8)
        options_layout.addWidget(self.only_pickable_check, 0, 0, 1, 2)
        options_layout.addWidget(self.use_range_check, 0, 2, 1, 2)
        options_layout.addWidget(QtWidgets.QLabel("Start ID"), 1, 0)
        options_layout.addWidget(self.range_start_spin, 1, 1)
        options_layout.addWidget(QtWidgets.QLabel("End ID"), 1, 2)
        options_layout.addWidget(self.range_end_spin, 1, 3)
        options_layout.addWidget(QtWidgets.QLabel("Frame delay (ms)"), 2, 0)
        options_layout.addWidget(self.delay_spin, 2, 1)
        options_layout.addWidget(QtWidgets.QLabel("Workers"), 2, 2)
        options_layout.addWidget(self.workers_spin, 2, 3)
        generator_layout.addWidget(options_box)

        actions = QtWidgets.QHBoxLayout()
        actions.addWidget(self.start_button)
        actions.addWidget(self.open_button)
        actions.addStretch(1)
        generator_layout.addLayout(actions)

        self.progress_bar.setTextVisible(True)
        generator_layout.addWidget(self.progress_bar)
        generator_layout.addWidget(self.status_label)

        log_box = QtWidgets.QGroupBox("Log")
        log_layout = QtWidgets.QVBoxLayout(log_box)
        log_layout.addWidget(self.log_text)
        log_box.setVisible(False)
        self.log_box = log_box
        generator_layout.addWidget(log_box, 1)

        blank_tab = QtWidgets.QWidget()
        blank_layout = QtWidgets.QVBoxLayout(blank_tab)
        blank_layout.addStretch(1)
        blank_label = QtWidgets.QLabel("Blank")
        blank_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        blank_font = blank_label.font()
        blank_font.setPointSize(14)
        blank_font.setBold(True)
        blank_label.setFont(blank_font)
        blank_layout.addWidget(blank_label)
        blank_layout.addStretch(1)

        self.tool_tabs.addTab(generator_tab, "GIF Generator")
        self.tool_tabs.addTab(blank_tab, "Blank")
        root_layout.addWidget(self.tool_tabs, 1)

        self._refresh_log_controls()
        self._toggle_range_inputs(False)
        self._on_tool_tab_changed(self.tool_tabs.currentIndex())

    def _add_row(self, layout: QtWidgets.QGridLayout, row: int, label: str, widget: QtWidgets.QWidget):
        layout.addWidget(QtWidgets.QLabel(label), row, 0)
        layout.addWidget(widget, row, 1, 1, 2)

    def _add_path_row(self, layout: QtWidgets.QGridLayout, row: int, label: str, edit: QtWidgets.QLineEdit, directory: bool = False):
        layout.addWidget(QtWidgets.QLabel(label), row, 0)
        layout.addWidget(edit, row, 1)
        button = QtWidgets.QPushButton("Browse...")
        button.clicked.connect(lambda: self.browse_path(edit, directory))
        layout.addWidget(button, row, 2)

    def browse_path(self, edit: QtWidgets.QLineEdit, directory: bool):
        if directory:
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select output folder")
        else:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select file")
        if path:
            edit.setText(path)
            if edit is self.spr_edit and not self.output_edit.text().strip():
                self.output_edit.setText(str(Path(path).parent / "generated_gifs"))

    def _toggle_range_inputs(self, enabled: bool):
        self.range_start_spin.setEnabled(enabled)
        self.range_end_spin.setEnabled(enabled)

    def _refresh_log_controls(self):
        self.log_box.setVisible(self.log_enabled)
        self.toggle_log_button.setText("Disable log" if self.log_enabled else "Enable log")

    def toggle_log_visibility(self):
        self.log_enabled = not self.log_enabled
        self._refresh_log_controls()
        if self.log_enabled:
            self.log("Log enabled.")

    def _on_tool_tab_changed(self, index: int):
        if index == 0:
            self.tool_title_label.setText("GIF Generator")
            self.setWindowTitle("TK Dev Tools")
        elif index == 1:
            self.tool_title_label.setText("Blank")
            self.setWindowTitle("TK Dev Tools")
        else:
            self.tool_title_label.setText("TK Dev Tools")

    def open_output(self):
        out = self.output_edit.text().strip()
        if not out:
            QtWidgets.QMessageBox.information(self, "Output", "Choose an output folder first.")
            return
        Path(out).mkdir(parents=True, exist_ok=True)
        os.startfile(out)

    def log(self, text: str):
        if not self.log_enabled:
            return
        self.log_text.append(text)
        self.log_text.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def open_external_url(self, url: str):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def show_about_dialog(self):
        message = (
            "<b>TK Dev Tools</b><br><br>"
            "Created by <b>LeoTKBR</b>.<br>"
            "Repository: <a href='{repo}'>{repo}</a><br><br>"
            "The goal of the project is to bring together several tools to make an OTAdmin's daily work easier.<br>"
            "Today the available module is the GIF generator, but the foundation is already prepared to grow with new utilities."
        ).format(repo=GITHUB_REPO_URL)
        QtWidgets.QMessageBox.information(self, "About", message)

    def _load_remote_repo_state(self) -> tuple[str, str, list[dict]]:
        repo_url = f"https://api.github.com/repos/{GITHUB_REPO_FULL_NAME}"
        repo_info = _http_get_json(repo_url)
        default_branch = repo_info["default_branch"]

        branch_info = _http_get_json(f"{repo_url}/branches/{default_branch}")
        commit_sha = branch_info["commit"]["sha"]
        commit_info = _http_get_json(f"{repo_url}/git/commits/{commit_sha}")
        tree_sha = commit_info["tree"]["sha"]

        tree_info = _http_get_json(f"{repo_url}/git/trees/{tree_sha}?recursive=1")
        tree_entries = tree_info.get("tree", [])
        return default_branch, commit_sha, tree_entries

    def _sync_integrity_report(self, report_lines: list[str], title: str = "Integrity"):
        if report_lines:
            QtWidgets.QMessageBox.information(self, title, "\n".join(report_lines))

    def check_integrity(self):
        if self._integrity_worker and self._integrity_worker.is_alive():
            QtWidgets.QMessageBox.information(self, "Integrity", "An integrity check is already in progress.")
            return

        self.integrity_button.setEnabled(False)
        self.status_label.setText("Checking integrity...")
        self._integrity_worker = threading.Thread(target=self.run_integrity_check, daemon=True)
        self._integrity_worker.start()

    def run_integrity_check(self):
        try:
            default_branch, commit_sha, tree_entries = self._load_remote_repo_state()
            repo_root = APP_DIR
            changed_files: list[str] = []
            repaired_files: list[str] = []
            checked_files = 0

            for entry in tree_entries:
                if entry.get("type") != "blob":
                    continue

                relative_path = Path(entry["path"])
                local_path = repo_root / relative_path
                remote_sha = entry.get("sha")
                checked_files += 1

                if local_path.exists() and local_path.is_file():
                    local_sha = _git_blob_sha_for_file(local_path)
                    if local_sha == remote_sha:
                        continue
                    changed_files.append(str(relative_path))
                else:
                    changed_files.append(str(relative_path))

                raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO_FULL_NAME}/{default_branch}/{relative_path.as_posix()}"
                data = _http_get_bytes(raw_url)
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(data)
                repaired_files.append(str(relative_path))

            report_lines = [
                f"Repository: {GITHUB_REPO_FULL_NAME}",
                f"Reference commit: {commit_sha[:12]}",
                f"Files checked: {checked_files}",
            ]
            if changed_files:
                report_lines.append(f"Missing or suspicious files found: {len(changed_files)}")
            else:
                report_lines.append("No divergences found.")
            if repaired_files:
                report_lines.append("Restored files:")
                report_lines.extend(f"- {path}" for path in repaired_files)
            self.emit_event("integrity_done", report_lines)
        except (HTTPError, URLError, KeyError, json.JSONDecodeError, OSError) as exc:
            self.emit_event("integrity_error", str(exc))

    def set_busy(self, busy: bool):
        self.start_button.setEnabled(not busy)

    def start_loading_indicator(self):
        self._loading_mode = True
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Loading assets...")

    def stop_loading_indicator(self):
        self._loading_mode = False
        self.progress_bar.setRange(0, max(1, self.progress_bar.maximum() if self.progress_bar.maximum() > 0 else 1))

    def emit_event(self, kind: str, *payload):
        self._queue.put(ProgressEvent(kind, payload))

    def start_generation(self):
        if self._worker and self._worker.is_alive():
            QtWidgets.QMessageBox.information(self, "Running", "Generation is already running.")
            return

        spr_path = Path(self.spr_edit.text().strip())
        dat_path = Path(self.dat_edit.text().strip())

        if not spr_path.exists():
            QtWidgets.QMessageBox.critical(self, "Missing file", "Choose a valid SPR file.")
            return
        if not dat_path.exists():
            QtWidgets.QMessageBox.critical(self, "Missing file", "Choose a valid DAT file.")
            return
        if not self.output_edit.text().strip():
            QtWidgets.QMessageBox.critical(self, "Missing output", "Choose an output folder.")
            return

        self.log_text.clear()
        self.progress_bar.setValue(0)
        self.start_loading_indicator()
        self.set_busy(True)

        self._worker = threading.Thread(target=self.run_generation, daemon=True)
        self._worker.start()

    def run_generation(self):
        try:
            client = Client(int(self.client_version_spin.value()))
            self.emit_event("log", f"Client version: {client.version}")
            self.emit_event("log", "Loading DAT (items only)...")
            dat_manager = DatManager(client)
            dat_manager.load_dat(Path(self.dat_edit.text().strip()))

            if self.use_range_check.isChecked():
                start_id = int(self.range_start_spin.value())
                end_id = int(self.range_end_spin.value())
                if start_id > end_id:
                    raise RuntimeError("Start ID must be less than or equal to End ID.")
                self.emit_event("log", f"Using ID range {start_id}..{end_id}")
            else:
                start_id = None
                end_id = None

            jobs = build_jobs(dat_manager, self.only_pickable_check.isChecked(), start_id, end_id)
            total = len(jobs)
            if total == 0:
                raise RuntimeError("No items matched the selected filters.")

            output_dir = Path(self.output_edit.text().strip())
            output_dir.mkdir(parents=True, exist_ok=True)
            self.emit_event("log", f"Found {total} item(s)")
            self.emit_event("log", f"Workers: {max(1, int(self.workers_spin.value()))}")

            used_sprite_ids = collect_used_sprite_ids(dat_manager, jobs)
            self.emit_event("log", f"Loading SPR... ({len(used_sprite_ids):,} used sprites)")
            sprite_manager = SpriteManager(client)
            sprite_manager.load_spr(Path(self.spr_edit.text().strip()), used_sprite_ids if used_sprite_ids else None)

            self.emit_event("total", total)

            def task(job_pair):
                output_id, client_id = job_pair
                thing = dat_manager.get_item(client_id)
                if thing is None:
                    raise RuntimeError(f"Missing DAT item {client_id}")
                fallback_duration = int(self.delay_spin.value())
                frames, durations = build_item_frames(thing, sprite_manager, fallback_duration)
                if not frames:
                    raise RuntimeError(f"No frames generated for item {client_id}")
                if all(is_blank_frame(frame) for frame in frames):
                    return output_id, None
                out_file = output_dir / "items" / f"{output_id}.gif"
                save_gif(frames, out_file, durations if durations else fallback_duration)
                return output_id, out_file

            completed = 0
            workers = max(1, int(self.workers_spin.value()))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(task, job): job for job in jobs}
                for future in as_completed(futures):
                    output_id, out_file = future.result()
                    completed += 1
                    if out_file is not None:
                        self.emit_event("progress", completed, total, output_id, str(out_file))
                    else:
                        self.emit_event("progress", completed, total, output_id, "[skipped blank]")

            self.emit_event("done", str(output_dir))
        except Exception as exc:
            self.emit_event("error", str(exc))

    def poll_queue(self):
        while True:
            try:
                event = self._queue.get_nowait()
            except Empty:
                break

            kind = event.kind
            payload = event.payload
            if kind == "log":
                self.log(payload[0])
            elif kind == "total":
                total = int(payload[0])
                if self._loading_mode:
                    self.progress_bar.setRange(0, total)
                    self.progress_bar.setValue(0)
                    self._loading_mode = False
                else:
                    self.progress_bar.setRange(0, max(1, total))
                    self.progress_bar.setValue(0)
            elif kind == "progress":
                done, total, output_id, out_file = payload
                self.progress_bar.setValue(int(done))
                self.status_label.setText(f"{done}/{total}")
                self.log(f"Done {output_id}: {out_file}")
            elif kind == "done":
                out_dir = payload[0]
                self.stop_loading_indicator()
                self.status_label.setText(f"Finished: {out_dir}")
                self.log("All GIFs generated.")
                self.set_busy(False)
                QtWidgets.QMessageBox.information(self, "Finished", f"GIFs generated in:\n{out_dir}")
            elif kind == "error":
                self.stop_loading_indicator()
                self.status_label.setText("Error")
                self.log("ERROR: " + payload[0])
                self.set_busy(False)
                QtWidgets.QMessageBox.critical(self, "Conversion failed", payload[0])
            elif kind == "integrity_done":
                self.status_label.setText("Integrity check complete")
                self.integrity_button.setEnabled(True)
                self._sync_integrity_report(payload[0], "Integrity")
            elif kind == "integrity_error":
                self.status_label.setText("Integrity check failed")
                self.integrity_button.setEnabled(True)
                QtWidgets.QMessageBox.critical(self, "Integrity", payload[0])

    def closeEvent(self, event):
        event.accept()


def show_main_window(app: QtWidgets.QApplication):
    apply_dark_theme(app)
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    window = ItemImageFramesWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)

    def show_window():
        window.show()
        app._main_window = window

    show_splash_then_start(app, show_window)
    return window


def main():
    app = QtWidgets.QApplication(sys.argv)
    show_main_window(app)
    app.exec()
