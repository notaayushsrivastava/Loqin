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
from pywifi import const
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QDialog, QVBoxLayout, 
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, 
    QCheckBox, QMessageBox, QDialog, QVBoxLayout, QLabel, QProgressDialog,
    QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QTableWidget,
    QHeaderView, QTableWidgetItem, QAbstractItemView, QTabWidget,
    QWidget, QFormLayout
)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QColor, QPainter, QDesktopServices, QCursor
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QUrl, QAbstractNativeEventFilter

APP_NAME = "Loqin"
APPDATA_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "Loqin")
CONFIG_FILE = os.path.join(APPDATA_DIR, "Loqin_config.json")
APP_VERSION = "1.4.5"
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

    def nativeEventFilter(self, eventType, message):
        """Intercept native Windows messages to detect sleep/wake"""
        
        # message is a memory address pointing to the Windows MSG structure.
        # We use ctypes.wintypes to extract the data.
        msg = ctypes.wintypes.MSG.from_address(int(message))
        
        if msg.message == WM_POWERBROADCAST:
            if msg.wParam == PBT_APMSUSPEND:
                # Safely set the worker to paused using the existing attribute
                if hasattr(self.tray_app, 'worker') and self.tray_app.worker:
                    self.tray_app.worker.is_paused = True

                # Drop the Wi-Fi session so the user can use their phone
                self.tray_app.force_logout()
                    
            elif msg.wParam == PBT_APMRESUMEAUTOMATIC:
                # Safely resume the worker
                if hasattr(self.tray_app, 'worker') and self.tray_app.worker:
                    self.tray_app.worker.is_paused = False
                    
        # Return False, 0 to allow PyQt to continue processing the event normally
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


# --- AUTO-UPDATER THREADS ---
class UpdateChecker(QThread):
    update_found = pyqtSignal(str, str, str)
    no_update_found = pyqtSignal() # New signal for up-to-date status

    def run(self):
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
                    # Emit signal if no newer version is found
                    self.no_update_found.emit()
        except Exception as e:
            print(f"Update check failed: {e}")

class AccountDetailsDialog(QDialog):
    # Notice we now pass username and account_url into the dialog
    def __init__(self, username, account_url, parent=None):
        super().__init__(parent)
        self.username = username
        self.account_url = account_url
        
        self.setWindowTitle("Loqin • Account Management")
        self.setWindowIcon(QIcon(resource_path("loqin_logo_small.png"))) 
        self.resize(750, 450) 
        
        self.setStyleSheet("""
            QDialog { 
                background-color: #171A22; 
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
            }
            /* Table Styling */
            QTableWidget {
                background-color: #1E222D;
                color: #DDDDDD;
                gridline-color: #2C313E;
                border: 1px solid #2C313E;
                border-radius: 8px;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #171A22;
                color: #3da5ff;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #2C313E;
            }
            QTableWidget::item { padding: 4px; }
            
            /* Tab Styling */
            QTabWidget::pane { border: 1px solid #2C313E; border-radius: 4px; }
            QTabBar::tab {
                background: #1E222D; color: #BBBBBB; padding: 10px 20px; 
                border: 1px solid #2C313E; border-bottom: none; 
                border-top-left-radius: 4px; border-top-right-radius: 4px;
            }
            QTabBar::tab:selected { background: #171A22; color: #3da5ff; font-weight: bold; }
            
            /* Form Styling */
            QLineEdit {
                background: #1E222D; color: #FFF; border: 1px solid #2C313E; 
                border-radius: 4px; padding: 6px; font-size: 14px;
            }
            QPushButton {
                background: #3da5ff; color: #171A22; font-weight: bold; 
                border-radius: 4px; padding: 8px; font-size: 14px;
            }
            QPushButton:hover { background: #2b8ee0; }
        """)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # Build Tabs
        self.setup_history_tab()
        self.setup_password_tab()

    def setup_history_tab(self):
        self.history_tab = QWidget()
        layout = QVBoxLayout(self.history_tab)
        
        title = QLabel("<b>Recent Network Sessions</b>")
        title.setStyleSheet("font-size: 16px; margin-bottom: 5px;")
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
        
        title = QLabel("<b>Reset Network Password</b>")
        title.setStyleSheet("font-size: 16px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout.setSpacing(15)

        container_old, self.old_pw_input = self.create_password_field()
        container_new, self.new_pw_input = self.create_password_field()
        container_confirm, self.confirm_pw_input = self.create_password_field()

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
                color: #3da5ff;
                border: none;
                font-size: 13px;
                text-align: left;
                padding-left: 0px;
            }
            QPushButton:hover {
                text-decoration: underline;
                color: #5bb3ff;
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
            total_label_item.setForeground(QColor("#2ecc71")) 
            total_label_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(total_row, 0, total_label_item)
            
            for col_offset, text in enumerate(grand_total_data):
                item = QTableWidgetItem(text)
                item.setForeground(QColor("#2ecc71"))
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

        # 1. Header Text Widget
        header_label = QLabel(f"<h3>A new version ({version}) of Loqin is available!</h3>")
        layout.addWidget(header_label)

        # 2. Release Notes Display
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        
        # Format release notes markdown
        markdown_content = f"**Release Notes:**\n\n{notes}"
        self.text_browser.setMarkdown(markdown_content)
        layout.addWidget(self.text_browser)

        # 3. Action Buttons
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
            self.graph.setBackground("#171A22")
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
        self.setFixedSize(410, 270)
        self.setWindowIcon(QIcon(resource_path("loqin_logo_small.png")))
        
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
        pass_container, self.pass_input = self.create_password_field()
        self.pass_input.setText(ConfigManager.get_password(self.user_input.text()))
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

        # --- NEW: Install the Power Event Filter ---
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

        self.worker = None
        self.start_monitoring_timer()

        self.force_logout()
        
        # Bandwidth & Speed Meter update timer (1 second interval)
        self.speed_timer = QTimer()
        self.speed_timer.timeout.connect(self.update_bandwidth_meters)
        self.speed_timer.start(1000)

        self.has_checked_for_updates = False

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
            
        self.config = ConfigManager.load_config()
        self.worker = NetworkWorker(self.config)
        self.worker.status_signal.connect(self.handle_status)
        self.worker.account_data_signal.connect(self.handle_account_url)
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

        # --- Trigger Update Check on Successful Connection ---
        if color_type == "green":
            if "successfully" in message:
                self.tray.showMessage("Loqin", message, self.icon, 3000)
            
            # Check for updates only once per app session to avoid API rate limits
            if not getattr(self, 'has_checked_for_updates', False):
                self.check_for_updates(True)
                self.has_checked_for_updates = True

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
        
        # We only want to unpause the app and update UI when the final message is emitted,
        # skipping the initial "Optimizing Network..." status.
        if message != "Optimizing Network...":
            if hasattr(self, 'worker') and self.worker:
                self.worker.is_paused = False
                self.pause_action.setText("Pause Loqin")
                
                # Update tooltip to reflect the new state accurately
                if "OFF" in message:
                    self.tray.setToolTip("Loqin - Active")
                else:
                    self.tray.setToolTip("Loqin - Active (Performance Mode)")
                
            # Trigger an immediate login check for both success (green) and warning (yellow) states
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

        self.timer = QTimer()
        self.timer.timeout.connect(self.trigger_manual_check)
        self.timer.start(self.config.get("interval", 10) * 1000)
        self.trigger_manual_check()

    def force_logout(self):
        """Silently drops the Pronto Networks Wi-Fi session."""
        try:
            # Standard Pronto Network global logout URL
            requests.get("http://phc.prontonetworks.com/cgi-bin/authlogout", timeout=3)
            print("Successfully dropped existing Wi-Fi session on startup.")
        except Exception as e:
            print(f"Logout check bypassed (likely not connected): {e}")

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