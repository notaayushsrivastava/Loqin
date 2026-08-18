import sys
import json
import os
import time
import requests
import keyring
import psutil
import subprocess
import pyqtgraph as pg
import re
import ctypes
import ctypes.wintypes
import pywifi
import winreg
from pywifi import const
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout, 
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, 
    QCheckBox, QMessageBox, QDialog, QVBoxLayout, QLabel, QProgressDialog,
    QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QTableWidget,
    QHeaderView, QTableWidgetItem, QAbstractItemView, QTabWidget,
    QWidget, QFormLayout, QScrollArea, QInputDialog, QGridLayout, QFrame,
    QGraphicsOpacityEffect
)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QColor, QPainter, QDesktopServices, QCursor
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QUrl, QAbstractNativeEventFilter, QPropertyAnimation, QEasingCurve, QSize

APP_NAME = "Loqin"
APPDATA_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "Loqin")
CONFIG_FILE = os.path.join(APPDATA_DIR, "Loqin_config.json")
APP_VERSION = "1.6.4"
GITHUB_API_URL = "https://api.github.com/repos/notaayushsrivastava/loqin/releases/latest"

# --- WINDOWS STARTUP REGISTRY HELPER ---
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "Loqin"

MUTEX_NAME = "Global\\Loqin_SingleInstance_Mutex_AayushSrivastava"

# --- Windows API Power Broadcast Constants ---
WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND = 0x0004            # System is suspending (Sleep)
PBT_APMRESUMEAUTOMATIC = 0x0012    # System resumed automatically

def ensure_single_instance():
    # Create or open named mutex
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    
    # ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == 183:
        # Create temporary QApplication to display warning message
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None, 
            "Loqin Already Running", 
            "Another instance of Loqin is already running in the system tray."
        )
        sys.exit(0)
    
    return mutex

def set_auto_start(enabled: bool):
    """Add or remove the app from Windows Registry run-on-startup."""
    if sys.platform != "win32":
        return

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS)
        if enabled:
            if getattr(sys, 'frozen', False):
                exe_path = f'"{sys.executable}"'
            else:
                exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
            winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_REG_NAME)
            except OSError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Failed to update registry: {e}")

def is_auto_start_enabled() -> bool:
    """Check if the registry key currently exists."""
    if sys.platform != "win32":
        return False

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_REG_NAME)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False
    except Exception as e:
        print(f"Failed to read registry: {e}")
        return False

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # In dev mode, the base path is the current working directory
        base_path = os.path.abspath(".")
        
    # Automatically route all requests through the new 'assets' folder
    return os.path.join(base_path, "assets", relative_path)

def create_status_icon(color_type: str) -> QIcon:
    """Generates a smooth colored circle icon (Green, Yellow, Red) for status indicators."""
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if color_type == "green":
        painter.setBrush(QColor(46, 204, 113))  # Connected
    elif color_type == "yellow":
        painter.setBrush(QColor(241, 196, 15))  # Portal / Working
    else:
        painter.setBrush(QColor(231, 76, 60))   # Error / Offline

    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 12, 12)
    painter.end()
    return QIcon(pixmap)


class PowerEventFilter(QAbstractNativeEventFilter):
    def __init__(self, tray_app):
        super().__init__()
        self.tray_app = tray_app
        self.last_event_time = 0
        self.last_wparam = None

    def nativeEventFilter(self, eventType, message):
        """Intercept native Windows messages to detect sleep/wake"""
        msg = ctypes.wintypes.MSG.from_address(int(message))
        
        if msg.message == WM_POWERBROADCAST:
            current_time = time.time()
            
            # --- FIX: Debounce duplicate power messages delivered across multiple window handles ---
            if msg.wParam == self.last_wparam and (current_time - self.last_event_time) < 2.0:
                return False, 0
                
            self.last_event_time = current_time
            self.last_wparam = msg.wParam

            if msg.wParam == PBT_APMSUSPEND:
                if hasattr(self.tray_app, 'worker') and self.tray_app.worker:
                    self.tray_app.worker.is_paused = True
                self.tray_app.force_logout()
                    
            elif msg.wParam == PBT_APMRESUMEAUTOMATIC:
                if hasattr(self.tray_app, 'worker') and self.tray_app.worker:
                    self.tray_app.worker.is_paused = False
                
                # --- FIX: Reset update flag so UpdateChecker waits for active Wi-Fi ---
                self.tray_app.has_checked_for_updates = False

                # --- Trigger auto-connect on wake ---
                QTimer.singleShot(2000, self.tray_app.auto_connect_last_wifi)
                
                # --- Run Performance Thread on wake (only if turned on) ---
                if hasattr(self.tray_app, 'perf_action') and self.tray_app.perf_action.isChecked():
                    # Delay by 5 seconds to ensure the initial auto-connect has time to resolve first
                    QTimer.singleShot(5000, lambda: self.tray_app.trigger_performance_mode(checked=True))
                    
        return False, 0


# --- WORKER THREAD: Performance Mode Wi-Fi Selector ---
class PerformanceModeThread(QThread):
    status_signal = pyqtSignal(str, str)

    def __init__(self, use_best=True):
        super().__init__()
        self.use_best = use_best  

    def run(self):
        status_msg = "Optimizing Network..." if self.use_best else "Reverting Network..."
        self.status_signal.emit(status_msg, "yellow")
        
        try:
            wifi = pywifi.PyWiFi()
            iface = wifi.interfaces()[0]
            
            # Start scan and wait for results
            iface.scan()
            self.sleep(4) 
            
            results = iface.scan_results()
            target_networks = [n for n in results if "VIT" in (n.ssid or "").upper()]
            
            if not target_networks:
                self.status_signal.emit("No VIT networks found in range.", "error")
                return
                
            # Sort by signal strength:
            # - reverse=True  -> Strongest signal first (Performance Mode ON)
            # - reverse=False -> Weakest signal first (Performance Mode OFF)
            target_networks.sort(key=lambda x: x.signal, reverse=self.use_best)
            selected_network = target_networks[0]
            
            # When Performance Mode is turned OFF, force connection to the poorer BSSID
            if not self.use_best:
                iface.disconnect()
                self.sleep(1)
                
                # Create profile bound to the weaker BSSID
                profile = pywifi.Profile()
                profile.ssid = selected_network.ssid
                profile.bssid = selected_network.bssid
                profile.auth = const.AUTH_ALG_OPEN
                profile.akm.append(const.AKM_TYPE_NONE)
                
                iface.remove_all_network_profiles()
                tmp_profile = iface.add_network_profile(profile)
                iface.connect(tmp_profile)
                
                self.sleep(3)  # Allow time for connection to switch
                self.status_signal.emit("Performance Mode OFF", "green")
                return

            # --- Performance Mode ON Logic ---
            # Get current BSSID using Windows netsh
            current_bssid = None
            try:
                output = subprocess.check_output(
                    ["netsh", "wlan", "show", "interfaces"], 
                    creationflags=0x08000000
                ).decode("utf-8", errors="ignore")
                
                for line in output.split('\n'):
                    if "BSSID" in line and "BSSID" == line.split(":")[0].strip():
                        parts = line.split(":")
                        if len(parts) >= 4:
                            current_bssid = ":".join(parts[1:]).strip().lower().replace("-", ":")
                            break
            except Exception as e:
                print(f"Could not get current BSSID: {e}")
                
            best_bssid = selected_network.bssid.strip().lower().replace("-", ":") if selected_network.bssid else ""
            
            if current_bssid and current_bssid == best_bssid:
                self.status_signal.emit("Performance Mode ON", "green")
            else:
                self.status_signal.emit("Performance Mode ON", "yellow")
                
        except Exception as e:
            self.status_signal.emit(f"Wi-Fi Error: {str(e)}", "error")


# --- WI-FI HELPERS / AUTO-CONNECT ---
def get_current_wifi_ssid():
    """Return the currently connected Wi-Fi SSID using Windows WLAN APIs."""
    if sys.platform != "win32":
        return ""

    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            creationflags=0x08000000,
            timeout=5
        ).decode("utf-8", errors="ignore")

        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("SSID") and not stripped.startswith("BSSID"):
                parts = stripped.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
    except Exception:
        pass

    return ""


class WiFiConnectThread(QThread):
    """Connect to a previously saved Windows Wi-Fi profile without blocking the UI."""
    connected = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, ssid, parent=None):
        super().__init__(parent)
        self.ssid = ssid

    def run(self):
        if not self.ssid:
            self.failed.emit("No Wi-Fi network was selected.")
            return

        try:
            # Reuse the Wi-Fi profile already stored by Windows.
            result = subprocess.run(
                ["netsh", "wlan", "connect", f"name={self.ssid}"],
                capture_output=True,
                text=True,
                creationflags=0x08000000,
                timeout=10
            )

            # netsh can return before association actually finishes.
            deadline = time.time() + 12
            while time.time() < deadline:
                current_ssid = get_current_wifi_ssid()
                if current_ssid.lower() == self.ssid.lower():
                    self.connected.emit(self.ssid)
                    return
                self.msleep(500)

            detail = (result.stdout or result.stderr or "Windows could not connect to the saved Wi-Fi profile.").strip()
            self.failed.emit(detail)
        except Exception as exc:
            self.failed.emit(str(exc))


# --- WI-FI PICKER ---
class WiFiScanThread(QThread):
    """Keep the (occasionally slow) Windows WLAN scan off the UI thread."""
    networks_found = pyqtSignal(list)
    scan_failed = pyqtSignal(str)

    def run(self):
        try:
            wifi = pywifi.PyWiFi()
            interfaces = wifi.interfaces()
            if not interfaces:
                raise RuntimeError("No Wi-Fi adapter was found.")

            iface = interfaces[0]
            iface.scan()
            self.sleep(3) # Wait for the hardware scan to populate
            networks = {}
            for network in iface.scan_results():
                ssid = (network.ssid or "").strip()
                if not ssid:
                    continue
                # Several access points can broadcast the same name. One card per SSID
                # is less noisy, and the strongest signal is the useful one.
                signal = int(network.signal or -100)
                existing = networks.get(ssid)
                if existing is None or signal > existing["signal"]:
                    networks[ssid] = {
                        "ssid": ssid,
                        "signal": signal,
                        "secured": network.akm != [const.AKM_TYPE_NONE],
                    }
            self.networks_found.emit(list(networks.values()))
        except Exception as exc:
            self.scan_failed.emit(str(exc))


def wifi_signal_color(signal):
    """Map Wi-Fi RSSI (dBm) to a connection-quality border color."""
    try:
        signal = int(signal)
    except (TypeError, ValueError):
        signal = -100

    # Excellent -> Poor. RSSI is normally a negative dBm value.
    if signal >= -50:
        return "#14532D"      # Dark green - excellent
    if signal >= -60:
        return "#16A34A"      # Green - very good
    if signal >= -67:
        return "#84CC16"      # Lime - good
    if signal >= -75:
        return "#EAB308"      # Yellow - fair
    if signal >= -85:
        return "#F97316"      # Orange - weak
    return "#DC2626"          # Red - poor


class _LegacyWiFiPickerDialog(QDialog):
    wifi_chosen = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize the background scan thread
        self.scan_thread = WiFiScanThread()
        self.scan_thread.networks_found.connect(self.on_scan_finished)
        self.scan_thread.scan_failed.connect(self.on_scan_failed)
        
        self.is_connecting = False
        self.initial_scan_done = False
        self.reusable_network_buttons = []
        self.skeleton_anims = [] # Keep animation references alive

        self.setWindowTitle("Loqin • Choose Wi-Fi")
        self.setMinimumSize(760, 580)
        self.resize(860, 680)

        # Matched directly to styles.css design tokens
        self.setStyleSheet("""
            QDialog {
                background-color: #090b18;
                font-family: 'Manrope', 'Segoe UI', sans-serif;
            }
            QLabel { 
                color: #f4f7fb; 
            }
            QScrollArea { 
                border: none; 
                background: transparent; 
            }
            QWidget#cardsContainer { 
                background: transparent; 
            }
            QScrollBar:vertical { 
                width: 6px; 
                background: transparent; 
                margin: 0px; 
            }
            QScrollBar::handle:vertical { 
                background: rgba(138, 160, 255, 0.3); 
                border-radius: 3px; 
                min-height: 28px; 
            }
            QScrollBar::handle:vertical:hover { 
                background: rgba(102, 199, 255, 0.5); 
            }
            
            /* Styled like .button-secondary in styles.css */
            QPushButton#refresh {
                color: #f4f7fb;
                background-color: rgba(16, 21, 38, 0.74);
                border: 1px solid rgba(102, 199, 255, 0.22);
                border-radius: 12px;
                font-size: 14px; 
                font-weight: 700;
                padding: 8px 20px; 
            }
            QPushButton#refresh:hover { 
                background-color: rgba(28, 36, 64, 0.9);
                border-color: rgba(102, 199, 255, 0.5);
            }
            QPushButton#refresh:pressed { 
                background-color: rgba(12, 15, 30, 0.9); 
                color: #a7b0d6; 
            }
            
            /* Skeleton loading card matching var(--panel) */
            QFrame#skeletonTile { 
                background: rgba(20, 26, 46, 0.6); 
                border: 1px solid rgba(146, 160, 215, 0.12);
                border-radius: 16px; 
                min-height: 80px; 
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(16)

        # Heading matching brand font style
        heading = QLabel("Wi-Fi")
        heading.setStyleSheet("font-size: 28px; font-weight: 800; color: #f4f7fb; letter-spacing: -0.03em; padding-bottom: 4px;")
        layout.addWidget(heading)

        toolbar = QHBoxLayout()
        self.status = QLabel("Scanning nearby networks…")
        self.status.setStyleSheet("color: #a7b0d6; font-size: 14px;")
        toolbar.addWidget(self.status)
        toolbar.addStretch()

        refresh = QPushButton("Refresh")
        refresh.setObjectName("refresh")
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.clicked.connect(self.scan_networks)
        toolbar.addWidget(refresh)
        layout.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards = QWidget()
        self.cards.setObjectName("cardsContainer")

        self.cards_layout = QGridLayout(self.cards)
        self.cards_layout.setContentsMargins(0, 10, 0, 10)
        self.cards_layout.setSpacing(14)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.cards)
        layout.addWidget(self.scroll, 1)

        self.show_skeleton_loading()

        # Set up a silent 5-second auto-refresher
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.setInterval(5000)
        self.auto_refresh_timer.timeout.connect(self.scan_networks)
        self.auto_refresh_timer.start()

        # Trigger first real scan
        self.scan_networks()

    def show_skeleton_loading(self, count=6, columns=2):
        """Displays temporary wireframe cards with a pulsing opacity animation."""
        self.clear_cards_layout()
        self.skeleton_anims.clear()
        
        for index in range(count):
            skeleton = QFrame()
            skeleton.setObjectName("skeletonTile")
            
            effect = QGraphicsOpacityEffect(skeleton)
            skeleton.setGraphicsEffect(effect)
            
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(1200)
            anim.setStartValue(0.25)
            anim.setKeyValueAt(0.5, 0.75)
            anim.setEndValue(0.25)
            anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            anim.setLoopCount(-1)
            anim.start()
            
            self.skeleton_anims.append(anim)
            
            row = index // columns
            col = index % columns
            self.cards_layout.addWidget(skeleton, row, col)

    def clear_cards_layout(self):
        """Helper to clear the grid layout completely."""
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def scan_networks(self):
        if self.is_connecting or self.scan_thread.isRunning():
            return
            
        if not self.initial_scan_done:
            self.status.setText("Scanning nearby networks…")
            
        self.scan_thread.start()

    def on_scan_failed(self, error):
        self.status.setText(f"Scan failed: {error}")
        self.status.setStyleSheet("color: #ff7b88; font-size: 14px;")

    def on_scan_finished(self, networks):
        portal_networks = []
        normal_networks = []
        
        networks.sort(key=lambda x: x['signal'], reverse=True)
        
        for net in networks:
            if not net.get('secured', True):
                portal_networks.append(net)
            else:
                normal_networks.append(net)
                
        self.update_networks_ui(portal_networks, normal_networks)
        
        current_time = datetime.now().strftime("%I:%M:%S %p")
        self.status.setText(f"Scan complete. Last updated at {current_time}")
        self.status.setStyleSheet("color: #a7b0d6; font-size: 14px;")

    def update_networks_ui(self, portal_networks, normal_networks, columns=2):
        combined_networks = [(net, True) for net in portal_networks] + [(net, False) for net in normal_networks]

        if not self.initial_scan_done:
            self.skeleton_anims.clear()
            self.clear_cards_layout()
            self.initial_scan_done = True

        for index in range(max(len(combined_networks), len(self.reusable_network_buttons))):
            if index < len(combined_networks):
                network_data, is_portal = combined_networks[index]
                ssid = network_data.get("ssid", "Unknown") if isinstance(network_data, dict) else str(network_data)
                signal = int(network_data.get("signal", -100)) if isinstance(network_data, dict) else -100
                signal_color = wifi_signal_color(signal)

                if index >= len(self.reusable_network_buttons):
                    btn = QPushButton()
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setMinimumHeight(80)
                    self.reusable_network_buttons.append(btn)
                    row = index // columns
                    col = index % columns
                    self.cards_layout.addWidget(btn, row, col)

                btn = self.reusable_network_buttons[index]
                btn.setText(f"  {ssid}")
                btn.setIcon(QIcon(resource_path("wifi.svg")))
                btn.setIconSize(QSize(32, 32))

                if is_portal:
                    # Inspired by .button-primary (Linear gradient with dark high-contrast text)
                    background_css = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #66c7ff, stop:1 #bb7cff)"
                    hover_background_css = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7ad0ff, stop:1 #c78eff)"
                    pressed_background_css = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #50b9f0, stop:1 #a86be6)"
                    text_color = "#06101c"
                    border_css = f"1px solid rgba(255, 255, 255, 0.3); border-left: 5px solid {signal_color}"
                else:
                    # Inspired by --panel and --line (Dark glass cards)
                    background_css = "rgba(16, 21, 38, 0.74)"
                    hover_background_css = "rgba(28, 36, 64, 0.9)"
                    pressed_background_css = "rgba(12, 15, 30, 0.9)"
                    text_color = "#f4f7fb"
                    border_css = f"1px solid rgba(146, 160, 215, 0.18); border-left: 5px solid {signal_color}"

                btn.setStyleSheet(f"""
                    QPushButton {{
                        color: {text_color};
                        background: {background_css};
                        border: {border_css};
                        border-radius: 16px;
                        padding: 16px 20px;
                        font-size: 15px;
                        font-weight: 700;
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        background: {hover_background_css};
                        border-color: {'rgba(255, 255, 255, 0.5)' if is_portal else 'rgba(102, 199, 255, 0.4)'};
                    }}
                    QPushButton:pressed {{
                        background: {pressed_background_css};
                    }}
                """)

                try:
                    btn.clicked.disconnect()
                except TypeError:
                    pass

                btn.clicked.connect(
                    lambda checked=False, target_ssid=ssid: self.connect_to_network(target_ssid)
                )
                btn.setVisible(True)
            else:
                self.reusable_network_buttons[index].setVisible(False)

    def connect_to_network(self, ssid):
        self.is_connecting = True
        self.status.setText(f"Connecting to {ssid}...")
        self.status.setStyleSheet("color: #66c7ff; font-size: 14px;")
        self.auto_refresh_timer.stop()
        self.wifi_chosen.emit(ssid)
        self.accept()

# --- UI: WI-FI Picker ---
class WiFiPickerDialog(QDialog):
    """inspired by https://loqin-vit.vercel.app"""
    wifi_chosen = pyqtSignal(str)
    portal_pattern = re.compile(r"^(?:VIT|[A-Z]-VIT)$", re.IGNORECASE)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan_thread = WiFiScanThread()
        self.scan_thread.networks_found.connect(self.on_scan_finished)
        self.scan_thread.scan_failed.connect(self.on_scan_failed)
        self.is_connecting = False
        self.initial_scan_done = False
        self.skeleton_anims = []
        self.setWindowTitle("Loqin • Wi-Fi")
        self.setWindowIcon(QIcon(resource_path("loqin_logo_small.png")))
        self.setMinimumSize(760, 620)
        self.resize(920, 720)
        self.setStyleSheet("""
            QDialog { background: #090b18; color: #f4f7fb; font-family: 'Manrope', 'Segoe UI', sans-serif; }
            QFrame#topbar { background: rgba(10,13,26,0.86); border: 1px solid rgba(146,160,215,0.18); border-radius: 22px; }
            QFrame#brandMark { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(102,199,255,0.18),stop:1 rgba(187,124,255,0.16)); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; }
            QFrame#heroPanel { background: rgba(10,18,32,0.66); border: 1px solid rgba(146,160,215,0.18); border-radius: 30px; }
            QLabel { color: #f4f7fb; }
            QLabel#muted, QLabel#subtext { color: #a7b0d6; }
            QLabel#eyebrow { color: #a7b0d6; font-size: 11px; font-weight: 800; letter-spacing: 2px; }
            QLabel#heroTitle { color: #f4f7fb; font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 34px; font-weight: 700; }
            QLabel#brandName { color: #f4f7fb; font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 18px; font-weight: 700; }
            QLabel#brandCaption { color: #a7b0d6; font-size: 11px; }
            QLabel#statusPill { color: #e0f4ff; background: rgba(102,199,255,0.08); border: 1px solid rgba(102,199,255,0.18); border-radius: 14px; padding: 8px 12px; }
            QPushButton#refresh { color: #f4f7fb; background: rgba(16,21,38,0.74); border: 1px solid rgba(102,199,255,0.22); border-radius: 16px; padding: 11px 20px; font-weight: 800; }
            QPushButton#refresh:hover { background: rgba(28,36,64,0.9); border-color: rgba(102,199,255,0.5); }
            QPushButton#wifiCard { color: #f4f7fb; background: rgba(16,21,38,0.86); border: 1px solid rgba(146,160,215,0.18); border-radius: 18px; padding: 18px; font-size: 15px; font-weight: 800; text-align: left; }
            QPushButton#wifiCard:hover { background: rgba(28,36,64,0.9); border-color: rgba(102,199,255,0.5); }
            QPushButton#portalCard { color: #06101c; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #66c7ff,stop:1 #bb7cff); border: 1px solid rgba(255,255,255,0.30); border-radius: 18px; padding: 18px; font-size: 15px; font-weight: 800; text-align: left; }
            QPushButton#portalCard:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7ad0ff,stop:1 #c78eff); }
            QScrollArea { border: none; background: transparent; }
            QWidget#cardsContainer { background: transparent; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: rgba(138,160,255,0.3); border-radius: 3px; min-height: 28px; }
            QFrame#skeletonTile { background: rgba(20,26,46,0.6); border: 1px solid rgba(146,160,215,0.12); border-radius: 18px; min-height: 94px; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 30)
        root.setSpacing(18)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(16, 12, 16, 12)
        mark = QFrame()
        mark.setObjectName("brandMark")
        mark.setFixedSize(44, 44)
        mark_layout = QVBoxLayout(mark)
        mark_layout.setContentsMargins(8, 8, 8, 8)
        logo = QLabel()
        logo.setPixmap(QPixmap(resource_path("loqin_logo_small.png")).scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        mark_layout.addWidget(logo)
        top_layout.addWidget(mark)
        brand = QVBoxLayout()
        brand.setSpacing(1)
        name = QLabel("Loqin")
        name.setObjectName("brandName")
        caption = QLabel("PC Wi-Fi Client")
        caption.setObjectName("brandCaption")
        brand.addWidget(name)
        brand.addWidget(caption)
        top_layout.addLayout(brand)
        top_layout.addStretch()
        pill = QLabel("●  Wi-Fi selector")
        pill.setObjectName("statusPill")
        top_layout.addWidget(pill)
        root.addWidget(topbar)

        hero = QFrame()
        hero.setObjectName("heroPanel")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(26, 24, 26, 24)
        hero_layout.setSpacing(10)
        eyebrow = QLabel("NETWORK CONTROL")
        eyebrow.setObjectName("eyebrow")
        hero_layout.addWidget(eyebrow)
        heading = QLabel("Choose your network.")
        heading.setObjectName("heroTitle")
        hero_layout.addWidget(heading)
        subtext = QLabel("Select a nearby Wi-Fi network to connect Loqin and continue in the background.")
        subtext.setObjectName("subtext")
        subtext.setWordWrap(True)
        hero_layout.addWidget(subtext)
        toolbar = QHBoxLayout()
        self.status = QLabel("Scanning nearby networks…")
        self.status.setObjectName("muted")
        toolbar.addWidget(self.status)
        toolbar.addStretch()
        refresh = QPushButton("Refresh")
        refresh.setObjectName("refresh")
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.clicked.connect(self.scan_networks)
        toolbar.addWidget(refresh)
        hero_layout.addLayout(toolbar)
        root.addWidget(hero)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.cards = QWidget()
        self.cards.setObjectName("cardsContainer")
        self.cards_layout = QGridLayout(self.cards)
        self.cards_layout.setContentsMargins(0, 0, 6, 0)
        self.cards_layout.setSpacing(14)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.cards)
        root.addWidget(self.scroll, 1)

        
        self.show_skeleton_loading()
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.setInterval(5000)
        self.auto_refresh_timer.timeout.connect(self.scan_networks)
        self.auto_refresh_timer.start()
        self.scan_networks()

    def show_skeleton_loading(self, count=6, columns=2):
        self.clear_cards_layout()
        self.skeleton_anims.clear()
        for index in range(count):
            skeleton = QFrame()
            skeleton.setObjectName("skeletonTile")
            effect = QGraphicsOpacityEffect(skeleton)
            skeleton.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(1400)
            anim.setStartValue(0.28)
            anim.setKeyValueAt(0.5, 0.75)
            anim.setEndValue(0.28)
            anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            anim.setLoopCount(-1)
            anim.start()
            self.skeleton_anims.append(anim)
            self.cards_layout.addWidget(skeleton, index // columns, index % columns)

    def clear_cards_layout(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def scan_networks(self):
        if self.is_connecting or self.scan_thread.isRunning():
            return
        if not self.initial_scan_done:
            self.status.setText("Scanning nearby networks…")
        self.scan_thread.start()

    def on_scan_failed(self, error):
        self.status.setText(f"Scan failed: {error}")
        self.status.setStyleSheet("color: #ff7b88; font-size: 14px;")

    def on_scan_finished(self, networks):
        networks.sort(key=lambda item: item.get("signal", -100), reverse=True)
        portal = [net for net in networks if self.portal_pattern.fullmatch(net.get("ssid", "").strip())]
        normal = [net for net in networks if net not in portal]
        self.update_networks_ui(portal, normal)
        self.status.setText(f"{len(networks)} networks found • updated {datetime.now().strftime('%I:%M:%S %p')}")
        self.status.setStyleSheet("color: #a7b0d6; font-size: 14px;")

    def update_networks_ui(self, portal_networks, normal_networks, columns=2):
        self.skeleton_anims.clear()
        self.clear_cards_layout()
        self.initial_scan_done = True

        # Keep the visual grouping explicit while retaining the website's grid rhythm.
        groups = []
        if portal_networks:
            groups.append(("PORTAL WI-FI", portal_networks, True))
        if normal_networks:
            groups.append(("OTHER NETWORKS", normal_networks, False))
        row = 0
        for section_name, section_networks, is_portal in groups:
            section = QLabel(section_name)
            section.setObjectName("eyebrow")
            section.setStyleSheet("color: #a7b0d6; font-size: 11px; font-weight: 800; letter-spacing: 2px; padding: 8px 2px 0;")
            self.cards_layout.addWidget(section, row, 0, 1, columns)
            row += 1
            for index, network in enumerate(section_networks):
                column = index % columns
                card_row = row + (index // columns)
                self.add_network_card(network, is_portal, card_row, column)
            row += (len(section_networks) + columns - 1) // columns

    def add_network_card(self, network, is_portal, row, column):
        ssid = network.get("ssid", "Unknown")
        signal = int(network.get("signal", -100))
        security = "Open network" if not network.get("secured", True) else "Secured network"
        button = QPushButton(f"{ssid}\n{security}  •  {signal} dBm")
        button.setObjectName("portalCard" if is_portal else "wifiCard")
        button.setIcon(QIcon(resource_path("wifi.svg")))
        button.setIconSize(QSize(30, 30))
        button.setMinimumHeight(94)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda checked=False, target=ssid: self.connect_to_network(target))
        self.cards_layout.addWidget(button, row, column)

    def connect_to_network(self, ssid):
        self.is_connecting = True
        self.status.setText(f"Connecting to {ssid}…")
        self.status.setStyleSheet("color: #66c7ff; font-size: 14px;")
        self.auto_refresh_timer.stop()
        self.wifi_chosen.emit(ssid)
        self.accept()

# --- AUTO-UPDATER THREADS ---
class UpdateChecker(QThread):
    update_found = pyqtSignal(str, str, str)
    no_update_found = pyqtSignal()

    def run(self):
        max_retries = 5
        retry_delay = 5  # Wait 5 seconds between attempts
        
        for attempt in range(max_retries):
            print(f"Checking for updates (Attempt {attempt + 1}/{max_retries})...")
            try:
                headers = {
                    "Accept": "application/vnd.github+json"
                }
                res = requests.get(GITHUB_API_URL, timeout=5, headers=headers)
                
                if res.status_code == 200:
                    data = res.json()
                    latest_version_tag = data.get("tag_name", "").replace("v", "")
                    
                    current_v = tuple(map(int, APP_VERSION.split('.')))
                    latest_v = tuple(map(int, latest_version_tag.split('.')))
                    
                    if latest_v > current_v:
                        download_url = "https://raw.githubusercontent.com/notaayushsrivastava/Loqin/master/Output/Install_Loqin_Update.exe"
                        
                        self.update_found.emit(
                            latest_version_tag, 
                            download_url, 
                            data.get("body", "Bug fixes and improvements.")
                        )
                    else:
                        self.no_update_found.emit()
                        
                    # Exit the thread successfully
                    return 
                    
            except requests.exceptions.SSLError:
                print(f"HTTPS intercepted by captive portal. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                
            except Exception as e:
                print(f"Update check failed due to network error: {e}")
                # For non-SSL errors (like no connection at all), abort entirely
                return 
                
        print("Update check aborted: Captive portal is persistently intercepting HTTPS traffic.")

class AccountDetailsDialog(QDialog):
    # Notice we now pass username and account_url into the dialog
    def __init__(self, username, account_url, parent=None):
        super().__init__(parent)
        self.username = username
        self.account_url = account_url
        
        self.setWindowTitle("Loqin • Account Management")
        self.setWindowIcon(QIcon(resource_path("loqin_logo_small.png"))) 
        self.resize(860, 560) 
        
        self.setStyleSheet("""
            QDialog { background: #090b18; color: #f4f7fb; font-family: 'Manrope', 'Segoe UI', sans-serif; }
            QFrame#accountHeader { background: rgba(10,13,26,0.86); border: 1px solid rgba(146,160,215,0.18); border-radius: 22px; }
            QFrame#accountMark { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(102,199,255,0.18),stop:1 rgba(187,124,255,0.16)); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; }
            QLabel { color: #f4f7fb; font-size: 14px; }
            QTableWidget { background: rgba(16,21,38,0.86); color: #f4f7fb; gridline-color: rgba(146,160,215,0.12); border: 1px solid rgba(146,160,215,0.18); border-radius: 18px; font-size: 12px; selection-background-color: rgba(102,199,255,0.22); selection-color: #f4f7fb; }
            QHeaderView::section { background: rgba(20,26,46,0.96); color: #a7b0d6; font-weight: 800; padding: 10px 8px; border: none; border-bottom: 1px solid rgba(146,160,215,0.18); }
            QTableWidget::item { padding: 7px; border: none; }
            QTabWidget::pane { border: 1px solid rgba(146,160,215,0.18); border-radius: 18px; top: -1px; background: rgba(10,18,32,0.66); }
            QTabBar::tab { background: rgba(255,255,255,0.03); color: #a7b0d6; padding: 11px 18px; margin-right: 8px; border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; font-weight: 800; }
            QTabBar::tab:hover { color: #f4f7fb; border-color: rgba(102,199,255,0.3); }
            QTabBar::tab:selected { color: #f4f7fb; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(102,199,255,0.16),stop:1 rgba(187,124,255,0.14)); border-color: rgba(102,199,255,0.3); }
            QLineEdit { background: rgba(16,21,38,0.86); color: #f4f7fb; border: 1px solid rgba(146,160,215,0.18); border-radius: 12px; padding: 8px 10px; font-size: 14px; }
            QLineEdit:focus { border-color: rgba(102,199,255,0.65); background: rgba(20,26,46,0.96); }
            QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #66c7ff,stop:1 #bb7cff); color: #06101c; font-weight: 800; border: 1px solid rgba(255,255,255,0.22); border-radius: 14px; padding: 10px 14px; font-size: 14px; }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7ad0ff,stop:1 #c78eff); }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(16)

        account_header = QFrame()
        account_header.setObjectName("accountHeader")
        header_layout = QHBoxLayout(account_header)
        header_layout.setContentsMargins(16, 14, 16, 14)
        mark = QFrame()
        mark.setObjectName("accountMark")
        mark.setFixedSize(44, 44)
        mark_layout = QVBoxLayout(mark)
        mark_layout.setContentsMargins(8, 8, 8, 8)
        logo = QLabel()
        logo.setPixmap(QPixmap(resource_path("loqin_logo_small.png")).scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        mark_layout.addWidget(logo)
        header_layout.addWidget(mark)
        title_layout = QVBoxLayout()
        title_layout.setSpacing(1)
        title = QLabel("Account management")
        title.setStyleSheet("font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 700; color: #f4f7fb;")
        subtitle = QLabel("Review your session history or update your portal password.")
        subtitle.setStyleSheet("color: #a7b0d6; font-size: 12px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        account_pill = QLabel("Secure account tools")
        account_pill.setStyleSheet("color: #e0f4ff; background: rgba(102,199,255,0.08); border: 1px solid rgba(102,199,255,0.18); border-radius: 14px; padding: 8px 12px; font-weight: 700;")
        header_layout.addWidget(account_pill)
        layout.addWidget(account_header)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # Build Tabs
        self.setup_history_tab()
        self.setup_password_tab()

    def setup_history_tab(self):
        self.history_tab = QWidget()
        layout = QVBoxLayout(self.history_tab)
        
        title = QLabel("Recent network sessions")
        title.setStyleSheet("font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 18px; font-weight: 700; color: #f4f7fb; margin-bottom: 6px;")
        layout.addWidget(title)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Location", "Login Time", "Logout Time", 
            "Usage Time", "Upload", "Download", "Total Data"
        ])
        
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True) 
        self.table.verticalHeader().setVisible(False) 
        
        layout.addWidget(self.table)
        self.tabs.addTab(self.history_tab, "Usage History")

    def create_password_field(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        line_edit = QLineEdit()
        line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        line_edit.setFixedWidth(250)
        
        toggle_btn = QPushButton("👁")
        toggle_btn.setFixedSize(32, 32)
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setCheckable(True)
        toggle_btn.setStyleSheet("""
            QPushButton {
                background: #1E222D; 
                color: #BBBBBB; 
                border: 1px solid #2C313E; 
                border-radius: 4px; 
                font-size: 14px;
            }
            QPushButton:checked {
                background: #3da5ff; 
                color: #171A22; 
                border: 1px solid #3da5ff;
            }
            QPushButton:hover {
                border: 1px solid #3da5ff;
            }
        """)
        
        def on_toggle(checked):
            if checked:
                line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                toggle_btn.setText("🔒")
            else:
                line_edit.setEchoMode(QLineEdit.EchoMode.Password)
                toggle_btn.setText("👁")
                
        toggle_btn.toggled.connect(on_toggle)
        
        layout.addWidget(line_edit)
        layout.addWidget(toggle_btn)
        return container, line_edit

    def setup_password_tab(self):
        self.password_tab = QWidget()
        layout = QVBoxLayout(self.password_tab)
        
        title = QLabel("Reset network password")
        title.setStyleSheet("font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 18px; font-weight: 700; color: #f4f7fb; margin-bottom: 12px;")
        layout.addWidget(title)
        
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setSpacing(15)

        container_old, self.old_pw_input = self.create_password_field()
        container_new, self.new_pw_input = self.create_password_field()
        container_confirm, self.confirm_pw_input = self.create_password_field()
        for password_container in (container_old, container_new, container_confirm):
            password_container.findChild(QPushButton).setStyleSheet("""
                QPushButton { background: rgba(16,21,38,0.86); color: #a7b0d6; border: 1px solid rgba(146,160,215,0.18); border-radius: 10px; font-size: 14px; }
                QPushButton:checked { background: #66c7ff; color: #06101c; border-color: #66c7ff; }
                QPushButton:hover { border-color: #66c7ff; }
            """)

        form_layout.addRow("Current Password:", container_old)
        form_layout.addRow("New Password:", container_new)
        form_layout.addRow("Confirm Password:", container_confirm)
        
        layout.addLayout(form_layout)
        
        # Forgot Password Button
        forgot_btn = QPushButton("Forgot Password?")
        forgot_btn.setFixedWidth(287)
        forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #a7b0d6;
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 12px;
                font-size: 13px;
                text-align: left;
                padding: 8px 10px;
            }
            QPushButton:hover {
                color: #f4f7fb;
                border-color: rgba(102,199,255,0.3);
                background: rgba(255,255,255,0.03);
            }
        """)
        forgot_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://hostelwifi.vit.ac.in/index.php?a=add&category=4")))

        self.update_btn = QPushButton("Update Password")
        self.update_btn.setFixedWidth(287)
        self.update_btn.clicked.connect(self.submit_password_change)
        
        # Group buttons under form layout
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(forgot_btn)
        btn_layout.setContentsMargins(120, 10, 0, 0)
        layout.addLayout(btn_layout)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("margin-left: 120px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.tabs.addTab(self.password_tab, "Change Password")

    def populate_table(self, rows_data, grand_total_data):
        self.table.setRowCount(0) 
        for row_idx, row_data in enumerate(rows_data):
            self.table.insertRow(row_idx)
            for col_idx, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)

        if grand_total_data:
            total_row = self.table.rowCount()
            self.table.insertRow(total_row)
            
            total_label_item = QTableWidgetItem("Grand Total")
            total_label_item.setForeground(QColor("#8ff3c8")) 
            total_label_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(total_row, 0, total_label_item)
            
            for col_offset, text in enumerate(grand_total_data):
                item = QTableWidgetItem(text)
                item.setForeground(QColor("#8ff3c8"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(total_row, col_offset + 3, item)
                
            self.table.setSpan(total_row, 0, 1, 3) 

    def submit_password_change(self):
        old_pw = self.old_pw_input.text()
        new_pw = self.new_pw_input.text()
        confirm_pw = self.confirm_pw_input.text()

        if not old_pw or not new_pw or not confirm_pw:
            self.status_label.setStyleSheet("color: #f1c40f; margin-left: 120px;")
            self.status_label.setText("Warning: Please fill all fields.")
            return
            
        if new_pw != confirm_pw:
            self.status_label.setStyleSheet("color: #e74c3c; margin-left: 120px;")
            self.status_label.setText("Error: New passwords do not match.")
            return

        self.status_label.setStyleSheet("color: #3da5ff; margin-left: 120px;")
        self.status_label.setText("Updating password...")
        self.update_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            # Dynamically parse the IP (e.g., http://136.233.9.110) from the valid session URL
            parsed = urlparse(self.account_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            # Use a Session to capture the JSESSIONID cookie automatically
            session = requests.Session()
            session.get(f"{base_url}/registration/main.do?content_key=%2FChangePassword.jsp", timeout=5)

            payload = {
                "changeUserId": self.username,
                "changePassword": old_pw,
                "changeNewPassword": new_pw,
                "changeConfirmNewPassword": confirm_pw,
                "submit": "Update"
            }
            
            headers = {
                "Referer": f"{base_url}/registration/main.do?content_key=%2FChangePassword.jsp"
            }

            response = session.post(f"{base_url}/registration/changePassword.do", data=payload, headers=headers, timeout=5)

            # Pronto generally returns 200 OK whether it succeeds or fails, so we ensure it went through
            if response.status_code == 200:
                self.status_label.setStyleSheet("color: #2ecc71; margin-left: 120px; font-weight: bold;")
                self.status_label.setText("Success! Password updated.")
                
                # IMPORTANT: Update your local config file immediately so the app doesn't break
                # Assuming your config manager has a method like this:
                # ConfigManager.save_config({"username": self.username}, new_pw)

                keyring.set_password(APP_NAME, self.username, new_pw)
                
            else:
                self.status_label.setStyleSheet("color: #e74c3c; margin-left: 120px;")
                self.status_label.setText(f"Failed with status: {response.status_code}")

        except Exception as e:
            self.status_label.setStyleSheet("color: #e74c3c; margin-left: 120px;")
            self.status_label.setText(f"Connection Error: {e}")
        finally:
            self.update_btn.setEnabled(True)

class UpdateDownloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            # No token needed here either!
            res = requests.get(self.url, stream=True, timeout=15, allow_redirects=True)
            res.raise_for_status() 
            
            total_size = int(res.headers.get('content-length', 0))
            
            temp_dir = os.environ.get("TEMP", APPDATA_DIR)
            exe_path = os.path.join(temp_dir, "Install_Loqin_Update.exe")
            
            downloaded = 0
            with open(exe_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            self.progress.emit(int((downloaded / total_size) * 100))
            
            self.finished.emit(exe_path)
        except Exception as e:
            print(f"Download failed: {e}")
            self.finished.emit("")

class ReleaseNotesDialog(QDialog):
    def __init__(self, version, notes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Available")
        self.resize(480, 380)

        layout = QVBoxLayout(self)

        # Header Text Widget
        header_label = QLabel(f"<h3>A new version ({version}) of Loqin is available!</h3>")
        layout.addWidget(header_label)

        # Release Notes Display
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        
        # Format release notes markdown
        markdown_content = f"**Release Notes:**\n\n{notes}"
        self.text_browser.setMarkdown(markdown_content)
        layout.addWidget(self.text_browser)

        # Action Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        button_box.button(QDialogButtonBox.StandardButton.Yes).setText("Install Now")
        button_box.button(QDialogButtonBox.StandardButton.No).setText("Later")
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


# --- HELPER: Secure Credentials & Config Management ---
class ConfigManager:
    @staticmethod
    def ensure_dir_exists():
        if not os.path.exists(APPDATA_DIR):
            os.makedirs(APPDATA_DIR, exist_ok=True)

    @staticmethod
    def load_config():
        default_config = {
            "username": "",
            "interval": 10,
            "auto_connect": True,
            "last_wifi_ssid": ""
        }
        ConfigManager.ensure_dir_exists()
        
        config_needs_saving = False

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded_data = json.load(f)
                    default_config.update(loaded_data)
                    
                    # --- SECURITY MIGRATION ---
                    # If the Inno Setup installer left a plain-text password in the JSON,
                    # we secure it into the OS keyring and delete it from the JSON.
                    if "password" in loaded_data:
                        pwd = loaded_data["password"]
                        if pwd and default_config["username"]:
                            ConfigManager.set_password(default_config["username"], pwd)
                        
                        # Remove password from the active config dictionary
                        if "password" in default_config:
                            del default_config["password"]
                        
                        # Flag the file to be overwritten without the password
                        config_needs_saving = True
                        
            except Exception:
                pass
        else:
            # File doesn't exist yet, we need to create it
            config_needs_saving = True

        # Save config if it's a first run OR if we just scrubbed the password
        if config_needs_saving:
            ConfigManager.save_config(default_config)
            
        return default_config

    @staticmethod
    def save_config(config):
        ConfigManager.ensure_dir_exists()
        
        # Double-check that we never accidentally save a password in plain text
        clean_config = config.copy()
        if "password" in clean_config:
            del clean_config["password"]
            
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(clean_config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    @staticmethod
    def get_password(username):
        if not username:
            return ""
        return keyring.get_password(APP_NAME, username) or ""

    @staticmethod
    def set_password(username, password):
        if username:
            keyring.set_password(APP_NAME, username, password)


# --- WORKER THREAD: Non-blocking Network Ping & Login ---
class NetworkWorker(QThread):
    status_signal = pyqtSignal(str, str)
    account_data_signal = pyqtSignal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.is_running = True
        self.is_paused = False

    def check_network_state(self):
        try:
            res = requests.get("http://clients3.google.com/generate_204", timeout=3, allow_redirects=False)
            if res.status_code == 204:
                return "ONLINE"
            else:
                return "PORTAL"
        except requests.exceptions.RequestException:
            return "OFFLINE"

    def run(self):
        while self.is_running:
            # --- 2. Add this pause check ---
            if self.is_paused:
                self.sleep(1) # Sleep briefly so we don't hog the CPU while paused
                continue      # Skip the rest of the loop and check again
            # -------------------------------
            username = self.config.get("username")
            password = ConfigManager.get_password(username)

            if not username or not password:
                self.status_signal.emit("Missing credentials", "error")
                return

            state = self.check_network_state()

            if state == "ONLINE":
                self.status_signal.emit("Connected", "green")
                return
            elif state == "OFFLINE":
                self.status_signal.emit("Waiting for Wi-Fi...", "yellow")
                return
                
            self.status_signal.emit("Portal detected. Authenticating...", "yellow")
            self.login(username, password)
            return

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        return self.is_paused

    def login(self, username, password):
        base_url = "http://phc.prontonetworks.com"
        auth_url = f"{base_url}/cgi-bin/authlogin?URI=http://example.com"

        payload = {
            "userId": username,
            "password": password,
            "serviceName": "ProntoAuthentication",
            "URI": "http://example.com"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": base_url,
            "Referer": f"{base_url}/cgi-bin/authlogin?URI=http://www.msftconnecttest.com/redirect"
        }

        try:
            response = requests.post(auth_url, data=payload, headers=headers, timeout=5)
            if self.check_network_state() == "ONLINE":
                self.status_signal.emit("Logged in successfully!", "green")
                html_content = response.text 

                # This regex finds the link, capturing both the FULL URL (Group 1) and just the IP (Group 2)
                match = re.search(r'href="(http://([0-9\.]+)/registration/Main\.jsp\?sessionId=[^"]+)"', html_content)

                if match:
                    full_account_url = match.group(1) 
                    # Example: http://136.233.9.110/registration/Main.jsp?sessionId=1785581532416&wispId=1
                    
                    portal_ip = match.group(2)        
                    # Example: 136.233.9.110

                    print(f"Extracted IP: {portal_ip}")
                    
                    # Emit the full URL to the main thread so your account dialog can scrape it
                    self.account_data_signal.emit(full_account_url)
                else:
                    print("Could not find the account link in the response HTML.")
            else:
                self.status_signal.emit("Login failed. Check credentials.", "error")
        except Exception as e:
            print(e)
            self.status_signal.emit("Portal timeout or error.", "error")


class SpeedGraphDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Loqin • Live Network Monitor")
        self.setWindowIcon(QIcon(resource_path("loqin_logo_small.png")))
        self.resize(820, 520)

        self.download_history = [0] * 60
        self.upload_history = [0] * 60

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # ---------------- Header Bar ---------------- #
        header_layout = QHBoxLayout()

        title = QLabel("Real-Time Network Usage")
        title.setStyleSheet("color: #f4f7fb; font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 700;")

        # Always on top checkbox
        self.pin_checkbox = QCheckBox("Always on Top")
        self.pin_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_checkbox.setStyleSheet("""
            QCheckBox {
                color: #a7b0d6;
                font-size: 13px;
                font-weight: 500;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid rgba(146,160,215,0.4);
                border-radius: 5px;
                background: rgba(255,255,255,0.04);
            }
            QCheckBox::indicator:checked {
                background: #66c7ff;
                border: 1px solid #66c7ff;
            }
            QCheckBox:hover {
                color: #f4f7fb;
            }
        """)
        self.pin_checkbox.toggled.connect(self.toggle_always_on_top)

        # --- NYAN CAT EASTER EGG TRACKERS ---
        self.secret_code = "nyan"
        self.code_index = 0
        self.nyan_mode = False

        # Centers the title while pushing the pin checkbox to the far right
        header_layout.addStretch()
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.pin_checkbox)

        layout.addLayout(header_layout)

        self.graph = pg.PlotWidget()

        layout.addWidget(self.graph)

        self.stats = QLabel()
        self.stats.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.stats.setStyleSheet("color: #a7b0d6; font-size: 13px; padding: 8px;")

        layout.addWidget(self.stats)

        self.setStyleSheet("""
            QDialog { background: #090b18; color: #f4f7fb; font-family: 'Manrope', 'Segoe UI', sans-serif; }
        """)

        # ---------------- Graph ---------------- #

        self.graph.setBackground("#10162a")

        self.graph.showGrid(
            x=True,
            y=True,
            alpha=0.25
        )

        self.graph.hideButtons()

        self.graph.setMouseEnabled(False, False)

        self.graph.setMenuEnabled(False)

        self.graph.setClipToView(True)

        self.graph.setDownsampling(mode="peak")

        self.graph.setLabel("left", "Speed (KB/s)", color="#a7b0d6")

        self.graph.setLabel("bottom", "Time", color="#a7b0d6")

        self.graph.getAxis("left").setPen(pg.mkPen("#59658a"))

        self.graph.getAxis("bottom").setPen(pg.mkPen("#59658a"))

        self.graph.getAxis("left").setTextPen("#a7b0d6")

        self.graph.getAxis("bottom").setTextPen("#a7b0d6")

        self.graph.setYRange(0, 100)

        # Download curve
        self.download_curve = self.graph.plot(
            pen=pg.mkPen("#66c7ff", width=3),
            name="Download"
        )

        # Upload curve
        self.upload_curve = self.graph.plot(
            pen=pg.mkPen("#8ff3c8", width=3),
            name="Upload"
        )

        legend = self.graph.addLegend()

        legend.setBrush(pg.mkBrush(20, 26, 46, 220))

        legend.setOffset((15, 15))

    def keyPressEvent(self, event):
        char = event.text().lower()
        if char == self.secret_code[self.code_index]:
            self.code_index += 1
            if self.code_index == len(self.secret_code):
                self.toggle_nyan_mode()
                self.code_index = 0
        else:
            self.code_index = 0
            
        super().keyPressEvent(event)

    def generate_nyan_cursor(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 1. Rainbow Trail (left side)
        rainbow_colors = ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0099FF", "#8B00FF"]
        for i, color in enumerate(rainbow_colors):
            painter.fillRect(0, 10 + (i * 2), 12, 2, QColor(color))

        # 2. Pop-Tart Body (center)
        painter.fillRect(12, 9, 14, 14, QColor("#FFD1DC"))  # Biscuit Crust
        painter.fillRect(13, 10, 12, 12, QColor("#FF69B4")) # Pink Frosting
        # Frosting Sprinkles
        painter.fillRect(15, 12, 2, 2, QColor("#FF007F"))
        painter.fillRect(20, 15, 2, 2, QColor("#FF007F"))
        painter.fillRect(16, 18, 2, 2, QColor("#FF007F"))

        # 3. Cat Head & Ears (right side)
        painter.fillRect(22, 13, 9, 8, QColor("#999999"))   # Head Base
        painter.fillRect(23, 10, 2, 3, QColor("#999999"))   # Left Ear
        painter.fillRect(28, 10, 2, 3, QColor("#999999"))   # Right Ear
        painter.fillRect(24, 15, 2, 2, QColor("#000000"))   # Left Eye
        painter.fillRect(28, 15, 2, 2, QColor("#000000"))   # Right Eye
        painter.fillRect(26, 18, 2, 1, QColor("#FFB6C1"))   # Cheek

        painter.end()
        # Set hotspot near the cat's nose
        return QCursor(pixmap, 26, 15)

    def toggle_nyan_mode(self):
        self.nyan_mode = not self.nyan_mode
        
        if self.nyan_mode:
            self.setWindowTitle("Loqin • Nyan Cat Mode!")
            self.setCursor(self.generate_nyan_cursor())
            self.graph.setBackground("#0F051D") # Deep space background
            self.download_curve.setPen(pg.mkPen("#FF69B4", width=3)) # Hot pink
            self.upload_curve.setPen(pg.mkPen("#00FFFF", width=3))   # Electric cyan
            self.stats.setStyleSheet("""
                QLabel{ color:#FFD1DC; font-size:13px; font-weight: bold; }
            """)
        else:
            self.setWindowTitle("Loqin • Live Network Monitor")
            self.unsetCursor() # Reverts back to standard Windows cursor
            self.graph.setBackground("#10162a")
            self.download_curve.setPen(pg.mkPen("#3da5ff", width=3))
            self.upload_curve.setPen(pg.mkPen("#2ecc71", width=3))
            self.stats.setStyleSheet("""
                QLabel{ color:#cccccc; font-size:13px; }
            """)
    

    def toggle_always_on_top(self, checked):
        was_visible = self.isVisible()

        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)

        # Qt hides windows briefly when modifying flags, re-show if open
        if was_visible:
            self.show()

    def update_data(self, download, upload):

        download /= 1024
        upload /= 1024

        self.download_history.pop(0)
        self.download_history.append(download)

        self.upload_history.pop(0)
        self.upload_history.append(upload)

        maximum = max(
            max(self.download_history),
            max(self.upload_history),
            100
        )

        self.graph.setYRange(0, maximum * 1.15)

        self.download_curve.setData(self.download_history)

        self.upload_curve.setData(self.upload_history)

        self.stats.setText(
            f"""
            <font color='#3da5ff'>↓ {download:.1f} KB/s</font>
            &nbsp;&nbsp;&nbsp;&nbsp;
            <font color='#2ecc71'>↑ {upload:.1f} KB/s</font>
            &nbsp;&nbsp;&nbsp;&nbsp;
            Peak: {maximum:.1f} KB/s
            """
        )

# --- UI: Configuration Settings Window ---
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loqin for PC - Settings")
        self.setFixedSize(520, 600)
        self.setWindowIcon(QIcon(resource_path("loqin_logo_small.png")))
        self.setStyleSheet("""
            QDialog { background: #090b18; color: #f4f7fb; font-family: 'Manrope', 'Segoe UI', sans-serif; }
            QLabel { color: #a7b0d6; font-size: 13px; }
            QLineEdit, QSpinBox { color: #f4f7fb; background: rgba(16,21,38,0.86); border: 1px solid rgba(146,160,215,0.18); border-radius: 12px; padding: 9px 11px; min-height: 18px; }
            QLineEdit:focus, QSpinBox:focus { border-color: rgba(102,199,255,0.65); background: rgba(20,26,46,0.96); }
            QSpinBox::up-button, QSpinBox::down-button { width: 22px; border: none; background: transparent; }
            QCheckBox { color: #a7b0d6; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid rgba(146,160,215,0.4); border-radius: 5px; background: rgba(255,255,255,0.04); }
            QCheckBox::indicator:checked { background: #66c7ff; border-color: #66c7ff; }
            QPushButton { color: #06101c; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #66c7ff,stop:1 #bb7cff); border: 1px solid rgba(255,255,255,0.22); border-radius: 14px; padding: 10px 16px; font-weight: 800; }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7ad0ff,stop:1 #c78eff); }
        """)
        
        self.config = ConfigManager.load_config()
        self.init_ui()

    def create_password_field(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        line_edit = QLineEdit()
        line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        toggle_btn = QPushButton("👁")
        toggle_btn.setFixedSize(32, 32)
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.setCheckable(True)
        toggle_btn.setStyleSheet("""
            QPushButton {
                background: #1E222D; 
                color: #BBBBBB; 
                border: 1px solid #2C313E; 
                border-radius: 4px; 
                font-size: 14px;
            }
            QPushButton:checked {
                background: #3da5ff; 
                color: #171A22; 
                border: 1px solid #3da5ff;
            }
            QPushButton:hover {
                border: 1px solid #3da5ff;
            }
        """)
        
        def on_toggle(checked):
            if checked:
                line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                toggle_btn.setText("🔒")
            else:
                line_edit.setEchoMode(QLineEdit.EchoMode.Password)
                toggle_btn.setText("👁")
                
        toggle_btn.toggled.connect(on_toggle)
        
        layout.addWidget(line_edit)
        layout.addWidget(toggle_btn)
        return container, line_edit

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        logo_label = QLabel()
        pixmap = QPixmap(resource_path("wizard_banner.bmp"))
        scaled_pixmap = pixmap.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        layout.addWidget(QLabel("Registration Number / Username:"))
        self.user_input = QLineEdit(self.config.get("username", ""))
        layout.addWidget(self.user_input)

        layout.addWidget(QLabel("Password:"))
        pass_container, self.pass_input = self.create_password_field()
        self.pass_input.setText(ConfigManager.get_password(self.user_input.text()))
        pass_container.findChild(QPushButton).setStyleSheet("""
            QPushButton { background: rgba(16,21,38,0.86); color: #a7b0d6; border: 1px solid rgba(146,160,215,0.18); border-radius: 10px; font-size: 14px; }
            QPushButton:checked { background: #66c7ff; color: #06101c; border-color: #66c7ff; }
            QPushButton:hover { border-color: #66c7ff; }
        """)
        layout.addWidget(pass_container)

        # Forgot Password Button for Settings Window
        forgot_settings_btn = QPushButton("Forgot Password?")
        forgot_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_settings_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #3da5ff;
                border: none;
                font-size: 12px;
                text-align: left;
                padding-left: 2px;
                margin-top: 2px;
                margin-bottom: 6px;
            }
            QPushButton:hover {
                text-decoration: underline;
                color: #5bb3ff;
            }
        """)
        forgot_settings_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://hostelwifi.vit.ac.in/index.php?a=add&category=4")))
        layout.addWidget(forgot_settings_btn)

        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Check Frequency (seconds):"))
        self.interval_input = QSpinBox()
        self.interval_input.setRange(5, 300)
        self.interval_input.setValue(self.config.get("interval", 10))
        interval_layout.addWidget(self.interval_input)
        layout.addLayout(interval_layout)
        
        self.startup_cb = QCheckBox("Launch automatically on Windows startup")
        self.startup_cb.setChecked(is_auto_start_enabled())
        layout.addWidget(self.startup_cb)

        self.save_btn = QPushButton("Save and Apply")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        layout.addStretch()
        self.setLayout(layout)

    def save_settings(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Warning", "Username and Password cannot be empty.")
            return

        set_auto_start(self.startup_cb.isChecked())

        self.config["username"] = username
        self.config["interval"] = self.interval_input.value()

        ConfigManager.save_config(self.config)
        ConfigManager.set_password(username, password)

        QMessageBox.information(self, "Success", "Settings saved successfully!")
        self.accept()

# --- SYSTEM TRAY APP ---
class LoqinTrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Loqin")
        self.app.setQuitOnLastWindowClosed(False)

        # --- Install the Power Event Filter ---
        self.power_filter = PowerEventFilter(self)
        self.app.installNativeEventFilter(self.power_filter)

        # Load both icons using the resource_path function
        self.default_icon = QIcon(resource_path("loqin_logo_small.png"))
        self.perf_icon = QIcon(resource_path("loqin_logo_performance.png")) 
        
        # Set the default icon on startup
        self.icon = self.default_icon 
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.default_icon) 
        self.tray.setVisible(True)
        
        # --- FIX 2: Pass self.icon instead of MessageIcon.Information ---
        self.tray.showMessage(
            "Loqin", 
            "Loqin has started! Monitoring your connection in the background.", 
            self.icon, 
            3000
        )

        self.config = ConfigManager.load_config()
        
        # Bandwidth Tracking Metrics setup
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        
        self.graph_dialog = None
        self.build_menu()

        self.wifi_picker = None
        self.waiting_for_wifi_choice = True
        self.selected_wifi_ssid = ""
        self.wifi_connect_thread = None
        self.wifi_startup_thread = None

        self.worker = None
        self.status_action.setText("Status: Looking for your last Wi-Fi...")
        self.status_action.setIcon(create_status_icon("yellow"))
        self.tray.setToolTip("Loqin - Connecting to Wi-Fi")

        self.force_logout()
        # Give Windows a moment to initialize its WLAN service, then try the
        # last successfully connected Wi-Fi before showing the picker.
        QTimer.singleShot(1200, self.auto_connect_last_wifi)
        
        # Bandwidth & Speed Meter update timer (1 second interval)
        self.speed_timer = QTimer()
        self.speed_timer.timeout.connect(self.update_bandwidth_meters)
        self.speed_timer.start(1000)

        self.has_checked_for_updates = False

        # Call during app initialization or initial startup timer
        QTimer.singleShot(1000, self.check_and_auto_connect)

    def build_menu(self):
        self.menu = QMenu()

        # Connection Status action with colored dot icon
        self.status_action = QAction("Status: Initializing...", self.menu)
        self.status_action.setIcon(create_status_icon("yellow"))
        self.status_action.setEnabled(True)
        self.menu.addAction(self.status_action)

        self.menu.addSeparator()

        # Static Upload / Download Speed Meter action
        self.speed_action = QAction("Speed: ↓ 0 KB/s  ↑ 0 KB/s", self.menu)
        self.speed_action.setEnabled(False)
        self.menu.addAction(self.speed_action)

        # Toggleable Speed Graph action
        self.graph_action = QAction("Show Speed Graph", self.menu)
        self.graph_action.triggered.connect(self.toggle_speed_graph)
        self.menu.addAction(self.graph_action)

        self.menu.addSeparator()

        connect_action = QAction("Connect Now", self.menu)
        connect_action.triggered.connect(self.trigger_manual_check)
        self.menu.addAction(connect_action)

        wifi_action = QAction("Choose Wi-Fi", self.menu)
        wifi_action.triggered.connect(self.open_wifi_picker)
        self.menu.addAction(wifi_action)

        self.pause_action = QAction("Pause Loqin", self.menu)
        self.pause_action.triggered.connect(self.toggle_service_pause)
        self.menu.addAction(self.pause_action)

        self.perf_action = QAction("Performance Mode", self.menu)
        self.perf_action.setCheckable(True)
        self.perf_action.setChecked(False) # Set default state
        self.perf_action.triggered.connect(self.trigger_performance_mode)
        self.menu.addAction(self.perf_action)   

        self.menu.addSeparator()


        self.account_action = QAction("View Account Details", self.menu)
        self.account_action.setEnabled(False) # Disabled until we get the URL
        self.account_action.triggered.connect(self.show_account_details)
        self.menu.addAction(self.account_action)

        self.update_action = QAction("Check for Updates", self.menu)
        self.update_action.triggered.connect(self.check_for_updates)
        self.menu.addAction(self.update_action)

        settings_action = QAction("Configure Settings", self.menu)
        settings_action.triggered.connect(self.open_settings)
        self.menu.addAction(settings_action)

        self.menu.addSeparator()

        # ---------------- HELP SUBMENU ---------------- #
        help_menu = self.menu.addMenu("Help")

        website_action = QAction("Website", self.menu)
        website_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://loqin-vit.vercel.app/")))
        help_menu.addAction(website_action)

        how_to_action = QAction("How to use", self.menu)
        how_to_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/notaayushsrivastava/loqin#readme")))
        help_menu.addAction(how_to_action)

        releases_action = QAction("GitHub Releases", self.menu)
        releases_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/notaayushsrivastava/loqin/releases")))
        help_menu.addAction(releases_action)

        info_action = QAction("Bug Report", self.menu)
        info_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/notaayushsrivastava/loqin/issues")))
        help_menu.addAction(info_action)
        # ---------------------------------------------- #

        self.menu.addSeparator()

        quit_action = QAction("Exit Loqin", self.menu)
        quit_action.triggered.connect(self.close_app)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_tray_icon_activated)
        self.tray.setToolTip("Loqin PC")

    def on_tray_icon_activated(self, reason):
        """Handles clicks on the system tray icon."""
        # QSystemTrayIcon.Trigger represents a standard left-click
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Display the menu at the current mouse position
            menu = self.tray.contextMenu()
            if menu is not None:
                menu.exec(QCursor.pos())

    def toggle_service_pause(self):
        # Ensure the worker actually exists before trying to pause it
        if hasattr(self, 'worker') and self.worker:
            is_now_paused = self.worker.toggle_pause()
            
            if is_now_paused:
                self.pause_action.setText("Resume Loqin")
                self.tray.setToolTip("Loqin - Paused")
            else:
                self.pause_action.setText("Pause Loqin")
                self.tray.setToolTip("Loqin - Active")

    def close_app(self):
        # Wrap logout in a try-except with a timeout so it doesn't hang the app closing
        try:
            requests.get('http://phc.prontonetworks.com/cgi-bin/authlogout/', timeout=2)
        except Exception:
            pass
            
        # Nicely shut down threads before quitting 
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.is_running = False
            self.worker.quit()
            self.worker.wait()
            
        if hasattr(self, 'perf_thread') and self.perf_thread and self.perf_thread.isRunning():
            self.perf_thread.quit()
            self.perf_thread.wait()

        if hasattr(self, 'update_checker') and self.update_checker and self.update_checker.isRunning():
            self.update_checker.quit()
            self.update_checker.wait()

        self.app.quit()

    def update_bandwidth_meters(self):
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        
        elapsed = current_time - self.last_time
        if elapsed > 0:
            dl_speed = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / elapsed
            ul_speed = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / elapsed
            
            self.last_net_io = current_net_io
            self.last_time = current_time

            # Format text cleanly (KB/s or MB/s)
            dl_str = f"{dl_speed / 1024:.1f} KB/s" if dl_speed < 1048576 else f"{dl_speed / 1048576:.1f} MB/s"
            ul_str = f"{ul_speed / 1024:.1f} KB/s" if ul_speed < 1048576 else f"{ul_speed / 1048576:.1f} MB/s"
            
            # Update static speed meter in tray menu
            self.speed_action.setText(f"Speed: ↓ {dl_str}  ↑ {ul_str}")

            # Feed graph window if open
            if self.graph_dialog and self.graph_dialog.isVisible():
                self.graph_dialog.update_data(dl_speed, ul_speed)

    def toggle_speed_graph(self):
        if not self.graph_dialog:
            self.graph_dialog = SpeedGraphDialog()
            # Reset menu action text whenever the dialog is closed manually
            self.graph_dialog.finished.connect(lambda: self.graph_action.setText("Show Speed Graph"))
        
        if self.graph_dialog.isVisible():
            # If open but buried behind other windows, bring it to the front
            if not self.graph_dialog.isActiveWindow():
                self.graph_dialog.showNormal()
                self.graph_dialog.raise_()
                self.graph_dialog.activateWindow()
                self.graph_action.setText("Hide Speed Graph")
            else:
                # If already in focus, hide it
                self.graph_dialog.hide()
                self.graph_action.setText("Show Speed Graph")
        else:
            # If closed or hidden, open and focus it
            self.graph_dialog.showNormal()
            self.graph_dialog.raise_()
            self.graph_dialog.activateWindow()
            self.graph_action.setText("Hide Speed Graph")

    def open_settings(self):
        # Check if the settings dialog already exists and is open
        if hasattr(self, 'settings_dialog') and self.settings_dialog is not None:
            if self.settings_dialog.isVisible():
                self.settings_dialog.showNormal()     # Restores if minimized
                self.settings_dialog.raise_()         # Brings to the front of the screen
                self.settings_dialog.activateWindow() # Gives it keyboard focus
                return

        # If not open, create and execute it
        self.settings_dialog = SettingsDialog()
        if self.settings_dialog.exec():
            self.config = ConfigManager.load_config()
            self.start_monitoring_timer()
            
        # Clean up the reference after the window is closed
        self.settings_dialog = None

    def trigger_manual_check(self):
        # Prevent overwriting an actively running thread
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            return

        if self.waiting_for_wifi_choice:
            self.status_action.setText("Status: Choose Wi-Fi to continue")
            self.status_action.setIcon(create_status_icon("yellow"))
            self.tray.setToolTip("Loqin - Waiting for Wi-Fi selection")
            return
            
        # --- NEW: Detect New Wi-Fi (BSSID Change) ---
        current_bssid = None
        try:
            output = subprocess.check_output(
                ["netsh", "wlan", "show", "interfaces"], 
                creationflags=0x08000000
            ).decode("utf-8", errors="ignore")
            
            for line in output.split('\n'):
                if "BSSID" in line and "BSSID" == line.split(":")[0].strip():
                    parts = line.split(":")
                    if len(parts) >= 4:
                        current_bssid = ":".join(parts[1:]).strip().lower().replace("-", ":")
                        break
        except Exception:
            pass

        if not hasattr(self, 'last_bssid'):
            self.last_bssid = current_bssid

        # If a new Wi-Fi connection is detected and Performance Mode is ON
        if current_bssid and current_bssid != self.last_bssid:
            self.last_bssid = current_bssid
            if self.perf_action.isChecked():
                # Avoid infinite optimization loops if the thread itself changed the BSSID
                if getattr(self, 'just_optimized', False):
                    self.just_optimized = False
                else:
                    self.trigger_performance_mode(checked=True)
                    return  # Skip standard worker; Performance Mode handles it
        
        self.last_bssid = current_bssid
        self.just_optimized = False # Ensure the flag resets
        # --------------------------------------------
            
        self.config = ConfigManager.load_config()
        self.worker = NetworkWorker(self.config)
        self.worker.status_signal.connect(self.handle_status)
        self.worker.account_data_signal.connect(self.handle_account_url)
        self.worker.start()

    def handle_status(self, message, color_type):
        self.status_action.setText(f"Status: {message}")
        self.status_action.setIcon(create_status_icon(color_type))
        
        if message == "Missing credentials":
            if hasattr(self, 'worker') and self.worker:
                self.worker.is_paused = True
                self.pause_action.setText("Resume Loqin")
                self.tray.setToolTip("Loqin - Paused (Missing Credentials)")

            # Open settings dialog automatically on main thread
            QTimer.singleShot(100, self.open_settings)
            return

        # --- Trigger Update Check on Successful Connection ---
        if color_type == "green":
            current_ssid = get_current_wifi_ssid()
            if current_ssid:
                self.selected_wifi_ssid = current_ssid
                self.save_last_wifi(current_ssid)

            if "successfully" in message:
                self.tray.showMessage("Loqin", message, self.icon, 3000)
            
            # Check for updates only once per app session to avoid API rate limits
            if not getattr(self, 'has_checked_for_updates', False):
                self.has_checked_for_updates = True
                # FIX: Wait 3.5 seconds before checking updates to let the 
                # captive portal firewall fully open up HTTPS traffic.
                QTimer.singleShot(3500, lambda: self.check_for_updates(True))

        elif color_type == "error":
            self.tray.showMessage("Loqin", message, self.icon, 3000)

    def trigger_performance_mode(self, checked=False):
        if hasattr(self, 'perf_thread') and self.perf_thread.isRunning():
            return
            
        if hasattr(self, 'worker') and self.worker:
            self.worker.is_paused = True
            self.pause_action.setText("Resume Loqin")
            self.tray.setToolTip("Loqin - Paused (Optimizing Network)")
            
        # Icon swap
        if checked:
            self.tray.setIcon(self.perf_icon)
            self.icon = self.perf_icon  # Updates self.icon so pop-up notifications use it too
        else:
            self.tray.setIcon(self.default_icon)
            self.icon = self.default_icon
            
        self.perf_thread = PerformanceModeThread(use_best=checked)
        self.perf_thread.status_signal.connect(self.handle_perf_status)
        self.perf_thread.start()

    def handle_perf_status(self, message, color_type):
        self.status_action.setText(f"Status: {message}")
        self.status_action.setIcon(create_status_icon(color_type))
        self.tray.showMessage("Performance Mode", message, self.icon, 4000)
        
        if message != "Optimizing Network...":
            # --- NEW: Set flag so we don't infinitely loop BSSID changes ---
            self.just_optimized = True
            
            if hasattr(self, 'worker') and self.worker:
                self.worker.is_paused = False
                self.pause_action.setText("Pause Loqin")
                
                if "OFF" in message:
                    self.tray.setToolTip("Loqin - Active")
                else:
                    self.tray.setToolTip("Loqin - Active (Performance Mode)")
                
            if color_type in ["green", "yellow"]:
                QTimer.singleShot(1000, self.trigger_manual_check)

    def handle_account_url(self, url):
        self.current_account_url = url
        print(url)
        self.account_action.setEnabled(True)

    def show_account_details(self):
        if not hasattr(self, 'current_account_url'):
            return
            
        username = self.config.get("username")
        self.account_dialog = AccountDetailsDialog(username, self.current_account_url)
        self.account_dialog.show()
        QApplication.processEvents()
        
        try:
            response = requests.get(self.current_account_url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            rows_data = []
            
            # 1. Scrape all standard session rows (#DDDDDD and #F3F3F3 backgrounds)
            session_rows = soup.find_all('tr', attrs={'bgcolor': ['#DDDDDD', '#F3F3F3']})
            for tr in session_rows:
                cols = [td.text.strip() for td in tr.find_all('td')]
                if len(cols) == 7:
                    rows_data.append(cols)
            
            # 2. Scrape Grand Total summary row
            grand_total_data = []
            grand_total_label = soup.find(string=lambda text: text and "Grand Total" in text)
            if grand_total_label:
                tr = grand_total_label.find_parent('tr')
                # Extract Usage Time, Upload, Download, Total Data
                cols = [td.text.strip() for td in tr.find_all('td')]
                grand_total_data = cols[1:] # Skip label cell
                
            # 3. Feed the full table data to the Qt Dialog
            self.account_dialog.populate_table(rows_data, grand_total_data)
            
        except Exception as e:
            print(f"Failed to scrape account history table: {e}")


    def check_for_updates(self, silent=False):
        """
        Checks for updates on GitHub.
        :param silent: If True, suppresses the 'Up to Date' dialog when no new updates are found.
        """
        # Prevent multiple update threads from running simultaneously
        if hasattr(self, 'update_checker') and self.update_checker and self.update_checker.isRunning():
            return
            
        if not silent:
            self.update_action.setText("Checking for updates...")
            self.update_action.setEnabled(False)
        
        self.update_checker = UpdateChecker()
        self.update_checker.update_found.connect(self.prompt_update)
        
        # Only show the "Up to Date" popup if triggered manually (not on startup)
        if not silent:
            self.update_checker.no_update_found.connect(self.prompt_no_update) 
            self.update_checker.finished.connect(lambda: self.update_action.setText("Check for Updates"))
            self.update_checker.finished.connect(lambda: self.update_action.setEnabled(True))
            
        self.update_checker.start()

    def prompt_no_update(self):
        """Displays a GUI dialog when the app is already on the latest version."""
        QMessageBox.information(
            None,
            "Up to Date",
            f"You are already running the latest version of Loqin (v{APP_VERSION}).\nNo new updates were found :P"
        )

    def prompt_update(self, version, url, notes):
        if hasattr(self, 'progress_dialog') and self.progress_dialog.isVisible():
            return

        dialog = ReleaseNotesDialog(version, notes)
        dialog.setWindowIcon(self.icon)

        # Exec returns QDialog.DialogCode.Accepted if they click "Install Now"
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.start_download(url)

    def start_download(self, url):
        self.progress_dialog = QProgressDialog("Downloading update...", "Cancel", 0, 100)
        self.progress_dialog.setWindowTitle("Updating Loqin")
        self.progress_dialog.setWindowIcon(self.icon)
        self.progress_dialog.setFixedSize(350, 100)
        self.progress_dialog.show()
        
        self.downloader = UpdateDownloader(url)
        self.downloader.progress.connect(self.progress_dialog.setValue)
        self.downloader.finished.connect(self.install_update)
        
        # Cancel button logic
        self.progress_dialog.canceled.connect(self.downloader.terminate)
        
        self.downloader.start()

    def install_update(self, exe_path):
        self.progress_dialog.close()
        
        # We ensure the downloaded web installer is somewhat valid (> 1MB check removed since web installers are tiny)
        if not exe_path or not os.path.exists(exe_path):
            QMessageBox.warning(
                None, 
                "Update Failed", 
                "The update installer could not be found."
            )
            return
            
        try:
            # os.startfile natively triggers the UAC Admin prompt required by Inno Setup
            if sys.platform == "win32":
                os.startfile(exe_path)
            else:
                subprocess.Popen([exe_path])
                
            # Exit the current app so the installer can replace it
            self.app.quit()
        except Exception as e:
            QMessageBox.critical(None, "Update Error", f"Failed to launch the installer:\n{str(e)}")

    def start_monitoring_timer(self):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()

        self.timer = QTimer(self.app)
        self.timer.timeout.connect(self.trigger_manual_check)
        self.timer.start(self.config.get("interval", 10) * 1000)

        if not self.waiting_for_wifi_choice:
            self.trigger_manual_check()

    def save_last_wifi(self, ssid):
        """Persist the last successfully connected Wi-Fi SSID."""
        ssid = (ssid or "").strip()
        if not ssid:
            return
        self.config["last_wifi_ssid"] = ssid
        ConfigManager.save_config(self.config)

    def auto_connect_last_wifi(self):
        """Scan for the last Wi-Fi. Use it automatically when it is in range."""
        last_ssid = (self.config.get("last_wifi_ssid") or "").strip()

        if not last_ssid:
            self.open_wifi_picker()
            return

        if get_current_wifi_ssid().lower() == last_ssid.lower():
            self.on_wifi_connection_success(last_ssid, automatic=True)
            return

        self.status_action.setText(f"Status: Searching for {last_ssid}...")
        self.status_action.setIcon(create_status_icon("yellow"))
        self.tray.setToolTip(f"Loqin - Looking for {last_ssid}")

        if self.wifi_startup_thread and self.wifi_startup_thread.isRunning():
            return

        self.wifi_startup_thread = WiFiScanThread()
        self.wifi_startup_thread.networks_found.connect(
            lambda networks: self.on_startup_scan_finished(networks, last_ssid)
        )
        self.wifi_startup_thread.scan_failed.connect(self.on_startup_scan_failed)
        self.wifi_startup_thread.finished.connect(self._cleanup_startup_wifi_thread)
        self.wifi_startup_thread.start()

    def _cleanup_startup_wifi_thread(self):
        self.wifi_startup_thread = None

    def on_startup_scan_finished(self, networks, last_ssid):
        available = any(
            isinstance(network, dict) and
            network.get("ssid", "").strip().lower() == last_ssid.lower()
            for network in networks
        )

        if available:
            self.connect_to_wifi(last_ssid, automatic=True)
        else:
            self.status_action.setText("Status: Last Wi-Fi not in range")
            self.status_action.setIcon(create_status_icon("yellow"))
            self.open_wifi_picker()

    def on_startup_scan_failed(self, error):
        print(f"Startup Wi-Fi scan failed: {error}")
        self.open_wifi_picker()

    def connect_to_wifi(self, ssid, automatic=False):
        """Connect to a Windows-saved Wi-Fi profile without blocking the UI."""
        if self.wifi_connect_thread and self.wifi_connect_thread.isRunning():
            return

        self.selected_wifi_ssid = ssid
        self.status_action.setText(
            f"Status: {'Connecting to your last Wi-Fi' if automatic else f'Connecting to {ssid}'}..."
        )
        self.status_action.setIcon(create_status_icon("yellow"))
        self.tray.setToolTip(f"Loqin - Connecting to {ssid}")

        self.wifi_connect_thread = WiFiConnectThread(ssid)
        self.wifi_connect_thread.connected.connect(
            lambda connected_ssid: self.on_wifi_connection_success(connected_ssid, automatic)
        )
        self.wifi_connect_thread.failed.connect(
            lambda error: self.on_wifi_connection_failed(ssid, error)
        )
        self.wifi_connect_thread.finished.connect(self._cleanup_wifi_connect_thread)
        self.wifi_connect_thread.start()

    def _cleanup_wifi_connect_thread(self):
        self.wifi_connect_thread = None

    def on_wifi_connection_success(self, ssid, automatic=False):
        self.selected_wifi_ssid = ssid
        self.waiting_for_wifi_choice = False
        self.save_last_wifi(ssid)

        self.status_action.setText(f"Status: Wi-Fi connected ({ssid})")
        self.status_action.setIcon(create_status_icon("green"))
        self.tray.setToolTip(f"Loqin - Active")

        if self.wifi_picker and self.wifi_picker.isVisible():
            self.wifi_picker.close()

        self.start_monitoring_timer()

    def on_wifi_connection_failed(self, ssid, error):
        print(f"Could not connect to {ssid}: {error}")
        self.waiting_for_wifi_choice = True
        self.status_action.setText("Status: Choose Wi-Fi to continue")
        self.status_action.setIcon(create_status_icon("yellow"))
        self.tray.setToolTip("Loqin - Waiting for Wi-Fi selection")
        self.open_wifi_picker()

    def force_logout(self):
        """Silently drops the Pronto Networks Wi-Fi session."""
        try:
            # Standard Pronto Network global logout URL
            requests.get("http://phc.prontonetworks.com/cgi-bin/authlogout", timeout=3)
            print("Successfully dropped existing Wi-Fi session.")
        except Exception as e:
            print(f"Logout check bypassed (likely not connected): {e}")

    def open_wifi_picker(self):
        if self.wifi_picker is None:
            self.wifi_picker = WiFiPickerDialog()
            self.wifi_picker.wifi_chosen.connect(self.on_wifi_chosen)
            self.wifi_picker.finished.connect(self.wifi_picker.scan_thread.exit)
        else:
            # The previous picker closes after emitting a selection; make it reusable
            # when the user opens "Choose Wi-Fi" again from the tray.
            self.wifi_picker.is_connecting = False
            self.wifi_picker.scan_networks()
        self.wifi_picker.show()
        self.wifi_picker.raise_()
        self.wifi_picker.activateWindow()

    def check_and_auto_connect(self):
        """
        Scans for available Wi-Fi networks and checks if the last connected Wi-Fi is in range.
        """
        last_ssid = (self.config.get("last_wifi_ssid") or "").strip()
        current_ssid = get_current_wifi_ssid()

        # if already connected to the target last wifi, just force re-login
        if current_ssid and last_ssid and current_ssid.lower() == last_ssid.lower():
            print(f"Already connected to '{current_ssid}'. Performing login...")
            self.trigger_manual_check()
            return

        print("Scanning nearby Wi-Fi networks to locate last connected network...")
        self.tray.setToolTip("Loqin - Scanning for Wi-Fi...")
        
        # Run background scan thread
        self.startup_scan_thread = WiFiScanThread()
        self.startup_scan_thread.networks_found.connect(self._on_auto_connect_scan_finished)
        self.startup_scan_thread.scan_failed.connect(lambda err: self.open_wifi_picker())
        self.startup_scan_thread.start()

    def _on_auto_connect_scan_finished(self, networks):
        """Callback handling the results of the initial Wi-Fi range check."""
        last_ssid = (self.config.get("last_wifi_ssid") or "").strip()
        available_ssids = [net.get("ssid") for net in networks if net.get("ssid")]

        # Check if last_ssid exists and is currently in range
        if last_ssid and last_ssid in available_ssids:
            print(f"Last connected Wi-Fi '{last_ssid}' is in range. Auto-connecting...")
            self.connect_to_wifi(last_ssid, automatic=True)
        else:
            print(f"Last connected Wi-Fi '{last_ssid}' is NOT in range. Opening Wi-Fi Picker...")
            self.open_wifi_picker()

    def on_wifi_chosen(self, ssid):
        """Triggered when a Wi-Fi network is selected from the WiFiPickerDialog."""
        print(f"Wi-Fi selection changed via picker to: {ssid}")
        self.save_last_wifi(ssid)
        self.connect_to_wifi(ssid, automatic=False)

    def connect_and_relogin(self, ssid):
        """Connects to target SSID, waits for interface handshake, drops session, and logs in."""
        self.tray.setToolTip(f"Loqin - Connecting to {ssid}...")
        self.status_action.setText(f"Connecting to {ssid}...")
        
        # Connect to Wi-Fi network
        self.connect_to_wifi(ssid, automatic=False)

        # Schedule re-login after giving Windows 4 seconds to assign IP & route traffic
        QTimer.singleShot(4000, self.force_logout_and_relogin)

    def force_logout_and_relogin(self):
        """Clears existing portal session and initiates fresh captive portal authentication."""
        print("Resetting portal session and logging in...")
        self.tray.setToolTip("Loqin - Re-logging in...")
        self.status_action.setText("Logging in...")
        
        # Drop previous network session (Pronto Networks logout)
        self.force_logout()

        # Trigger captive portal login sequence through the existing worker flow.
        QTimer.singleShot(1000, self.trigger_manual_check)

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    mutex_handle = ensure_single_instance()
    if sys.platform == "win32":
        try:
            myappid = 'Loqin' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"Failed to set AppUserModelID: {e}")

    # Initialize your app as normal
    app = LoqinTrayApp()
    app.run()
