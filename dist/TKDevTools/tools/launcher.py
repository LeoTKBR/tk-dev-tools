from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from dependency_bootstrap import REQUIRED_REQUIREMENTS, get_missing_requirements, parse_requirement


def _is_pyside6_available() -> bool:
    return importlib.util.find_spec("PySide6") is not None


def _install_requirements(requirements: list[str]) -> bool:
    if not requirements:
        return True

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--progress-bar",
        "off",
        *requirements,
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

    assert process.stdout is not None
    for line in process.stdout:
        line = line.rstrip()
        if line:
            print(line)

    return process.wait() == 0


def _run_qt_bootstrap_or_main():
    from PySide6 import QtWidgets

    from bootstrap_ui import DependencyBootstrapWindow, apply_bootstrap_theme

    app = QtWidgets.QApplication(sys.argv)
    apply_bootstrap_theme(app)
    app.setQuitOnLastWindowClosed(False)

    def launch_main_window():
        from qt_ui import show_main_window

        window = show_main_window(app)
        app.setQuitOnLastWindowClosed(True)
        return window

    missing = get_missing_requirements(REQUIRED_REQUIREMENTS)
    if not missing:
        launch_main_window()
        sys.exit(app.exec())

    window = DependencyBootstrapWindow(missing)

    def on_open_tools():
        launcher_path = Path(__file__).resolve()
        subprocess.Popen([sys.executable, str(launcher_path)], cwd=str(launcher_path.parent))
        app.quit()

    window.open_tools_requested.connect(on_open_tools)
    window.show()
    app._bootstrap_window = window
    sys.exit(app.exec())


def main():
    missing = get_missing_requirements(REQUIRED_REQUIREMENTS)
    if not missing:
        _run_qt_bootstrap_or_main()
        return

    print("Missing dependencies detected:")
    for requirement in missing:
        print(f"- {requirement.requirement}")

    if not _is_pyside6_available():
        pyside_requirement = [requirement.requirement for requirement in missing if parse_requirement(requirement.requirement)[0].lower() == "pyside6"]
        if pyside_requirement:
            print("PySide6 is missing. Installing it first so the Qt bootstrap can start.")
            if not _install_requirements(pyside_requirement):
                raise SystemExit("Failed to install PySide6.")

        if not _is_pyside6_available():
            raise SystemExit("PySide6 is still unavailable after installation.")

    _run_qt_bootstrap_or_main()


if __name__ == "__main__":
    main()
