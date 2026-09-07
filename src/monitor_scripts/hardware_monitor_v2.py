import sys
import psutil
import subprocess
import os
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
        self.setFixedHeight(15) # Magasság felezve (30 -> 15)

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

        # Szöveg kiírása (kisebb font miatt 15px-be férjen)
        painter.setPen(QColor("white"))
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        text = f"{self.label_text} [{self.val1+self.val2:.1f}%]"
        painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "  " + text)


class MultiBar(QWidget):
    def __init__(self, label_text, color_map, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.color_map = color_map # list of (color_hex, value_percentage)
        self.setFixedHeight(15)
        self.text_override = ""

    def update_values(self, color_map, text_override=""):
        self.color_map = color_map
        self.text_override = text_override
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor("#1e293b"))

        width = self.rect().width()
        height = self.rect().height()

        current_x = 0
        for color_hex, val_pct in self.color_map:
            w = int((val_pct / 100.0) * width)
            if w > 0:
                painter.fillRect(current_x, 0, w, height, QColor(color_hex))
                current_x += w

        painter.setPen(QColor("white"))
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        text = self.text_override if self.text_override else self.label_text
        painter.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft, "  " + text)


class HardwareMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hardver Monitor (Htop + Nvtop)")
        self.resize(1000, 800)
        self.setStyleSheet("QMainWindow { background-color: #0f172a; color: white; }")

        # Ablak ikon (Tálcára tételhez klasszikus system monitor ikon pajzs helyett)
        icon_path = "/usr/share/icons/oxygen/base/128x128/apps/utilities-system-monitor.png"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme("utilities-system-monitor"))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # --- Felső statisztikák (Htop stílus) ---
        self.stats_header = QLabel("Uptime: N/A  |  Load average: N/A  |  Tasks: N/A")
        self.stats_header.setStyleSheet("color: #cbd5e1; font-weight: bold; font-size: 13px; margin-bottom: 5px;")
        self.layout.addWidget(self.stats_header)

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
            bar = ResourceBar(f"{i+1}")
            self.cpu_bars.append(bar)
            if i % 2 == 0:
                col1.addWidget(bar)
            else:
                col2.addWidget(bar)
        cpu_layout.addLayout(col1)
        cpu_layout.addLayout(col2)
        self.layout.addLayout(cpu_layout)

        # --- Memória és Swap ---
        mem_layout = QVBoxLayout()

        # Jelmagyarázat
        legend_lbl = QLabel("Jelmagyarázat: [Zöld=Használt] [Kék=Puffer] [Sárga=Cache] | CPU: [Zöld=User] [Vörös=Sys]")
        legend_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        mem_layout.addWidget(legend_lbl)

        self.mem_bar = MultiBar("Mem", [])
        self.swap_bar = MultiBar("Swp", [])
        mem_layout.addWidget(self.mem_bar)
        mem_layout.addWidget(self.swap_bar)
        self.layout.addLayout(mem_layout)

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

    def get_uptime(self):
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
            hours, rem = divmod(uptime_seconds, 3600)
            minutes, _ = divmod(rem, 60)
            return f"{int(hours):02d}:{int(minutes):02d}:{int(_):02d}"
        except:
            return "N/A"

    def get_loadavg(self):
        try:
            avg1, avg5, avg15 = os.getloadavg()
            return f"{avg1:.2f} {avg5:.2f} {avg15:.2f}"
        except:
            return "N/A"

    def update_stats(self):
        # 0. Felső Statisztika Frissítés
        try:
            tasks_total = len(psutil.pids())
            # Gyors becslés a running taskokra htop stílusban
            running = len([p for p in psutil.process_iter(['status']) if p.info.get('status') == psutil.STATUS_RUNNING])

            uptime = self.get_uptime()
            loadavg = self.get_loadavg()

            self.stats_header.setText(f"Uptime: {uptime}  |  Load average: {loadavg}  |  Tasks: {tasks_total}, {running} running")
        except:
            pass

        # 1. CPU Frissítés
        total_times = psutil.cpu_times_percent(percpu=False)
        self.total_cpu_bar.update_values(total_times.user, total_times.system)

        core_times = psutil.cpu_times_percent(percpu=True)
        for i, c in enumerate(core_times):
            if i < len(self.cpu_bars):
                self.cpu_bars[i].update_values(c.user, c.system)

        # 1.5 Memória és SWAP
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        mem_used_pct = (mem.used / mem.total) * 100
        mem_buff_pct = (getattr(mem, 'buffers', 0) / mem.total) * 100
        mem_cach_pct = (getattr(mem, 'cached', 0) / mem.total) * 100

        mem_colors = [
            ("#16a34a", mem_used_pct), # Zöld
            ("#2563eb", mem_buff_pct), # Kék
            ("#eab308", mem_cach_pct), # Sárga
        ]
        used_gb = mem.used / (1024**3)
        total_gb = mem.total / (1024**3)
        self.mem_bar.update_values(mem_colors, f"Mem [{used_gb:.1f}G / {total_gb:.1f}G]")

        swap_used_pct = (swap.used / swap.total) * 100 if swap.total > 0 else 0
        swap_colors = [("#dc2626", swap_used_pct)] # Piros swap
        swap_gb = swap.used / (1024**3)
        swap_tot_gb = swap.total / (1024**3)
        self.swap_bar.update_values(swap_colors, f"Swp [{swap_gb:.1f}G / {swap_tot_gb:.1f}G]")

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
                    pid_item.setData(Qt.UserRole, int(pid))

                    cpu_item = NumericItem()
                    cpu_item.setData(Qt.DisplayRole, f"{cpu:.1f}")
                    cpu_item.setData(Qt.UserRole, float(cpu))

                    ram_item = NumericItem()
                    ram_item.setData(Qt.DisplayRole, f"{ram:.1f}")
                    ram_item.setData(Qt.UserRole, float(ram))

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
