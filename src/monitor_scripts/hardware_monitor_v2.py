import sys
import psutil
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QIcon

class ResourceBar(QWidget):
    def __init__(self, label_text, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.val1 = 0.0 # Zöld (User)
        self.val2 = 0.0 # Vörös (System/Kernel)
        self.setFixedHeight(30)

    def update_values(self, val1, val2=0.0):
        self.val1 = val1
        self.val2 = val2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Háttér (sötét kék/szürke)
        painter.fillRect(self.rect(), QColor("#1e293b"))

        width = self.rect().width()
        height = self.rect().height()

        total = self.val1 + self.val2
        if total > 100:
            total = 100

        w1 = int((self.val1 / 100.0) * width)
        w2 = int((self.val2 / 100.0) * width)

        # Erdőzöld (val1)
        painter.fillRect(0, 0, w1, height, QColor("#16a34a"))
        # Téglavörös (val2)
        painter.fillRect(w1, 0, w2, height, QColor("#dc2626"))

        # Szöveg kiírása
        painter.setPen(QColor("white"))
        font = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(font)
        text = f"{self.label_text} [{self.val1+self.val2:.1f}%]"
        painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "  " + text)

class HardwareMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hardver Monitor (Htop + Nvtop)")
        self.resize(1000, 800)
        self.setStyleSheet("QMainWindow { background-color: #0f172a; color: white; }")

        # Ablak ikon (Tálcára tételhez pajzs ikon)
        icon_path = "/usr/share/icons/oxygen/base/128x128/status/security-high.png"
        import os
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("utilities-system-monitor"))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # --- CPU Szekció ---
        self.cpu_bars = []
        self.cpu_count = psutil.cpu_count()

        cpu_header = QLabel(f"CPU Terhelés (Magok száma: {self.cpu_count})")
        cpu_header.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px;")
        self.layout.addWidget(cpu_header)

        self.total_cpu_bar = ResourceBar("CPU Összesített")
        self.layout.addWidget(self.total_cpu_bar)

        # CPU Magok elrendezése (2 oszlopos rács)
        cpu_layout = QHBoxLayout()
        col1 = QVBoxLayout()
        col2 = QVBoxLayout()
        for i in range(self.cpu_count):
            bar = ResourceBar(f"CPU Mag {i+1}")
            self.cpu_bars.append(bar)
            if i % 2 == 0:
                col1.addWidget(bar)
            else:
                col2.addWidget(bar)
        cpu_layout.addLayout(col1)
        cpu_layout.addLayout(col2)
        self.layout.addLayout(cpu_layout)

        # --- GPU Szekció ---
        gpu_header = QLabel("GPU & VRAM (NVIDIA)")
        gpu_header.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.layout.addWidget(gpu_header)

        self.gpu_bar = ResourceBar("GPU Mag")
        self.vram_bar = ResourceBar("VRAM")
        self.layout.addWidget(self.gpu_bar)
        self.layout.addWidget(self.vram_bar)

        # --- Processzek (Win XP Stílusú táblázat) ---
        proc_header = QLabel("Folyamatok (Processzek)")
        proc_header.setStyleSheet("color: #64748b; font-weight: bold; font-size: 14px; margin-top: 10px;")
        self.layout.addWidget(proc_header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Név / Argumentumok", "PID", "CPU %", "RAM %"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e293b; color: white; gridline-color: #334155; border: none; }
            QHeaderView::section { background-color: #0f172a; color: #94a3b8; font-weight: bold; border: 1px solid #334155; }
        """)
        self.layout.addWidget(self.table)

        self.processes = {} # {pid: row_index}
        self.process_cache = {} # {pid: psutil.Process instance}

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000) # 2 másodperces frissítés

        self.update_stats()
        # Alapértelmezett rendezés Név alapján (ABC) - mint Win XP
        self.table.sortItems(0, Qt.AscendingOrder)

    def update_stats(self):
        # 1. CPU Frissítés
        total_times = psutil.cpu_times_percent(percpu=False)
        self.total_cpu_bar.update_values(total_times.user, total_times.system)

        core_times = psutil.cpu_times_percent(percpu=True)
        for i, c in enumerate(core_times):
            if i < len(self.cpu_bars):
                self.cpu_bars[i].update_values(c.user, c.system)

        # 2. GPU Frissítés
        try:
            cmd = "nvidia-smi --query-gpu=utilization.gpu,utilization.memory --format=csv,noheader,nounits"
            output = subprocess.check_output(cmd, shell=True, text=True).strip()
            if output:
                parts = output.split(',')
                if len(parts) >= 2:
                    gpu_util = float(parts[0].strip())
                    mem_util = float(parts[1].strip())
                    self.gpu_bar.update_values(gpu_util)
                    self.vram_bar.update_values(mem_util)
        except Exception as e:
            self.gpu_bar.update_values(0)
            self.vram_bar.update_values(0)
            self.gpu_bar.label_text = "GPU (Nem elérhető nvidia-smi)"

        # 3. Processzek Frissítése
        is_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False) # Ideiglenesen kikapcsoljuk az ugrálás miatt

        current_pids = set()

        # Csak a memóriát, cmdline-t kérjük iterációkor
        for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent']):
            try:
                info = p.info
                pid = info['pid']
                current_pids.add(pid)

                if pid not in self.process_cache:
                    self.process_cache[pid] = p
                    p.cpu_percent(interval=None) # Inicializálás
                    cpu = 0.0
                else:
                    cpu = self.process_cache[pid].cpu_percent(interval=None)

                # Hogy a 100% a teljes gépet jelentse, nem csak 1 magot (Win XP Task Manager stílus):
                cpu = cpu / self.cpu_count

                cmdline = info.get('cmdline')
                if cmdline:
                    name = " ".join(cmdline)
                else:
                    name = info.get('name', 'Ismeretlen')

                ram = info.get('memory_percent', 0.0) or 0.0

                class NumericItem(QTableWidgetItem):
                    def __lt__(self, other):
                        if (isinstance(other, QTableWidgetItem)):
                            return self.data(Qt.UserRole) < other.data(Qt.UserRole)
                        return super(NumericItem, self).__lt__(other)

                if pid in self.processes:
                    # Meglévő sor frissítése (in-place update, így nem ugrál a kurzor)
                    row = self.processes[pid]

                    cpu_item = self.table.item(row, 2)
                    cpu_item.setData(Qt.DisplayRole, f"{cpu:.1f}")
                    cpu_item.setData(Qt.UserRole, cpu)

                    ram_item = self.table.item(row, 3)
                    ram_item.setData(Qt.DisplayRole, f"{ram:.1f}")
                    ram_item.setData(Qt.UserRole, ram)
                else:
                    # Új sor beszúrása
                    row = self.table.rowCount()
                    self.table.insertRow(row)

                    name_item = QTableWidgetItem(name)

                    pid_item = NumericItem()
                    pid_item.setData(Qt.DisplayRole, str(pid))
                    pid_item.setData(Qt.UserRole, pid)

                    cpu_item = NumericItem()
                    cpu_item.setData(Qt.DisplayRole, f"{cpu:.1f}")
                    cpu_item.setData(Qt.UserRole, cpu)

                    ram_item = NumericItem()
                    ram_item.setData(Qt.DisplayRole, f"{ram:.1f}")
                    ram_item.setData(Qt.UserRole, ram)

                    self.table.setItem(row, 0, name_item)
                    self.table.setItem(row, 1, pid_item)
                    self.table.setItem(row, 2, cpu_item)
                    self.table.setItem(row, 3, ram_item)

                    self.processes[pid] = row
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Halott processzek törlése
        pids_to_remove = set(self.processes.keys()) - current_pids
        if pids_to_remove:
            rows_to_remove = sorted([self.processes[pid] for pid in pids_to_remove], reverse=True)
            for row in rows_to_remove:
                self.table.removeRow(row)

            for pid in pids_to_remove:
                if pid in self.process_cache:
                    del self.process_cache[pid]

            # Újraépítjük a sor indexeket a törlés után
            self.processes = {}
            for row in range(self.table.rowCount()):
                pid = self.table.item(row, 1).data(Qt.UserRole)
                self.processes[pid] = row

        if is_sorting:
            self.table.setSortingEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = HardwareMonitor()
    window.show()
    sys.exit(app.exec_())
