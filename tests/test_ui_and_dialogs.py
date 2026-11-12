from PyQt6.QtWidgets import QApplication
import pytest

import app as loqin_app


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_settings_dialog_fields(qapp):
    dialog = loqin_app.SettingsDialog()
    assert dialog.interval_input.minimum() == 10
    assert dialog.interval_input.maximum() == 300
    assert "Fallback Check Interval" in dialog.interval_label.text()
    assert "captive portal" in dialog.interval_label.toolTip().lower()


def test_status_icon_creation(qapp):
    for color in ["green", "yellow", "red", "error", "unknown"]:
        icon = loqin_app.create_status_icon(color)
        assert icon is not None
        assert not icon.isNull()
