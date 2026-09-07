import sys
import subprocess
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget, QListWidget, QFrame, QSystemTrayIcon, QMenu, QAction, QInputDialog, QLineEdit, QTextEdit, QFileDialog
from PyQt5.QtCore import QTimer, Qt, QProcess
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()

        # A QProcess objektumok inicializálása az UI felépítése ELŐTT kell történjen!
        self.clam_start_proc = QProcess(self)
        self.clam_stop_proc = QProcess(self)
        self.clam_status_proc = QProcess(self)

        self.clam_scan_proc = QProcess(self)
        self.clam_update_proc = QProcess(self)
        self.clam_cron_proc = QProcess(self)


        self.f2b_start_proc = QProcess(self)
        self.f2b_stop_proc = QProcess(self)
        self.f2b_status_proc = QProcess(self)

        self.wd_start_proc = QProcess(self)
        self.wd_stop_proc = QProcess(self)
        self.wd_status_proc = QProcess(self)

        self.clam_status_proc.finished.connect(self.clam_status_finished)
        self.f2b_status_proc.finished.connect(self.f2b_status_finished)
        self.wd_status_proc.finished.connect(self.wd_status_finished)

        self.clam_scan_proc.readyReadStandardOutput.connect(self.clam_scan_output)
        self.clam_scan_proc.readyReadStandardError.connect(self.clam_scan_error)
        self.clam_scan_proc.finished.connect(self.clam_scan_finished)

        self.clam_update_proc.readyReadStandardOutput.connect(self.clam_update_output)
        self.clam_update_proc.finished.connect(self.clam_update_finished)


        self.sudo_password = None

        self.initUI()
        self.statusBar().showMessage('Ready. Awaiting commands.')


        # Tray Icon beállítása (KDE Plasma stílushoz illeszkedő, ahogy a korábbi kódokban volt)
        self.tray_icon = QSystemTrayIcon(self)

        # A biztonsági pajzs ikon betöltése abszolút elérési útról (MX Linux Oxygen téma)
        icon_path = "/usr/share/icons/oxygen/base/128x128/status/security-high.png"
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            icon = QIcon.fromTheme("security-high")

        self.tray_icon.setIcon(icon)


        show_action = QAction("Megjelenítés", self)
        quit_action = QAction("Bezárás", self)
        clear_pwd_action = QAction("Sudo Jelszó Törlése", self)
        clear_pwd_action.triggered.connect(self.clear_password)
        show_action.triggered.connect(self.show_normal)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(clear_pwd_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_clicked)
        self.tray_icon.show()


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_statuses)
        self.timer.start(3000)

    def initUI(self):
        self.setWindowTitle("CyberSec Control Center")

        # Set Window Icon (shows on KDE taskbar when minimized)
        icon_path = "/usr/share/icons/oxygen/base/128x128/status/security-high.png"
        import os
        from PyQt5.QtGui import QIcon
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("security-high"))

        self.resize(700, 450)

        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QListWidget {
                background-color: #1e293b;
                color: #94a3b8;
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
            QListWidget::item { padding: 15px; border-radius: 8px; }
            QListWidget::item:selected { background-color: #334155; color: #f8fafc; }
            QListWidget::item:hover { background-color: #475569; color: #f8fafc; }

            QLabel { color: #f1f5f9; }

            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1d4ed8; }
            QPushButton#stopBtn { background-color: #ef4444; }
            QPushButton#stopBtn:hover { background-color: #dc2626; }
            QPushButton#stopBtn:pressed { background-color: #b91c1c; }

            QFrame#mainPanel {
                background-color: #1e293b;
                border-radius: 12px;
            }
            QFrame#statusCard {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)

        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItem("🛡️ ClamAV")
        self.sidebar.addItem("🧱 Fail2ban")
        self.sidebar.addItem("👁️ Watchdog")
        self.sidebar.currentRowChanged.connect(self.switch_page)

        # Main Content Area
        self.stack = QStackedWidget()

        # Pages - Using QProcess to start/stop without blocking the GUI
        self.clam_page = QFrame()
        self.clam_page.setObjectName("mainPanel")
        clam_layout = QVBoxLayout()
        clam_layout.setContentsMargins(40, 40, 40, 40)
        clam_layout.setSpacing(20)

        clam_title = QLabel("ClamAV Antivirus & Scanner")
        clam_title.setFont(QFont("Segoe UI", 24, QFont.Bold))
        clam_desc = QLabel("Protects the system against malicious files and trojans.")
        clam_desc.setFont(QFont("Segoe UI", 12))
        clam_desc.setStyleSheet("color: #94a3b8;")

        # Status Card (Daemon)
        status_card = QFrame()
        status_card.setObjectName("statusCard")
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(20, 20, 20, 20)
        status_header = QLabel("DAEMON STATUS")
        status_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        status_header.setStyleSheet("color: #64748b;")
        self.clam_status = QLabel("Checking...")
        self.clam_status.setFont(QFont("Monospace", 18, QFont.Bold))
        status_layout.addWidget(status_header)
        status_layout.addWidget(self.clam_status)

        # Daemon Controls
        daemon_controls = QHBoxLayout()
        btn_start = QPushButton("START DAEMON")
        btn_stop = QPushButton("STOP DAEMON")
        btn_stop.setObjectName("stopBtn")
        btn_start.clicked.connect(lambda: self.execute_sudo_cmd(self.clam_start_proc, ["/usr/sbin/service", "clamav-daemon", "start"]))
        btn_stop.clicked.connect(lambda: self.execute_sudo_cmd(self.clam_stop_proc, ["/usr/sbin/service", "clamav-daemon", "stop"]))
        daemon_controls.addWidget(btn_start)
        daemon_controls.addWidget(btn_stop)
        status_layout.addLayout(daemon_controls)
        status_card.setLayout(status_layout)

        # Scanner Controls
        scan_card = QFrame()
        scan_card.setObjectName("statusCard")
        scan_layout = QVBoxLayout()
        scan_layout.setContentsMargins(20, 20, 20, 20)
        scan_header = QLabel("SCANNER & UPDATER")
        scan_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        scan_header.setStyleSheet("color: #64748b;")

        # Buttons row 1: Scanning
        scan_btns1 = QHBoxLayout()
        btn_scan_root = QPushButton("Root (/) Scan")
        btn_scan_home = QPushButton("Home (/home) Scan")
        btn_scan_custom = QPushButton("Custom Folder...")
        btn_scan_root.clicked.connect(lambda: self.start_clam_scan("/"))
        btn_scan_home.clicked.connect(lambda: self.start_clam_scan("/home"))
        btn_scan_custom.clicked.connect(self.start_custom_scan)
        scan_btns1.addWidget(btn_scan_root)
        scan_btns1.addWidget(btn_scan_home)
        scan_btns1.addWidget(btn_scan_custom)

        # Buttons row 2: Updating
        scan_btns2 = QHBoxLayout()
        btn_update_manual = QPushButton("Update Signatures")
        self.btn_update_auto = QPushButton("Auto Update (Cron): OFF")
        btn_upgrade_engine = QPushButton("Upgrade ClamAV Engine")

        btn_update_manual.clicked.connect(self.start_manual_update)
        self.btn_update_auto.clicked.connect(self.toggle_auto_update)
        btn_upgrade_engine.clicked.connect(self.start_engine_upgrade)

        scan_btns2.addWidget(btn_update_manual)
        scan_btns2.addWidget(self.btn_update_auto)
        scan_btns2.addWidget(btn_upgrade_engine)

        scan_layout.addWidget(scan_header)
        scan_layout.addLayout(scan_btns1)
        scan_layout.addLayout(scan_btns2)

        # Output Log Console
        self.clam_log = QTextEdit()
        self.clam_log.setReadOnly(True)
        self.clam_log.setStyleSheet("background-color: #000; color: #0f0; font-family: monospace; font-size: 11px;")
        scan_layout.addWidget(self.clam_log)
        scan_card.setLayout(scan_layout)

        clam_layout.addWidget(clam_title)
        clam_layout.addWidget(clam_desc)
        clam_layout.addWidget(status_card)
        clam_layout.addWidget(scan_card)
        self.clam_page.setLayout(clam_layout)
        self.f2b_page, self.f2b_status = self.create_page(
            "Fail2ban Intrusion Prevention",
            "Bans IPs that show malicious signs like too many password failures.",
            lambda: self.execute_sudo_cmd(self.f2b_start_proc, ["/usr/sbin/service", "fail2ban", "start"]),
            lambda: self.execute_sudo_cmd(self.f2b_stop_proc, ["/usr/sbin/service", "fail2ban", "stop"])
        )
        self.wd_page, self.wd_status = self.create_page(
            "Merkava Cryptominer Watchdog",
            "Continuously scans process list and kills known crypto miners.",
            lambda: self.execute_sudo_cmd(self.wd_start_proc, ["bash", "-c", "(sudo crontab -l 2>/dev/null | grep -v miner_watchdog; echo '* * * * * /usr/local/bin/miner_watchdog.sh') | sudo crontab -"]),
            lambda: self.execute_sudo_cmd(self.wd_stop_proc, ["bash", "-c", "sudo crontab -l 2>/dev/null | grep -v miner_watchdog | sudo crontab -"])
        )

        self.stack.addWidget(self.clam_page)
        self.stack.addWidget(self.f2b_page)
        self.stack.addWidget(self.wd_page)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.sidebar.setCurrentRow(0)
        self.update_statuses()


    def execute_sudo_cmd(self, proc_obj, args_list):
        if not self.sudo_password:
            pwd, ok = QInputDialog.getText(self, "Sudo Authentication", "Enter your password for root privileges:", QLineEdit.Password)
            if ok and pwd:
                self.sudo_password = pwd
                self.statusBar().showMessage('Password saved in memory.', 5000)
            else:
                return

        # Start sudo with -S to read from stdin
        proc_obj.start("sudo", ["-S"] + args_list)
        # Write the password to the process's stdin
        proc_obj.write((self.sudo_password + "\n").encode())

    def create_page(self, title_text, desc_text, start_cb, stop_cb):
        page = QFrame()
        page.setObjectName("mainPanel")
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 24, QFont.Bold))

        desc = QLabel(desc_text)
        desc.setFont(QFont("Segoe UI", 12))
        desc.setStyleSheet("color: #94a3b8;")
        desc.setWordWrap(True)

        status_card = QFrame()
        status_card.setObjectName("statusCard")
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(20, 20, 20, 20)

        status_header = QLabel("CURRENT STATUS")
        status_header.setFont(QFont("Segoe UI", 10, QFont.Bold))
        status_header.setStyleSheet("color: #64748b;")

        status_lbl = QLabel("Checking...")
        status_lbl.setFont(QFont("Monospace", 18, QFont.Bold))

        status_layout.addWidget(status_header)
        status_layout.addWidget(status_lbl)
        status_card.setLayout(status_layout)

        controls_layout = QHBoxLayout()
        btn_start = QPushButton("START SERVICE")
        btn_start.setCursor(Qt.PointingHandCursor)
        btn_start.clicked.connect(start_cb)
        btn_start.clicked.connect(lambda: QTimer.singleShot(1000, self.update_statuses))

        btn_stop = QPushButton("STOP SERVICE")
        btn_stop.setObjectName("stopBtn")
        btn_stop.setCursor(Qt.PointingHandCursor)
        btn_stop.clicked.connect(stop_cb)
        btn_stop.clicked.connect(lambda: QTimer.singleShot(1000, self.update_statuses))

        controls_layout.addWidget(btn_start)
        controls_layout.addWidget(btn_stop)

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addSpacing(20)
        layout.addWidget(status_card)
        layout.addStretch()
        layout.addLayout(controls_layout)

        page.setLayout(layout)
        return page, status_lbl


    def show_normal(self):
        self.showNormal()
        self.activateWindow()

    def tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("CyberSec Dashboard", "Az alkalmazás a tálcán fut tovább.", QSystemTrayIcon.Information, 2000)

    def clear_password(self):
        self.sudo_password = None
        self.statusBar().showMessage('Sudo Password cleared.', 5000)


    # --- ClamAV Scanner & Updater Logic ---
    def start_clam_scan(self, target_dir):
        if self.clam_scan_proc.state() == QProcess.Running:
            self.clam_log.append("⚠️ A scan is already running! Please wait or terminate it.")
            return

        self.clam_log.clear()
        self.clam_log.append(f"[*] Starting Advanced ClamAV Scan on: {target_dir}")
        self.clam_log.append("[*] (Includes emails, archives, macros, html, pua, phishing)")

        # Extended ClamAV flags for maximum detection
        clam_args = [
            "clamscan", "-r", "-i",
            "--phishing-sigs=yes", "--phishing-scan-urls=yes",
            "--detect-pua=yes", "--scan-mail=yes",
            "--scan-archive=yes", "--scan-ole2=yes",
            "--scan-pe=yes", "--scan-html=yes",
            target_dir
        ]
        self.execute_sudo_cmd(self.clam_scan_proc, clam_args)

    def start_custom_scan(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory to Scan")
        if folder:
            self.start_clam_scan(folder)

    def clam_scan_output(self):
        text = self.clam_scan_proc.readAllStandardOutput().data().decode(errors='ignore')
        self.clam_log.append(text.strip())
        self.clam_log.verticalScrollBar().setValue(self.clam_log.verticalScrollBar().maximum())

    def clam_scan_error(self):
        text = self.clam_scan_proc.readAllStandardError().data().decode(errors='ignore')
        self.clam_log.append(f"<span style='color:red'>{text.strip()}</span>")

    def clam_scan_finished(self, exitCode, exitStatus):
        self.clam_log.append(f"[-] Scan finished with exit code {exitCode}.")
        self.clam_log.verticalScrollBar().setValue(self.clam_log.verticalScrollBar().maximum())

    def start_manual_update(self):
        if self.clam_update_proc.state() == QProcess.Running:
            self.clam_log.append("⚠️ An update is already running!")
            return

        self.clam_log.clear()
        self.clam_log.append("[*] Starting manual signature update (freshclam)...")
        self.execute_sudo_cmd(self.clam_update_proc, ["freshclam"])

    def start_engine_upgrade(self):
        if self.clam_update_proc.state() == QProcess.Running:
            self.clam_log.append("⚠️ An update/upgrade process is already running!")
            return

        self.clam_log.clear()
        self.clam_log.append("[*] Starting ClamAV Engine Upgrade via APT...")
        # Force apt-get to upgrade clamav packages non-interactively
        cmd = "apt-get update && apt-get install --only-upgrade -y clamav clamav-daemon clamav-freshclam"
        self.execute_sudo_cmd(self.clam_update_proc, ["bash", "-c", cmd])

    def clam_update_output(self):
        text = self.clam_update_proc.readAllStandardOutput().data().decode(errors='ignore')
        self.clam_log.append(text.strip())
        self.clam_log.verticalScrollBar().setValue(self.clam_log.verticalScrollBar().maximum())

    def clam_update_finished(self, exitCode, exitStatus):
        self.clam_log.append(f"[-] Update finished with exit code {exitCode}.")

    def toggle_auto_update(self):
        # We use standard bash pipe for crontab via sudo since it's NOPASSWD
        if "ON" in self.btn_update_auto.text():
            cmd = "sudo crontab -l 2>/dev/null | grep -v update_clamav.sh | sudo crontab -"
            self.clam_log.append("[*] Disabling automatic updates...")
            self.btn_update_auto.setText("Auto Update (Cron): OFF")
        else:
            cmd = "(sudo crontab -l 2>/dev/null | grep -v update_clamav.sh; echo '0 */4 * * * /usr/local/bin/update_clamav.sh') | sudo crontab -"
            self.clam_log.append("[*] Enabling automatic updates (every 4 hours)...")
            self.btn_update_auto.setText("Auto Update (Cron): ON")

        self.clam_cron_proc.start("bash", ["-c", cmd])
        # Force a status update check slightly after
        QTimer.singleShot(1500, self.update_statuses)

    # --- End ClamAV Logic ---

    def switch_page(self, index):

        self.stack.setCurrentIndex(index)

    def update_statuses(self):
        # Fire off asynchronous status checks
        # ClamAV
        if self.clam_status_proc.state() == QProcess.NotRunning:
            self.clam_status_proc.start("pgrep", ["-x", "clamd"])

        # Fail2ban
        if self.f2b_status_proc.state() == QProcess.NotRunning:
            self.f2b_status_proc.start("pgrep", ["-x", "fail2ban-server"])

        # Watchdog
        if self.wd_status_proc.state() == QProcess.NotRunning:
            self.wd_status_proc.start("bash", ["-c", "sudo crontab -l 2>/dev/null | grep miner_watchdog.sh"])

    # --- Slot callbacks for when status processes finish ---

    def clam_status_finished(self, exitCode, exitStatus):
        if exitStatus == QProcess.NormalExit and exitCode == 0:
            self.clam_status.setText("● SYSTEM ACTIVE")
            self.clam_status.setStyleSheet("color: #22c55e;")
        else:
            self.clam_status.setText("○ SYSTEM OFFLINE")
            self.clam_status.setStyleSheet("color: #64748b;")

    def f2b_status_finished(self, exitCode, exitStatus):
        if exitStatus == QProcess.NormalExit and exitCode == 0:
            self.f2b_status.setText("● SYSTEM ACTIVE")
            self.f2b_status.setStyleSheet("color: #22c55e;")
        else:
            self.f2b_status.setText("○ SYSTEM OFFLINE")
            self.f2b_status.setStyleSheet("color: #64748b;")

    def wd_status_finished(self, exitCode, exitStatus):
        if exitStatus == QProcess.NormalExit and exitCode == 0:
            # grep found the cron job
            self.wd_status.setText("● SYSTEM ACTIVE")
            self.wd_status.setStyleSheet("color: #22c55e;")
        else:
            self.wd_status.setText("○ SYSTEM OFFLINE")
            self.wd_status.setStyleSheet("color: #64748b;")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    socket = QLocalSocket()
    socket.connectToServer('Jules_CyberSec_Instance')
    if socket.waitForConnected(500):
        socket.write(b"SHOW")
        socket.waitForBytesWritten(500)
        sys.exit(0)

    server = QLocalServer()
    server.removeServer('Jules_CyberSec_Instance')
    server.listen('Jules_CyberSec_Instance')

    window = Dashboard()

    def handle_connection():
        conn = server.nextPendingConnection()
        conn.waitForReadyRead(500)
        if conn.readAll() == b"SHOW":
            window.show_normal()
        conn.disconnectFromServer()

    server.newConnection.connect(handle_connection)

    if "--hidden" not in sys.argv:
        window.show()

    sys.exit(app.exec_())
