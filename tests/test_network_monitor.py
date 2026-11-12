import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import pytest

import app as loqin_app
from network_monitor import (
    BaseNetworkEventMonitor,
    WindowsNetworkEventMonitor,
    MacNetworkEventMonitor,
    FallbackNetworkEventMonitor,
    get_network_event_monitor,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_monitor_factory():
    monitor = get_network_event_monitor()
    assert isinstance(monitor, BaseNetworkEventMonitor)
    if sys.platform == "win32":
        assert isinstance(monitor, WindowsNetworkEventMonitor)
    elif sys.platform == "darwin":
        assert isinstance(monitor, MacNetworkEventMonitor)


def test_monitor_lifecycle():
    monitor = get_network_event_monitor()
    monitor.start()
    assert monitor.is_running() is True
    monitor.stop()
    assert monitor.is_running() is False


def test_fallback_monitor():
    fallback = FallbackNetworkEventMonitor()
    errors = []
    fallback.monitor_error.connect(lambda msg: errors.append(msg))
    fallback.start()
    assert fallback.is_running() is True
    assert len(errors) == 1
    assert "fallback polling mode" in errors[0]
    fallback.stop()
    assert fallback.is_running() is False


def test_tray_app_disconnection_and_connection_events(qapp):
    tray_app = loqin_app.LoqinTrayApp.__new__(loqin_app.LoqinTrayApp)
    tray_app.app = qapp
    tray_app.waiting_for_wifi_choice = False
    tray_app.status_action = loqin_app.QAction("Status: Initializing")
    tray_app.tray = loqin_app.QSystemTrayIcon()
    tray_app.network_debounce_timer = QTimer(qapp)
    tray_app.network_debounce_timer.setSingleShot(True)
    tray_app.network_debounce_timer.start(5000)

    # 1. Disconnection event
    tray_app.on_network_changed("disconnected")
    assert not tray_app.network_debounce_timer.isActive()
    assert tray_app.status_action.text() == "Status: Waiting for Wi-Fi..."

    # 2. Connection event
    tray_app.on_network_changed("connected")
    assert tray_app.network_debounce_timer.isActive()
    assert tray_app.network_debounce_timer.interval() == 750
