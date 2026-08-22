'\nwhat have i done\n'
_z='Loqin - Waiting for Wi-Fi selection'
_y='Status: Choose Wi-Fi to continue'
_x='update_checker'
_w='perf_thread'
_v='Loqin - Active'
_u='Check for Updates'
_t='Performance Mode'
_s='#FF69B4'
_r='#10162a'
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
_g='Scanning nearby networks…'
_f='eyebrow'
_e='secured'
_d='Optimizing Network...'
_c='Resume Loqin'
_b='Pause Loqin'
_a='Show Speed Graph'
_Z='ONLINE'
_Y='#8ff3c8'
_X='ssid'
_W='ignore'
_V='utf-8'
_U='interfaces'
_T='show'
_S='last_wifi_ssid'
_R='interval'
_Q='signal'
_P='wlan'
_O='netsh'
_N='BSSID'
_M='error'
_L='win32'
_K='password'
_J='username'
_I='loqin_logo_small.png'
_H='worker'
_G='green'
_F='Loqin'
_E=':'
_D='yellow'
_C=None
_B=True
_A=False
import sys,json,os,time,requests,keyring,psutil,subprocess,pyqtgraph as pg,re,ctypes,ctypes.wintypes,pywifi,winreg
from pywifi import const
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
from PyQt6.QtWidgets import QApplication,QSystemTrayIcon,QMenu,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QSpinBox,QCheckBox,QMessageBox,QProgressDialog,QTextBrowser,QDialogButtonBox,QTableWidget,QHeaderView,QTableWidgetItem,QAbstractItemView,QTabWidget,QWidget,QFormLayout,QScrollArea,QGridLayout,QFrame,QGraphicsOpacityEffect
from PyQt6.QtGui import QIcon,QAction,QPixmap,QColor,QPainter,QDesktopServices,QCursor
from PyQt6.QtCore import QThread,pyqtSignal,Qt,QTimer,QUrl,QAbstractNativeEventFilter,QPropertyAnimation,QEasingCurve,QSize
APP_NAME=_F
APPDATA_DIR=os.path.join(os.getenv('APPDATA',os.path.expanduser('~')),_F)
CONFIG_FILE=os.path.join(APPDATA_DIR,'Loqin_config.json')
APP_VERSION='1.7.0'
GITHUB_API_URL='https://api.github.com/repos/notaayushsrivastava/loqin/releases/latest'
REG_PATH='Software\\Microsoft\\Windows\\CurrentVersion\\Run'
APP_REG_NAME=_F
MUTEX_NAME='Global\\Loqin_SingleInstance_Mutex_AayushSrivastava'
WM_POWERBROADCAST=536
PBT_APMSUSPEND=4
PBT_APMRESUMEAUTOMATIC=18
def ensure_single_instance():
	A=ctypes.windll.kernel32;B=A.CreateMutexW(_C,_A,MUTEX_NAME)
	if A.GetLastError()==183:C=QApplication(sys.argv);QMessageBox.warning(_C,'Loqin Already Running','Another instance of Loqin is already running in the system tray.');sys.exit(0)
	return B
def set_auto_start(enabled):
	'Add or remove the app from Windows Registry run-on-startup.'
	if sys.platform!=_L:return
	try:
		A=winreg.OpenKey(winreg.HKEY_CURRENT_USER,REG_PATH,0,winreg.KEY_ALL_ACCESS)
		if enabled:
			if getattr(sys,'frozen',_A):B=f'"{sys.executable}"'
			else:B=f'"{sys.executable}" "{os.path.abspath(__file__)}"'
			winreg.SetValueEx(A,APP_REG_NAME,0,winreg.REG_SZ,B)
		else:
			try:winreg.DeleteValue(A,APP_REG_NAME)
			except OSError:pass
		winreg.CloseKey(A)
	except Exception as C:print(f"Failed to update registry: {C}")
def is_auto_start_enabled():
	'Check if the registry key currently exists'
	if sys.platform!=_L:return _A
	try:A=winreg.OpenKey(winreg.HKEY_CURRENT_USER,REG_PATH,0,winreg.KEY_READ);winreg.QueryValueEx(A,APP_REG_NAME);winreg.CloseKey(A);return _B
	except OSError:return _A
	except Exception as B:print(f"Failed to read registry: {B}");return _A
def resource_path(relative_path):
	'Get absolute path to resource converting image assets to .icns on macOS';C=relative_path
	try:D=sys._MEIPASS
	except Exception:D=os.path.abspath('.')
	A=os.path.join(D,'assets',C)
	if sys.platform=='darwin':
		E,F=os.path.splitext(A)
		if F.lower()in['.png','.ico','.jpg','.jpeg','.bmp']:
			B=f"{E}.icns"
			if not os.path.exists(B)and os.path.exists(A):
				try:G=Image.open(A);G.save(B,format='ICNS')
				except Exception as H:print(f"Failed to convert {C} to .icns: {H}");return A
			if os.path.exists(B):return B
	return A
def create_status_icon(color_type):
	'Generates a smooth colored circle icon (Green, Yellow, Red) for status indicators';C=color_type;B=QPixmap(16,16);B.fill(Qt.GlobalColor.transparent);A=QPainter(B);A.setRenderHint(QPainter.RenderHint.Antialiasing)
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
			if B.wParam==A.last_wparam and C-A.last_event_time<2.:return _A,0
			A.last_event_time=C;A.last_wparam=B.wParam
			if B.wParam==PBT_APMSUSPEND:
				if hasattr(A.tray_app,_H)and A.tray_app.worker:A.tray_app.worker.is_paused=_B
				A.tray_app.force_logout_and_relogin()
			elif B.wParam==PBT_APMRESUMEAUTOMATIC:
				if hasattr(A.tray_app,_H)and A.tray_app.worker:A.tray_app.worker.is_paused=_A
				A.tray_app.has_checked_for_updates=_A;QTimer.singleShot(2000,A.tray_app.auto_connect_last_wifi)
				if hasattr(A.tray_app,'perf_action')and A.tray_app.perf_action.isChecked():QTimer.singleShot(5000,lambda:A.tray_app.trigger_performance_mode(checked=_B))
		return _A,0
class PerformanceModeThread(QThread):
	status_signal=pyqtSignal(str,str)
	def __init__(A,use_best=_B):super().__init__();A.use_best=use_best
	def run(A):
		J='Performance Mode ON';K=_d if A.use_best else'Reverting Network...';A.status_signal.emit(K,_D)
		try:
			L=pywifi.PyWiFi();B=L.interfaces()[0];B.scan();A.sleep(4);M=B.scan_results();E=[A for A in M if'VIT'in(A.ssid or'').upper()]
			if not E:A.status_signal.emit('No VIT networks found in range.',_M);return
			E.sort(key=lambda x:x.signal,reverse=A.use_best);D=E[0]
			if not A.use_best:B.disconnect();A.sleep(1);C=pywifi.Profile();C.ssid=D.ssid;C.bssid=D.bssid;C.auth=const.AUTH_ALG_OPEN;C.akm.append(const.AKM_TYPE_NONE);B.remove_all_network_profiles();N=B.add_network_profile(C);B.connect(N);A.sleep(3);A.status_signal.emit('Performance Mode OFF',_G);return
			F=_C
			try:
				O=subprocess.check_output([_O,_P,_T,_U],creationflags=134217728).decode(_V,errors=_W)
				for G in O.split('\n'):
					if _N in G and _N==G.split(_E)[0].strip():
						I=G.split(_E)
						if len(I)>=4:F=_E.join(I[1:]).strip().lower().replace('-',_E);break
			except Exception as H:print(f"Could not get current BSSID: {H}")
			P=D.bssid.strip().lower().replace('-',_E)if D.bssid else''
			if F and F==P:A.status_signal.emit(J,_G)
			else:A.status_signal.emit(J,_D)
		except Exception as H:A.status_signal.emit(f"Wi-Fi Error: {str(H)}",_M)
def get_current_wifi_ssid():
	'Return the currently connected Wi-Fi SSID using Windows WLAN APIs.'
	if sys.platform!=_L:return''
	try:
		C=subprocess.check_output([_O,_P,_T,_U],creationflags=134217728,timeout=5).decode(_V,errors=_W)
		for D in C.splitlines():
			A=D.strip()
			if A.startswith('SSID')and not A.startswith(_N):
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
			B=subprocess.run([_O,_P,'connect',f"name={A.ssid}"],capture_output=_B,text=_B,creationflags=134217728,timeout=10);C=time.time()+12
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
class WiFiPickerDialog(QDialog):
	'inspired by https://loqin-vit.vercel.app';wifi_chosen=pyqtSignal(str);portal_pattern=re.compile('^(?:VIT|[A-Z]-VIT)$',re.IGNORECASE)
	def __init__(A,parent=_C):super().__init__(parent);A.scan_thread=WiFiScanThread();A.scan_thread.networks_found.connect(A.on_scan_finished);A.scan_thread.scan_failed.connect(A.on_scan_failed);A.is_connecting=_A;A.initial_scan_done=_A;A.skeleton_anims=[];A.setWindowTitle('Loqin • Wi-Fi');A.setWindowIcon(QIcon(resource_path(_I)));A.setMinimumSize(760,620);A.resize(920,720);A.setStyleSheet("\n            QDialog { background: #090b18; color: #f4f7fb; font-family: 'Manrope', 'Segoe UI', sans-serif; }\n            QFrame#topbar { background: rgba(10,13,26,0.86); border: 1px solid rgba(146,160,215,0.18); border-radius: 22px; }\n            QFrame#brandMark { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(102,199,255,0.18),stop:1 rgba(187,124,255,0.16)); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; }\n            QFrame#heroPanel { background: rgba(10,18,32,0.66); border: 1px solid rgba(146,160,215,0.18); border-radius: 30px; }\n            QLabel { color: #f4f7fb; }\n            QLabel#muted, QLabel#subtext { color: #a7b0d6; }\n            QLabel#eyebrow { color: #a7b0d6; font-size: 11px; font-weight: 800; letter-spacing: 2px; }\n            QLabel#heroTitle { color: #f4f7fb; font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 34px; font-weight: 700; }\n            QLabel#brandName { color: #f4f7fb; font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 18px; font-weight: 700; }\n            QLabel#brandCaption { color: #a7b0d6; font-size: 11px; }\n            QLabel#statusPill { color: #e0f4ff; background: rgba(102,199,255,0.08); border: 1px solid rgba(102,199,255,0.18); border-radius: 14px; padding: 8px 12px; }\n            QPushButton#refresh { color: #f4f7fb; background: rgba(16,21,38,0.74); border: 1px solid rgba(102,199,255,0.22); border-radius: 16px; padding: 11px 20px; font-weight: 800; }\n            QPushButton#refresh:hover { background: rgba(28,36,64,0.9); border-color: rgba(102,199,255,0.5); }\n            QPushButton#wifiCard { color: #f4f7fb; background: rgba(16,21,38,0.86); border: 1px solid rgba(146,160,215,0.18); border-radius: 18px; padding: 18px; font-size: 15px; font-weight: 800; text-align: left; }\n            QPushButton#wifiCard:hover { background: rgba(28,36,64,0.9); border-color: rgba(102,199,255,0.5); }\n            QPushButton#portalCard { color: #06101c; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #66c7ff,stop:1 #bb7cff); border: 1px solid rgba(255,255,255,0.30); border-radius: 18px; padding: 18px; font-size: 15px; font-weight: 800; text-align: left; }\n            QPushButton#portalCard:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7ad0ff,stop:1 #c78eff); }\n            QScrollArea { border: none; background: transparent; }\n            QWidget#cardsContainer { background: transparent; }\n            QScrollBar:vertical { width: 6px; background: transparent; }\n            QScrollBar::handle:vertical { background: rgba(138,160,255,0.3); border-radius: 3px; min-height: 28px; }\n            QFrame#skeletonTile { background: rgba(20,26,46,0.6); border: 1px solid rgba(146,160,215,0.12); border-radius: 18px; min-height: 94px; }\n        ");C=QVBoxLayout(A);C.setContentsMargins(30,26,30,30);C.setSpacing(18);I=QFrame();I.setObjectName('topbar');D=QHBoxLayout(I);D.setContentsMargins(16,12,16,12);E=QFrame();E.setObjectName('brandMark');E.setFixedSize(44,44);L=QVBoxLayout(E);L.setContentsMargins(8,8,8,8);M=QLabel();M.setPixmap(QPixmap(resource_path(_I)).scaled(28,28,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));L.addWidget(M);D.addWidget(E);F=QVBoxLayout();F.setSpacing(1);N=QLabel(_F);N.setObjectName('brandName');O=QLabel('PC Wi-Fi Client');O.setObjectName('brandCaption');F.addWidget(N);F.addWidget(O);D.addLayout(F);D.addStretch();P=QLabel('●  Wi-Fi selector');P.setObjectName('statusPill');D.addWidget(P);C.addWidget(I);J=QFrame();J.setObjectName('heroPanel');B=QVBoxLayout(J);B.setContentsMargins(26,24,26,24);B.setSpacing(10);Q=QLabel('NETWORK CONTROL');Q.setObjectName(_f);B.addWidget(Q);R=QLabel('Choose your network.');R.setObjectName('heroTitle');B.addWidget(R);K=QLabel('Select a nearby Wi-Fi network to connect Loqin and continue in the background.');K.setObjectName('subtext');K.setWordWrap(_B);B.addWidget(K);G=QHBoxLayout();A.status=QLabel(_g);A.status.setObjectName('muted');G.addWidget(A.status);G.addStretch();H=QPushButton('Refresh');H.setObjectName('refresh');H.setCursor(Qt.CursorShape.PointingHandCursor);H.clicked.connect(A.scan_networks);G.addWidget(H);B.addLayout(G);C.addWidget(J);A.scroll=QScrollArea();A.scroll.setWidgetResizable(_B);A.cards=QWidget();A.cards.setObjectName('cardsContainer');A.cards_layout=QGridLayout(A.cards);A.cards_layout.setContentsMargins(0,0,6,0);A.cards_layout.setSpacing(14);A.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop);A.scroll.setWidget(A.cards);C.addWidget(A.scroll,1);A.show_skeleton_loading();A.auto_refresh_timer=QTimer(A);A.auto_refresh_timer.setInterval(5000);A.auto_refresh_timer.timeout.connect(A.scan_networks);A.auto_refresh_timer.start();A.scan_networks()
	def show_skeleton_loading(B,count=6,columns=2):
		D=columns;B.clear_cards_layout();B.skeleton_anims.clear()
		for E in range(count):C=QFrame();C.setObjectName('skeletonTile');F=QGraphicsOpacityEffect(C);C.setGraphicsEffect(F);A=QPropertyAnimation(F,b'opacity');A.setDuration(1400);A.setStartValue(.28);A.setKeyValueAt(.5,.75);A.setEndValue(.28);A.setEasingCurve(QEasingCurve.Type.InOutSine);A.setLoopCount(-1);A.start();B.skeleton_anims.append(A);B.cards_layout.addWidget(C,E//D,E%D)
	def clear_cards_layout(A):
		while A.cards_layout.count():
			B=A.cards_layout.takeAt(0)
			if B.widget():B.widget().deleteLater()
	def scan_networks(A):
		if A.is_connecting or A.scan_thread.isRunning():return
		if not A.initial_scan_done:A.status.setText(_g)
		A.scan_thread.start()
	def on_scan_failed(A,error):A.status.setText(f"Scan failed: {error}");A.status.setStyleSheet('color: #ff7b88; font-size: 14px;')
	def on_scan_finished(A,networks):B=networks;B.sort(key=lambda item:item.get(_Q,-100),reverse=_B);C=[B for B in B if A.portal_pattern.fullmatch(B.get(_X,'').strip())];D=[A for A in B if A not in C];A.update_networks_ui(C,D);A.status.setText(f"{len(B)} networks found • updated {datetime.now().strftime("%I:%M:%S %p")}");A.status.setStyleSheet('color: #a7b0d6; font-size: 14px;')
	def update_networks_ui(A,portal_networks,normal_networks,columns=2):
		G=normal_networks;F=portal_networks;B=columns;A.skeleton_anims.clear();A.clear_cards_layout();A.initial_scan_done=_B;D=[]
		if F:D.append(('PORTAL WI-FI',F,_B))
		if G:D.append(('OTHER NETWORKS',G,_A))
		C=0
		for(J,H,K)in D:
			E=QLabel(J);E.setObjectName(_f);E.setStyleSheet('color: #a7b0d6; font-size: 11px; font-weight: 800; letter-spacing: 2px; padding: 8px 2px 0;');A.cards_layout.addWidget(E,C,0,1,B);C+=1
			for(I,L)in enumerate(H):M=I%B;N=C+I//B;A.add_network_card(L,K,N,M)
			C+=(len(H)+B-1)//B
	def add_network_card(C,network,is_portal,row,column):B=network;D=B.get(_X,'Unknown');E=int(B.get(_Q,-100));F='Open network'if not B.get(_e,_B)else'Secured network';A=QPushButton(f"{D}\n{F}  •  {E} dBm");A.setObjectName('portalCard'if is_portal else'wifiCard');A.setIcon(QIcon(resource_path('wifi.svg')));A.setIconSize(QSize(30,30));A.setMinimumHeight(94);A.setCursor(Qt.CursorShape.PointingHandCursor);A.clicked.connect(lambda checked=_A,target=D:C.connect_to_network(target));C.cards_layout.addWidget(A,row,column)
	def connect_to_network(A,ssid):
		A.is_connecting=_B;A.status.setText(f"Connecting to {ssid}…");A.status.setStyleSheet('color: #66c7ff; font-size: 14px;');A.auto_refresh_timer.stop()
		if A.scan_thread.isRunning():A.scan_thread.wait()
		A.wifi_chosen.emit(ssid);A.accept()
class UpdateChecker(QThread):
	update_found=pyqtSignal(str,str,str);no_update_found=pyqtSignal()
	def run(A):
		B=5;C=5
		for H in range(B):
			print(f"Checking for updates (Attempt {H+1}/{B})...")
			try:
				I={'Accept':'application/vnd.github+json'};D=requests.get(GITHUB_API_URL,timeout=5,headers=I)
				if D.status_code==200:
					E=D.json();F=E.get('tag_name','').replace('v','');J=tuple(map(int,APP_VERSION.split('.')));K=tuple(map(int,F.split('.')))
					if K>J:
						if sys.platform==_L:G='https://raw.githubusercontent.com/notaayushsrivastava/Loqin/master/Output/Install_Loqin_Update.exe'
						else:G='https://raw.githubusercontent.com/notaayushsrivastava/Loqin/master/Output/Install_Loqin_macOS.dmg'
						A.update_found.emit(F,G,E.get('body','Bug fixes and improvements.'))
					else:A.no_update_found.emit()
					return
			except requests.exceptions.SSLError:print(f"HTTPS intercepted by captive portal. Retrying in {C} seconds...");time.sleep(C)
			except Exception as L:print(f"Update check failed due to network error: {L}");return
		print('Update check aborted: Captive portal is persistently intercepting HTTPS traffic.')
class AccountDetailsDialog(QDialog):
	def __init__(A,username,account_url,parent=_C):super().__init__(parent);A.username=username;A.account_url=account_url;A.setWindowTitle('Loqin • Account Management');A.setWindowIcon(QIcon(resource_path(_I)));A.resize(860,560);A.setStyleSheet("\n            QDialog { background: #090b18; color: #f4f7fb; font-family: 'Manrope', 'Segoe UI', sans-serif; }\n            QFrame#accountHeader { background: rgba(10,13,26,0.86); border: 1px solid rgba(146,160,215,0.18); border-radius: 22px; }\n            QFrame#accountMark { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(102,199,255,0.18),stop:1 rgba(187,124,255,0.16)); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; }\n            QLabel { color: #f4f7fb; font-size: 14px; }\n            QTableWidget { background: rgba(16,21,38,0.86); color: #f4f7fb; gridline-color: rgba(146,160,215,0.12); border: 1px solid rgba(146,160,215,0.18); border-radius: 18px; font-size: 12px; selection-background-color: rgba(102,199,255,0.22); selection-color: #f4f7fb; }\n            QHeaderView::section { background: rgba(20,26,46,0.96); color: #a7b0d6; font-weight: 800; padding: 10px 8px; border: none; border-bottom: 1px solid rgba(146,160,215,0.18); }\n            QTableWidget::item { padding: 7px; border: none; }\n            QTabWidget::pane { border: 1px solid rgba(146,160,215,0.18); border-radius: 18px; top: -1px; background: rgba(10,18,32,0.66); }\n            QTabBar::tab { background: rgba(255,255,255,0.03); color: #a7b0d6; padding: 11px 18px; margin-right: 8px; border: 1px solid rgba(255,255,255,0.1); border-radius: 14px; font-weight: 800; }\n            QTabBar::tab:hover { color: #f4f7fb; border-color: rgba(102,199,255,0.3); }\n            QTabBar::tab:selected { color: #f4f7fb; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 rgba(102,199,255,0.16),stop:1 rgba(187,124,255,0.14)); border-color: rgba(102,199,255,0.3); }\n            QLineEdit { background: rgba(16,21,38,0.86); color: #f4f7fb; border: 1px solid rgba(146,160,215,0.18); border-radius: 12px; padding: 8px 10px; font-size: 14px; }\n            QLineEdit:focus { border-color: rgba(102,199,255,0.65); background: rgba(20,26,46,0.96); }\n            QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #66c7ff,stop:1 #bb7cff); color: #06101c; font-weight: 800; border: 1px solid rgba(255,255,255,0.22); border-radius: 14px; padding: 10px 14px; font-size: 14px; }\n            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7ad0ff,stop:1 #c78eff); }\n        ");C=QVBoxLayout(A);C.setContentsMargins(24,22,24,24);C.setSpacing(16);F=QFrame();F.setObjectName('accountHeader');B=QHBoxLayout(F);B.setContentsMargins(16,14,16,14);D=QFrame();D.setObjectName('accountMark');D.setFixedSize(44,44);G=QVBoxLayout(D);G.setContentsMargins(8,8,8,8);H=QLabel();H.setPixmap(QPixmap(resource_path(_I)).scaled(28,28,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation));G.addWidget(H);B.addWidget(D);E=QVBoxLayout();E.setSpacing(1);I=QLabel('Account management');I.setStyleSheet("font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 700; color: #f4f7fb;");J=QLabel('Review your session history or update your portal password.');J.setStyleSheet('color: #a7b0d6; font-size: 12px;');E.addWidget(I);E.addWidget(J);B.addLayout(E);B.addStretch();K=QLabel('Secure account tools');K.setStyleSheet('color: #e0f4ff; background: rgba(102,199,255,0.08); border: 1px solid rgba(102,199,255,0.18); border-radius: 14px; padding: 8px 12px; font-weight: 700;');B.addWidget(K);C.addWidget(F);A.tabs=QTabWidget(A);C.addWidget(A.tabs);A.setup_history_tab();A.setup_password_tab()
	def setup_history_tab(A):A.history_tab=QWidget();B=QVBoxLayout(A.history_tab);C=QLabel('Recent network sessions');C.setStyleSheet("font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 18px; font-weight: 700; color: #f4f7fb; margin-bottom: 6px;");B.addWidget(C);A.table=QTableWidget();A.table.setColumnCount(7);A.table.setHorizontalHeaderLabels(['Location','Login Time','Logout Time','Usage Time',_h,_i,'Total Data']);A.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);D=A.table.horizontalHeader();D.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);D.setStretchLastSection(_B);A.table.verticalHeader().setVisible(_A);B.addWidget(A.table);A.tabs.addTab(A.history_tab,'Usage History')
	def create_password_field(F):
		D=QWidget();C=QHBoxLayout(D);C.setContentsMargins(0,0,0,0);C.setSpacing(5);B=QLineEdit();B.setEchoMode(QLineEdit.EchoMode.Password);B.setFixedWidth(250);A=QPushButton('👁');A.setFixedSize(32,32);A.setCursor(Qt.CursorShape.PointingHandCursor);A.setCheckable(_B);A.setStyleSheet(_j)
		def E(checked):
			if checked:B.setEchoMode(QLineEdit.EchoMode.Normal);A.setText('🔒')
			else:B.setEchoMode(QLineEdit.EchoMode.Password);A.setText('👁')
		A.toggled.connect(E);C.addWidget(B);C.addWidget(A);return D,B
	def setup_password_tab(A):
		A.password_tab=QWidget();C=QVBoxLayout(A.password_tab);F=QLabel('Reset network password');F.setStyleSheet("font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 18px; font-weight: 700; color: #f4f7fb; margin-bottom: 12px;");C.addWidget(F);B=QFormLayout();B.setLabelAlignment(Qt.AlignmentFlag.AlignRight);B.setFormAlignment(Qt.AlignmentFlag.AlignTop);B.setSpacing(15);G,A.old_pw_input=A.create_password_field();H,A.new_pw_input=A.create_password_field();I,A.confirm_pw_input=A.create_password_field()
		for J in(G,H,I):J.findChild(QPushButton).setStyleSheet('\n                QPushButton { background: rgba(16,21,38,0.86); color: #a7b0d6; border: 1px solid rgba(146,160,215,0.18); border-radius: 10px; font-size: 14px; }\n                QPushButton:checked { background: #66c7ff; color: #06101c; border-color: #66c7ff; }\n                QPushButton:hover { border-color: #66c7ff; }\n            ')
		B.addRow('Current Password:',G);B.addRow('New Password:',H);B.addRow('Confirm Password:',I);C.addLayout(B);D=QPushButton(_k);D.setFixedWidth(287);D.setCursor(Qt.CursorShape.PointingHandCursor);D.setStyleSheet('\n            QPushButton {\n                background: transparent;\n                color: #a7b0d6;\n                border: 1px solid rgba(255,255,255,0.12);\n                border-radius: 12px;\n                font-size: 13px;\n                text-align: left;\n                padding: 8px 10px;\n            }\n            QPushButton:hover {\n                color: #f4f7fb;\n                border-color: rgba(102,199,255,0.3);\n                background: rgba(255,255,255,0.03);\n            }\n        ');D.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(_l)));A.update_btn=QPushButton('Update Password');A.update_btn.setFixedWidth(287);A.update_btn.clicked.connect(A.submit_password_change);E=QVBoxLayout();E.setSpacing(6);E.addWidget(A.update_btn);E.addWidget(D);E.setContentsMargins(120,10,0,0);C.addLayout(E);A.status_label=QLabel('');A.status_label.setStyleSheet('margin-left: 120px;');C.addWidget(A.status_label);C.addStretch();A.tabs.addTab(A.password_tab,'Change Password')
	def populate_table(A,rows_data,grand_total_data):
		F=grand_total_data;A.table.setRowCount(0)
		for(G,H)in enumerate(rows_data):
			A.table.insertRow(G)
			for(I,D)in enumerate(H):B=QTableWidgetItem(D);B.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(G,I,B)
		if F:
			C=A.table.rowCount();A.table.insertRow(C);E=QTableWidgetItem(_m);E.setForeground(QColor(_Y));E.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(C,0,E)
			for(J,D)in enumerate(F):B=QTableWidgetItem(D);B.setForeground(QColor(_Y));B.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(C,J+3,B)
			A.table.setSpan(C,0,1,3)
	def submit_password_change(A):
		E='color: #e74c3c; margin-left: 120px;';F=A.old_pw_input.text();B=A.new_pw_input.text();C=A.confirm_pw_input.text()
		if not F or not B or not C:A.status_label.setStyleSheet('color: #f1c40f; margin-left: 120px;');A.status_label.setText('Warning: Please fill all fields.');return
		if B!=C:A.status_label.setStyleSheet(E);A.status_label.setText('Error: New passwords do not match.');return
		A.status_label.setStyleSheet('color: #3da5ff; margin-left: 120px;');A.status_label.setText('Updating password...');A.update_btn.setEnabled(_A);QApplication.processEvents()
		try:
			G=urlparse(A.account_url);D=f"{G.scheme}://{G.netloc}";H=requests.Session();H.get(f"{D}/registration/main.do?content_key=%2FChangePassword.jsp",timeout=5);J={'changeUserId':A.username,'changePassword':F,'changeNewPassword':B,'changeConfirmNewPassword':C,'submit':'Update'};K={_n:f"{D}/registration/main.do?content_key=%2FChangePassword.jsp"};I=H.post(f"{D}/registration/changePassword.do",data=J,headers=K,timeout=5)
			if I.status_code==200:A.status_label.setStyleSheet('color: #2ecc71; margin-left: 120px; font-weight: bold;');A.status_label.setText('Success! Password updated.');keyring.set_password(APP_NAME,A.username,B)
			else:A.status_label.setStyleSheet(E);A.status_label.setText(f"Failed with status: {I.status_code}")
		except Exception as L:A.status_label.setStyleSheet(E);A.status_label.setText(f"Connection Error: {L}")
		finally:A.update_btn.setEnabled(_B)
class UpdateDownloader(QThread):
	progress=pyqtSignal(int);finished=pyqtSignal(str)
	def __init__(A,url):super().__init__();A.url=url
	def run(A):
		try:
			B=requests.get(A.url,stream=_B,timeout=15,allow_redirects=_B);B.raise_for_status();D=int(B.headers.get('content-length',0));G=os.environ.get('TEMP',APPDATA_DIR);E=os.path.join(G,'Install_Loqin_Update.exe');F=0
			with open(E,'wb')as H:
				for C in B.iter_content(chunk_size=8192):
					if C:
						H.write(C);F+=len(C)
						if D:A.progress.emit(int(F/D*100))
			A.finished.emit(E)
		except Exception as I:print(f"Download failed: {I}");A.finished.emit('')
class ReleaseNotesDialog(QDialog):
	def __init__(A,version,notes,parent=_C):super().__init__(parent);A.setWindowTitle('Update Available');A.resize(480,380);C=QVBoxLayout(A);D=QLabel(f"<h3>A new version ({version}) of Loqin is available!</h3>");C.addWidget(D);A.text_browser=QTextBrowser();A.text_browser.setOpenExternalLinks(_B);E=f"**Release Notes:**\n\n{notes}";A.text_browser.setMarkdown(E);C.addWidget(A.text_browser);B=QDialogButtonBox(QDialogButtonBox.StandardButton.Yes|QDialogButtonBox.StandardButton.No);B.button(QDialogButtonBox.StandardButton.Yes).setText('Install Now');B.button(QDialogButtonBox.StandardButton.No).setText('Later');B.accepted.connect(A.accept);B.rejected.connect(A.reject);C.addWidget(B)
class ConfigManager:
	@staticmethod
	def ensure_dir_exists():
		if not os.path.exists(APPDATA_DIR):os.makedirs(APPDATA_DIR,exist_ok=_B)
	@staticmethod
	def load_config():
		A={_J:'',_R:10,'auto_connect':_B,_S:''};ConfigManager.ensure_dir_exists();B=_A
		if os.path.exists(CONFIG_FILE):
			try:
				with open(CONFIG_FILE,'r')as E:
					C=json.load(E);A.update(C)
					if _K in C:
						D=C[_K]
						if D and A[_J]:ConfigManager.set_password(A[_J],D)
						if _K in A:del A[_K]
						B=_B
			except Exception:pass
		else:B=_B
		if B:ConfigManager.save_config(A)
		return A
	@staticmethod
	def save_config(config):
		ConfigManager.ensure_dir_exists();A=config.copy()
		if _K in A:del A[_K]
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
	def __init__(A,config):super().__init__();A.config=config;A.is_running=_B;A.is_paused=_A
	@staticmethod
	def extract_account_url(html_content):
		'Try several possible portal response patterns so account details work even with slight HTML changes.';B=html_content
		if not B:return''
		C=['https?://(?:\\d{1,3}\\.){3}\\d+/[^\\"\\\'\\s]*?/registration/Main\\.jsp\\?sessionId=[^\\"\\\'\\s]+','https?://(?:\\d{1,3}\\.){3}\\d+/registration/Main\\.jsp\\?sessionId=[^\\"\\\'\\s]+','href=[\\"\\\'](https?://[^\\"\\\'\\s]+/registration/Main\\.jsp\\?sessionId=[^\\"\\\'\\s]+)[\\"\\\']','(https?://[^\\"\\\'\\s]+/registration/Main\\.jsp\\?sessionId=[^\\"\\\'\\s]+)']
		for D in C:
			A=re.search(D,B,re.IGNORECASE)
			if A:return A.group(1)if A.groups()else A.group(0)
		return''
	def check_network_state(B):
		try:
			A=requests.get('http://clients3.google.com/generate_204',timeout=3,allow_redirects=_A)
			if A.status_code==204:return _Z
			else:return'PORTAL'
		except requests.exceptions.RequestException:return _o
	def run(A):
		while A.is_running:
			if A.is_paused:A.sleep(1);continue
			B=A.config.get(_J);C=ConfigManager.get_password(B)
			if not B or not C:A.status_signal.emit(_p,_M);return
			D=A.check_network_state()
			if D==_Z:A.status_signal.emit('Connected',_G);return
			elif D==_o:A.status_signal.emit('Waiting for Wi-Fi...',_D);return
			A.status_signal.emit('Portal detected. Authenticating...',_D);A.login(B,C);return
	def toggle_pause(A):A.is_paused=not A.is_paused;return A.is_paused
	def login(B,username,password):
		F='registration/Main.jsp';E='http://phc.prontonetworks.com';G=f"{E}/cgi-bin/authlogin?URI=http://example.com";H={'userId':username,_K:password,'serviceName':'ProntoAuthentication','URI':'http://example.com'};I={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Content-Type':'application/x-www-form-urlencoded','Origin':E,_n:f"{E}/cgi-bin/authlogin?URI=http://www.msftconnecttest.com/redirect"}
		try:
			C=requests.post(G,data=H,headers=I,timeout=5)
			if B.check_network_state()==_Z:
				B.status_signal.emit('Logged in successfully!',_G);J=C.text;A=B.extract_account_url(J)
				if not A:
					for D in getattr(C,'history',[]):
						if D and D.url and F in D.url:A=D.url;break
				if not A and C.url and F in C.url:A=C.url
				if A:print(f"Extracted account URL: {A}");B.account_data_signal.emit(A)
				else:print('Could not find the account link in the response HTML.')
			else:B.status_signal.emit('Login failed. Check credentials.',_M)
		except Exception as K:print(K);B.status_signal.emit('Portal timeout or error.',_M)
class SpeedGraphDialog(QDialog):
	def __init__(A,parent=_C):I='#59658a';F='bottom';E='left';D='#a7b0d6';super().__init__(parent);A.setWindowTitle(_q);A.setWindowIcon(QIcon(resource_path(_I)));A.resize(820,520);A.download_history=[0]*60;A.upload_history=[0]*60;C=QVBoxLayout(A);C.setContentsMargins(15,15,15,15);B=QHBoxLayout();G=QLabel('Real-Time Network Usage');G.setStyleSheet("color: #f4f7fb; font-family: 'Space Grotesk', 'Segoe UI', sans-serif; font-size: 20px; font-weight: 700;");A.pin_checkbox=QCheckBox('Always on Top');A.pin_checkbox.setCursor(Qt.CursorShape.PointingHandCursor);A.pin_checkbox.setStyleSheet('\n            QCheckBox {\n                color: #a7b0d6;\n                font-size: 13px;\n                font-weight: 500;\n            }\n            QCheckBox::indicator {\n                width: 14px;\n                height: 14px;\n                border: 1px solid rgba(146,160,215,0.4);\n                border-radius: 5px;\n                background: rgba(255,255,255,0.04);\n            }\n            QCheckBox::indicator:checked {\n                background: #66c7ff;\n                border: 1px solid #66c7ff;\n            }\n            QCheckBox:hover {\n                color: #f4f7fb;\n            }\n        ');A.pin_checkbox.toggled.connect(A.toggle_always_on_top);A.secret_code='nyan';A.code_index=0;A.nyan_mode=_A;B.addStretch();B.addWidget(G);B.addStretch();B.addWidget(A.pin_checkbox);C.addLayout(B);A.graph=pg.PlotWidget();C.addWidget(A.graph);A.stats=QLabel();A.stats.setAlignment(Qt.AlignmentFlag.AlignCenter);A.stats.setStyleSheet('color: #a7b0d6; font-size: 13px; padding: 8px;');C.addWidget(A.stats);A.setStyleSheet("\n            QDialog { background: #090b18; color: #f4f7fb; font-family: 'Manrope', 'Segoe UI', sans-serif; }\n        ");A.graph.setBackground(_r);A.graph.showGrid(x=_B,y=_B,alpha=.25);A.graph.hideButtons();A.graph.setMouseEnabled(_A,_A);A.graph.setMenuEnabled(_A);A.graph.setClipToView(_B);A.graph.setDownsampling(mode='peak');A.graph.setLabel(E,'Speed (KB/s)',color=D);A.graph.setLabel(F,'Time',color=D);A.graph.getAxis(E).setPen(pg.mkPen(I));A.graph.getAxis(F).setPen(pg.mkPen(I));A.graph.getAxis(E).setTextPen(D);A.graph.getAxis(F).setTextPen(D);A.graph.setYRange(0,100);A.download_curve=A.graph.plot(pen=pg.mkPen('#66c7ff',width=3),name=_i);A.upload_curve=A.graph.plot(pen=pg.mkPen(_Y,width=3),name=_h);H=A.graph.addLegend();H.setBrush(pg.mkBrush(20,26,46,220));H.setOffset((15,15))
	def keyPressEvent(A,event):
		B=event;C=B.text().lower()
		if C==A.secret_code[A.code_index]:
			A.code_index+=1
			if A.code_index==len(A.secret_code):A.toggle_nyan_mode();A.code_index=0
		else:A.code_index=0
		super().keyPressEvent(B)
	def generate_nyan_cursor(I):
		E='#000000';D='#999999';C='#FF007F';B=QPixmap(32,32);B.fill(Qt.GlobalColor.transparent);A=QPainter(B);A.setRenderHint(QPainter.RenderHint.Antialiasing,_A);F=['#FF0000','#FF7F00','#FFFF00','#00FF00','#0099FF','#8B00FF']
		for(G,H)in enumerate(F):A.fillRect(0,10+G*2,12,2,QColor(H))
		A.fillRect(12,9,14,14,QColor('#FFD1DC'));A.fillRect(13,10,12,12,QColor(_s));A.fillRect(15,12,2,2,QColor(C));A.fillRect(20,15,2,2,QColor(C));A.fillRect(16,18,2,2,QColor(C));A.fillRect(22,13,9,8,QColor(D));A.fillRect(23,10,2,3,QColor(D));A.fillRect(28,10,2,3,QColor(D));A.fillRect(24,15,2,2,QColor(E));A.fillRect(28,15,2,2,QColor(E));A.fillRect(26,18,2,1,QColor('#FFB6C1'));A.end();return QCursor(B,26,15)
	def toggle_nyan_mode(A):
		A.nyan_mode=not A.nyan_mode
		if A.nyan_mode:A.setWindowTitle('Loqin • Nyan Cat Mode!');A.setCursor(A.generate_nyan_cursor());A.graph.setBackground('#0F051D');A.download_curve.setPen(pg.mkPen(_s,width=3));A.upload_curve.setPen(pg.mkPen('#00FFFF',width=3));A.stats.setStyleSheet('\n                QLabel{ color:#FFD1DC; font-size:13px; font-weight: bold; }\n            ')
		else:A.setWindowTitle(_q);A.unsetCursor();A.graph.setBackground(_r);A.download_curve.setPen(pg.mkPen('#3da5ff',width=3));A.upload_curve.setPen(pg.mkPen('#2ecc71',width=3));A.stats.setStyleSheet('\n                QLabel{ color:#cccccc; font-size:13px; }\n            ')
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
	def __init__(A,parent=_C):super().__init__(parent);A.setWindowTitle('Loqin for PC - Settings');A.setFixedSize(520,600);A.setWindowIcon(QIcon(resource_path(_I)));A.setStyleSheet("\n            QDialog { background: #090b18; color: #f4f7fb; font-family: 'Manrope', 'Segoe UI', sans-serif; }\n            QLabel { color: #a7b0d6; font-size: 13px; }\n            QLineEdit, QSpinBox { color: #f4f7fb; background: rgba(16,21,38,0.86); border: 1px solid rgba(146,160,215,0.18); border-radius: 12px; padding: 9px 11px; min-height: 18px; }\n            QLineEdit:focus, QSpinBox:focus { border-color: rgba(102,199,255,0.65); background: rgba(20,26,46,0.96); }\n            QSpinBox::up-button, QSpinBox::down-button { width: 22px; border: none; background: transparent; }\n            QCheckBox { color: #a7b0d6; font-size: 13px; spacing: 8px; }\n            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid rgba(146,160,215,0.4); border-radius: 5px; background: rgba(255,255,255,0.04); }\n            QCheckBox::indicator:checked { background: #66c7ff; border-color: #66c7ff; }\n            QPushButton { color: #06101c; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #66c7ff,stop:1 #bb7cff); border: 1px solid rgba(255,255,255,0.22); border-radius: 14px; padding: 10px 16px; font-weight: 800; }\n            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7ad0ff,stop:1 #c78eff); }\n        ");A.config=ConfigManager.load_config();A.init_ui()
	def create_password_field(F):
		D=QWidget();C=QHBoxLayout(D);C.setContentsMargins(0,0,0,0);C.setSpacing(5);B=QLineEdit();B.setEchoMode(QLineEdit.EchoMode.Password);A=QPushButton('👁');A.setFixedSize(32,32);A.setCursor(Qt.CursorShape.PointingHandCursor);A.setCheckable(_B);A.setStyleSheet(_j)
		def E(checked):
			if checked:B.setEchoMode(QLineEdit.EchoMode.Normal);A.setText('🔒')
			else:B.setEchoMode(QLineEdit.EchoMode.Password);A.setText('👁')
		A.toggled.connect(E);C.addWidget(B);C.addWidget(A);return D,B
	def init_ui(A):B=QVBoxLayout();B.setSpacing(10);B.setContentsMargins(28,26,28,26);B.setAlignment(Qt.AlignmentFlag.AlignTop);D=QLabel();G=QPixmap(resource_path('wizard_banner.bmp'));H=G.scaled(512,512,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation);D.setPixmap(H);D.setAlignment(Qt.AlignmentFlag.AlignCenter);B.addWidget(D);B.addWidget(QLabel('Registration Number / Username:'));A.user_input=QLineEdit(A.config.get(_J,''));B.addWidget(A.user_input);B.addWidget(QLabel('Password:'));F,A.pass_input=A.create_password_field();A.pass_input.setText(ConfigManager.get_password(A.user_input.text()));F.findChild(QPushButton).setStyleSheet('\n            QPushButton { background: rgba(16,21,38,0.86); color: #a7b0d6; border: 1px solid rgba(146,160,215,0.18); border-radius: 10px; font-size: 14px; }\n            QPushButton:checked { background: #66c7ff; color: #06101c; border-color: #66c7ff; }\n            QPushButton:hover { border-color: #66c7ff; }\n        ');B.addWidget(F);C=QPushButton(_k);C.setCursor(Qt.CursorShape.PointingHandCursor);C.setStyleSheet('\n            QPushButton {\n                background: transparent;\n                color: #3da5ff;\n                border: none;\n                font-size: 12px;\n                text-align: left;\n                padding-left: 2px;\n                margin-top: 2px;\n                margin-bottom: 6px;\n            }\n            QPushButton:hover {\n                text-decoration: underline;\n                color: #5bb3ff;\n            }\n        ');C.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(_l)));B.addWidget(C);E=QHBoxLayout();E.addWidget(QLabel('Check Frequency (seconds):'));A.interval_input=QSpinBox();A.interval_input.setRange(5,300);A.interval_input.setValue(A.config.get(_R,10));E.addWidget(A.interval_input);B.addLayout(E);A.startup_cb=QCheckBox('Launch automatically on Windows startup');A.startup_cb.setChecked(is_auto_start_enabled());B.addWidget(A.startup_cb);A.save_btn=QPushButton('Save and Apply');A.save_btn.clicked.connect(A.save_settings);B.addWidget(A.save_btn);B.addStretch();A.setLayout(B)
	def save_settings(A):
		B=A.user_input.text().strip();C=A.pass_input.text().strip()
		if not B or not C:QMessageBox.warning(A,'Warning','Username and Password cannot be empty.');return
		set_auto_start(A.startup_cb.isChecked());A.config[_J]=B;A.config[_R]=A.interval_input.value();ConfigManager.save_config(A.config);ConfigManager.set_password(B,C);QMessageBox.information(A,'Success','Settings saved successfully!');A.accept()
class LoqinTrayApp:
	def __init__(A):A.app=QApplication(sys.argv);A.app.setApplicationName(_F);A.app.setQuitOnLastWindowClosed(_A);A.power_filter=PowerEventFilter(A);A.app.installNativeEventFilter(A.power_filter);A.default_icon=QIcon(resource_path(_I));A.perf_icon=QIcon(resource_path('loqin_logo_performance.png'));A.icon=A.default_icon;A.tray=QSystemTrayIcon();A.tray.setIcon(A.default_icon);A.tray.setVisible(_B);A.tray.showMessage(_F,'Loqin has started! Monitoring your connection in the background.',A.icon,3000);A.config=ConfigManager.load_config();A.last_net_io=psutil.net_io_counters();A.last_time=time.time();A.graph_dialog=_C;A.build_menu();A.wifi_picker=_C;A.waiting_for_wifi_choice=_B;A.selected_wifi_ssid='';A.wifi_connect_thread=_C;A.wifi_startup_thread=_C;A.worker=_C;A.status_action.setText('Status: Looking for your last Wi-Fi...');A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip('Loqin - Connecting to Wi-Fi');A.force_logout_and_relogin();QTimer.singleShot(1200,A.auto_connect_last_wifi);A.speed_timer=QTimer();A.speed_timer.timeout.connect(A.update_bandwidth_meters);A.speed_timer.start(1000);A.has_checked_for_updates=_A
	def build_menu(A):A.menu=QMenu();A.status_action=QAction('Status: Initializing...',A.menu);A.status_action.setIcon(create_status_icon(_D));A.status_action.setEnabled(_B);A.menu.addAction(A.status_action);A.menu.addSeparator();A.speed_action=QAction('Speed: ↓ 0 KB/s  ↑ 0 KB/s',A.menu);A.speed_action.setEnabled(_A);A.menu.addAction(A.speed_action);A.graph_action=QAction(_a,A.menu);A.graph_action.triggered.connect(A.toggle_speed_graph);A.menu.addAction(A.graph_action);A.menu.addSeparator();C=QAction('Connect Now',A.menu);C.triggered.connect(A.connect_now);A.menu.addAction(C);D=QAction('Choose Wi-Fi',A.menu);D.triggered.connect(A.open_wifi_picker);A.menu.addAction(D);A.pause_action=QAction(_b,A.menu);A.pause_action.triggered.connect(A.toggle_service_pause);A.menu.addAction(A.pause_action);A.perf_action=QAction(_t,A.menu);A.perf_action.setCheckable(_B);A.perf_action.setChecked(_A);A.perf_action.triggered.connect(A.trigger_performance_mode);A.menu.addAction(A.perf_action);A.menu.addSeparator();A.account_action=QAction('View Account Details',A.menu);A.account_action.setEnabled(_A);A.account_action.triggered.connect(A.show_account_details);A.menu.addAction(A.account_action);A.update_action=QAction(_u,A.menu);A.update_action.triggered.connect(A.check_for_updates);A.menu.addAction(A.update_action);E=QAction('Configure Settings',A.menu);E.triggered.connect(A.open_settings);A.menu.addAction(E);A.menu.addSeparator();B=A.menu.addMenu('Help');F=QAction('Website',A.menu);F.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://loqin-vit.vercel.app/')));B.addAction(F);G=QAction('How to use',A.menu);G.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin#readme')));B.addAction(G);H=QAction('GitHub Releases',A.menu);H.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin/releases')));B.addAction(H);I=QAction('Bug Report',A.menu);I.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin/issues')));B.addAction(I);A.menu.addSeparator();J=QAction('Exit Loqin',A.menu);J.triggered.connect(A.close_app);A.menu.addAction(J);A.tray.setContextMenu(A.menu);A.tray.activated.connect(A.on_tray_icon_activated);A.tray.setToolTip('Loqin PC')
	def on_tray_icon_activated(B,reason):
		if reason==QSystemTrayIcon.ActivationReason.Trigger:
			A=B.tray.contextMenu()
			if A is not _C:A.exec(QCursor.pos())
	def toggle_service_pause(A):
		if hasattr(A,_H)and A.worker:
			B=A.worker.toggle_pause()
			if B:A.pause_action.setText(_c);A.tray.setToolTip('Loqin - Paused')
			else:A.pause_action.setText(_b);A.tray.setToolTip(_v)
	def close_app(A):
		try:requests.get('http://phc.prontonetworks.com/cgi-bin/authlogout/',timeout=2)
		except Exception:pass
		if hasattr(A,_H)and A.worker and A.worker.isRunning():A.worker.is_running=_A;A.worker.quit();A.worker.wait()
		if hasattr(A,_w)and A.perf_thread and A.perf_thread.isRunning():A.perf_thread.quit();A.perf_thread.wait()
		if hasattr(A,_x)and A.update_checker and A.update_checker.isRunning():A.update_checker.quit();A.update_checker.wait()
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
	def connect_now(A):
		C=(get_current_wifi_ssid()or'').strip();B=(A.config.get(_S)or'').strip()
		if B and C.lower()!=B.lower():A.auto_connect_last_wifi();return
		A.trigger_manual_check()
	def trigger_manual_check(A):
		if hasattr(A,_H)and A.worker and A.worker.isRunning():return
		if A.waiting_for_wifi_choice:A.status_action.setText(_y);A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip(_z);return
		B=_C
		try:
			E=subprocess.check_output([_O,_P,_T,_U],creationflags=134217728).decode(_V,errors=_W)
			for C in E.split('\n'):
				if _N in C and _N==C.split(_E)[0].strip():
					D=C.split(_E)
					if len(D)>=4:B=_E.join(D[1:]).strip().lower().replace('-',_E);break
		except Exception:pass
		if not hasattr(A,'last_bssid'):A.last_bssid=B
		if B and B!=A.last_bssid:
			A.last_bssid=B
			if A.perf_action.isChecked():
				if getattr(A,'just_optimized',_A):A.just_optimized=_A
				else:QTimer.singleShot(5000,lambda:A.trigger_performance_mode(checked=_B));return
		A.last_bssid=B;A.just_optimized=_A;A.config=ConfigManager.load_config();A.worker=NetworkWorker(A.config);A.worker.status_signal.connect(A.handle_status);A.worker.account_data_signal.connect(A.handle_account_url);A.worker.start()
	def handle_status(A,message,color_type):
		C=color_type;B=message;A.status_action.setText(f"Status: {B}");A.status_action.setIcon(create_status_icon(C))
		if B==_p:
			if hasattr(A,_H)and A.worker:A.worker.is_paused=_B;A.pause_action.setText(_c);A.tray.setToolTip('Loqin - Paused (Missing Credentials)')
			QTimer.singleShot(100,A.open_settings);return
		if C==_G:
			D=get_current_wifi_ssid()
			if D:A.selected_wifi_ssid=D;A.save_last_wifi(D)
			if'successfully'in B:A.tray.showMessage(_F,B,A.icon,3000)
			if not getattr(A,'has_checked_for_updates',_A):A.has_checked_for_updates=_B;QTimer.singleShot(3500,lambda:A.check_for_updates(_B))
		elif C==_M:A.tray.showMessage(_F,B,A.icon,3000)
	def trigger_performance_mode(A,checked=_A):
		B=checked
		if hasattr(A,_w)and A.perf_thread.isRunning():return
		if hasattr(A,_H)and A.worker:A.worker.is_paused=_B;A.pause_action.setText(_c);A.tray.setToolTip('Loqin - Paused (Optimizing Network)')
		if B:A.tray.setIcon(A.perf_icon);A.icon=A.perf_icon
		else:A.tray.setIcon(A.default_icon);A.icon=A.default_icon
		A.perf_thread=PerformanceModeThread(use_best=B);A.perf_thread.status_signal.connect(A.handle_perf_status);A.perf_thread.start()
	def handle_perf_status(A,message,color_type):
		C=color_type;B=message;A.status_action.setText(f"Status: {B}");A.status_action.setIcon(create_status_icon(C));A.tray.showMessage(_t,B,A.icon,4000)
		if B!=_d:
			A.just_optimized=_B
			if hasattr(A,_H)and A.worker:
				A.worker.is_paused=_A;A.pause_action.setText(_b)
				if'OFF'in B:A.tray.setToolTip(_v)
				else:A.tray.setToolTip('Loqin - Active (Performance Mode)')
			if C in[_G,_D]:QTimer.singleShot(1000,A.trigger_manual_check)
	def handle_account_url(A,url):A.current_account_url=url;print(url);A.account_action.setEnabled(_B)
	def show_account_details(A):
		if not hasattr(A,'current_account_url'):return
		H=A.config.get(_J);A.account_dialog=AccountDetailsDialog(H,A.current_account_url);A.account_dialog.show();QApplication.processEvents()
		try:
			I=requests.get(A.current_account_url,timeout=5);D=BeautifulSoup(I.text,'html.parser');E=[];J=D.find_all('tr',attrs={'bgcolor':['#DDDDDD','#F3F3F3']})
			for C in J:
				B=[A.text.strip()for A in C.find_all('td')]
				if len(B)==7:E.append(B)
			F=[];G=D.find(string=lambda text:text and _m in text)
			if G:C=G.find_parent('tr');B=[A.text.strip()for A in C.find_all('td')];F=B[1:]
			A.account_dialog.populate_table(E,F)
		except Exception as K:print(f"Failed to scrape account history table: {K}")
	def check_for_updates(A,silent=_A):
		B=silent
		if hasattr(A,_x)and A.update_checker and A.update_checker.isRunning():return
		if not B:A.update_action.setText('Checking for updates...');A.update_action.setEnabled(_A)
		A.update_checker=UpdateChecker();A.update_checker.update_found.connect(A.prompt_update)
		if not B:A.update_checker.no_update_found.connect(A.prompt_no_update);A.update_checker.finished.connect(lambda:A.update_action.setText(_u));A.update_checker.finished.connect(lambda:A.update_action.setEnabled(_B))
		A.update_checker.start()
	def prompt_no_update(A):QMessageBox.information(_C,'Up to Date',f"You are already running the latest version of Loqin (v{APP_VERSION}).\nNo new updates were found :P")
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
		A.timer=QTimer(A.app);A.timer.timeout.connect(A.trigger_manual_check);A.timer.start(A.config.get(_R,10)*1000)
		if not A.waiting_for_wifi_choice:A.trigger_manual_check()
	def save_last_wifi(B,ssid):
		A=ssid;A=(A or'').strip()
		if not A:return
		B.config[_S]=A;ConfigManager.save_config(B.config)
	def auto_connect_last_wifi(A):
		'Use the last successfully connected Wi-Fi automatically.';B=(A.config.get(_S)or'').strip()
		if not B:A.open_wifi_picker();return
		if get_current_wifi_ssid().lower()==B.lower():A.on_wifi_connection_success(B,automatic=_B);return
		A.status_action.setText(f"Status: Connecting to {B}...");A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip(f"Loqin - Connecting to {B}");A.connect_to_wifi(B,automatic=_B)
	def connect_to_wifi(A,ssid,automatic=_A):
		'Connect to a Windows-saved Wi-Fi profile without blocking the UI.';C=automatic;B=ssid
		if A.wifi_connect_thread and A.wifi_connect_thread.isRunning():return
		A.selected_wifi_ssid=B;A.status_action.setText(f"Status: {"Connecting to your last Wi-Fi"if C else f"Connecting to {B}"}...");A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip(f"Loqin - Connecting to {B}");A.wifi_connect_thread=WiFiConnectThread(B);A.wifi_connect_thread.connected.connect(lambda connected_ssid:A.on_wifi_connection_success(connected_ssid,C));A.wifi_connect_thread.failed.connect(lambda error:A.on_wifi_connection_failed(B,error));A.wifi_connect_thread.finished.connect(A._cleanup_wifi_connect_thread);A.wifi_connect_thread.start()
	def _cleanup_wifi_connect_thread(A):A.wifi_connect_thread=_C
	def on_wifi_connection_success(A,ssid,automatic=_A):
		B=ssid;A.selected_wifi_ssid=B;A.waiting_for_wifi_choice=_A;A.save_last_wifi(B);A.status_action.setText(f"Status: Wi-Fi connected ({B})");A.status_action.setIcon(create_status_icon(_G));A.tray.setToolTip(f"Loqin - Active")
		if A.wifi_picker and A.wifi_picker.isVisible():A.wifi_picker.close()
		A.start_monitoring_timer()
	def on_wifi_connection_failed(A,ssid,error):print(f"Could not connect to {ssid}: {error}");A.waiting_for_wifi_choice=_B;A.status_action.setText(_y);A.status_action.setIcon(create_status_icon(_D));A.tray.setToolTip(_z);A.open_wifi_picker()
	def force_logout(B):
		try:requests.get('http://phc.prontonetworks.com/cgi-bin/authlogout',timeout=3);print('Successfully dropped existing Wi-Fi session.')
		except Exception as A:print(f"Logout check bypassed (likely not connected): {A}")
	def open_wifi_picker(A):
		if A.wifi_picker is _C:A.wifi_picker=WiFiPickerDialog();A.wifi_picker.wifi_chosen.connect(A.on_wifi_chosen);A.wifi_picker.finished.connect(A.wifi_picker.scan_thread.exit)
		else:A.wifi_picker.is_connecting=_A;A.wifi_picker.scan_networks()
		A.wifi_picker.show();A.wifi_picker.raise_();A.wifi_picker.activateWindow()
	def on_wifi_chosen(B,ssid):A=ssid;print(f"Wi-Fi selection changed via picker to: {A}");B.save_last_wifi(A);B.connect_to_wifi(A,automatic=_A)
	def connect_and_relogin(A,ssid):B=ssid;A.tray.setToolTip(f"Loqin - Connecting to {B}...");A.status_action.setText(f"Connecting to {B}...");A.connect_to_wifi(B,automatic=_A);QTimer.singleShot(4000,A.force_logout_and_relogin)
	def force_logout_and_relogin(A):print('Resetting portal session and logging in...');A.tray.setToolTip('Loqin - Re-logging in...');A.status_action.setText('Logging in...');A.force_logout();QTimer.singleShot(1000,A.trigger_manual_check)
	def run(A):sys.exit(A.app.exec())
if __name__=='__main__':
	mutex_handle=ensure_single_instance()
	if sys.platform==_L:
		try:myappid=_F;ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
		except Exception as e:print(f"Failed to set AppUserModelID: {e}")
	app=LoqinTrayApp();app.run()