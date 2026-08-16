_A0='Loqin - Waiting for Wi-Fi selection'
_z='Status: Choose Wi-Fi to continue'
_y='update_checker'
_x='perf_thread'
_w='Loqin - Active'
_v='Check for Updates'
_u='Performance Mode'
_t='#FF69B4'
_s='#3da5ff'
_r='#171A22'
_q='Loqin • Live Network Monitor'
_p='Missing credentials'
_o='OFFLINE'
_n='Referer'
_m='Grand Total'
_l='https://hostelwifi.vit.ac.in/index.php?a=add&category=4'
_k='Forgot Password?'
_j='\n            QPushButton {\n                background: #1E222D; \n                color: #BBBBBB; \n                border: 1px solid #2C313E; \n                border-radius: 4px; \n                font-size: 14px;\n            }\n            QPushButton:checked {\n                background: #3da5ff; \n                color: #171A22; \n                border: 1px solid #3da5ff;\n            }\n            QPushButton:hover {\n                border: 1px solid #3da5ff;\n            }\n        '
_i='Download'
_h='Upload'
_g='color: #66c7ff; font-weight: 600;'
_f='Scanning nearby networks…'
_e='secured'
_d='Optimizing Network...'
_c='Resume Loqin'
_b='Pause Loqin'
_a='Show Speed Graph'
_Z='ONLINE'
_Y='last_wifi_ssid'
_X='ssid'
_W='ignore'
_V='utf-8'
_U='interfaces'
_T='show'
_S='interval'
_R='#2ecc71'
_Q='signal'
_P='wlan'
_O='netsh'
_N='loqin_logo_small.png'
_M='BSSID'
_L='win32'
_K='error'
_J='password'
_I='username'
_H='worker'
_G='green'
_F='Loqin'
_E=':'
_D='yellow'
_C=None
_B=False
_A=True
import sys,json,os,time,requests,keyring,psutil,subprocess,pyqtgraph as pg,re,ctypes,ctypes.wintypes,pywifi
from pywifi import const
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
from PyQt6.QtWidgets import QApplication,QSystemTrayIcon,QMenu,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QSpinBox,QCheckBox,QMessageBox,QDialog,QVBoxLayout,QLabel,QProgressDialog,QDialog,QVBoxLayout,QTextBrowser,QDialogButtonBox,QTableWidget,QHeaderView,QTableWidgetItem,QAbstractItemView,QTabWidget,QWidget,QFormLayout,QScrollArea,QInputDialog,QGridLayout,QFrame,QGraphicsOpacityEffect
from PyQt6.QtGui import QIcon,QAction,QPixmap,QColor,QPainter,QDesktopServices,QCursor
from PyQt6.QtCore import QThread,pyqtSignal,Qt,QTimer,QUrl,QAbstractNativeEventFilter,QPropertyAnimation,QEasingCurve,QSize
APP_NAME=_F
APPDATA_DIR=os.path.join(os.getenv('APPDATA',os.path.expanduser('~')),_F)
CONFIG_FILE=os.path.join(APPDATA_DIR,'Loqin_config.json')
APP_VERSION='1.6.0'
GITHUB_API_URL='https://api.github.com/repos/notaayushsrivastava/loqin/releases/latest'
REG_PATH='Software\\Microsoft\\Windows\\CurrentVersion\\Run'
APP_REG_NAME=_F
MUTEX_NAME='Global\\Loqin_SingleInstance_Mutex_AayushSrivastava'
WM_POWERBROADCAST=536
PBT_APMSUSPEND=4
PBT_APMRESUMEAUTOMATIC=18
def ensure_single_instance():
	A=ctypes.windll.kernel32;B=A.CreateMutexW(_C,_B,MUTEX_NAME)
	if A.GetLastError()==183:C=QApplication(sys.argv);QMessageBox.warning(_C,'Loqin Already Running','Another instance of Loqin is already running in the system tray.');sys.exit(0)
	return B
def set_auto_start(enabled):
	'Add or remove the app from Windows Registry run-on-startup.'
	if sys.platform!=_L:return
	import winreg as A
	try:
		B=A.OpenKey(A.HKEY_CURRENT_USER,REG_PATH,0,A.KEY_ALL_ACCESS)
		if enabled:
			if getattr(sys,'frozen',_B):C=f'"{sys.executable}"'
			else:C=f'"{sys.executable}" "{os.path.abspath(__file__)}"'
			A.SetValueEx(B,APP_REG_NAME,0,A.REG_SZ,C)
		else:
			try:A.DeleteValue(B,APP_REG_NAME)
			except OSError:pass
		A.CloseKey(B)
	except Exception as D:print(f"Failed to update registry: {D}")
def is_auto_start_enabled():
	'Check if the registry key currently exists.'
	if sys.platform!=_L:return _B
	import winreg as A
	try:B=A.OpenKey(A.HKEY_CURRENT_USER,REG_PATH,0,A.KEY_READ);A.QueryValueEx(B,APP_REG_NAME);A.CloseKey(B);return _A
	except OSError:return _B
	except Exception as C:print(f"Failed to read registry: {C}");return _B
def resource_path(relative_path):
	'Get absolute path to resource, works for dev and PyInstaller'
	try:A=sys._MEIPASS
	except Exception:A=os.path.abspath('.')
	return os.path.join(A,'assets',relative_path)
def create_status_icon(color_type):
	'Generates a smooth colored circle icon (Green, Yellow, Red) for status indicators.';C=color_type;B=QPixmap(16,16);B.fill(Qt.GlobalColor.transparent);A=QPainter(B);A.setRenderHint(QPainter.RenderHint.Antialiasing)
	if C==_G:A.setBrush(QColor(46,204,113))
	elif C==_D:A.setBrush(QColor(241,196,15))
	else:A.setBrush(QColor(231,76,60))
	A.setPen(Qt.PenStyle.NoPen);A.drawEllipse(2,2,12,12);A.end();return QIcon(B)
class PowerEventFilter(QAbstractNativeEventFilter):
	def __init__(A,tray_app):super().__init__();A.tray_app=tray_app;A.last_event_time=0;A.last_wparam=_C
	def nativeEventFilter(A,eventType,message):
		'Intercept native Windows messages to detect sleep/wake';B=ctypes.wintypes.MSG.from_address(int(message))
		if B.message==WM_POWERBROADCAST:
			C=time.time()
			if B.wParam==A.last_wparam and C-A.last_event_time<2.:return _B,0
			A.last_event_time=C;A.last_wparam=B.wParam
			if B.wParam==PBT_APMSUSPEND:
				if hasattr(A.tray_app,_H)and A.tray_app.worker:A.tray_app.worker.is_paused=_A
				A.tray_app.force_logout()
			elif B.wParam==PBT_APMRESUMEAUTOMATIC:
				if hasattr(A.tray_app,_H)and A.tray_app.worker:A.tray_app.worker.is_paused=_B
				A.tray_app.has_checked_for_updates=_B
				if hasattr(A.tray_app,'perf_action')and A.tray_app.perf_action.isChecked():A.tray_app.trigger_performance_mode(checked=_A)
		return _B,0
class PerformanceModeThread(QThread):
	status_signal=pyqtSignal(str,str)
	def __init__(A,use_best=_A):super().__init__();A.use_best=use_best
	def run(A):
		J='Performance Mode ON';K=_d if A.use_best else'Reverting Network...';A.status_signal.emit(K,_D)
		try:
			L=pywifi.PyWiFi();B=L.interfaces()[0];B.scan();A.sleep(4);M=B.scan_results();E=[A for A in M if'VIT'in(A.ssid or'').upper()]
			if not E:A.status_signal.emit('No VIT networks found in range.',_K);return
			E.sort(key=lambda x:x.signal,reverse=A.use_best);D=E[0]
			if not A.use_best:B.disconnect();A.sleep(1);C=pywifi.Profile();C.ssid=D.ssid;C.bssid=D.bssid;C.auth=const.AUTH_ALG_OPEN;C.akm.append(const.AKM_TYPE_NONE);B.remove_all_network_profiles();N=B.add_network_profile(C);B.connect(N);A.sleep(3);A.status_signal.emit('Performance Mode OFF',_G);return
			F=_C
			try:
				O=subprocess.check_output([_O,_P,_T,_U],creationflags=134217728).decode(_V,errors=_W)
				for G in O.split('\n'):
					if _M in G and _M==G.split(_E)[0].strip():
						I=G.split(_E)
						if len(I)>=4:F=_E.join(I[1:]).strip().lower().replace('-',_E);break
			except Exception as H:print(f"Could not get current BSSID: {H}")
			P=D.bssid.strip().lower().replace('-',_E)if D.bssid else''
			if F and F==P:A.status_signal.emit(J,_G)
			else:A.status_signal.emit(J,_D)
		except Exception as H:A.status_signal.emit(f"Wi-Fi Error: {str(H)}",_K)
def get_current_wifi_ssid():
	'Return the currently connected Wi-Fi SSID using Windows WLAN APIs.'
	if sys.platform!=_L:return''
	try:
		C=subprocess.check_output([_O,_P,_T,_U],creationflags=134217728,timeout=5).decode(_V,errors=_W)
		for D in C.splitlines():
			A=D.strip()
			if A.startswith('SSID')and not A.startswith(_M):
				B=A.split(_E,1)
				if len(B)==2:return B[1].strip()
	except Exception:pass
	return''
class WiFiConnectThread(QThread):
	'Connect to a previously saved Windows Wi-Fi profile without blocking the UI.';connected=pyqtSignal(str);failed=pyqtSignal(str)
	def __init__(A,ssid,parent=_C):super().__init__(parent);A.ssid=ssid
	def run(A):
		if not A.ssid:A.failed.emit('No Wi-Fi network was selected.');return
		try:
			B=subprocess.run([_O,_P,'connect',f"name={A.ssid}"],capture_output=_A,text=_A,creationflags=134217728,timeout=10);C=time.time()+12
			while time.time()<C:
				D=get_current_wifi_ssid()
				if D.lower()==A.ssid.lower():A.connected.emit(A.ssid);return
				A.msleep(500)
			E=(B.stdout or B.stderr or'Windows could not connect to the saved Wi-Fi profile.').strip();A.failed.emit(E)
		except Exception as F:A.failed.emit(str(F))
class WiFiScanThread(QThread):
	'Keep the (occasionally slow) Windows WLAN scan off the UI thread.';networks_found=pyqtSignal(list);scan_failed=pyqtSignal(str)
	def run(B):
		try:
			I=pywifi.PyWiFi();E=I.interfaces()
			if not E:raise RuntimeError('No Wi-Fi adapter was found.')
			F=E[0];F.scan();B.sleep(3);C={}
			for D in F.scan_results():
				A=(D.ssid or'').strip()
				if not A:continue
				G=int(D.signal or-100);H=C.get(A)
				if H is _C or G>H[_Q]:C[A]={_X:A,_Q:G,_e:D.akm!=[const.AKM_TYPE_NONE]}
			B.networks_found.emit(list(C.values()))
		except Exception as J:B.scan_failed.emit(str(J))
def wifi_signal_color(signal):
	'Map Wi-Fi RSSI (dBm) to a connection-quality border color.';A=signal
	try:A=int(A)
	except(TypeError,ValueError):A=-100
	if A>=-50:return'#14532D'
	if A>=-60:return'#16A34A'
	if A>=-67:return'#84CC16'
	if A>=-75:return'#EAB308'
	if A>=-85:return'#F97316'
	return'#DC2626'
class WiFiPickerDialog(QDialog):
	wifi_chosen=pyqtSignal(str)
	def __init__(A,parent=_C):super().__init__(parent);A.scan_thread=WiFiScanThread();A.scan_thread.networks_found.connect(A.on_scan_finished);A.scan_thread.scan_failed.connect(A.on_scan_failed);A.is_connecting=_B;A.initial_scan_done=_B;A.reusable_network_buttons=[];A.skeleton_anims=[];A.setWindowTitle('Loqin • Choose Wi-Fi');A.setMinimumSize(760,580);A.resize(860,680);A.setStyleSheet('\n            QDialog {\n                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,\n                    stop: 0 #2a1b42, stop: 0.5 #1e2247, stop: 1 #121832);\n            }\n            QLabel { color: #f4f7fb; }\n            QScrollArea { border: none; background: transparent; }\n            QWidget#cardsContainer { background: transparent; }\n            QScrollBar:vertical { width: 9px; background: transparent; margin: 6px; }\n            QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.2); border-radius: 4px; min-height: 28px; }\n            QPushButton#refresh {\n                color: #05111c;\n                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #66c7ff, stop: 1 #bb7cff);\n                border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px;\n                font-size: 13px; font-weight: 800; padding: 10px 16px; min-width: 110px;\n            }\n            QPushButton#refresh:hover { background: #82d4ff; }\n            QPushButton#wifiTile, QPushButton#portalTile {\n                text-align: center;\n                border-radius: 14px;\n                padding: 10px;\n                min-height: 156px;\n                min-width: 178px;\n                font-size: 16px;\n                font-weight: 700;\n                border: 2px solid transparent;\n            }\n            QPushButton#wifiTile {\n                color: #eff6ff;\n                background: rgba(255, 255, 255, 0.08);\n            }\n            QPushButton#wifiTile:hover {\n                background: rgba(255, 255, 255, 0.15);\n            }\n            QPushButton#portalTile {\n                color: #05111c;\n                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #66c7ff, stop: 1 #bb7cff);\n            }\n            QPushButton#portalTile:hover {\n                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #82d4ff, stop: 1 #d39fff);\n            }\n            QFrame#skeletonTile { background: rgba(255, 255, 255, 0.1); border-radius: 14px; min-height: 156px; min-width: 178px; }\n        ');B=QVBoxLayout(A);B.setContentsMargins(28,24,28,24);B.setSpacing(12);E=QLabel('Choose your network');E.setStyleSheet('font-size: 30px; font-weight: 700; color: #f8fafc;');B.addWidget(E);F=QLabel('Portal networks appear first. Pick a tile to connect.');F.setStyleSheet('color: #a7b0d6; font-size: 13px;');B.addWidget(F);C=QHBoxLayout();A.status=QLabel(_f);A.status.setStyleSheet(_g);C.addWidget(A.status);C.addStretch();D=QPushButton('Refresh');D.setObjectName('refresh');D.setCursor(Qt.CursorShape.PointingHandCursor);D.clicked.connect(A.scan_networks);C.addWidget(D);B.addLayout(C);A.scroll=QScrollArea();A.scroll.setWidgetResizable(_A);A.cards=QWidget();A.cards.setObjectName('cardsContainer');A.cards_layout=QGridLayout(A.cards);A.cards_layout.setContentsMargins(14,14,14,14);A.cards_layout.setSpacing(12);A.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft);A.scroll.setWidget(A.cards);B.addWidget(A.scroll,1);A.show_skeleton_loading();A.auto_refresh_timer=QTimer(A);A.auto_refresh_timer.setInterval(5000);A.auto_refresh_timer.timeout.connect(A.scan_networks);A.auto_refresh_timer.start();A.scan_networks()
	def show_skeleton_loading(B,count=6,columns=3):
		'Displays temporary wireframe cards with a pulsing opacity animation.';D=columns;B.clear_cards_layout();B.skeleton_anims.clear()
		for E in range(count):C=QFrame();C.setObjectName('skeletonTile');F=QGraphicsOpacityEffect(C);C.setGraphicsEffect(F);A=QPropertyAnimation(F,b'opacity');A.setDuration(1200);A.setStartValue(.3);A.setKeyValueAt(.5,.8);A.setEndValue(.3);A.setEasingCurve(QEasingCurve.Type.InOutSine);A.setLoopCount(-1);A.start();B.skeleton_anims.append(A);G=E//D;H=E%D;B.cards_layout.addWidget(C,G,H)
	def clear_cards_layout(A):
		'Helper to clear the grid layout completely.'
		while A.cards_layout.count():
			B=A.cards_layout.takeAt(0)
			if B.widget():B.widget().deleteLater()
	def scan_networks(A):
		if A.is_connecting or A.scan_thread.isRunning():return
		if not A.initial_scan_done:A.status.setText(_f)
		A.scan_thread.start()
	def on_scan_failed(A,error):A.status.setText(f"Scan failed: {error}");A.status.setStyleSheet('color: #e74c3c; font-weight: 600;')
	def on_scan_finished(A,networks):
		C=networks;D=[];E=[];C.sort(key=lambda x:x[_Q],reverse=_A)
		for B in C:
			if not B.get(_e,_A):D.append(B)
			else:E.append(B)
		A.update_networks_ui(D,E);F=datetime.now().strftime('%I:%M:%S %p');A.status.setText(f"Scan complete. Last updated at {F}");A.status.setStyleSheet(_g)
	def update_networks_ui(B,portal_networks,normal_networks,columns=3):
		M='wifi.svg';G=columns;E=[(A,_A)for A in portal_networks]+[(A,_B)for A in normal_networks]
		if not B.initial_scan_done:B.skeleton_anims.clear();B.clear_cards_layout();B.initial_scan_done=_A
		for C in range(max(len(E),len(B.reusable_network_buttons))):
			if C<len(E):
				D,H=E[C];I=D.get(_X,'Unknown')if isinstance(D,dict)else str(D);N=int(D.get(_Q,-100))if isinstance(D,dict)else-100;F=wifi_signal_color(N)
				if C>=len(B.reusable_network_buttons):A=QPushButton();A.setCursor(Qt.CursorShape.PointingHandCursor);A.setIcon(QIcon(resource_path(M)));A.setIconSize(QSize(54,54));A.setMinimumHeight(156);A.setMinimumWidth(178);B.reusable_network_buttons.append(A);O=C//G;P=C%G;B.cards_layout.addWidget(A,O,P)
				A=B.reusable_network_buttons[C];A.setText(I);A.setIcon(QIcon(resource_path(M)));A.setIconSize(QSize(54,54))
				if H:J='qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #66c7ff, stop: 1 #bb7cff)';K='qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #82d4ff, stop: 1 #d39fff)';L='#05111c'
				else:J='rgba(255, 255, 255, 0.08)';K='rgba(255, 255, 255, 0.15)';L='#eff6ff'
				A.setStyleSheet(f"""
                    QPushButton {{
                        color: {L};
                        background: {J};
                        border: 2px solid {F};
                        border-radius: 14px;
                        padding: 12px;
                        min-height: 156px;
                        min-width: 178px;
                        font-size: 16px;
                        font-weight: 700;
                    }}
                    QPushButton:hover {{
                        background: {K};
                        border: 2px solid {F};
                    }}
                    QPushButton:pressed {{
                        background: rgba(0, 0, 0, 0.16);
                        border: 2px solid {F};
                    }}
                """)
				try:A.clicked.disconnect()
				except TypeError:pass
				A.clicked.connect(lambda checked=_B,target_ssid=I:B.connect_to_network(target_ssid));Q='portalTile'if H else'wifiTile';A.setObjectName(Q);A.setVisible(_A)
			else:B.reusable_network_buttons[C].setVisible(_B)
	def connect_to_network(A,ssid):A.is_connecting=_A;A.status.setText(f"Connecting to {ssid}...");A.status.setStyleSheet('color: #f1c40f; font-weight: 600;');A.auto_refresh_timer.stop();A.wifi_chosen.emit(ssid);A.accept()
class UpdateChecker(QThread):
	update_found=pyqtSignal(str,str,str);no_update_found=pyqtSignal()
	def run(A):
		B=5;C=5
		for G in range(B):
			print(f"Checking for updates (Attempt {G+1}/{B})...")
			try:
				H={'Accept':'application/vnd.github+json'};D=requests.get(GITHUB_API_URL,timeout=5,headers=H)
				if D.status_code==200:
					E=D.json();F=E.get('tag_name','').replace('v','');I=tuple(map(int,APP_VERSION.split('.')));J=tuple(map(int,F.split('.')))
					if J>I:K='https://raw.githubusercontent.com/notaayushsrivastava/Loqin/master/Output/Install_Loqin_Update.exe';A.update_found.emit(F,K,E.get('body','Bug fixes and improvements.'))
					else:A.no_update_found.emit()
					return
			except requests.exceptions.SSLError:print(f"HTTPS intercepted by captive portal. Retrying in {C} seconds...");time.sleep(C)
			except Exception as L:print(f"Update check failed due to network error: {L}");return
		print('Update check aborted: Captive portal is persistently intercepting HTTPS traffic.')
class AccountDetailsDialog(QDialog):
	def __init__(A,username,account_url,parent=_C):super().__init__(parent);A.username=username;A.account_url=account_url;A.setWindowTitle('Loqin • Account Management');A.setWindowIcon(QIcon(resource_path(_N)));A.resize(750,450);A.setStyleSheet('\n            QDialog { \n                background-color: #171A22; \n            }\n            QLabel {\n                color: #FFFFFF;\n                font-size: 14px;\n            }\n            /* Table Styling */\n            QTableWidget {\n                background-color: #1E222D;\n                color: #DDDDDD;\n                gridline-color: #2C313E;\n                border: 1px solid #2C313E;\n                border-radius: 8px;\n                font-size: 12px;\n            }\n            QHeaderView::section {\n                background-color: #171A22;\n                color: #3da5ff;\n                font-weight: bold;\n                padding: 6px;\n                border: 1px solid #2C313E;\n            }\n            QTableWidget::item { padding: 4px; }\n            \n            /* Tab Styling */\n            QTabWidget::pane { border: 1px solid #2C313E; border-radius: 4px; }\n            QTabBar::tab {\n                background: #1E222D; color: #BBBBBB; padding: 10px 20px; \n                border: 1px solid #2C313E; border-bottom: none; \n                border-top-left-radius: 4px; border-top-right-radius: 4px;\n            }\n            QTabBar::tab:selected { background: #171A22; color: #3da5ff; font-weight: bold; }\n            \n            /* Form Styling */\n            QLineEdit {\n                background: #1E222D; color: #FFF; border: 1px solid #2C313E; \n                border-radius: 4px; padding: 6px; font-size: 14px;\n            }\n            QPushButton {\n                background: #3da5ff; color: #171A22; font-weight: bold; \n                border-radius: 4px; padding: 8px; font-size: 14px;\n            }\n            QPushButton:hover { background: #2b8ee0; }\n        ');B=QVBoxLayout(A);A.tabs=QTabWidget(A);B.addWidget(A.tabs);A.setup_history_tab();A.setup_password_tab()
	def setup_history_tab(A):A.history_tab=QWidget();B=QVBoxLayout(A.history_tab);C=QLabel('<b>Recent Network Sessions</b>');C.setStyleSheet('font-size: 16px; margin-bottom: 5px;');B.addWidget(C);A.table=QTableWidget();A.table.setColumnCount(7);A.table.setHorizontalHeaderLabels(['Location','Login Time','Logout Time','Usage Time',_h,_i,'Total Data']);A.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);D=A.table.horizontalHeader();D.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);D.setStretchLastSection(_A);A.table.verticalHeader().setVisible(_B);B.addWidget(A.table);A.tabs.addTab(A.history_tab,'Usage History')
	def create_password_field(F):
		D=QWidget();C=QHBoxLayout(D);C.setContentsMargins(0,0,0,0);C.setSpacing(5);B=QLineEdit();B.setEchoMode(QLineEdit.EchoMode.Password);B.setFixedWidth(250);A=QPushButton('👁');A.setFixedSize(32,32);A.setCursor(Qt.CursorShape.PointingHandCursor);A.setCheckable(_A);A.setStyleSheet(_j)
		def E(checked):
			if checked:B.setEchoMode(QLineEdit.EchoMode.Normal);A.setText('🔒')
			else:B.setEchoMode(QLineEdit.EchoMode.Password);A.setText('👁')
		A.toggled.connect(E);C.addWidget(B);C.addWidget(A);return D,B
	def setup_password_tab(A):A.password_tab=QWidget();C=QVBoxLayout(A.password_tab);F=QLabel('<b>Reset Network Password</b>');F.setStyleSheet('font-size: 16px; margin-bottom: 10px;');C.addWidget(F);B=QFormLayout();B.setLabelAlignment(Qt.AlignmentFlag.AlignRight);B.setFormAlignment(Qt.AlignmentFlag.AlignTop);B.setSpacing(15);G,A.old_pw_input=A.create_password_field();H,A.new_pw_input=A.create_password_field();I,A.confirm_pw_input=A.create_password_field();B.addRow('Current Password:',G);B.addRow('New Password:',H);B.addRow('Confirm Password:',I);C.addLayout(B);D=QPushButton(_k);D.setFixedWidth(287);D.setCursor(Qt.CursorShape.PointingHandCursor);D.setStyleSheet('\n            QPushButton {\n                background: transparent;\n                color: #3da5ff;\n                border: none;\n                font-size: 13px;\n                text-align: left;\n                padding-left: 0px;\n            }\n            QPushButton:hover {\n                text-decoration: underline;\n                color: #5bb3ff;\n            }\n        ');D.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(_l)));A.update_btn=QPushButton('Update Password');A.update_btn.setFixedWidth(287);A.update_btn.clicked.connect(A.submit_password_change);E=QVBoxLayout();E.setSpacing(6);E.addWidget(A.update_btn);E.addWidget(D);E.setContentsMargins(120,10,0,0);C.addLayout(E);A.status_label=QLabel('');A.status_label.setStyleSheet('margin-left: 120px;');C.addWidget(A.status_label);C.addStretch();A.tabs.addTab(A.password_tab,'Change Password')
	def populate_table(A,rows_data,grand_total_data):
		F=grand_total_data;A.table.setRowCount(0)
		for(G,H)in enumerate(rows_data):
			A.table.insertRow(G)
			for(I,D)in enumerate(H):B=QTableWidgetItem(D);B.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(G,I,B)
		if F:
			C=A.table.rowCount();A.table.insertRow(C);E=QTableWidgetItem(_m);E.setForeground(QColor(_R));E.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(C,0,E)
			for(J,D)in enumerate(F):B=QTableWidgetItem(D);B.setForeground(QColor(_R));B.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(C,J+3,B)
			A.table.setSpan(C,0,1,3)
	def submit_password_change(A):
		E='color: #e74c3c; margin-left: 120px;';F=A.old_pw_input.text();B=A.new_pw_input.text();C=A.confirm_pw_input.text()
		if not F or not B or not C:A.status_label.setStyleSheet('color: #f1c40f; margin-left: 120px;');A.status_label.setText('Warning: Please fill all fields.');return
		if B!=C:A.status_label.setStyleSheet(E);A.status_label.setText('Error: New passwords do not match.');return
		A.status_label.setStyleSheet('color: #3da5ff; margin-left: 120px;');A.status_label.setText('Updating password...');A.update_btn.setEnabled(_B);QApplication.processEvents()
		try:
			G=urlparse(A.account_url);D=f"{G.scheme}://{G.netloc}";H=requests.Session();H.get(f"{D}/registration/main.do?content_key=%2FChangePassword.jsp",timeout=5);J={'changeUserId':A.username,'changePassword':F,'changeNewPassword':B,'changeConfirmNewPassword':C,'submit':'Update'};K={_n:f"{D}/registration/main.do?content_key=%2FChangePassword.jsp"};I=H.post(f"{D}/registration/changePassword.do",data=J,headers=K,timeout=5)
			if I.status_code==200:A.status_label.setStyleSheet('color: #2ecc71; margin-left: 120px; font-weight: bold;');A.status_label.setText('Success! Password updated.');keyring.set_password(APP_NAME,A.username,B)
			else:A.status_label.setStyleSheet(E);A.status_label.setText(f"Failed with status: {I.status_code}")
		except Exception as L:A.status_label.setStyleSheet(E);A.status_label.setText(f"Connection Error: {L}")
		finally:A.update_btn.setEnabled(_A)
class UpdateDownloader(QThread):
	progress=pyqtSignal(int);finished=pyqtSignal(str)
	def __init__(A,url):super().__init__();A.url=url
	def run(A):
		try:
			B=requests.get(A.url,stream=_A,timeout=15,allow_redirects=_A);B.raise_for_status();D=int(B.headers.get('content-length',0));G=os.environ.get('TEMP',APPDATA_DIR);E=os.path.join(G,'Install_Loqin_Update.exe');F=0
			with open(E,'wb')as H:
				for C in B.iter_content(chunk_size=8192):
					if C:
						H.write(C);F+=len(C)
						if D:A.progress.emit(int(F/D*100))
			A.finished.emit(E)
		except Exception as I:print(f"Download failed: {I}");A.finished.emit('')
class ReleaseNotesDialog(QDialog):
	def __init__(A,version,notes,parent=_C):super().__init__(parent);A.setWindowTitle('Update Available');A.resize(480,380);C=QVBoxLayout(A);D=QLabel(f"<h3>A new version ({version}) of Loqin is available!</h3>");C.addWidget(D);A.text_browser=QTextBrowser();A.text_browser.setOpenExternalLinks(_A);E=f"**Release Notes:**\n\n{notes}";A.text_browser.setMarkdown(E);C.addWidget(A.text_browser);B=QDialogButtonBox(QDialogButtonBox.StandardButton.Yes|QDialogButtonBox.StandardButton.No);B.button(QDialogButtonBox.StandardButton.Yes).setText('Install Now');B.button(QDialogButtonBox.StandardButton.No).setText('Later');B.accepted.connect(A.accept);B.rejected.connect(A.reject);C.addWidget(B)
class ConfigManager:
	@staticmethod
	def ensure_dir_exists():
		if not os.path.exists(APPDATA_DIR):os.makedirs(APPDATA_DIR,exist_ok=_A)
	@staticmethod
	def load_config():
		A={_I:'',_S:10,'auto_connect':_A,_Y:''};ConfigManager.ensure_dir_exists();B=_B
		if os.path.exists(CONFIG_FILE):
			try:
				with open(CONFIG_FILE,'r')as E:
					C=json.load(E);A.update(C)
					if _J in C:
						D=C[_J]
						if D and A[_I]:ConfigManager.set_password(A[_I],D)
						if _J in A:del A[_J]
						B=_A
			except Exception:pass
		else:B=_A
		if B:ConfigManager.save_config(A)
		return A
	@staticmethod
	def save_config(config):
		ConfigManager.ensure_dir_exists();A=config.copy()
		if _J in A:del A[_J]
		try:
			with open(CONFIG_FILE,'w')as B:json.dump(A,B,indent=4)
		except Exception as C:print(f"Failed to save config: {C}")
	@staticmethod
	def get_password(username):
		A=username
		if not A:return''
		return keyring.get_password(APP_NAME,A)or''
	@staticmethod
	def set_password(username,password):
		A=username
		if A:keyring.set_password(APP_NAME,A,password)
class NetworkWorker(QThread):
	status_signal=pyqtSignal(str,str);account_data_signal=pyqtSignal(str)
	def __init__(A,config):super().__init__();A.config=config;A.is_running=_A;A.is_paused=_B
	def check_network_state(B):
		try:
			A=requests.get('http://clients3.google.com/generate_204',timeout=3,allow_redirects=_B)
			if A.status_code==204:return _Z
			else:return'PORTAL'
		except requests.exceptions.RequestException:return _o
	def run(A):
		while A.is_running:
			if A.is_paused:A.sleep(1);continue
			B=A.config.get(_I);C=ConfigManager.get_password(B)
			if not B or not C:A.status_signal.emit(_p,_K);return
			D=A.check_network_state()
			if D==_Z:A.status_signal.emit('Connected',_G);return
			elif D==_o:A.status_signal.emit('Waiting for Wi-Fi...',_D);return
			A.status_signal.emit('Portal detected. Authenticating...',_D);A.login(B,C);return
	def toggle_pause(A):A.is_paused=not A.is_paused;return A.is_paused
	def login(A,username,password):
		B='http://phc.prontonetworks.com';D=f"{B}/cgi-bin/authlogin?URI=http://example.com";E={'userId':username,_J:password,'serviceName':'ProntoAuthentication','URI':'http://example.com'};F={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Content-Type':'application/x-www-form-urlencoded','Origin':B,_n:f"{B}/cgi-bin/authlogin?URI=http://www.msftconnecttest.com/redirect"}
		try:
			G=requests.post(D,data=E,headers=F,timeout=5)
			if A.check_network_state()==_Z:
				A.status_signal.emit('Logged in successfully!',_G);H=G.text;C=re.search('href="(http://([0-9\\.]+)/registration/Main\\.jsp\\?sessionId=[^"]+)"',H)
				if C:I=C.group(1);J=C.group(2);print(f"Extracted IP: {J}");A.account_data_signal.emit(I)
				else:print('Could not find the account link in the response HTML.')
			else:A.status_signal.emit('Login failed. Check credentials.',_K)
		except Exception as K:print(K);A.status_signal.emit('Portal timeout or error.',_K)
class SpeedGraphDialog(QDialog):
	def __init__(A,parent=_C):I='#777';F='bottom';E='left';D='#BBBBBB';super().__init__(parent);A.setWindowTitle(_q);A.setWindowIcon(QIcon(resource_path(_N)));A.resize(720,420);A.download_history=[0]*60;A.upload_history=[0]*60;C=QVBoxLayout(A);C.setContentsMargins(15,15,15,15);B=QHBoxLayout();G=QLabel('Real-Time Network Usage');G.setStyleSheet('\n            QLabel{\n                color:white;\n                font-size:18px;\n                font-weight:600;\n            }\n        ');A.pin_checkbox=QCheckBox('Always on Top');A.pin_checkbox.setCursor(Qt.CursorShape.PointingHandCursor);A.pin_checkbox.setStyleSheet('\n            QCheckBox {\n                color: #BBBBBB;\n                font-size: 13px;\n                font-weight: 500;\n            }\n            QCheckBox::indicator {\n                width: 14px;\n                height: 14px;\n                border: 1px solid #777777;\n                border-radius: 3px;\n                background: #171A22;\n            }\n            QCheckBox::indicator:checked {\n                background: #3da5ff;\n                border: 1px solid #3da5ff;\n            }\n            QCheckBox:hover {\n                color: #FFFFFF;\n            }\n        ');A.pin_checkbox.toggled.connect(A.toggle_always_on_top);A.secret_code='nyan';A.code_index=0;A.nyan_mode=_B;B.addStretch();B.addWidget(G);B.addStretch();B.addWidget(A.pin_checkbox);C.addLayout(B);A.graph=pg.PlotWidget();C.addWidget(A.graph);A.stats=QLabel();A.stats.setAlignment(Qt.AlignmentFlag.AlignCenter);A.stats.setStyleSheet('\n            QLabel{\n                color:#cccccc;\n                font-size:13px;\n            }\n        ');C.addWidget(A.stats);A.setStyleSheet('\n            QDialog{\n                background:#171A22;\n            }\n        ');A.graph.setBackground(_r);A.graph.showGrid(x=_A,y=_A,alpha=.25);A.graph.hideButtons();A.graph.setMouseEnabled(_B,_B);A.graph.setMenuEnabled(_B);A.graph.setClipToView(_A);A.graph.setDownsampling(mode='peak');A.graph.setLabel(E,'Speed (KB/s)',color=D);A.graph.setLabel(F,'Time',color=D);A.graph.getAxis(E).setPen(pg.mkPen(I));A.graph.getAxis(F).setPen(pg.mkPen(I));A.graph.getAxis(E).setTextPen(D);A.graph.getAxis(F).setTextPen(D);A.graph.setYRange(0,100);A.download_curve=A.graph.plot(pen=pg.mkPen(_s,width=3),name=_i);A.upload_curve=A.graph.plot(pen=pg.mkPen(_R,width=3),name=_h);H=A.graph.addLegend();H.setBrush(pg.mkBrush(30,30,30,200));H.setOffset((15,15))
	def keyPressEvent(A,event):
		B=event;C=B.text().lower()
		if C==A.secret_code[A.code_index]:
			A.code_index+=1
			if A.code_index==len(A.secret_code):A.toggle_nyan_mode();A.code_index=0
		else:A.code_index=0
		super().keyPressEvent(B)
	def generate_nyan_cursor(I):
		E='#000000';D='#999999';C='#FF007F';B=QPixmap(32,32);B.fill(Qt.GlobalColor.transparent);A=QPainter(B);A.setRenderHint(QPainter.RenderHint.Antialiasing,_B);F=['#FF0000','#FF7F00','#FFFF00','#00FF00','#0099FF','#8B00FF']
		for(G,H)in enumerate(F):A.fillRect(0,10+G*2,12,2,QColor(H))
		A.fillRect(12,9,14,14,QColor('#FFD1DC'));A.fillRect(13,10,12,12,QColor(_t));A.fillRect(15,12,2,2,QColor(C));A.fillRect(20,15,2,2,QColor(C));A.fillRect(16,18,2,2,QColor(C));A.fillRect(22,13,9,8,QColor(D));A.fillRect(23,10,2,3,QColor(D));A.fillRect(28,10,2,3,QColor(D));A.fillRect(24,15,2,2,QColor(E));A.fillRect(28,15,2,2,QColor(E));A.fillRect(26,18,2,1,QColor('#FFB6C1'));A.end();return QCursor(B,26,15)
	def toggle_nyan_mode(A):
		A.nyan_mode=not A.nyan_mode
		if A.nyan_mode:A.setWindowTitle('Loqin • Nyan Cat Mode!');A.setCursor(A.generate_nyan_cursor());A.graph.setBackground('#0F051D');A.download_curve.setPen(pg.mkPen(_t,width=3));A.upload_curve.setPen(pg.mkPen('#00FFFF',width=3));A.stats.setStyleSheet('\n                QLabel{ color:#FFD1DC; font-size:13px; font-weight: bold; }\n            ')
		else:A.setWindowTitle(_q);A.unsetCursor();A.graph.setBackground(_r);A.download_curve.setPen(pg.mkPen(_s,width=3));A.upload_curve.setPen(pg.mkPen(_R,width=3));A.stats.setStyleSheet('\n                QLabel{ color:#cccccc; font-size:13px; }\n            ')
	def toggle_always_on_top(A,checked):
		B=A.isVisible()
		if checked:A.setWindowFlags(A.windowFlags()|Qt.WindowType.WindowStaysOnTopHint)
		else:A.setWindowFlags(A.windowFlags()&~Qt.WindowType.WindowStaysOnTopHint)
		if B:A.show()
	def update_data(A,download,upload):C=upload;B=download;B/=1024;C/=1024;A.download_history.pop(0);A.download_history.append(B);A.upload_history.pop(0);A.upload_history.append(C);D=max(max(A.download_history),max(A.upload_history),100);A.graph.setYRange(0,D*1.15);A.download_curve.setData(A.download_history);A.upload_curve.setData(A.upload_history);A.stats.setText(f"""
            <font color='#3da5ff'>↓ {B:.1f} KB/s</font>
            &nbsp;&nbsp;&nbsp;&nbsp;
            <font color='#2ecc71'>↑ {C:.1f} KB/s</font>
            &nbsp;&nbsp;&nbsp;&nbsp;
            Peak: {D:.1f} KB/s
            """)
class SettingsDialog(QDialog):
	def __init__(A,parent=_C):super().__init__(parent);A.setWindowTitle('Loqin for PC - Settings');A.setFixedSize(410,270);A.setWindowIcon(QIcon(resource_path(_N)));A.config=ConfigManager.load_config();A.init_ui()
	def create_password_field(F):
		D=QWidget();C=QHBoxLayout(D);C.setContentsMargins(0,0,0,0);C.setSpacing(5);B=QLineEdit();B.setEchoMode(QLineEdit.EchoMode.Password);A=QPushButton('👁');A.setFixedSize(32,32);A.setCursor(Qt.CursorShape.PointingHandCursor);A.setCheckable(_A);A.setStyleSheet(_j)
		def E(checked):
			if checked:B.setEchoMode(QLineEdit.EchoMode.Normal);A.setText('🔒')
			else:B.setEchoMode(QLineEdit.EchoMode.Password);A.setText('👁')
		A.toggled.connect(E);C.addWidget(B);C.addWidget(A);return D,B
	def init_ui(A):B=QVBoxLayout();B.setSpacing(4);B.setContentsMargins(15,15,15,15);B.setAlignment(Qt.AlignmentFlag.AlignTop);D=QLabel();F=QPixmap(resource_path(_N));G=F.scaled(32,32,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation);D.setPixmap(G);D.setAlignment(Qt.AlignmentFlag.AlignCenter);B.addWidget(D);B.addWidget(QLabel('Registration Number / Username:'));A.user_input=QLineEdit(A.config.get(_I,''));B.addWidget(A.user_input);B.addWidget(QLabel('Password:'));H,A.pass_input=A.create_password_field();A.pass_input.setText(ConfigManager.get_password(A.user_input.text()));B.addWidget(H);C=QPushButton(_k);C.setCursor(Qt.CursorShape.PointingHandCursor);C.setStyleSheet('\n            QPushButton {\n                background: transparent;\n                color: #3da5ff;\n                border: none;\n                font-size: 12px;\n                text-align: left;\n                padding-left: 2px;\n                margin-top: 2px;\n                margin-bottom: 6px;\n            }\n            QPushButton:hover {\n                text-decoration: underline;\n                color: #5bb3ff;\n            }\n        ');C.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(_l)));B.addWidget(C);E=QHBoxLayout();E.addWidget(QLabel('Check Frequency (seconds):'));A.interval_input=QSpinBox();A.interval_input.setRange(5,300);A.interval_input.setValue(A.config.get(_S,10));E.addWidget(A.interval_input);B.addLayout(E);A.startup_cb=QCheckBox('Launch automatically on Windows startup');A.startup_cb.setChecked(is_auto_start_enabled());B.addWidget(A.startup_cb);A.save_btn=QPushButton('Save and Apply');A.save_btn.clicked.connect(A.save_settings);B.addWidget(A.save_btn);B.addStretch();A.setLayout(B)
	def save_settings(A):
		B=A.user_input.text().strip();C=A.pass_input.text().strip()
		if not B or not C:QMessageBox.warning(A,'Warning','Username and Password cannot be empty.');return
		set_auto_start(A.startup_cb.isChecked());A.config[_I]=B;A.config[_S]=A.interval_input.value();ConfigManager.save_config(A.config);ConfigManager.set_password(B,C);QMessageBox.information(A,'Success','Settings saved successfully!');A.accept()
class LoqinTrayApp:
	def __init__(A):A.app=QApplication(sys.argv);A.app.setApplicationName(_F);A.app.setQuitOnLastWindowClosed(_B);A.power_filter=PowerEventFilter(A);A.app.installNativeEventFilter(A.power_filter);A.default_icon=QIcon(resource_path(_N));A.perf_icon=QIcon(resource_path('loqin_logo_performance.png'));A.icon=A.default_icon;A.tray=QSystemTrayIcon();A.tray.setIcon(A.default_icon);A.tray.setVisible(_A);A.tray.showMessage(_F,'Loqin has started! Monitoring your connection in the background.',A.icon,3000);A.config=ConfigManager.load_config();A.last_net_io=psutil.net_io_counters();A.last_time=time.time();A.graph_dialog=_C;A.build_menu();A.wifi_picker=_C;A.waiting_for_wifi_choice=_A;A.selected_wifi_ssid='';A.wifi_connect_thread=_C;A.wifi_startup_thread=_C;A.worker=_C;A.status_action.setText('Status: Looking for your last Wi-Fi...');A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip('Loqin - Connecting to Wi-Fi');A.force_logout();QTimer.singleShot(1200,A.auto_connect_last_wifi);A.speed_timer=QTimer();A.speed_timer.timeout.connect(A.update_bandwidth_meters);A.speed_timer.start(1000);A.has_checked_for_updates=_B
	def build_menu(A):A.menu=QMenu();A.status_action=QAction('Status: Initializing...',A.menu);A.status_action.setIcon(create_status_icon(_D));A.status_action.setEnabled(_A);A.menu.addAction(A.status_action);A.menu.addSeparator();A.speed_action=QAction('Speed: ↓ 0 KB/s  ↑ 0 KB/s',A.menu);A.speed_action.setEnabled(_B);A.menu.addAction(A.speed_action);A.graph_action=QAction(_a,A.menu);A.graph_action.triggered.connect(A.toggle_speed_graph);A.menu.addAction(A.graph_action);A.menu.addSeparator();C=QAction('Connect Now',A.menu);C.triggered.connect(A.trigger_manual_check);A.menu.addAction(C);D=QAction('Choose Wi-Fi',A.menu);D.triggered.connect(A.open_wifi_picker);A.menu.addAction(D);A.pause_action=QAction(_b,A.menu);A.pause_action.triggered.connect(A.toggle_service_pause);A.menu.addAction(A.pause_action);A.perf_action=QAction(_u,A.menu);A.perf_action.setCheckable(_A);A.perf_action.setChecked(_B);A.perf_action.triggered.connect(A.trigger_performance_mode);A.menu.addAction(A.perf_action);A.menu.addSeparator();A.account_action=QAction('View Account Details',A.menu);A.account_action.setEnabled(_B);A.account_action.triggered.connect(A.show_account_details);A.menu.addAction(A.account_action);A.update_action=QAction(_v,A.menu);A.update_action.triggered.connect(A.check_for_updates);A.menu.addAction(A.update_action);E=QAction('Configure Settings',A.menu);E.triggered.connect(A.open_settings);A.menu.addAction(E);A.menu.addSeparator();B=A.menu.addMenu('Help');F=QAction('How to use',A.menu);F.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin#readme')));B.addAction(F);G=QAction('GitHub Releases',A.menu);G.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin/releases')));B.addAction(G);H=QAction('Bug Report',A.menu);H.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin/issues')));B.addAction(H);A.menu.addSeparator();I=QAction('Exit Loqin',A.menu);I.triggered.connect(A.close_app);A.menu.addAction(I);A.tray.setContextMenu(A.menu);A.tray.activated.connect(A.on_tray_icon_activated);A.tray.setToolTip('Loqin PC')
	def on_tray_icon_activated(B,reason):
		'Handles clicks on the system tray icon.'
		if reason==QSystemTrayIcon.ActivationReason.Trigger:
			A=B.tray.contextMenu()
			if A is not _C:A.exec(QCursor.pos())
	def toggle_service_pause(A):
		if hasattr(A,_H)and A.worker:
			B=A.worker.toggle_pause()
			if B:A.pause_action.setText(_c);A.tray.setToolTip('Loqin - Paused')
			else:A.pause_action.setText(_b);A.tray.setToolTip(_w)
	def close_app(A):
		try:requests.get('http://phc.prontonetworks.com/cgi-bin/authlogout/',timeout=2)
		except Exception:pass
		if hasattr(A,_H)and A.worker and A.worker.isRunning():A.worker.is_running=_B;A.worker.quit();A.worker.wait()
		if hasattr(A,_x)and A.perf_thread and A.perf_thread.isRunning():A.perf_thread.quit();A.perf_thread.wait()
		if hasattr(A,_y)and A.update_checker and A.update_checker.isRunning():A.update_checker.quit();A.update_checker.wait()
		A.app.quit()
	def update_bandwidth_meters(A):
		D=psutil.net_io_counters();F=time.time();E=F-A.last_time
		if E>0:
			B=(D.bytes_recv-A.last_net_io.bytes_recv)/E;C=(D.bytes_sent-A.last_net_io.bytes_sent)/E;A.last_net_io=D;A.last_time=F;G=f"{B/1024:.1f} KB/s"if B<1048576 else f"{B/1048576:.1f} MB/s";H=f"{C/1024:.1f} KB/s"if C<1048576 else f"{C/1048576:.1f} MB/s";A.speed_action.setText(f"Speed: ↓ {G}  ↑ {H}")
			if A.graph_dialog and A.graph_dialog.isVisible():A.graph_dialog.update_data(B,C)
	def toggle_speed_graph(A):
		B='Hide Speed Graph'
		if not A.graph_dialog:A.graph_dialog=SpeedGraphDialog();A.graph_dialog.finished.connect(lambda:A.graph_action.setText(_a))
		if A.graph_dialog.isVisible():
			if not A.graph_dialog.isActiveWindow():A.graph_dialog.showNormal();A.graph_dialog.raise_();A.graph_dialog.activateWindow();A.graph_action.setText(B)
			else:A.graph_dialog.hide();A.graph_action.setText(_a)
		else:A.graph_dialog.showNormal();A.graph_dialog.raise_();A.graph_dialog.activateWindow();A.graph_action.setText(B)
	def open_settings(A):
		if hasattr(A,'settings_dialog')and A.settings_dialog is not _C:
			if A.settings_dialog.isVisible():A.settings_dialog.showNormal();A.settings_dialog.raise_();A.settings_dialog.activateWindow();return
		A.settings_dialog=SettingsDialog()
		if A.settings_dialog.exec():A.config=ConfigManager.load_config();A.start_monitoring_timer()
		A.settings_dialog=_C
	def trigger_manual_check(A):
		if hasattr(A,_H)and A.worker and A.worker.isRunning():return
		if A.waiting_for_wifi_choice:A.status_action.setText(_z);A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip(_A0);return
		B=_C
		try:
			E=subprocess.check_output([_O,_P,_T,_U],creationflags=134217728).decode(_V,errors=_W)
			for C in E.split('\n'):
				if _M in C and _M==C.split(_E)[0].strip():
					D=C.split(_E)
					if len(D)>=4:B=_E.join(D[1:]).strip().lower().replace('-',_E);break
		except Exception:pass
		if not hasattr(A,'last_bssid'):A.last_bssid=B
		if B and B!=A.last_bssid:
			A.last_bssid=B
			if A.perf_action.isChecked():
				if getattr(A,'just_optimized',_B):A.just_optimized=_B
				else:A.trigger_performance_mode(checked=_A);return
		A.last_bssid=B;A.just_optimized=_B;A.config=ConfigManager.load_config();A.worker=NetworkWorker(A.config);A.worker.status_signal.connect(A.handle_status);A.worker.account_data_signal.connect(A.handle_account_url);A.worker.start()
	def handle_status(A,message,color_type):
		C=color_type;B=message;A.status_action.setText(f"Status: {B}");A.status_action.setIcon(create_status_icon(C))
		if B==_p:
			if hasattr(A,_H)and A.worker:A.worker.is_paused=_A;A.pause_action.setText(_c);A.tray.setToolTip('Loqin - Paused (Missing Credentials)')
			QTimer.singleShot(100,A.open_settings);return
		if C==_G:
			D=get_current_wifi_ssid()
			if D:A.selected_wifi_ssid=D;A.save_last_wifi(D)
			if'successfully'in B:A.tray.showMessage(_F,B,A.icon,3000)
			if not getattr(A,'has_checked_for_updates',_B):A.has_checked_for_updates=_A;QTimer.singleShot(3500,lambda:A.check_for_updates(_A))
		elif C==_K:A.tray.showMessage(_F,B,A.icon,3000)
	def trigger_performance_mode(A,checked=_B):
		B=checked
		if hasattr(A,_x)and A.perf_thread.isRunning():return
		if hasattr(A,_H)and A.worker:A.worker.is_paused=_A;A.pause_action.setText(_c);A.tray.setToolTip('Loqin - Paused (Optimizing Network)')
		if B:A.tray.setIcon(A.perf_icon);A.icon=A.perf_icon
		else:A.tray.setIcon(A.default_icon);A.icon=A.default_icon
		A.perf_thread=PerformanceModeThread(use_best=B);A.perf_thread.status_signal.connect(A.handle_perf_status);A.perf_thread.start()
	def handle_perf_status(A,message,color_type):
		C=color_type;B=message;A.status_action.setText(f"Status: {B}");A.status_action.setIcon(create_status_icon(C));A.tray.showMessage(_u,B,A.icon,4000)
		if B!=_d:
			A.just_optimized=_A
			if hasattr(A,_H)and A.worker:
				A.worker.is_paused=_B;A.pause_action.setText(_b)
				if'OFF'in B:A.tray.setToolTip(_w)
				else:A.tray.setToolTip('Loqin - Active (Performance Mode)')
			if C in[_G,_D]:QTimer.singleShot(1000,A.trigger_manual_check)
	def handle_account_url(A,url):A.current_account_url=url;print(url);A.account_action.setEnabled(_A)
	def show_account_details(A):
		if not hasattr(A,'current_account_url'):return
		H=A.config.get(_I);A.account_dialog=AccountDetailsDialog(H,A.current_account_url);A.account_dialog.show();QApplication.processEvents()
		try:
			I=requests.get(A.current_account_url,timeout=5);D=BeautifulSoup(I.text,'html.parser');E=[];J=D.find_all('tr',attrs={'bgcolor':['#DDDDDD','#F3F3F3']})
			for C in J:
				B=[A.text.strip()for A in C.find_all('td')]
				if len(B)==7:E.append(B)
			F=[];G=D.find(string=lambda text:text and _m in text)
			if G:C=G.find_parent('tr');B=[A.text.strip()for A in C.find_all('td')];F=B[1:]
			A.account_dialog.populate_table(E,F)
		except Exception as K:print(f"Failed to scrape account history table: {K}")
	def check_for_updates(A,silent=_B):
		"\n        Checks for updates on GitHub.\n        :param silent: If True, suppresses the 'Up to Date' dialog when no new updates are found.\n        ";B=silent
		if hasattr(A,_y)and A.update_checker and A.update_checker.isRunning():return
		if not B:A.update_action.setText('Checking for updates...');A.update_action.setEnabled(_B)
		A.update_checker=UpdateChecker();A.update_checker.update_found.connect(A.prompt_update)
		if not B:A.update_checker.no_update_found.connect(A.prompt_no_update);A.update_checker.finished.connect(lambda:A.update_action.setText(_v));A.update_checker.finished.connect(lambda:A.update_action.setEnabled(_A))
		A.update_checker.start()
	def prompt_no_update(A):'Displays a GUI dialog when the app is already on the latest version.';QMessageBox.information(_C,'Up to Date',f"You are already running the latest version of Loqin (v{APP_VERSION}).\nNo new updates were found :P")
	def prompt_update(A,version,url,notes):
		if hasattr(A,'progress_dialog')and A.progress_dialog.isVisible():return
		B=ReleaseNotesDialog(version,notes);B.setWindowIcon(A.icon)
		if B.exec()==QDialog.DialogCode.Accepted:A.start_download(url)
	def start_download(A,url):A.progress_dialog=QProgressDialog('Downloading update...','Cancel',0,100);A.progress_dialog.setWindowTitle('Updating Loqin');A.progress_dialog.setWindowIcon(A.icon);A.progress_dialog.setFixedSize(350,100);A.progress_dialog.show();A.downloader=UpdateDownloader(url);A.downloader.progress.connect(A.progress_dialog.setValue);A.downloader.finished.connect(A.install_update);A.progress_dialog.canceled.connect(A.downloader.terminate);A.downloader.start()
	def install_update(B,exe_path):
		A=exe_path;B.progress_dialog.close()
		if not A or not os.path.exists(A):QMessageBox.warning(_C,'Update Failed','The update installer could not be found.');return
		try:
			if sys.platform==_L:os.startfile(A)
			else:subprocess.Popen([A])
			B.app.quit()
		except Exception as C:QMessageBox.critical(_C,'Update Error',f"Failed to launch the installer:\n{str(C)}")
	def start_monitoring_timer(A):
		if hasattr(A,'timer')and A.timer:A.timer.stop()
		A.timer=QTimer(A.app);A.timer.timeout.connect(A.trigger_manual_check);A.timer.start(A.config.get(_S,10)*1000)
		if not A.waiting_for_wifi_choice:A.trigger_manual_check()
	def save_last_wifi(B,ssid):
		'Persist the last successfully connected Wi-Fi SSID.';A=ssid;A=(A or'').strip()
		if not A:return
		B.config[_Y]=A;ConfigManager.save_config(B.config)
	def auto_connect_last_wifi(A):
		'Scan for the last Wi-Fi. Use it automatically when it is in range.';B=(A.config.get(_Y)or'').strip()
		if not B:A.open_wifi_picker();return
		if get_current_wifi_ssid().lower()==B.lower():A.on_wifi_connection_success(B,automatic=_A);return
		A.status_action.setText(f"Status: Searching for {B}...");A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip(f"Loqin - Looking for {B}")
		if A.wifi_startup_thread and A.wifi_startup_thread.isRunning():return
		A.wifi_startup_thread=WiFiScanThread();A.wifi_startup_thread.networks_found.connect(lambda networks:A.on_startup_scan_finished(networks,B));A.wifi_startup_thread.scan_failed.connect(A.on_startup_scan_failed);A.wifi_startup_thread.finished.connect(A._cleanup_startup_wifi_thread);A.wifi_startup_thread.start()
	def _cleanup_startup_wifi_thread(A):A.wifi_startup_thread=_C
	def on_startup_scan_finished(A,networks,last_ssid):
		B=last_ssid;C=any(isinstance(A,dict)and A.get(_X,'').strip().lower()==B.lower()for A in networks)
		if C:A.connect_to_wifi(B,automatic=_A)
		else:A.status_action.setText('Status: Last Wi-Fi not in range');A.status_action.setIcon(create_status_icon(_D));A.open_wifi_picker()
	def on_startup_scan_failed(A,error):print(f"Startup Wi-Fi scan failed: {error}");A.open_wifi_picker()
	def connect_to_wifi(A,ssid,automatic=_B):
		'Connect to a Windows-saved Wi-Fi profile without blocking the UI.';C=automatic;B=ssid
		if A.wifi_connect_thread and A.wifi_connect_thread.isRunning():return
		A.selected_wifi_ssid=B;A.status_action.setText(f"Status: {"Connecting to your last Wi-Fi"if C else f"Connecting to {B}"}...");A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip(f"Loqin - Connecting to {B}");A.wifi_connect_thread=WiFiConnectThread(B);A.wifi_connect_thread.connected.connect(lambda connected_ssid:A.on_wifi_connection_success(connected_ssid,C));A.wifi_connect_thread.failed.connect(lambda error:A.on_wifi_connection_failed(B,error));A.wifi_connect_thread.finished.connect(A._cleanup_wifi_connect_thread);A.wifi_connect_thread.start()
	def _cleanup_wifi_connect_thread(A):A.wifi_connect_thread=_C
	def on_wifi_connection_success(A,ssid,automatic=_B):
		B=ssid;A.selected_wifi_ssid=B;A.waiting_for_wifi_choice=_B;A.save_last_wifi(B);A.status_action.setText(f"Status: Wi-Fi connected ({B})");A.status_action.setIcon(create_status_icon(_G));A.tray.setToolTip(f"Loqin - {B}")
		if A.wifi_picker and A.wifi_picker.isVisible():A.wifi_picker.close()
		A.start_monitoring_timer()
	def on_wifi_connection_failed(A,ssid,error):print(f"Could not connect to {ssid}: {error}");A.waiting_for_wifi_choice=_A;A.status_action.setText(_z);A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip(_A0);A.open_wifi_picker()
	def force_logout(B):
		'Silently drops the Pronto Networks Wi-Fi session.'
		try:requests.get('http://phc.prontonetworks.com/cgi-bin/authlogout',timeout=3);print('Successfully dropped existing Wi-Fi session.')
		except Exception as A:print(f"Logout check bypassed (likely not connected): {A}")
	def open_wifi_picker(A):
		if A.wifi_picker is _C:A.wifi_picker=WiFiPickerDialog();A.wifi_picker.wifi_chosen.connect(A.on_wifi_chosen)
		else:A.wifi_picker.scan_networks()
		A.wifi_picker.show();A.wifi_picker.raise_();A.wifi_picker.activateWindow()
	def on_wifi_chosen(A,ssid):A.connect_to_wifi(ssid,automatic=_B)
	def run(A):sys.exit(A.app.exec())
if __name__=='__main__':
	mutex_handle=ensure_single_instance()
	if sys.platform==_L:
		try:myappid=_F;ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
		except Exception as e:print(f"Failed to set AppUserModelID: {e}")
	app=LoqinTrayApp();app.run()