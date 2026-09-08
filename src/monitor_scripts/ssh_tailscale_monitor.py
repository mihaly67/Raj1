import sys
import subprocess
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QLabel, QTextEdit, QSystemTrayIcon, QMenu, QAction, QStyle)
from PyQt5.QtCore import QTimer, Qt

class SysMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jules SSH & Tailscale Monitor")
        self.resize(700, 550)

        # Main Widget and Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Title Label
        self.title_label = QLabel("<b>Jules Box Rendszer Állapot (MX Linux / SysVinit)</b>")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # Text Area for Status
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        # Text is white per user request
        self.status_text.setStyleSheet("background-color: #1e1e1e; color: #ffffff; font-family: monospace; font-size: 13px;")
        layout.addWidget(self.status_text)

        # Setup System Tray
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        hide_action = QAction("Hide", self)

        show_action.triggered.connect(self.showNormal)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # Update Timer - 5 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)

        # Initial Update
        self.update_status()

    def run_cmd(self, cmd):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
            return result.stdout.strip() if result.stdout else result.stderr.strip()
        except Exception as e:
            return str(e)

    def parse_tailscale(self, ts_output):
        lines = ts_output.split("\n")
        parsed_lines = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Remove redundant user emails and OS info to clean up parsing
            line = re.sub(r'deszkmihaly67@\s+linux\s+', '', line)

            # Now parts should be roughly: IP, NAME, STATUS
            parts = re.split(r'\s{2,}', line)

            if len(parts) >= 2:
                ip = parts[0]
                name = parts[1]
                status_raw = parts[2] if len(parts) > 2 else "-"
                status_raw_lower = status_raw.lower()

                # Make status human readable
                if name.lower() == "jules":
                    status = "[Helyi gép / ONLINE]"
                elif "active" in status_raw_lower:
                    status = "[ONLINE / AKTÍV]"
                elif "idle" in status_raw_lower:
                    status = "[ONLINE / IDLE]"
                elif "offline" in status_raw_lower:
                    status = "[OFFLINE]"
                else:
                    status = "[ONLINE / STANDBY]" # Ha csak '-' van, az azt jelenti a tailscale-nél, hogy jelen van, de nincs forgalom

                parsed_lines.append(f"{ip:<15} {name:<12} {status}")
            else:
                parsed_lines.append(line)

        if not parsed_lines:
            return "Nincs adat a hálózatról."

        return "\n".join(parsed_lines)

    def update_status(self):
        output = "=== SSH SZOLGÁLTATÁS ÁLLAPOTA ===\n"
        ssh_status = self.run_cmd("/etc/init.d/ssh status")
        output += f"{ssh_status}\n\n"

        output += "=== NYITOTT PORTOK (Tűzfal / Listen) ===\n"
        ports = self.run_cmd("ss -ltn | grep -E ':22 |:8000 |:8765 |:5555 |:5556 |:5557 '")
        output += f"{ports}\n\n"

        output += "=== TAILSCALE HÁLÓZAT (Devboxok) ===\n"
        ts_status = self.run_cmd("tailscale status")
        output += f"{self.parse_tailscale(ts_status)}\n"

        self.status_text.setText(output)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Monitor Fut",
            "Az alkalmazás a tálcára került.",
            QSystemTrayIcon.Information,
            2000
        )


from PyQt5.QtNetwork import QLocalSocket, QLocalServer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    socket = QLocalSocket()
    socket.connectToServer('Jules_SSH_Monitor_Instance')
    if socket.waitForConnected(500):
        socket.write(b"SHOW")
        socket.waitForBytesWritten(500)
        sys.exit(0)

    server = QLocalServer()
    server.removeServer('Jules_SSH_Monitor_Instance')
    if not server.listen('Jules_SSH_Monitor_Instance'):
        print(f"Failed to listen on socket: {server.errorString()}")
        sys.exit(1)

    monitor = SysMonitor()

    def on_new_connection():
        conn = server.nextPendingConnection()
        conn.waitForReadyRead(500)
        conn.readAll()
        monitor.showNormal()
        monitor.activateWindow()

    server.newConnection.connect(on_new_connection)

    if "--hidden" not in sys.argv:
        monitor.show()

    sys.exit(app.exec_())
