_g='update_checker'
_f='perf_thread'
_e='Loqin - Active'
_d='Check for Updates'
_c='Performance Mode'
_b='Show Speed Graph'
_a='Missing credentials'
_Z='OFFLINE'
_Y='Referer'
_X='Grand Total'
_W='https://hostelwifi.vit.ac.in/index.php?a=add&category=4'
_V='Forgot Password?'
_U='\n            QPushButton {\n                background: #1E222D; \n                color: #BBBBBB; \n                border: 1px solid #2C313E; \n                border-radius: 4px; \n                font-size: 14px;\n            }\n            QPushButton:checked {\n                background: #3da5ff; \n                color: #171A22; \n                border: 1px solid #3da5ff;\n            }\n            QPushButton:hover {\n                border: 1px solid #3da5ff;\n            }\n        '
_T='Download'
_S='Upload'
_R='Optimizing Network...'
_Q='Resume Loqin'
_P='Pause Loqin'
_O='ONLINE'
_N='#2ecc71'
_M='interval'
_L='win32'
_K='loqin_logo_small.png'
_J='error'
_I='password'
_H='username'
_G='yellow'
_F='green'
_E='worker'
_D='Loqin'
_C=None
_B=False
_A=True
import sys,json,os,time,requests,keyring,psutil,subprocess,pyqtgraph as pg,re,ctypes,ctypes.wintypes,pywifi
from pywifi import const
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from PyQt6.QtWidgets import QApplication,QSystemTrayIcon,QMenu,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QSpinBox,QCheckBox,QMessageBox,QDialog,QVBoxLayout,QLabel,QProgressDialog,QDialog,QVBoxLayout,QTextBrowser,QDialogButtonBox,QTableWidget,QHeaderView,QTableWidgetItem,QAbstractItemView,QTabWidget,QWidget,QFormLayout
from PyQt6.QtGui import QIcon,QAction,QPixmap,QColor,QPainter,QDesktopServices,QCursor
from PyQt6.QtCore import QThread,pyqtSignal,Qt,QTimer,QUrl,QAbstractNativeEventFilter
APP_NAME=_D
APPDATA_DIR=os.path.join(os.getenv('APPDATA',os.path.expanduser('~')),_D)
CONFIG_FILE=os.path.join(APPDATA_DIR,'Loqin_config.json')
APP_VERSION='1.4.4'
GITHUB_API_URL='https://api.github.com/repos/notaayushsrivastava/loqin/releases/latest'
REG_PATH='Software\\Microsoft\\Windows\\CurrentVersion\\Run'
APP_REG_NAME=_D
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
	if C==_F:A.setBrush(QColor(46,204,113))
	elif C==_G:A.setBrush(QColor(241,196,15))
	else:A.setBrush(QColor(231,76,60))
	A.setPen(Qt.PenStyle.NoPen);A.drawEllipse(2,2,12,12);A.end();return QIcon(B)
class PowerEventFilter(QAbstractNativeEventFilter):
	def __init__(A,tray_app):super().__init__();A.tray_app=tray_app
	def nativeEventFilter(A,eventType,message):
		'Intercept native Windows messages to detect sleep/wake';B=ctypes.wintypes.MSG.from_address(int(message))
		if B.message==WM_POWERBROADCAST:
			if B.wParam==PBT_APMSUSPEND:
				if hasattr(A.tray_app,_E)and A.tray_app.worker:A.tray_app.worker.is_paused=_A
			elif B.wParam==PBT_APMRESUMEAUTOMATIC:
				if hasattr(A.tray_app,_E)and A.tray_app.worker:A.tray_app.worker.is_paused=_B
		return _B,0
class PerformanceModeThread(QThread):
	status_signal=pyqtSignal(str,str)
	def __init__(A,use_best=_A):super().__init__();A.use_best=use_best
	def run(A):
		L='Performance Mode ON';K='BSSID';D=':';M=_R if A.use_best else'Reverting Network...';A.status_signal.emit(M,_G)
		try:
			N=pywifi.PyWiFi();B=N.interfaces()[0];B.scan();A.sleep(4);O=B.scan_results();F=[A for A in O if'VIT'in(A.ssid or'').upper()]
			if not F:A.status_signal.emit('No VIT networks found in range.',_J);return
			F.sort(key=lambda x:x.signal,reverse=A.use_best);E=F[0]
			if not A.use_best:B.disconnect();A.sleep(1);C=pywifi.Profile();C.ssid=E.ssid;C.bssid=E.bssid;C.auth=const.AUTH_ALG_OPEN;C.akm.append(const.AKM_TYPE_NONE);B.remove_all_network_profiles();P=B.add_network_profile(C);B.connect(P);A.sleep(3);A.status_signal.emit('Performance Mode OFF',_F);return
			G=_C
			try:
				Q=subprocess.check_output(['netsh','wlan','show','interfaces'],creationflags=134217728).decode('utf-8',errors='ignore')
				for H in Q.split('\n'):
					if K in H and K==H.split(D)[0].strip():
						J=H.split(D)
						if len(J)>=4:G=D.join(J[1:]).strip().lower().replace('-',D);break
			except Exception as I:print(f"Could not get current BSSID: {I}")
			R=E.bssid.strip().lower().replace('-',D)if E.bssid else''
			if G and G==R:A.status_signal.emit(L,_F)
			else:A.status_signal.emit(L,_G)
		except Exception as I:A.status_signal.emit(f"Wi-Fi Error: {str(I)}",_J)
class UpdateChecker(QThread):
	update_found=pyqtSignal(str,str,str);no_update_found=pyqtSignal()
	def run(A):
		try:
			E={'Accept':'application/vnd.github+json'};B=requests.get(GITHUB_API_URL,timeout=5,headers=E)
			if B.status_code==200:
				C=B.json();D=C.get('tag_name','').replace('v','');F=tuple(map(int,APP_VERSION.split('.')));G=tuple(map(int,D.split('.')))
				if G>F:H='https://raw.githubusercontent.com/notaayushsrivastava/Loqin/master/Output/Install_Loqin_Update.exe';A.update_found.emit(D,H,C.get('body','Bug fixes and improvements.'))
				else:A.no_update_found.emit()
		except Exception as I:print(f"Update check failed: {I}")
class AccountDetailsDialog(QDialog):
	def __init__(A,username,account_url,parent=_C):super().__init__(parent);A.username=username;A.account_url=account_url;A.setWindowTitle('Loqin • Account Management');A.setWindowIcon(QIcon(resource_path(_K)));A.resize(750,450);A.setStyleSheet('\n            QDialog { \n                background-color: #171A22; \n            }\n            QLabel {\n                color: #FFFFFF;\n                font-size: 14px;\n            }\n            /* Table Styling */\n            QTableWidget {\n                background-color: #1E222D;\n                color: #DDDDDD;\n                gridline-color: #2C313E;\n                border: 1px solid #2C313E;\n                border-radius: 8px;\n                font-size: 12px;\n            }\n            QHeaderView::section {\n                background-color: #171A22;\n                color: #3da5ff;\n                font-weight: bold;\n                padding: 6px;\n                border: 1px solid #2C313E;\n            }\n            QTableWidget::item { padding: 4px; }\n            \n            /* Tab Styling */\n            QTabWidget::pane { border: 1px solid #2C313E; border-radius: 4px; }\n            QTabBar::tab {\n                background: #1E222D; color: #BBBBBB; padding: 10px 20px; \n                border: 1px solid #2C313E; border-bottom: none; \n                border-top-left-radius: 4px; border-top-right-radius: 4px;\n            }\n            QTabBar::tab:selected { background: #171A22; color: #3da5ff; font-weight: bold; }\n            \n            /* Form Styling */\n            QLineEdit {\n                background: #1E222D; color: #FFF; border: 1px solid #2C313E; \n                border-radius: 4px; padding: 6px; font-size: 14px;\n            }\n            QPushButton {\n                background: #3da5ff; color: #171A22; font-weight: bold; \n                border-radius: 4px; padding: 8px; font-size: 14px;\n            }\n            QPushButton:hover { background: #2b8ee0; }\n        ');B=QVBoxLayout(A);A.tabs=QTabWidget(A);B.addWidget(A.tabs);A.setup_history_tab();A.setup_password_tab()
	def setup_history_tab(A):A.history_tab=QWidget();B=QVBoxLayout(A.history_tab);C=QLabel('<b>Recent Network Sessions</b>');C.setStyleSheet('font-size: 16px; margin-bottom: 5px;');B.addWidget(C);A.table=QTableWidget();A.table.setColumnCount(7);A.table.setHorizontalHeaderLabels(['Location','Login Time','Logout Time','Usage Time',_S,_T,'Total Data']);A.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);D=A.table.horizontalHeader();D.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);D.setStretchLastSection(_A);A.table.verticalHeader().setVisible(_B);B.addWidget(A.table);A.tabs.addTab(A.history_tab,'Usage History')
	def create_password_field(F):
		D=QWidget();C=QHBoxLayout(D);C.setContentsMargins(0,0,0,0);C.setSpacing(5);B=QLineEdit();B.setEchoMode(QLineEdit.EchoMode.Password);B.setFixedWidth(250);A=QPushButton('👁');A.setFixedSize(32,32);A.setCursor(Qt.CursorShape.PointingHandCursor);A.setCheckable(_A);A.setStyleSheet(_U)
		def E(checked):
			if checked:B.setEchoMode(QLineEdit.EchoMode.Normal);A.setText('🔒')
			else:B.setEchoMode(QLineEdit.EchoMode.Password);A.setText('👁')
		A.toggled.connect(E);C.addWidget(B);C.addWidget(A);return D,B
	def setup_password_tab(A):A.password_tab=QWidget();C=QVBoxLayout(A.password_tab);F=QLabel('<b>Reset Network Password</b>');F.setStyleSheet('font-size: 16px; margin-bottom: 10px;');C.addWidget(F);B=QFormLayout();B.setLabelAlignment(Qt.AlignmentFlag.AlignRight);B.setFormAlignment(Qt.AlignmentFlag.AlignTop);B.setSpacing(15);G,A.old_pw_input=A.create_password_field();H,A.new_pw_input=A.create_password_field();I,A.confirm_pw_input=A.create_password_field();B.addRow('Current Password:',G);B.addRow('New Password:',H);B.addRow('Confirm Password:',I);C.addLayout(B);D=QPushButton(_V);D.setFixedWidth(287);D.setCursor(Qt.CursorShape.PointingHandCursor);D.setStyleSheet('\n            QPushButton {\n                background: transparent;\n                color: #3da5ff;\n                border: none;\n                font-size: 13px;\n                text-align: left;\n                padding-left: 0px;\n            }\n            QPushButton:hover {\n                text-decoration: underline;\n                color: #5bb3ff;\n            }\n        ');D.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(_W)));A.update_btn=QPushButton('Update Password');A.update_btn.setFixedWidth(287);A.update_btn.clicked.connect(A.submit_password_change);E=QVBoxLayout();E.setSpacing(6);E.addWidget(A.update_btn);E.addWidget(D);E.setContentsMargins(120,10,0,0);C.addLayout(E);A.status_label=QLabel('');A.status_label.setStyleSheet('margin-left: 120px;');C.addWidget(A.status_label);C.addStretch();A.tabs.addTab(A.password_tab,'Change Password')
	def populate_table(A,rows_data,grand_total_data):
		F=grand_total_data;A.table.setRowCount(0)
		for(G,H)in enumerate(rows_data):
			A.table.insertRow(G)
			for(I,D)in enumerate(H):B=QTableWidgetItem(D);B.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(G,I,B)
		if F:
			C=A.table.rowCount();A.table.insertRow(C);E=QTableWidgetItem(_X);E.setForeground(QColor(_N));E.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(C,0,E)
			for(J,D)in enumerate(F):B=QTableWidgetItem(D);B.setForeground(QColor(_N));B.setTextAlignment(Qt.AlignmentFlag.AlignCenter);A.table.setItem(C,J+3,B)
			A.table.setSpan(C,0,1,3)
	def submit_password_change(A):
		E='color: #e74c3c; margin-left: 120px;';F=A.old_pw_input.text();B=A.new_pw_input.text();C=A.confirm_pw_input.text()
		if not F or not B or not C:A.status_label.setStyleSheet('color: #f1c40f; margin-left: 120px;');A.status_label.setText('Warning: Please fill all fields.');return
		if B!=C:A.status_label.setStyleSheet(E);A.status_label.setText('Error: New passwords do not match.');return
		A.status_label.setStyleSheet('color: #3da5ff; margin-left: 120px;');A.status_label.setText('Updating password...');A.update_btn.setEnabled(_B);QApplication.processEvents()
		try:
			G=urlparse(A.account_url);D=f"{G.scheme}://{G.netloc}";H=requests.Session();H.get(f"{D}/registration/main.do?content_key=%2FChangePassword.jsp",timeout=5);J={'changeUserId':A.username,'changePassword':F,'changeNewPassword':B,'changeConfirmNewPassword':C,'submit':'Update'};K={_Y:f"{D}/registration/main.do?content_key=%2FChangePassword.jsp"};I=H.post(f"{D}/registration/changePassword.do",data=J,headers=K,timeout=5)
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
		A={_H:'',_M:10,'auto_connect':_A};ConfigManager.ensure_dir_exists();B=_B
		if os.path.exists(CONFIG_FILE):
			try:
				with open(CONFIG_FILE,'r')as E:
					C=json.load(E);A.update(C)
					if _I in C:
						D=C[_I]
						if D and A[_H]:ConfigManager.set_password(A[_H],D)
						if _I in A:del A[_I]
						B=_A
			except Exception:pass
		else:B=_A
		if B:ConfigManager.save_config(A)
		return A
	@staticmethod
	def save_config(config):
		ConfigManager.ensure_dir_exists();A=config.copy()
		if _I in A:del A[_I]
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
			if A.status_code==204:return _O
			else:return'PORTAL'
		except requests.exceptions.RequestException:return _Z
	def run(A):
		while A.is_running:
			if A.is_paused:A.sleep(1);continue
			B=A.config.get(_H);C=ConfigManager.get_password(B)
			if not B or not C:A.status_signal.emit(_a,_J);return
			D=A.check_network_state()
			if D==_O:A.status_signal.emit('Connected',_F);return
			elif D==_Z:A.status_signal.emit('Waiting for Wi-Fi...',_G);return
			A.status_signal.emit('Portal detected. Authenticating...',_G);A.login(B,C);return
	def toggle_pause(A):A.is_paused=not A.is_paused;return A.is_paused
	def login(A,username,password):
		B='http://phc.prontonetworks.com';D=f"{B}/cgi-bin/authlogin?URI=http://example.com";E={'userId':username,_I:password,'serviceName':'ProntoAuthentication','URI':'http://example.com'};F={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)','Content-Type':'application/x-www-form-urlencoded','Origin':B,_Y:f"{B}/cgi-bin/authlogin?URI=http://www.msftconnecttest.com/redirect"}
		try:
			G=requests.post(D,data=E,headers=F,timeout=5)
			if A.check_network_state()==_O:
				A.status_signal.emit('Logged in successfully!',_F);H=G.text;C=re.search('href="(http://([0-9\\.]+)/registration/Main\\.jsp\\?sessionId=[^"]+)"',H)
				if C:I=C.group(1);J=C.group(2);print(f"Extracted IP: {J}");A.account_data_signal.emit(I)
				else:print('Could not find the account link in the response HTML.')
			else:A.status_signal.emit('Login failed. Check credentials.',_J)
		except Exception as K:print(K);A.status_signal.emit('Portal timeout or error.',_J)
class SpeedGraphDialog(QDialog):
	def __init__(A,parent=_C):I='#777';F='bottom';E='left';D='#BBBBBB';super().__init__(parent);A.setWindowTitle('Loqin • Live Network Monitor');A.setWindowIcon(QIcon(resource_path(_K)));A.resize(720,420);A.download_history=[0]*60;A.upload_history=[0]*60;C=QVBoxLayout(A);C.setContentsMargins(15,15,15,15);B=QHBoxLayout();G=QLabel('Real-Time Network Usage');G.setStyleSheet('\n            QLabel{\n                color:white;\n                font-size:18px;\n                font-weight:600;\n            }\n        ');A.pin_checkbox=QCheckBox('Always on Top');A.pin_checkbox.setCursor(Qt.CursorShape.PointingHandCursor);A.pin_checkbox.setStyleSheet('\n            QCheckBox {\n                color: #BBBBBB;\n                font-size: 13px;\n                font-weight: 500;\n            }\n            QCheckBox::indicator {\n                width: 14px;\n                height: 14px;\n                border: 1px solid #777777;\n                border-radius: 3px;\n                background: #171A22;\n            }\n            QCheckBox::indicator:checked {\n                background: #3da5ff;\n                border: 1px solid #3da5ff;\n            }\n            QCheckBox:hover {\n                color: #FFFFFF;\n            }\n        ');A.pin_checkbox.toggled.connect(A.toggle_always_on_top);B.addStretch();B.addWidget(G);B.addStretch();B.addWidget(A.pin_checkbox);C.addLayout(B);A.graph=pg.PlotWidget();C.addWidget(A.graph);A.stats=QLabel();A.stats.setAlignment(Qt.AlignmentFlag.AlignCenter);A.stats.setStyleSheet('\n            QLabel{\n                color:#cccccc;\n                font-size:13px;\n            }\n        ');C.addWidget(A.stats);A.setStyleSheet('\n            QDialog{\n                background:#171A22;\n            }\n        ');A.graph.setBackground('#171A22');A.graph.showGrid(x=_A,y=_A,alpha=.25);A.graph.hideButtons();A.graph.setMouseEnabled(_B,_B);A.graph.setMenuEnabled(_B);A.graph.setClipToView(_A);A.graph.setDownsampling(mode='peak');A.graph.setLabel(E,'Speed (KB/s)',color=D);A.graph.setLabel(F,'Time',color=D);A.graph.getAxis(E).setPen(pg.mkPen(I));A.graph.getAxis(F).setPen(pg.mkPen(I));A.graph.getAxis(E).setTextPen(D);A.graph.getAxis(F).setTextPen(D);A.graph.setYRange(0,100);A.download_curve=A.graph.plot(pen=pg.mkPen('#3da5ff',width=3),name=_T);A.upload_curve=A.graph.plot(pen=pg.mkPen(_N,width=3),name=_S);H=A.graph.addLegend();H.setBrush(pg.mkBrush(30,30,30,200));H.setOffset((15,15))
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
	def __init__(A,parent=_C):super().__init__(parent);A.setWindowTitle('Loqin for PC - Settings');A.setFixedSize(410,270);A.setWindowIcon(QIcon(resource_path(_K)));A.config=ConfigManager.load_config();A.init_ui()
	def create_password_field(F):
		D=QWidget();C=QHBoxLayout(D);C.setContentsMargins(0,0,0,0);C.setSpacing(5);B=QLineEdit();B.setEchoMode(QLineEdit.EchoMode.Password);A=QPushButton('👁');A.setFixedSize(32,32);A.setCursor(Qt.CursorShape.PointingHandCursor);A.setCheckable(_A);A.setStyleSheet(_U)
		def E(checked):
			if checked:B.setEchoMode(QLineEdit.EchoMode.Normal);A.setText('🔒')
			else:B.setEchoMode(QLineEdit.EchoMode.Password);A.setText('👁')
		A.toggled.connect(E);C.addWidget(B);C.addWidget(A);return D,B
	def init_ui(A):B=QVBoxLayout();B.setSpacing(4);B.setContentsMargins(15,15,15,15);B.setAlignment(Qt.AlignmentFlag.AlignTop);D=QLabel();F=QPixmap(resource_path(_K));G=F.scaled(32,32,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation);D.setPixmap(G);D.setAlignment(Qt.AlignmentFlag.AlignCenter);B.addWidget(D);B.addWidget(QLabel('Registration Number / Username:'));A.user_input=QLineEdit(A.config.get(_H,''));B.addWidget(A.user_input);B.addWidget(QLabel('Password:'));H,A.pass_input=A.create_password_field();A.pass_input.setText(ConfigManager.get_password(A.user_input.text()));B.addWidget(H);C=QPushButton(_V);C.setCursor(Qt.CursorShape.PointingHandCursor);C.setStyleSheet('\n            QPushButton {\n                background: transparent;\n                color: #3da5ff;\n                border: none;\n                font-size: 12px;\n                text-align: left;\n                padding-left: 2px;\n                margin-top: 2px;\n                margin-bottom: 6px;\n            }\n            QPushButton:hover {\n                text-decoration: underline;\n                color: #5bb3ff;\n            }\n        ');C.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(_W)));B.addWidget(C);E=QHBoxLayout();E.addWidget(QLabel('Check Frequency (seconds):'));A.interval_input=QSpinBox();A.interval_input.setRange(5,300);A.interval_input.setValue(A.config.get(_M,10));E.addWidget(A.interval_input);B.addLayout(E);A.startup_cb=QCheckBox('Launch automatically on Windows startup');A.startup_cb.setChecked(is_auto_start_enabled());B.addWidget(A.startup_cb);A.save_btn=QPushButton('Save and Apply');A.save_btn.clicked.connect(A.save_settings);B.addWidget(A.save_btn);B.addStretch();A.setLayout(B)
	def save_settings(A):
		B=A.user_input.text().strip();C=A.pass_input.text().strip()
		if not B or not C:QMessageBox.warning(A,'Warning','Username and Password cannot be empty.');return
		set_auto_start(A.startup_cb.isChecked());A.config[_H]=B;A.config[_M]=A.interval_input.value();ConfigManager.save_config(A.config);ConfigManager.set_password(B,C);QMessageBox.information(A,'Success','Settings saved successfully!');A.accept()
class LoqinTrayApp:
	def __init__(A):A.app=QApplication(sys.argv);A.app.setApplicationName(_D);A.app.setQuitOnLastWindowClosed(_B);A.power_filter=PowerEventFilter(A);A.app.installNativeEventFilter(A.power_filter);A.default_icon=QIcon(resource_path(_K));A.perf_icon=QIcon(resource_path('loqin_logo_performance.png'));A.icon=A.default_icon;A.tray=QSystemTrayIcon();A.tray.setIcon(A.default_icon);A.tray.setVisible(_A);A.tray.showMessage(_D,'Loqin has started! Monitoring your connection in the background.',A.icon,3000);A.config=ConfigManager.load_config();A.last_net_io=psutil.net_io_counters();A.last_time=time.time();A.graph_dialog=_C;A.build_menu();A.worker=_C;A.start_monitoring_timer();A.force_logout();A.speed_timer=QTimer();A.speed_timer.timeout.connect(A.update_bandwidth_meters);A.speed_timer.start(1000);A.has_checked_for_updates=_B
	def build_menu(A):A.menu=QMenu();A.status_action=QAction('Status: Initializing...',A.menu);A.status_action.setIcon(create_status_icon(_G));A.status_action.setEnabled(_A);A.menu.addAction(A.status_action);A.menu.addSeparator();A.speed_action=QAction('Speed: ↓ 0 KB/s  ↑ 0 KB/s',A.menu);A.speed_action.setEnabled(_B);A.menu.addAction(A.speed_action);A.graph_action=QAction(_b,A.menu);A.graph_action.triggered.connect(A.toggle_speed_graph);A.menu.addAction(A.graph_action);A.menu.addSeparator();C=QAction('Connect Now',A.menu);C.triggered.connect(A.trigger_manual_check);A.menu.addAction(C);A.pause_action=QAction(_P,A.menu);A.pause_action.triggered.connect(A.toggle_service_pause);A.menu.addAction(A.pause_action);A.perf_action=QAction(_c,A.menu);A.perf_action.setCheckable(_A);A.perf_action.setChecked(_B);A.perf_action.triggered.connect(A.trigger_performance_mode);A.menu.addAction(A.perf_action);A.menu.addSeparator();A.account_action=QAction('View Account Details',A.menu);A.account_action.setEnabled(_B);A.account_action.triggered.connect(A.show_account_details);A.menu.addAction(A.account_action);A.update_action=QAction(_d,A.menu);A.update_action.triggered.connect(A.check_for_updates);A.menu.addAction(A.update_action);D=QAction('Configure Settings',A.menu);D.triggered.connect(A.open_settings);A.menu.addAction(D);A.menu.addSeparator();B=A.menu.addMenu('Help');E=QAction('How to use',A.menu);E.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin#readme')));B.addAction(E);F=QAction('GitHub Releases',A.menu);F.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin/releases')));B.addAction(F);G=QAction('Project Info',A.menu);G.triggered.connect(lambda:QDesktopServices.openUrl(QUrl('https://github.com/notaayushsrivastava/loqin')));B.addAction(G);A.menu.addSeparator();H=QAction('Exit Loqin',A.menu);H.triggered.connect(A.close_app);A.menu.addAction(H);A.tray.setContextMenu(A.menu);A.tray.activated.connect(A.on_tray_icon_activated);A.tray.setToolTip('Loqin PC')
	def on_tray_icon_activated(B,reason):
		'Handles clicks on the system tray icon.'
		if reason==QSystemTrayIcon.ActivationReason.Trigger:
			A=B.tray.contextMenu()
			if A is not _C:A.exec(QCursor.pos())
	def toggle_service_pause(A):
		if hasattr(A,_E)and A.worker:
			B=A.worker.toggle_pause()
			if B:A.pause_action.setText(_Q);A.tray.setToolTip('Loqin - Paused')
			else:A.pause_action.setText(_P);A.tray.setToolTip(_e)
	def close_app(A):
		try:requests.get('http://phc.prontonetworks.com/cgi-bin/authlogout/',timeout=2)
		except Exception:pass
		if hasattr(A,_E)and A.worker and A.worker.isRunning():A.worker.is_running=_B;A.worker.quit();A.worker.wait()
		if hasattr(A,_f)and A.perf_thread and A.perf_thread.isRunning():A.perf_thread.quit();A.perf_thread.wait()
		if hasattr(A,_g)and A.update_checker and A.update_checker.isRunning():A.update_checker.quit();A.update_checker.wait()
		A.app.quit()
	def update_bandwidth_meters(A):
		D=psutil.net_io_counters();F=time.time();E=F-A.last_time
		if E>0:
			B=(D.bytes_recv-A.last_net_io.bytes_recv)/E;C=(D.bytes_sent-A.last_net_io.bytes_sent)/E;A.last_net_io=D;A.last_time=F;G=f"{B/1024:.1f} KB/s"if B<1048576 else f"{B/1048576:.1f} MB/s";H=f"{C/1024:.1f} KB/s"if C<1048576 else f"{C/1048576:.1f} MB/s";A.speed_action.setText(f"Speed: ↓ {G}  ↑ {H}")
			if A.graph_dialog and A.graph_dialog.isVisible():A.graph_dialog.update_data(B,C)
	def toggle_speed_graph(A):
		B='Hide Speed Graph'
		if not A.graph_dialog:A.graph_dialog=SpeedGraphDialog()
		if A.graph_dialog.isVisible():
			if not A.graph_dialog.isActiveWindow():A.graph_dialog.showNormal();A.graph_dialog.raise_();A.graph_dialog.activateWindow();A.graph_action.setText(B)
			else:A.graph_dialog.hide();A.graph_action.setText(_b)
		else:A.graph_dialog.showNormal();A.graph_dialog.raise_();A.graph_dialog.activateWindow();A.graph_action.setText(B)
	def open_settings(A):
		if hasattr(A,'settings_dialog')and A.settings_dialog is not _C:
			if A.settings_dialog.isVisible():A.settings_dialog.showNormal();A.settings_dialog.raise_();A.settings_dialog.activateWindow();return
		A.settings_dialog=SettingsDialog()
		if A.settings_dialog.exec():A.config=ConfigManager.load_config();A.start_monitoring_timer()
		A.settings_dialog=_C
	def trigger_manual_check(A):
		if hasattr(A,_E)and A.worker and A.worker.isRunning():return
		A.config=ConfigManager.load_config();A.worker=NetworkWorker(A.config);A.worker.status_signal.connect(A.handle_status);A.worker.account_data_signal.connect(A.handle_account_url);A.worker.start()
	def handle_status(A,message,color_type):
		C=color_type;B=message;A.status_action.setText(f"Status: {B}");A.status_action.setIcon(create_status_icon(C))
		if B==_a:
			if hasattr(A,_E)and A.worker:A.worker.is_paused=_A;A.pause_action.setText(_Q);A.tray.setToolTip('Loqin - Paused (Missing Credentials)')
			QTimer.singleShot(100,A.open_settings);return
		if C==_F:
			if'successfully'in B:A.tray.showMessage(_D,B,A.icon,3000)
			if not getattr(A,'has_checked_for_updates',_B):A.check_for_updates(_A);A.has_checked_for_updates=_A
		elif C==_J:A.tray.showMessage(_D,B,A.icon,3000)
	def trigger_performance_mode(A,checked=_B):
		B=checked
		if hasattr(A,_f)and A.perf_thread.isRunning():return
		if hasattr(A,_E)and A.worker:A.worker.is_paused=_A;A.pause_action.setText(_Q);A.tray.setToolTip('Loqin - Paused (Optimizing Network)')
		if B:A.tray.setIcon(A.perf_icon);A.icon=A.perf_icon
		else:A.tray.setIcon(A.default_icon);A.icon=A.default_icon
		A.perf_thread=PerformanceModeThread(use_best=B);A.perf_thread.status_signal.connect(A.handle_perf_status);A.perf_thread.start()
	def handle_perf_status(A,message,color_type):
		C=color_type;B=message;A.status_action.setText(f"Status: {B}");A.status_action.setIcon(create_status_icon(C));A.tray.showMessage(_c,B,A.icon,4000)
		if B!=_R:
			if hasattr(A,_E)and A.worker:
				A.worker.is_paused=_B;A.pause_action.setText(_P)
				if'OFF'in B:A.tray.setToolTip(_e)
				else:A.tray.setToolTip('Loqin - Active (Performance Mode)')
			if C in[_F,_G]:QTimer.singleShot(1000,A.trigger_manual_check)
	def handle_account_url(A,url):A.current_account_url=url;print(url);A.account_action.setEnabled(_A)
	def show_account_details(A):
		if not hasattr(A,'current_account_url'):return
		H=A.config.get(_H);A.account_dialog=AccountDetailsDialog(H,A.current_account_url);A.account_dialog.show();QApplication.processEvents()
		try:
			I=requests.get(A.current_account_url,timeout=5);D=BeautifulSoup(I.text,'html.parser');E=[];J=D.find_all('tr',attrs={'bgcolor':['#DDDDDD','#F3F3F3']})
			for C in J:
				B=[A.text.strip()for A in C.find_all('td')]
				if len(B)==7:E.append(B)
			F=[];G=D.find(string=lambda text:text and _X in text)
			if G:C=G.find_parent('tr');B=[A.text.strip()for A in C.find_all('td')];F=B[1:]
			A.account_dialog.populate_table(E,F)
		except Exception as K:print(f"Failed to scrape account history table: {K}")
	def check_for_updates(A,silent=_B):
		"\n        Checks for updates on GitHub.\n        :param silent: If True, suppresses the 'Up to Date' dialog when no new updates are found.\n        ";B=silent
		if hasattr(A,_g)and A.update_checker and A.update_checker.isRunning():return
		if not B:A.update_action.setText('Checking for updates...');A.update_action.setEnabled(_B)
		A.update_checker=UpdateChecker();A.update_checker.update_found.connect(A.prompt_update)
		if not B:A.update_checker.no_update_found.connect(A.prompt_no_update);A.update_checker.finished.connect(lambda:A.update_action.setText(_d));A.update_checker.finished.connect(lambda:A.update_action.setEnabled(_A))
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
		A.timer=QTimer();A.timer.timeout.connect(A.trigger_manual_check);A.timer.start(A.config.get(_M,10)*1000);A.trigger_manual_check()
	def force_logout(B):
		'Silently drops the Pronto Networks Wi-Fi session.'
		try:requests.get('http://phc.prontonetworks.com/cgi-bin/authlogout',timeout=3);print('Successfully dropped existing Wi-Fi session on startup.')
		except Exception as A:print(f"Logout check bypassed (likely not connected): {A}")
	def run(A):sys.exit(A.app.exec())
if __name__=='__main__':
	mutex_handle=ensure_single_instance()
	if sys.platform==_L:
		try:myappid=_D;ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
		except Exception as e:print(f"Failed to set AppUserModelID: {e}")
	app=LoqinTrayApp();app.run()