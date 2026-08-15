_o='update_checker'
_n='perf_thread'
_m='Loqin - Active'
_l='Check for Updates'
_k='Performance Mode'
_j='#FF69B4'
_i='#3da5ff'
_h='#171A22'
_g='Loqin • Live Network Monitor'
_f='Missing credentials'
_e='OFFLINE'
_d='Referer'
_c='Grand Total'
_b='https://hostelwifi.vit.ac.in/index.php?a=add&category=4'
_a='Forgot Password?'
_Z='\n            QPushButton {\n                background: #1E222D; \n                color: #BBBBBB; \n                border: 1px solid #2C313E; \n                border-radius: 4px; \n                font-size: 14px;\n            }\n            QPushButton:checked {\n                background: #3da5ff; \n                color: #171A22; \n                border: 1px solid #3da5ff;\n            }\n            QPushButton:hover {\n                border: 1px solid #3da5ff;\n            }\n        '
_Y='Download'
_X='Upload'
_W='ignore'
_V='interfaces'
_U='Optimizing Network...'
_T='Resume Loqin'
_S='Pause Loqin'
_R='Show Speed Graph'
_Q='ONLINE'
_P='interval'
_O='#2ecc71'
_N='BSSID'
_M='win32'
_L='loqin_logo_small.png'
_K='error'
_J='password'
_I='username'
_H='yellow'
_G='green'
_F='worker'
_E='Loqin'
_D=':'
_C=None
_B=True
_A=False
import sys,json,os,time,requests,keyring,psutil,subprocess,pyqtgraph as pg,re,ctypes,ctypes.wintypes,pywifi
from pywifi import const
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from PyQt6.QtWidgets import QApplication,QSystemTrayIcon,QMenu,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QSpinBox,QCheckBox,QMessageBox,QDialog,QVBoxLayout,QLabel,QProgressDialog,QDialog,QVBoxLayout,QTextBrowser,QDialogButtonBox,QTableWidget,QHeaderView,QTableWidgetItem,QAbstractItemView,QTabWidget,QWidget,QFormLayout
from PyQt6.QtGui import QIcon,QAction,QPixmap,QColor,QPainter,QDesktopServices,QCursor
from PyQt6.QtCore import QThread,pyqtSignal,Qt,QTimer,QUrl,QAbstractNativeEventFilter
APP_NAME=_E
APPDATA_DIR=os.path.join(os.getenv('APPDATA',os.path.expanduser('~')),_E)
CONFIG_FILE=os.path.join(APPDATA_DIR,'Loqin_config.json')
APP_VERSION='1.5.0'
GITHUB_API_URL='https://api.github.com/repos/notaayushsrivastava/loqin/releases/latest'
REG_PATH='Software\\Microsoft\\Windows\\CurrentVersion\\Run'
APP_REG_NAME=_E
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
	if sys.platform!=_M:return
	import winreg as A
	try:
		B=A.OpenKey(A.HKEY_CURRENT_USER,REG_PATH,0,A.KEY_ALL_ACCESS)
		if enabled:
			if getattr(sys,'frozen',_A):C=f'"{sys.executable}"'
			else:C=f'"{sys.executable}" "{os.path.abspath(__file__)}"'
			A.SetValueEx(B,APP_REG_NAME,0,A.REG_SZ,C)
		else:
			try:A.DeleteValue(B,APP_REG_NAME)
			except OSError:pass
		A.CloseKey(B)
	except Exception as D:print(f"Failed to update registry: {D}")
def is_auto_start_enabled():
	'Check if the registry key currently exists.'
	if sys.platform!=_M:return _A
	import winreg as A
	try:B=A.OpenKey(A.HKEY_CURRENT_USER,REG_PATH,0,A.KEY_READ);A.QueryValueEx(B,APP_REG_NAME);A.CloseKey(B);return _B
	except OSError:return _A
	except Exception as C:print(f"Failed to read registry: {C}");return _A
def resource_path(relative_path):
	'Get absolute path to resource, works for dev and PyInstaller'
	try:A=sys._MEIPASS
	except Exception:A=os.path.abspath('.')
	return os.path.join(A,'assets',relative_path)
def create_status_icon(color_type):
	'Generates a smooth colored circle icon (Green, Yellow, Red) for status indicators.';C=color_type;B=QPixmap(16,16);B.fill(Qt.GlobalColor.transparent);A=QPainter(B);A.setRenderHint(QPainter.RenderHint.Antialiasing)
	if C==_G:A.setBrush(QColor(46,204,113))
	elif C==_H:A.setBrush(QColor(241,196,15))
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
				if hasattr(A.tray_app,_F)and A.tray_app.worker:A.tray_app.worker.is_paused=_B
				A.tray_app.force_logout()
			elif B.wParam==PBT_APMRESUMEAUTOMATIC:
				if hasattr(A.tray_app,_F)and A.tray_app.worker:A.tray_app.worker.is_paused=_A
				A.tray_app.has_checked_for_updates=_A
				if hasattr(A.tray_app,'perf_action')and A.tray_app.perf_action.isChecked():A.tray_app.trigger_performance_mode(checked=_B)
		return _A,0
class PerformanceModeThread(QThread):
	status_signal=pyqtSignal(str,str)
	def __init__(A,use_best=_B):super().__init__();A.use_best=use_best
	def run(A):
		J='Performance Mode ON';K=_U if A.use_best else'Reverting Network...';A.status_signal.emit(K,_H)
		try:
			L=pywifi.PyWiFi();B=L.interfaces()[0];B.scan();A.sleep(4);M=B.scan_results();E=[A for A in M if'VIT'in(A.ssid or'').upper()]
			if not E:A.status_signal.emit('No VIT networks found in range.',_K);return
			E.sort(key=lambda x:x.signal,reverse=A.use_best);D=E[0]
			if not A.use_best:B.disconnect();A.sleep(1);C=pywifi.Profile();C.ssid=D.ssid;C.bssid=D.bssid;C.auth=const.AUTH_ALG_OPEN;C.akm.append(const.AKM_TYPE_NONE);B.remove_all_network_profiles();N=B.add_network_profile(C);B.connect(N);A.sleep(3);A.status_signal.emit('Performance Mode OFF',_G);return
			F=_C
			try:
				O=subprocess.check_output(['netsh','wlan','show',_V],creationflags=134217728).decode('utf-8',errors=_W)
				for G in O.split('\n'):
					if _N in G and _N==G.split(_D)[0].strip():
						I=G.split(_D)
						if len(I)>=4:F=_D.join(I[1:]).strip().lower().replace('-',_D);break
			except Exception as H:print(f"Could not get current BSSID: {H}")
			P=D.bssid.strip().lower().replace('-',_D)if D.bssid else''
			if F and F==P:A.status_signal.emit(J,_G)
			else:A.status_signal.emit(J,_H)
		except Exception as H:A.status_signal.emit(f"Wi-Fi Error: {str(H)}",_K)
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
	def __init__(A,username,account_url,parent=_C):super().__init__(parent);A.username=username;A.account_url=account_url;A.setWindowTitle('Loqin • Account Management');A.setWindowIcon(QIcon(resource_path(_L)));A.resize(750,450);A.setStyleSheet('\n            QDialog { \n                background-color: #171A22; \n            }\n            QLabel {\n                color: #FFFFFF;\n                font-size: 14px;\n            }\n            /* Table Styling */\n            QTableWidget {\n                background-color: #1E222D;\n                color: #DDDDDD;\n                gridline-color: #2C313E;\n                border: 1px solid #2C313E;\n                border-radius: 8px;\n                font-size: 12px;\n            }\n            QHeaderView::section {\n                background-color: #171A22;\n                color: #3da5ff;\n                font-weight: bold;\n                padding: 6px;\n                border: 1px solid #2C313E;\n            }\n            QTableWidget::item { padding: 4px; }\n            \n            /* Tab Styling */\n            QTabWidget::pane { border: 1px solid #2C313E; border-radius: 4px; }\n            QTabBar::tab {\n                background: #1E222D; color: #BBBBBB; padding: 10px 20px; \n                border: 1px solid #2C313E; border-bottom: none; \n                border-top-left-radius: 4px; border-top-right-radius: 4px;\n            }\n            QTabBar::tab:selected { background: #171A22; color: #3da5ff; font-weight: bold; }\n            \n            /* Form Styling */\n            QLineEdit {\n                background: #1E222D; color: #FFF; border: 1px solid #2C313E; \n                border-radius: 4px; padding: 6px; font-size: 14px;\n            }\n            QPushButton {\n                background: #3da5ff; color: #171A22; font-weight: bold; \n                border-radius: 4px; padding: 8px; font-size: 14px;\n            }\n            QPushButton:hover { background: #2b8ee0; }\n        ');B=QVBoxLayout(A);A.tabs=QTabWidget(A);B.addWidget(A.tabs);A.setup_history_tab();A.setup_password_tab()
	def setup_history_tab(A):A.history_tab=QWidget();B=QVBoxLayout(A.history_tab);C=QLabel('<b>Recent Network Sessions</b>');C.setStyleSheet('font-size: 16px; margin-bottom: 5px;');B.addWidget(C);A.table=QTableWidget();A.table.setColumnCount(7);A.table.setHorizontalHeaderLabels(['Location','Login Time','Logout Time','Usage Time',_X,_Y,'Total Data']);A.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);D=A.table.horizontalHeader();D.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);D.setStretchLastSection(_B);A.table.verticalHeader().setVisible(_A);B.addWidget(A.table);A.tabs.addTab(A.history_tab,'Usage History')
	def create_password_field(F):
		D=QWidget();C=QHBoxLayout(D);C.setContentsMargins(0,0,0,0);C.setSpacing(5);B=QLineEdit();B.setEchoMode(QLineEdit.EchoMode.Password);B.setFixedWidth(250);A=QPushButton('👁');A.setFixedSize(32,32);A.setCursor(Qt.CursorShape.PointingHandCursor);A.setCheckable(_B);A.setStyleSheet(_Z)
		def E(checked):
			if checked:B.setEchoMode(QLineEdit.EchoMode.Normal);A.setText('🔒')
			else:B.setEchoMode(QLineEdit.EchoMode.Password);A.setText('👁')
		A.toggled.connect(E);C.addWidget(B);C.addWidget(A);return D,B
	def setup_password_tab(A):A.password_tab=QWidget();C=QVBoxLayout(A.password_tab);F=QLabel('<b>Reset Network Password</b>');F.setStyleSheet('font-size: 16px; margin-bottom: 10px;');C.addWidget(F);B=QFormLayout();B.setLabelAlignment(Qt.AlignmentFlag.AlignRight);B.setFormAlignment(Qt.AlignmentFlag.AlignTop);B.setSpacing(15);G,A.old_pw_input=A.create_password_field();H,A.new_pw_input=A.create_password_field();I,A.confirm_pw_input=A.create_password_field();B.addRow('Current Password:',G);B.addRow('New Password:',H);B.addRow('Confirm Password:',I);C.addLayout(B);D=QPushButton(_a);D.setFixedWidth(287);D.setCursor(Qt.CursorShape.PointingHandCursor);D.setStyleSheet('\n            QPushButton {\n                background: transparent;\n                color: #3da5ff;\n                border: none;\n                font-size: 13px;\n                text-align: left;\n                padding-left: 0px;\n            }\n            QPushButton:hover {\n                text-decoration: underline;\n                color: #5bb3ff;\n            }\n        ');D.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(_b)));A.update_btn=QPushButton('Update Password');A.update_btn.setFixedWidth(287);A.update_btn.clicked.connect(A.submit_password_change);E=QVBoxLayout();E.setSpacing(6);E.addWidget(A.update_btn);E.addWidget(D);E.setContentsMargins(120,10,0,0);C.addLayout(E);A.status_label=QLabel('');A.status_label.setStyleSheet('margin-left: 120px;');C.addWidget(A.status_label);C.addStretch();A.tabs.addTab(A.password_tab,'Change Password')
	def populate_table(A,rows_data,grand_total_data):
		F=grand_total_data;A.table.setRowCount(0)
		for(G,H)in enumerate(rows_data):
			A.table.insertRow(G)
			for(I,D)in enumerate(H):B=QTableWidgetItem(D);B.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(G,I,B)
		if F:
			C=A.table.rowCount();A.table.insertRow(C);E=QTableWidgetItem(_c);E.setForeground(QColor(_O));E.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(C,0,E)
			for(J,D)in enumerate(F):B=QTableWidgetItem(D);B.setForeground(QColor(_O));B.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(C,J+3,B)
			A.table.setSpan(C,0,1,3)
	def submit_password_change(A):
		E='color: #e74c3c; margin-left: 120px;';F=A.old_pw_input.text();B=A.new_pw_input.text();C=A.confirm_pw_input.text()
		if not F or not B or not C:A.status_label.setStyleSheet('color: #f1c40f; margin-left: 120px;');A.status_label.setText('Warning: Please fill all fields.');return
		if B!=C:A.status_label.setStyleSheet(E);A.status_label.setText('Error: New passwords do not match.');return
		A.status_label.setStyleSheet('color: #3da5ff; margin-left: 120px;');A.status_label.setText('Updating password...');A.update_btn.setEnabled(_A);QApplication.processEvents()
		try:
			G=urlparse(A.account_url);D=f"{G.scheme}://{G.netloc}";H=requests.Session();H.get(f"{D}/registration/main.do?content_key=%2FChangePassword.jsp",timeout=5);J={'changeUserId':A.username,'changePassword':F,'changeNewPassword':B,'changeConfirmNewPassword':C,'submit':'Update'};K={_d:f"{D}/registration/main.do?content_key=%2FChangePassword.jsp"};I=H.post(f"{D}/registration/changePassword.do",data=J,headers=K,timeout=5)
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
		A={_I:'',_P:10,'auto_connect':_B};ConfigManager.ensure_dir_exists();B=_A
		if os.path.exists(CONFIG_FILE):
			try:
				with open(CONFIG_FILE,'r')as E:
					C=json.load(E);A.update(C)
					if _J in C:
						D=C[_J]
						if D and A[_I]:ConfigManager.set_password(A[_I],D)
						if _J in A:del A[_J]
						B=_B
			except Exception:pass
		else:B=_B
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
	def __init__(A,config):super().__init__();A.config=config;A.is_running=_B;A.is_paused=_A
	def check_network_state(B):
		try:
			A=requests.get('http://clients3.google.com/generate_204',timeout=3,allow_redirects=_A)
			if A.status_code==204:return _Q
			else:return'PORTAL'
		except requests.exceptions.RequestException:return _e
	def run(A):
		while A.is_running:
			if A.is_paused:A.sleep(1);continue
			B=A.config.get(_I);C=ConfigManager.get_password(B)
			if not B or not C:A.status_signal.emit(_f,_K);return
			D=A.check_network_state()
			if D==_Q:A.status_signal.emit('Connected',_G);return
			elif D==_e:A.status_signal.emit('Waiting for Wi-Fi...',_H);return
			A.status_signal.emit('Portal detected. Authenticating...',_H);A.login(B,C);return
	def toggle_pause(A):A.is_paused=not A.is_paused;return A.is_paused
	def login(A,username,password):
		B='http://phc.prontonetworks.com';D=f"{B}/cgi-bin/authlogin?URI=http://example.com";E={'userId':username,_J:password,'serviceName':'ProntoAuthentication','URI':'http://example.com'};F={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Content-Type':'application/x-www-form-urlencoded','Origin':B,_d:f"{B}/cgi-bin/authlogin?URI=http://www.msftconnecttest.com/redirect"}
		try:
			G=requests.post(D,data=E,headers=F,timeout=5)
			if A.check_network_state()==_Q:
				A.status_signal.emit('Logged in successfully!',_G);H=G.text;C=re.search('href="(http://([0-9\\.]+)/registration/Main\\.jsp\\?sessionId=[^"]+)"',H)
				if C:I=C.group(1);J=C.group(2);print(f"Extracted IP: {J}");A.account_data_signal.emit(I)
				else:print('Could not find the account link in the response HTML.')
			else:A.status_signal.emit('Login failed. Check credentials.',_K)
		except Exception as K:print(K);A.status_signal.emit('Portal timeout or error.',_K)
class SpeedGraphDialog(QDialog):
	def __init__(A,parent=_C):I='#777';F='bottom';E='left';D='#BBBBBB';super().__init__(parent);A.setWindowTitle(_g);A.setWindowIcon(QIcon(resource_path(_L)));A.resize(720,420);A.download_history=[0]*60;A.upload_history=[0]*60;C=QVBoxLayout(A);C.setContentsMargins(15,15,15,15);B=QHBoxLayout();G=QLabel('Real-Time Network Usage');G.setStyleSheet('\n            QLabel{\n                color:white;\n                font-size:18px;\n                font-weight:600;\n            }\n        ');A.pin_checkbox=QCheckBox('Always on Top');A.pin_checkbox.setCursor(Qt.CursorShape.PointingHandCursor);A.pin_checkbox.setStyleSheet('\n            QCheckBox {\n                color: #BBBBBB;\n                font-size: 13px;\n                font-weight: 500;\n            }\n            QCheckBox::indicator {\n                width: 14px;\n                height: 14px;\n                border: 1px solid #777777;\n                border-radius: 3px;\n                background: #171A22;\n            }\n            QCheckBox::indicator:checked {\n                background: #3da5ff;\n                border: 1px solid #3da5ff;\n            }\n            QCheckBox:hover {\n                color: #FFFFFF;\n            }\n        ');A.pin_checkbox.toggled.connect(A.toggle_always_on_top);A.secret_code='nyan';A.code_index=0;A.nyan_mode=_A;B.addStretch();B.addWidget(G);B.addStretch();B.addWidget(A.pin_checkbox);C.addLayout(B);A.graph=pg.PlotWidget();C.addWidget(A.graph);A.stats=QLabel();A.stats.setAlignment(Qt.AlignmentFlag.AlignCenter);A.stats.setStyleSheet('\n            QLabel{\n                color:#cccccc;\n                font-size:13px;\n            }\n        ');C.addWidget(A.stats);A.setStyleSheet('\n            QDialog{\n                background:#171A22;\n            }\n        ');A.graph.setBackground(_h);A.graph.showGrid(x=_B,y=_B,alpha=.25);A.graph.hideButtons();A.graph.setMouseEnabled(_A,_A);A.graph.setMenuEnabled(_A);A.graph.setClipToView(_B);A.graph.setDownsampling(mode='peak');A.graph.setLabel(E,'Speed (KB/s)',color=D);A.graph.setLabel(F,'Time',color=D);A.graph.getAxis(E).setPen(pg.mkPen(I));A.graph.getAxis(F).setPen(pg.mkPen(I));A.graph.getAxis(E).setTextPen(D);A.graph.getAxis(F).setTextPen(D);A.graph.setYRange(0,100);A.download_curve=A.graph.plot(pen=pg.mkPen(_i,width=3),name=_Y);A.upload_curve=A.graph.plot(pen=pg.mkPen(_O,width=3),name=_X);H=A.graph.addLegend();H.setBrush(pg.mkBrush(30,30,30,200));H.setOffset((15,15))
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
		A.fillRect(12,9,14,14,QColor('#FFD1DC'));A.fillRect(13,10,12,12,QColor(_j));A.fillRect(15,12,2,2,QColor(C));A.fillRect(20,15,2,2,QColor(C));A.fillRect(16,18,2,2,QColor(C));A.fillRect(22,13,9,8,QColor(D));A.fillRect(23,10,2,3,QColor(D));A.fillRect(28,10,2,3,QColor(D));A.fillRect(24,15,2,2,QColor(E));A.fillRect(28,15,2,2,QColor(E));A.fillRect(26,18,2,1,QColor('#FFB6C1'));A.end();return QCursor(B,26,15)
	def toggle_nyan_mode(A):
		A.nyan_mode=not A.nyan_mode
		if A.nyan_mode:A.setWindowTitle('Loqin • Nyan Cat Mode!');A.setCursor(A.generate_nyan_cursor());A.graph.setBackground('#0F051D');A.download_curve.setPen(pg.mkPen(_j,width=3));A.upload_curve.setPen(pg.mkPen('#00FFFF',width=3));A.stats.setStyleSheet('\n                QLabel{ color:#FFD1DC; font-size:13px; font-weight: bold; }\n            ')
		else:A.setWindowTitle(_g);A.unsetCursor();A.graph.setBackground(_h);A.download_curve.setPen(pg.mkPen(_i,width=3));A.upload_curve.setPen(pg.mkPen(_O,width=3));A.stats.setStyleSheet('\n                QLabel{ color:#cccccc; font-size:13px; }\n            ')
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
	def __init__(A,parent=_C):super().__init__(parent);A.setWindowTitle('Loqin for PC - Settings');A.setFixedSize(410,270);A.setWindowIcon(QIcon(resource_path(_L)));A.config=ConfigManager.load_config();A.init_ui()
	def create_password_field(F):
		D=QWidget();C=QHBoxLayout(D);C.setContentsMargins(0,0,0,0);C.setSpacing(5);B=QLineEdit();B.setEchoMode(QLineEdit.EchoMode.Password);A=QPushButton('👁');A.setFixedSize(32,32);A.setCursor(Qt.CursorShape.PointingHandCursor);A.setCheckable(_B);A.setStyleSheet(_Z)
		def E(checked):
			if checked:B.setEchoMode(QLineEdit.EchoMode.Normal);A.setText('🔒')
			else:B.setEchoMode(QLineEdit.EchoMode.Password);A.setText('👁')
		A.toggled.connect(E);C.addWidget(B);C.addWidget(A);return D,B
	def init_ui(A):B=QVBoxLayout();B.setSpacing(4);B.setContentsMargins(15,15,15,15);B.setAlignment(Qt.AlignmentFlag.AlignTop);D=QLabel();F=QPixmap(resource_path(_L));G=F.scaled(32,32,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation);D.setPixmap(G);D.setAlignment(Qt.AlignmentFlag.AlignCenter);B.addWidget(D);B.addWidget(QLabel('Registration Number / Username:'));A.user_input=QLineEdit(A.config.get(_I,''));B.addWidget(A.user_input);B.addWidget(QLabel('Password:'));H,A.pass_input=A.create_password_field();A.pass_input.setText(ConfigManager.get_password(A.user_input.text()));B.addWidget(H);C=QPushButton(_a);C.setCursor(Qt.CursorShape.PointingHandCursor);C.setStyleSheet('\n            QPushButton {\n                background: transparent;\n                color: #3da5ff;\n                border: none;\n                font-size: 12px;\n                text-align: left;\n                padding-left: 2px;\n                margin-top: 2px;\n                margin-bottom: 6px;\n            }\n            QPushButton:hover {\n                text-decoration: underline;\n                color: #5bb3ff;\n            }\n        ');C.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(_b)));B.addWidget(C);E=QHBoxLayout();E.addWidget(QLabel('Check Frequency (seconds):'));A.interval_input=QSpinBox();A.interval_input.setRange(5,300);A.interval_input.setValue(A.config.get(_P,10));E.addWidget(A.interval_input);B.addLayout(E);A.startup_cb=QCheckBox('Launch automatically on Windows startup');A.startup_cb.setChecked(is_auto_start_enabled());B.addWidget(A.startup_cb);A.save_btn=QPushButton('Save and Apply');A.save_btn.clicked.connect(A.save_settings);B.addWidget(A.save_btn);B.addStretch();A.setLayout(B)
	def save_settings(A):
		B=A.user_input.text().strip();C=A.pass_input.text().strip()
		if not B or not C:QMessageBox.warning(A,'Warning','Username and Password cannot be empty.');return
		set_auto_start(A.startup_cb.isChecked());A.config[_I]=B;A.config[_P]=A.interval_input.value();ConfigManager.save_config(A.config);ConfigManager.set_password(B,C);QMessageBox.information(A,'Success','Settings saved successfully!');A.accept()
class LoqinTrayApp:
	def __init__(A):A.app=QApplication(sys.argv);A.app.setApplicationName(_E);A.app.setQuitOnLastWindowClosed(_A);A.power_filter=PowerEventFilter(A);A.app.installNativeEventFilter(A.power_filter);A.default_icon=QIcon(resource_path(_L));A.perf_icon=QIcon(resource_path('loqin_logo_performance.png'));A.icon=A.default_icon;A.tray=QSystemTrayIcon();A.tray.setIcon(A.default_icon);A.tray.setVisible(_B);A.tray.showMessage(_E,'Loqin has started! Monitoring your connection in the background.',A.icon,3000);A.config=ConfigManager.load_config();A.last_net_io=psutil.net_io_counters();A.last_time=time.time();A.graph_dialog=_C;A.build_menu();A.worker=_C;A.start_monitoring_timer();A.force_logout();A.speed_timer=QTimer();A.speed_timer.timeout.connect(A.update_bandwidth_meters);A.speed_timer.start(1000);A.has_checked_for_updates=_A
	def build_menu(A):A.menu=QMenu();A.status_action=QAction('Status: Initializing...',A.menu);A.status_action.setIcon(create_status_icon(_H));A.status_action.setEnabled(_B);A.menu.addAction(A.status_action);A.menu.addSeparator();A.speed_action=QAction('Speed: ↓ 0 KB/s  ↑ 0 KB/s',A.menu);A.speed_action.setEnabled(_A);A.menu.addAction(A.speed_action);A.graph_action=QAction(_R,A.menu);A.graph_action.triggered.connect(A.toggle_speed_graph);A.menu.addAction(A.graph_action);A.menu.addSeparator();C=QAction('Connect Now',A.menu);C.triggered.connect(A.trigger_manual_check);A.menu.addAction(C);A.pause_action=QAction(_S,A.menu);A.pause_action.triggered.connect(A.toggle_service_pause);A.menu.addAction(A.pause_action);A.perf_action=QAction(_k,A.menu);A.perf_action.setCheckable(_B);A.perf_action.setChecked(_A);A.perf_action.triggered.connect(A.trigger_performance_mode);A.menu.addAction(A.perf_action);A.menu.addSeparator();A.account_action=QAction('View Account Details',A.menu);A.account_action.setEnabled(_A);A.account_action.triggered.connect(A.show_account_details);A.menu.addAction(A.account_action);A.update_action=QAction(_l,A.menu);A.update_action.triggered.connect(A.check_for_updates);A.menu.addAction(A.update_action);D=QAction('Configure Settings',A.menu);D.triggered.connect(A.open_settings);A.menu.addAction(D);A.menu.addSeparator();B=A.menu.addMenu('Help');E=QAction('How to use',A.menu);E.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin#readme')));B.addAction(E);F=QAction('GitHub Releases',A.menu);F.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin/releases')));B.addAction(F);G=QAction('Bug Report',A.menu);G.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin/issues')));B.addAction(G);A.menu.addSeparator();H=QAction('Exit Loqin',A.menu);H.triggered.connect(A.close_app);A.menu.addAction(H);A.tray.setContextMenu(A.menu);A.tray.activated.connect(A.on_tray_icon_activated);A.tray.setToolTip('Loqin PC')
	def on_tray_icon_activated(B,reason):
		'Handles clicks on the system tray icon.'
		if reason==QSystemTrayIcon.ActivationReason.Trigger:
			A=B.tray.contextMenu()
			if A is not _C:A.exec(QCursor.pos())
	def toggle_service_pause(A):
		if hasattr(A,_F)and A.worker:
			B=A.worker.toggle_pause()
			if B:A.pause_action.setText(_T);A.tray.setToolTip('Loqin - Paused')
			else:A.pause_action.setText(_S);A.tray.setToolTip(_m)
	def close_app(A):
		try:requests.get('http://phc.prontonetworks.com/cgi-bin/authlogout/',timeout=2)
		except Exception:pass
		if hasattr(A,_F)and A.worker and A.worker.isRunning():A.worker.is_running=_A;A.worker.quit();A.worker.wait()
		if hasattr(A,_n)and A.perf_thread and A.perf_thread.isRunning():A.perf_thread.quit();A.perf_thread.wait()
		if hasattr(A,_o)and A.update_checker and A.update_checker.isRunning():A.update_checker.quit();A.update_checker.wait()
		A.app.quit()
	def update_bandwidth_meters(A):
		D=psutil.net_io_counters();F=time.time();E=F-A.last_time
		if E>0:
			B=(D.bytes_recv-A.last_net_io.bytes_recv)/E;C=(D.bytes_sent-A.last_net_io.bytes_sent)/E;A.last_net_io=D;A.last_time=F;G=f"{B/1024:.1f} KB/s"if B<1048576 else f"{B/1048576:.1f} MB/s";H=f"{C/1024:.1f} KB/s"if C<1048576 else f"{C/1048576:.1f} MB/s";A.speed_action.setText(f"Speed: ↓ {G}  ↑ {H}")
			if A.graph_dialog and A.graph_dialog.isVisible():A.graph_dialog.update_data(B,C)
	def toggle_speed_graph(A):
		B='Hide Speed Graph'
		if not A.graph_dialog:A.graph_dialog=SpeedGraphDialog();A.graph_dialog.finished.connect(lambda:A.graph_action.setText(_R))
		if A.graph_dialog.isVisible():
			if not A.graph_dialog.isActiveWindow():A.graph_dialog.showNormal();A.graph_dialog.raise_();A.graph_dialog.activateWindow();A.graph_action.setText(B)
			else:A.graph_dialog.hide();A.graph_action.setText(_R)
		else:A.graph_dialog.showNormal();A.graph_dialog.raise_();A.graph_dialog.activateWindow();A.graph_action.setText(B)
	def open_settings(A):
		if hasattr(A,'settings_dialog')and A.settings_dialog is not _C:
			if A.settings_dialog.isVisible():A.settings_dialog.showNormal();A.settings_dialog.raise_();A.settings_dialog.activateWindow();return
		A.settings_dialog=SettingsDialog()
		if A.settings_dialog.exec():A.config=ConfigManager.load_config();A.start_monitoring_timer()
		A.settings_dialog=_C
	def trigger_manual_check(A):
		if hasattr(A,_F)and A.worker and A.worker.isRunning():return
		B=_C
		try:
			E=subprocess.check_output(['netsh','wlan','show',_V],creationflags=134217728).decode('utf-8',errors=_W)
			for C in E.split('\n'):
				if _N in C and _N==C.split(_D)[0].strip():
					D=C.split(_D)
					if len(D)>=4:B=_D.join(D[1:]).strip().lower().replace('-',_D);break
		except Exception:pass
		if not hasattr(A,'last_bssid'):A.last_bssid=B
		if B and B!=A.last_bssid:
			A.last_bssid=B
			if A.perf_action.isChecked():
				if getattr(A,'just_optimized',_A):A.just_optimized=_A
				else:A.trigger_performance_mode(checked=_B);return
		A.last_bssid=B;A.just_optimized=_A;A.config=ConfigManager.load_config();A.worker=NetworkWorker(A.config);A.worker.status_signal.connect(A.handle_status);A.worker.account_data_signal.connect(A.handle_account_url);A.worker.start()
	def handle_status(A,message,color_type):
		C=color_type;B=message;A.status_action.setText(f"Status: {B}");A.status_action.setIcon(create_status_icon(C))
		if B==_f:
			if hasattr(A,_F)and A.worker:A.worker.is_paused=_B;A.pause_action.setText(_T);A.tray.setToolTip('Loqin - Paused (Missing Credentials)')
			QTimer.singleShot(100,A.open_settings);return
		if C==_G:
			if'successfully'in B:A.tray.showMessage(_E,B,A.icon,3000)
			if not getattr(A,'has_checked_for_updates',_A):A.has_checked_for_updates=_B;QTimer.singleShot(3500,lambda:A.check_for_updates(_B))
		elif C==_K:A.tray.showMessage(_E,B,A.icon,3000)
	def trigger_performance_mode(A,checked=_A):
		B=checked
		if hasattr(A,_n)and A.perf_thread.isRunning():return
		if hasattr(A,_F)and A.worker:A.worker.is_paused=_B;A.pause_action.setText(_T);A.tray.setToolTip('Loqin - Paused (Optimizing Network)')
		if B:A.tray.setIcon(A.perf_icon);A.icon=A.perf_icon
		else:A.tray.setIcon(A.default_icon);A.icon=A.default_icon
		A.perf_thread=PerformanceModeThread(use_best=B);A.perf_thread.status_signal.connect(A.handle_perf_status);A.perf_thread.start()
	def handle_perf_status(A,message,color_type):
		C=color_type;B=message;A.status_action.setText(f"Status: {B}");A.status_action.setIcon(create_status_icon(C));A.tray.showMessage(_k,B,A.icon,4000)
		if B!=_U:
			A.just_optimized=_B
			if hasattr(A,_F)and A.worker:
				A.worker.is_paused=_A;A.pause_action.setText(_S)
				if'OFF'in B:A.tray.setToolTip(_m)
				else:A.tray.setToolTip('Loqin - Active (Performance Mode)')
			if C in[_G,_H]:QTimer.singleShot(1000,A.trigger_manual_check)
	def handle_account_url(A,url):A.current_account_url=url;print(url);A.account_action.setEnabled(_B)
	def show_account_details(A):
		if not hasattr(A,'current_account_url'):return
		H=A.config.get(_I);A.account_dialog=AccountDetailsDialog(H,A.current_account_url);A.account_dialog.show();QApplication.processEvents()
		try:
			I=requests.get(A.current_account_url,timeout=5);D=BeautifulSoup(I.text,'html.parser');E=[];J=D.find_all('tr',attrs={'bgcolor':['#DDDDDD','#F3F3F3']})
			for C in J:
				B=[A.text.strip()for A in C.find_all('td')]
				if len(B)==7:E.append(B)
			F=[];G=D.find(string=lambda text:text and _c in text)
			if G:C=G.find_parent('tr');B=[A.text.strip()for A in C.find_all('td')];F=B[1:]
			A.account_dialog.populate_table(E,F)
		except Exception as K:print(f"Failed to scrape account history table: {K}")
	def check_for_updates(A,silent=_A):
		"\n        Checks for updates on GitHub.\n        :param silent: If True, suppresses the 'Up to Date' dialog when no new updates are found.\n        ";B=silent
		if hasattr(A,_o)and A.update_checker and A.update_checker.isRunning():return
		if not B:A.update_action.setText('Checking for updates...');A.update_action.setEnabled(_A)
		A.update_checker=UpdateChecker();A.update_checker.update_found.connect(A.prompt_update)
		if not B:A.update_checker.no_update_found.connect(A.prompt_no_update);A.update_checker.finished.connect(lambda:A.update_action.setText(_l));A.update_checker.finished.connect(lambda:A.update_action.setEnabled(_B))
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
			if sys.platform==_M:os.startfile(A)
			else:subprocess.Popen([A])
			B.app.quit()
		except Exception as C:QMessageBox.critical(_C,'Update Error',f"Failed to launch the installer:\n{str(C)}")
	def start_monitoring_timer(A):
		if hasattr(A,'timer')and A.timer:A.timer.stop()
		A.timer=QTimer();A.timer.timeout.connect(A.trigger_manual_check);A.timer.start(A.config.get(_P,10)*1000);A.trigger_manual_check()
	def force_logout(B):
		'Silently drops the Pronto Networks Wi-Fi session.'
		try:requests.get('http://phc.prontonetworks.com/cgi-bin/authlogout',timeout=3);print('Successfully dropped existing Wi-Fi session.')
		except Exception as A:print(f"Logout check bypassed (likely not connected): {A}")
	def run(A):sys.exit(A.app.exec())
if __name__=='__main__':
	mutex_handle=ensure_single_instance()
	if sys.platform==_M:
		try:myappid=_E;ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
		except Exception as e:print(f"Failed to set AppUserModelID: {e}")
	app=LoqinTrayApp();app.run()