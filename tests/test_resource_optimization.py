import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import pytest

import app as loqin_app


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_deferred_heavy_imports():
    # pyqtgraph and bs4 should not be imported on simple import of app
    # (Note: if tests ran prior in the same process, we check they are not imported in fresh subprocess or test dialog behavior)
    assert not hasattr(loqin_app, "pg")
    assert not hasattr(loqin_app, "BeautifulSoup")


def test_speed_graph_dialog_lazy_loading(qapp):
    # Opening SpeedGraphDialog should provide self.pg
    dialog = loqin_app.SpeedGraphDialog()
    assert hasattr(dialog, "pg")
    assert "pyqtgraph" in sys.modules
    dialog.update_data(5120, 2048)
    dialog.close()


def test_tray_speed_timer_lifecycle(qapp):
    tray_app = loqin_app.LoqinTrayApp.__new__(loqin_app.LoqinTrayApp)
    tray_app.app = qapp
    tray_app.last_net_io = None
    tray_app.last_time = 0
    tray_app.graph_dialog = None
    tray_app.menu_visible = False
    tray_app.speed_timer = QTimer(qapp)
    tray_app.speed_action = loqin_app.QAction("Speed", None)
    tray_app.graph_action = loqin_app.QAction("Show Speed Graph", None)

    # Initial state: timer should NOT be active
    tray_app._evaluate_speed_timer()
    assert not tray_app.speed_timer.isActive()

    # Menu opened -> timer becomes active
    tray_app._on_menu_about_to_show()
    assert tray_app.speed_timer.isActive()

    # Menu closed -> timer stops
    tray_app._on_menu_about_to_hide()
    assert not tray_app.speed_timer.isActive()

    # Toggle speed graph -> opens dialog, timer starts
    tray_app.toggle_speed_graph()
    assert tray_app.graph_dialog is not None
    assert tray_app.speed_timer.isActive()
    assert tray_app.graph_action.text() == "Hide Speed Graph"

    # Toggle speed graph again -> closes dialog, releases reference, timer stops
    tray_app.toggle_speed_graph()
    assert tray_app.graph_dialog is None
    assert not tray_app.speed_timer.isActive()
    assert tray_app.graph_action.text() == "Show Speed Graph"


def test_wifi_picker_timer_lifecycle(qapp):
    picker = loqin_app.WiFiPickerDialog()
    # Should not be running before show
    assert not picker.auto_refresh_timer.isActive()

    # Simulate show event -> starts timer
    picker.show()
    qapp.processEvents()
    assert picker.auto_refresh_timer.isActive()

    # Simulate close -> stops timer
    picker.close()
    qapp.processEvents()
    assert not picker.auto_refresh_timer.isActive()


def test_wifi_picker_in_place_update(qapp):
    picker = loqin_app.WiFiPickerDialog()
    networks_1 = [
        {"ssid": "VIT", "signal": -60, "secured": True},
        {"ssid": "Guest", "signal": -75, "secured": False},
    ]
    picker.on_scan_finished(networks_1)
    assert len(picker.displayed_cards) == 2
    btn_vit = picker.displayed_cards[("VIT", True)]
    assert "-60 dBm" in btn_vit.text()

    # Second scan with updated signal only
    networks_2 = [
        {"ssid": "VIT", "signal": -50, "secured": True},
        {"ssid": "Guest", "signal": -72, "secured": False},
    ]
    picker.on_scan_finished(networks_2)
    # Button instance should be preserved (updated in place)
    assert picker.displayed_cards[("VIT", True)] is btn_vit
    assert "-50 dBm" in btn_vit.text()
    picker.close()
