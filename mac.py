"""
macOS entry point.

does cool shit natively via CoreWLAN
"""

from __future__ import annotations

import fcntl
import importlib.util
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import types
import threading
import time
from pathlib import Path

try:
    import objc
    from CoreWLAN import CWInterface, CWWiFiClient
except ImportError:
    raise SystemExit("Missing macOS dependencies. Please run: pip install pyobjc-framework-CoreWLAN")

if sys.platform != "darwin":
    raise SystemExit("ts not a mac vro")


APP_NAME = "Loqin"
APP_SUPPORT = Path.home() / "Library" / "Application Support" / APP_NAME
LAUNCH_AGENT = Path.home() / "Library" / "LaunchAgents" / "com.loqin.app.plist"
LOCK_PATH = Path(tempfile.gettempdir()) / "com.loqin.app.lock"


def _install_import_shims() -> None:
    """
    cheating by loading app then switching 
    """
    if "winreg" not in sys.modules:
        sys.modules["winreg"] = types.ModuleType("winreg")
    if "pywifi" not in sys.modules:
        pywifi = types.ModuleType("pywifi")
        pywifi.const = types.ModuleType("pywifi.const")
        pywifi.PyWiFi = object
        pywifi.Profile = object
        sys.modules["pywifi"] = pywifi
        sys.modules["pywifi.const"] = pywifi.const


def _load_shared_app():
    _install_import_shims()
    source = Path(__file__).with_name("app.py")
    spec = importlib.util.spec_from_file_location("_loqin_shared", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the shared Loqin application module.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


loqin = _load_shared_app()
loqin.APPDATA_DIR = str(APP_SUPPORT)
loqin.CONFIG_FILE = str(APP_SUPPORT / "Loqin_config.json")


def _run(command: list[str], timeout: int = 12) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


WIFI_LOCK = threading.Lock()


def get_interface():
    """Retrieve the primary Wi-Fi interface safely."""
    client = CWWiFiClient.sharedWiFiClient()
    return client.interface()


def scan_wifi(max_retries: int = 3, retry_delay: float = 0.5) -> list[dict[str, object]]:
    """Scan nearby access points natively with automatic retry on resource busy."""
    with WIFI_LOCK:
        iface = get_interface()
        if not iface:
            raise RuntimeError("The macOS Wi-Fi interface is unavailable on this Mac.")

        networks_set = None
        last_error = None

        for attempt in range(max_retries):
            networks_set, error = iface.scanForNetworksWithName_error_(None, None)
            
            if not error and networks_set is not None:
                break  # Success

            err_msg = error.localizedDescription() if error else "Unknown scan error"
            last_error = err_msg

            # Check for busy states (err code -3908/-3905 or 'busy' in description)
            if "busy" in err_msg.lower() or "390" in err_msg:
                time.sleep(retry_delay)
                continue
            
            # Non-busy error, fail fast
            raise RuntimeError(f"Unable to scan for Wi-Fi networks: {err_msg}")

        if networks_set is None:
            raise RuntimeError(f"Wi-Fi interface was busy after {max_retries} attempts: {last_error}")

        networks: dict[str, dict[str, object]] = {}
        for network in networks_set.allObjects():
            ssid = network.ssid()
            if not ssid:
                continue

            is_secured = not network.supportsSecurity_(0)
            network_data = {
                "ssid": ssid,
                "signal": int(network.rssiValue()),
                "secured": is_secured,
            }

            if ssid not in networks or network_data["signal"] > networks[ssid]["signal"]:
                networks[ssid] = network_data

        return list(networks.values())


def wifi_device() -> str:
    """Return wifidevice"""
    iface = get_interface()
    if not iface:
        raise RuntimeError("No Wi-Fi adapter was found.")
    return iface.interfaceName()


def current_wifi_ssid() -> str:
    iface = get_interface()
    return iface.ssid() if iface and iface.ssid() else ""


def current_bssid() -> str:
    iface = get_interface()
    return iface.bssid().lower() if iface and iface.bssid() else ""


def set_auto_start(enabled: bool) -> None:
    """yes"""
    try:
        if enabled:
            LAUNCH_AGENT.parent.mkdir(parents=True, exist_ok=True)
            program_args = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(Path(__file__).resolve())]
            with LAUNCH_AGENT.open("wb") as file:
                plistlib.dump({"Label": "com.loqin.app", "ProgramArguments": program_args, "RunAtLoad": True}, file)
        elif LAUNCH_AGENT.exists():
            LAUNCH_AGENT.unlink()
    except OSError as exc:
        print(f"Failed to update the macOS login item: {exc}")


def is_auto_start_enabled() -> bool:
    return LAUNCH_AGENT.exists()


class PowerEventFilter(loqin.QAbstractNativeEventFilter):
    def __init__(self, tray_app):
        super().__init__()
        self.tray_app = tray_app

    def nativeEventFilter(self, event_type, message):
        return False, 0


class WiFiScanThread(loqin.QThread):
    networks_found = loqin.pyqtSignal(list)
    scan_failed = loqin.pyqtSignal(str)

    def run(self):
        try:
            self.networks_found.emit(scan_wifi())
        except Exception as exc:
            self.scan_failed.emit(str(exc))


class WiFiConnectThread(loqin.QThread):
    connected = loqin.pyqtSignal(str)
    failed = loqin.pyqtSignal(str)

    def __init__(self, ssid, parent=None):
        super().__init__(parent)
        self.ssid = ssid

    def run(self):
        if not self.ssid:
            self.failed.emit("No Wi-Fi network was selected.")
            return
        try:
            # Lock the Wi-Fi interface while macOS attempts to connect
            with WIFI_LOCK:
                result = _run(["networksetup", "-setairportnetwork", wifi_device(), self.ssid])
                
            if result.returncode:
                self.failed.emit((result.stderr or result.stdout or "macOS could not connect to this Wi-Fi network.").strip())
                return
                
            for _ in range(24):
                if current_wifi_ssid().casefold() == self.ssid.casefold():
                    self.connected.emit(self.ssid)
                    return
                self.msleep(500)
            self.failed.emit("macOS did not finish connecting to the selected Wi-Fi network.")
        except Exception as exc:
            self.failed.emit(str(exc))


class PerformanceModeThread(loqin.QThread):
    status_signal = loqin.pyqtSignal(str, str)

    def __init__(self, use_best=True):
        super().__init__()
        self.use_best = use_best

    def run(self):
        try:
            # scan_wifi() handles its own lock, so we can call it safely here
            networks = scan_wifi()
            candidates = [network for network in networks if "VIT" in str(network["ssid"]).upper()]
            if not candidates:
                self.status_signal.emit("No VIT networks found in range.", "error")
                return
            
            # Sorts the VIT networks by signal strength (RSSI). 
            selected = sorted(candidates, key=lambda item: int(item["signal"]), reverse=self.use_best)[0]
            
            # Lock the Wi-Fi interface during the handoff
            with WIFI_LOCK:
                result = _run(["networksetup", "-setairportnetwork", wifi_device(), str(selected["ssid"])])
                
            if result.returncode:
                self.status_signal.emit((result.stderr or "Could not switch Wi-Fi networks.").strip(), "error")
            else:
                self.status_signal.emit(f"Performance Mode {'ON' if self.use_best else 'OFF'}", "green")
        except Exception as exc:
            self.status_signal.emit(f"Wi-Fi Error: {exc}", "error")


class SettingsDialog(loqin.SettingsDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.startup_cb.setText("Launch automatically when you log in to macOS")


class LoqinTrayApp(loqin.LoqinTrayApp):
    def trigger_manual_check(self):
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            return
        if self.waiting_for_wifi_choice:
            self.status_action.setText("Status: Choose Wi-Fi to continue")
            self.status_action.setIcon(loqin.create_status_icon("yellow"))
            self.tray.setToolTip("Loqin - Waiting for Wi-Fi selection")
            return
        bssid = current_bssid()
        if hasattr(self, "last_bssid") and bssid and bssid != self.last_bssid and self.perf_action.isChecked():
            self.last_bssid = bssid
            if not getattr(self, "just_optimized", False):
                self.trigger_performance_mode(checked=True)
                return
        self.last_bssid = bssid
        self.just_optimized = False
        self.config = loqin.ConfigManager.load_config()
        self.worker = loqin.NetworkWorker(self.config)
        self.worker.status_signal.connect(self.handle_status)
        self.worker.account_data_signal.connect(self.handle_account_url)
        self.worker.start()

    def install_update(self, package_path):
        self.progress_dialog.close()
        if not package_path or not os.path.exists(package_path):
            loqin.QMessageBox.warning(None, "Update Failed", "The update package could not be found.")
            return
        subprocess.Popen(["open", package_path])
        self.app.quit()

def ensure_single_instance():
    LOCK_PATH.touch(exist_ok=True)
    lock_file = LOCK_PATH.open("r+")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        app = loqin.QApplication.instance() or loqin.QApplication(sys.argv)
        loqin.QMessageBox.warning(None, "Loqin Already Running", "Another instance of Loqin is already running in the menu bar.")
        raise SystemExit(0)
    return lock_file


loqin.get_current_wifi_ssid = current_wifi_ssid
loqin.current_bssid = current_bssid
loqin.set_auto_start = set_auto_start
loqin.is_auto_start_enabled = is_auto_start_enabled
loqin.PowerEventFilter = PowerEventFilter
loqin.WiFiScanThread = WiFiScanThread
loqin.WiFiConnectThread = WiFiConnectThread
loqin.PerformanceModeThread = PerformanceModeThread
loqin.SettingsDialog = SettingsDialog
loqin.LoqinTrayApp = LoqinTrayApp
loqin.ensure_single_instance = ensure_single_instance


if __name__ == "__main__":
    instance_lock = ensure_single_instance()
    app = LoqinTrayApp()
    app.run()