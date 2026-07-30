import sys
import json
import os
import re
import requests
import keyring
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout, 
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, 
    QCheckBox, QMessageBox
)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QColor, QPainter
from PyQt6.QtCore import QThread, pyqtSignal, Qt

APP_NAME = "Loqin"
CONFIG_FILE = "Loqin_config.json"

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
            # Check if running as PyInstaller .exe or a raw .py script
            if getattr(sys, 'frozen', False):
                exe_path = f'"{sys.executable}"'
            else:
                exe_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
                
            winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_REG_NAME)
            except OSError:
                pass # Already deleted
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
        # Key doesn't exist
        return False
    except Exception as e:
        print(f"Failed to read registry: {e}")
        return False
def resource_path(relative_path):
    """ Get the absolute path to a resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- PATH SETUP FOR WINDOWS APPDATA ---
APPDATA_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "Loqin")
CONFIG_FILE = os.path.join(APPDATA_DIR, "Loqin_config.json")


# --- HELPER: Secure Credentials & Config Management ---
class ConfigManager:
    @staticmethod
    def ensure_dir_exists():
        """Ensure %APPDATA%\Loqin directory exists before file operations"""
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

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    default_config.update(json.load(f))
            except Exception:
                pass
        else:
            # Auto-create the initial JSON file on first run
            ConfigManager.save_config(default_config)

        return default_config

    @staticmethod
    def save_config(config):
        ConfigManager.ensure_dir_exists()
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
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

    def run(self):
        username = self.config.get("username")
        password = ConfigManager.get_password(username)

        # DELETED: portal_ip = self.config.get("portal_ip")

        if not username or not password:
            self.status_signal.emit("Missing credentials", "warning")
            return

        if self.is_connected():
            self.status_signal.emit("Connected", "info")
            return

        self.status_signal.emit("Attempting login...", "info")
        
        # Call login without portal_ip
        self.login(username, password)

    def is_connected(self):
        try:
            res = requests.get("http://clients3.google.com/generate_204", timeout=3)
            return res.status_code == 204
        except Exception:
            return False

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
            res = requests.post(auth_url, data=payload, headers=headers, timeout=5)
            
            if self.is_connected():
                self.status_signal.emit("Logged in successfully!", "success")
            else:
                self.status_signal.emit("Login failed. Check credentials.", "error")
                
        except Exception as e:
            self.status_signal.emit(f"Network error: {str(e)}", "error")

# --- UI: Configuration Settings Window ---
# --- UI: Configuration Settings Window ---
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loqin for PC - Settings")
        self.setFixedSize(380, 270)
        
        # Set the window icon (matches tray logo filename)
        self.setWindowIcon(QIcon(resource_path("loqin_logo_small.png")))
        
        self.config = ConfigManager.load_config()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # --- FIX: Tight spacing and force elements to the top ---
        layout.setSpacing(4)                     # Very tight gap between items
        layout.setContentsMargins(15, 15, 15, 15) # Outer padding of the window
        layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Prevents elements from stretching apart
        # --------------------------------------------------------

        # Logo
        logo_label = QLabel()
        pixmap = QPixmap(resource_path("loqin_logo_small.png"))
        scaled_pixmap = pixmap.scaled(
            32, 32, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        logo_label.setPixmap(scaled_pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # Registration No / Username
        layout.addWidget(QLabel("Registration Number / Username:"))
        self.user_input = QLineEdit(self.config.get("username", ""))
        layout.addWidget(self.user_input)

        # Password
        layout.addWidget(QLabel("Password:"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setText(ConfigManager.get_password(self.user_input.text()))
        layout.addWidget(self.pass_input)

        # Ping Interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Check Frequency (seconds):"))
        self.interval_input = QSpinBox()
        self.interval_input.setRange(5, 300)
        self.interval_input.setValue(self.config.get("interval", 10))
        interval_layout.addWidget(self.interval_input)
        layout.addLayout(interval_layout)
        
        # Launch on Startup Checkbox
        self.startup_cb = QCheckBox("Launch automatically on Windows startup")
        self.startup_cb.setChecked(is_auto_start_enabled())
        layout.addWidget(self.startup_cb)

        # Save Button
        self.save_btn = QPushButton("Save & Apply")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        # --- FIX: Push all empty window space to the bottom ---
        layout.addStretch()
        # -----------------------------------------------------

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
        self.app.setQuitOnLastWindowClosed(False)

        icon_path = resource_path("loqin_logo_small.png")
        self.icon = QIcon(icon_path)
        
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)
        
        # --- FIX: Use native MessageIcon instead of self.icon ---
        self.tray.showMessage(
            "Loqin PC", 
            "Loqin has started! Monitoring your connection in the background. Access from system tray.", 
            QSystemTrayIcon.MessageIcon.Information, 
            3000
        )

        self.config = ConfigManager.load_config()
        self.build_menu()

        self.worker = None
        self.start_monitoring_timer()

    def build_menu(self):
        menu = QMenu()

        self.status_action = QAction("Status: Monitoring...", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        connect_action = QAction("Connect Now", menu)
        connect_action.triggered.connect(self.trigger_manual_check)
        menu.addAction(connect_action)

        settings_action = QAction("Configure Settings", menu)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        quit_action = QAction("Exit Loqin", menu)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Loqin PC")

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

    def handle_status(self, message, msg_type):
        self.status_action.setText(f"Status: {message}")
        if msg_type == "success":
            # --- FIX: Use Information icon ---
            self.tray.showMessage("Loqin PC", message, QSystemTrayIcon.MessageIcon.Information, 3000)
        elif msg_type == "error":
            # --- FIX: Use Warning icon ---
            self.tray.showMessage("Loqin PC", message, QSystemTrayIcon.MessageIcon.Warning, 3000)


    def start_monitoring_timer(self):
        from PyQt6.QtCore import QTimer
        if hasattr(self, 'timer') and self.timer:
            self.timer.stop()

        self.timer = QTimer()
        self.timer.timeout.connect(self.trigger_manual_check)
        self.timer.start(self.config.get("interval", 10) * 1000)
        self.trigger_manual_check()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = LoqinTrayApp()
    app.run()