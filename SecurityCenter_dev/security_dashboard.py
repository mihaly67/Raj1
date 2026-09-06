import sys
import subprocess
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget, QListWidget, QFrame, QSystemTrayIcon, QMenu, QAction, QInputDialog, QLineEdit
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

        self.f2b_start_proc = QProcess(self)
        self.f2b_stop_proc = QProcess(self)
        self.f2b_status_proc = QProcess(self)

        self.wd_start_proc = QProcess(self)
        self.wd_stop_proc = QProcess(self)
        self.wd_status_proc = QProcess(self)

        self.clam_status_proc.finished.connect(self.clam_status_finished)
        self.f2b_status_proc.finished.connect(self.f2b_status_finished)
        self.wd_status_proc.finished.connect(self.wd_status_finished)

        self.sudo_password = None

        self.initUI()
        self.statusBar().showMessage('Ready. Awaiting commands.')

        # Tray Icon beállítása (KDE Plasma stílushoz illeszkedő, ahogy a korábbi kódokban volt)
        self.tray_icon = QSystemTrayIcon(self)

        icon_path = "/usr/share/icons/oxygen/base/128x128/apps/security-high.png"
        if not os.path.exists(icon_path):
            icon_path = "/usr/share/icons/gnome/256x256/apps/security-high.png"

        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Fallback icon
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor("#3b82f6"))
            painter.drawEllipse(0, 0, 64, 64)
            painter.end()
            self.tray_icon.setIcon(QIcon(pixmap))

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
        self.clam_page, self.clam_status = self.create_page(
            "ClamAV Antivirus Daemon",
            "Protects the system against malicious files and trojans.",
            lambda: self.execute_sudo_cmd(self.clam_start_proc, ["/usr/sbin/service", "clamav-daemon", "start"]),
            lambda: self.execute_sudo_cmd(self.clam_stop_proc, ["/usr/sbin/service", "clamav-daemon", "stop"])
        )
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
