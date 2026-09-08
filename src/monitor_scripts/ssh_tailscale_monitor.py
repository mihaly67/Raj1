import sys
import subprocess
import re
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QLabel, QTextEdit, QSystemTrayIcon, QMenu, QAction, QFrame)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QIcon, QColor

class SysMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Jules SSH & Tailscale Monitor")
        self.resize(750, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QLabel { color: white; }
            QFrame#card {
                background-color: #1e293b;
                border-radius: 8px;
                border: 1px solid #334155;
            }
        """)

        icon_path = "/usr/share/icons/oxygen/base/128x128/places/network-server.png"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("network-wired"))

        # Main Widget and Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title Label
        title_label = QLabel("Hálózati Monitor (SSH & Tailscale)")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        layout.addWidget(title_label)

        # Text Area for Status
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        # Modern sötét terminál stílus a belső szövegdoboznak
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #0b0f19;
                color: #e2e8f0;
                font-family: monospace;
                font-size: 13px;
                border: none;
            }
        """)
        card_layout.addWidget(self.status_text)
        layout.addWidget(card)

        # Setup System Tray
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(QIcon.fromTheme("network-wired"))

        show_action = QAction("Megjelenítés", self)
        hide_action = QAction("Elrejtés", self)
        quit_action = QAction("Bezárás", self)

        show_action.triggered.connect(self.showNormal)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_clicked)
        self.tray_icon.show()

        # Update Timer - 5 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)

        # Initial Update
        self.update_status()

    def tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

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

            line = re.sub(r'deszkmihaly67@\s+linux\s+', '', line)
            parts = re.split(r'\s{2,}', line)

            if len(parts) >= 2:
                ip = parts[0]
                name = parts[1]
                status_raw = parts[2] if len(parts) > 2 else "-"
                status_raw_lower = status_raw.lower()

                # HTML styling based on status
                if name.lower() == "jules":
                    status = "<span style='color:#3b82f6;'>[Helyi gép / ONLINE]</span>"
                elif "active" in status_raw_lower:
                    status = "<span style='color:#22c55e;'>[ONLINE / AKTÍV]</span>"
                elif "idle" in status_raw_lower:
                    status = "<span style='color:#10b981;'>[ONLINE / IDLE]</span>"
                elif "offline" in status_raw_lower:
                    status = "<span style='color:#ef4444;'>[OFFLINE]</span>"
                else:
                    status = "<span style='color:#eab308;'>[ONLINE / STANDBY]</span>"

                parsed_lines.append(f"{ip:<15} {name:<12} {status}")
            else:
                parsed_lines.append(line)

        if not parsed_lines:
            return "<span style='color:#94a3b8;'>Nincs adat a hálózatról.</span>"

        return "<br>".join(parsed_lines)

    def update_status(self):
        output = "<h3 style='color:#64748b; margin-bottom:5px;'>=== SSH SZOLGÁLTATÁS ÁLLAPOTA ===</h3>"
        ssh_status = self.run_cmd("/etc/init.d/ssh status")

        # Colorize SSH output
        if "is running" in ssh_status or "active (running)" in ssh_status:
            ssh_status = f"<span style='color:#22c55e;'>{ssh_status}</span>"
        else:
            ssh_status = f"<span style='color:#ef4444;'>{ssh_status}</span>"

        output += f"{ssh_status}<br><br>"

        output += "<h3 style='color:#64748b; margin-bottom:5px;'>=== NYITOTT PORTOK (Tűzfal / Listen) ===</h3>"
        ports = self.run_cmd("ss -ltn | grep -E ':22 |:8000 |:8765 |:5555 |:5556 |:5557 '")
        if ports:
            # Highlight ports logically
            ports = ports.replace("\n", "<br>")
            output += f"<span style='color:#cbd5e1;'>{ports}</span><br><br>"
        else:
            output += "<span style='color:#94a3b8;'>Nincsenek figyelt portok.</span><br><br>"

        output += "<h3 style='color:#64748b; margin-bottom:5px;'>=== TAILSCALE HÁLÓZAT (Devboxok) ===</h3>"
        ts_status = self.run_cmd("tailscale status")
        output += f"{self.parse_tailscale(ts_status)}<br>"

        self.status_text.setHtml(output)

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
    app.setStyle('Fusion')
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
