import sys
import json
import os
import time
import requests
import keyring
import psutil
import subprocess
import pyqtgraph as pg
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout, 
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, 
    QCheckBox, QMessageBox, QDialog, QVBoxLayout, QLabel, QProgressDialog
)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QColor, QPainter, QDesktopServices
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QUrl


APP_NAME = "Loqin"
APPDATA_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "Loqin")
CONFIG_FILE = os.path.join(APPDATA_DIR, "Loqin_config.json")
APP_VERSION = "1.1.0"
GITHUB_API_URL = "https://api.github.com/repos/notaayushsrivastava/loqin/releases/latest"

# --- WINDOWS STARTUP REGISTRY HELPER ---
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "Loqin"

def set_auto_start(enabled: bool):
    """Add or remove the app from Windows Registry run-on-startup."""
    if sys.platform != "win32":
        return

    import winreg
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

    import winreg
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
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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


# --- AUTO-UPDATER THREADS ---
class UpdateChecker(QThread):
    update_found = pyqtSignal(str, str, str) # version, download_url, release_notes

    def run(self):
        try:
            res = requests.get(GITHUB_API_URL, timeout=5)
            if res.status_code == 200:
                data = res.json()
                latest_version_tag = data.get("tag_name", "").replace("v", "")
                
                # Simple version comparison (e.g., "1.0.1" > "1.0.0")
                current_v = tuple(map(int, APP_VERSION.split('.')))
                latest_v = tuple(map(int, latest_version_tag.split('.')))
                
                if latest_v > current_v:
                    download_url = None
                    # Find the .exe installer in the release assets
                    for asset in data.get("assets", []):
                        if asset["name"].endswith(".exe"):
                            download_url = asset["browser_download_url"]
                            break
                    
                    if download_url:
                        self.update_found.emit(latest_version_tag, download_url, data.get("body", "Bug fixes and improvements."))
        except Exception as e:
            print(f"Update check failed: {e}")

class UpdateDownloader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str) # Path to the downloaded .exe

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            res = requests.get(self.url, stream=True, timeout=10)
            total_size = int(res.headers.get('content-length', 0))
            
            # Save to Windows Temp folder
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
        except Exception:
            self.finished.emit("")


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
            "auto_connect": True
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
            requests.post(auth_url, data=payload, headers=headers, timeout=5)
            if self.check_network_state() == "ONLINE":
                self.status_signal.emit("Logged in successfully!", "green")
            else:
                self.status_signal.emit("Login failed. Check credentials.", "error")
        except Exception:
            self.status_signal.emit("Portal timeout or error.", "error")


class SpeedGraphDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Loqin • Live Network Monitor")
        self.setWindowIcon(QIcon(resource_path("loqin_logo_small.png")))
        self.resize(720, 420)

        self.download_history = [0] * 60
        self.upload_history = [0] * 60

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # ---------------- Header Bar ---------------- #
        header_layout = QHBoxLayout()

        title = QLabel("Real-Time Network Usage")
        title.setStyleSheet("""
            QLabel{
                color:white;
                font-size:18px;
                font-weight:600;
            }
        """)

        # Always on top checkbox
        self.pin_checkbox = QCheckBox("Always on Top")
        self.pin_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_checkbox.setStyleSheet("""
            QCheckBox {
                color: #BBBBBB;
                font-size: 13px;
                font-weight: 500;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #777777;
                border-radius: 3px;
                background: #171A22;
            }
            QCheckBox::indicator:checked {
                background: #3da5ff;
                border: 1px solid #3da5ff;
            }
            QCheckBox:hover {
                color: #FFFFFF;
            }
        """)
        self.pin_checkbox.toggled.connect(self.toggle_always_on_top)

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

        self.stats.setStyleSheet("""
            QLabel{
                color:#cccccc;
                font-size:13px;
            }
        """)

        layout.addWidget(self.stats)

        self.setStyleSheet("""
            QDialog{
                background:#171A22;
            }
        """)

        # ---------------- Graph ---------------- #

        self.graph.setBackground("#171A22")

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

        self.graph.setLabel("left", "Speed (KB/s)", color="#BBBBBB")

        self.graph.setLabel("bottom", "Time", color="#BBBBBB")

        self.graph.getAxis("left").setPen(pg.mkPen("#777"))

        self.graph.getAxis("bottom").setPen(pg.mkPen("#777"))

        self.graph.getAxis("left").setTextPen("#BBBBBB")

        self.graph.getAxis("bottom").setTextPen("#BBBBBB")

        self.graph.setYRange(0, 100)

        # Download curve
        self.download_curve = self.graph.plot(
            pen=pg.mkPen("#3da5ff", width=3),
            name="Download"
        )

        # Upload curve
        self.upload_curve = self.graph.plot(
            pen=pg.mkPen("#2ecc71", width=3),
            name="Upload"
        )

        legend = self.graph.addLegend()

        legend.setBrush(pg.mkBrush(30, 30, 30, 200))

        legend.setOffset((15, 15))

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
        self.setFixedSize(380, 270)
        self.setWindowIcon(QIcon(resource_path("loqin_logo_small.png")))
        
        self.config = ConfigManager.load_config()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        logo_label = QLabel()
        pixmap = QPixmap(resource_path("loqin_logo_small.png"))
        scaled_pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        layout.addWidget(QLabel("Registration Number / Username:"))
        self.user_input = QLineEdit(self.config.get("username", ""))
        layout.addWidget(self.user_input)

        layout.addWidget(QLabel("Password:"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setText(ConfigManager.get_password(self.user_input.text()))
        layout.addWidget(self.pass_input)

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

        self.save_btn = QPushButton("Save & Apply")
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

        icon_path = resource_path("loqin_logo_small.png")
        self.icon = QIcon(icon_path)
        
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.icon)
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

        self.worker = None
        self.start_monitoring_timer()
        
        # Bandwidth & Speed Meter update timer (1 second interval)
        self.speed_timer = QTimer()
        self.speed_timer.timeout.connect(self.update_bandwidth_meters)
        self.speed_timer.start(1000)

        self.check_for_updates()

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

        self.pause_action = QAction("Pause Loqin", self.menu)
        self.pause_action.triggered.connect(self.toggle_service_pause)
        self.menu.addAction(self.pause_action)

        self.menu.addSeparator()

        self.menu.addSeparator()

        self.update_action = QAction("Check for Updates", self.menu)
        self.update_action.triggered.connect(self.check_for_updates)
        self.menu.addAction(self.update_action)

        settings_action = QAction("Configure Settings", self.menu)
        settings_action.triggered.connect(self.open_settings)
        self.menu.addAction(settings_action)

        self.menu.addSeparator()

        # ---------------- HELP SUBMENU ---------------- #
        help_menu = self.menu.addMenu("Help")

        how_to_action = QAction("How to use", self.menu)
        how_to_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/notaayushsrivastava/loqin#readme")))
        help_menu.addAction(how_to_action)

        releases_action = QAction("GitHub Releases", self.menu)
        releases_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/notaayushsrivastava/loqin/releases")))
        help_menu.addAction(releases_action)

        info_action = QAction("Project Info", self.menu)
        info_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/notaayushsrivastava/loqin")))
        help_menu.addAction(info_action)
        # ---------------------------------------------- #

        self.menu.addSeparator()

        quit_action = QAction("Exit Loqin", self.menu)
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip("Loqin PC")

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
        
        if self.graph_dialog.isVisible():
            self.graph_dialog.hide()
            self.graph_action.setText("Show Speed Graph")
        else:
            self.graph_dialog.show()
            self.graph_action.setText("Hide Speed Graph")

    def open_settings(self):
        dialog = SettingsDialog()
        if dialog.exec():
            self.config = ConfigManager.load_config()
            self.start_monitoring_timer()

    def trigger_manual_check(self):
        self.config = ConfigManager.load_config()
        self.worker = NetworkWorker(self.config)
        self.worker.status_signal.connect(self.handle_status)
        self.worker.start()

    def handle_status(self, message, color_type):
        self.status_action.setText(f"Status: {message}")
        self.status_action.setIcon(create_status_icon(color_type))
        
        # --- FIX 1: Intercept missing credentials, pause thread, open settings ---
        if message == "Missing credentials":
            if hasattr(self, 'worker') and self.worker:
                self.worker.is_paused = True
                self.pause_action.setText("Resume Loqin")
                self.tray.setToolTip("Loqin - Paused (Missing Credentials)")

            # Open settings dialog automatically on main thread
            QTimer.singleShot(100, self.open_settings)
            return

        # --- FIX 2: Pass self.icon for custom app logo in notifications ---
        if color_type == "green" and "successfully" in message:
            self.tray.showMessage("Loqin", message, self.icon, 3000)
        elif color_type == "error":
            self.tray.showMessage("Loqin", message, self.icon, 3000)

    
    def check_for_updates(self):
        self.update_action.setText("Checking for updates...")
        self.update_action.setEnabled(False)
        
        self.update_checker = UpdateChecker()
        self.update_checker.update_found.connect(self.prompt_update)
        # If the thread finishes and no update was found, reset the button text
        self.update_checker.finished.connect(lambda: self.update_action.setText("Check for Updates"))
        self.update_checker.finished.connect(lambda: self.update_action.setEnabled(True))
        self.update_checker.start()

    def prompt_update(self, version, url, notes):
        # Don't prompt if a dialog is already open
        if hasattr(self, 'progress_dialog') and self.progress_dialog.isVisible():
            return

        reply = QMessageBox.question(
            None, 
            "Update Available",
            f"A new version ({version}) of Loqin is available!\n\nRelease Notes:\n{notes}\n\nWould you like to download and install it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
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
        
        if not exe_path or not os.path.exists(exe_path):
            QMessageBox.warning(None, "Update Failed", "Failed to download the update package. Please check your internet connection.")
            return
            
        # Launch the newly downloaded installer
        subprocess.Popen([exe_path])
        
        # Exit the current app so the installer can overwrite the files
        self.app.quit()

    def start_monitoring_timer(self):
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()

        self.timer = QTimer()
        self.timer.timeout.connect(self.trigger_manual_check)
        self.timer.start(self.config.get("interval", 10) * 1000)
        self.trigger_manual_check()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            myappid = 'Loqin' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"Failed to set AppUserModelID: {e}")

    # Initialize your app as normal
    app = LoqinTrayApp()
    app.run()