import os
import subprocess
import time

TARGET_DIR = "/home/misi/MX_LINUX_RAG"

# A felhasználó kérésére kifejezetten Xeon V3/V4 (Haswell/Broadwell-EP), HP Z440,
# magfeszültség és CUDA szabályozás témájú repók begyűjtése
xeon_cuda_repos = {
    "xeon-e5-v3-v4-turbo-unlock": "https://github.com/Koshak1013/HuananzhiX99_BIOS_mods.git", # Xeon V3 turbo unlock, undervolting bios mods
    "x99-tu-fwh-v3": "https://github.com/freecableguy/x99-tu-fwh.git", # Haswell-EP V3 Turbo Unlock
    "intel-pstate-control": "https://github.com/jlelli/intel-pstate-control.git", # CPU freq scaling
    "throttled": "https://github.com/erpalma/throttled.git", # Fix intel CPU throttling (undervolt/power limits)
    "linux-msr-tools": "https://github.com/intel/msr-tools.git", # Model Specific Registers (Voltage/Frequency)
    "hp-z-workstation-mac-pro": "https://github.com/khronokernel/HP-Z440-Z640-Z840-macOS.git", # Includes ACPI and SSDT tables for HP Z440 which are OS agnostic hardware insights
    "nvidia-smi-undervolt": "https://github.com/brianpowell/nvidia-smi-undervolt.git", # CUDA/Nvidia power management
    "nvitop": "https://github.com/XuehaiPan/nvitop.git", # NVIDIA GPU monitoring and control
    "cuda-samples-11.4": "https://github.com/NVIDIA/cuda-samples.git", # Official CUDA Samples for architecture
    "linux-cpupower": "https://github.com/torvalds/linux/tree/master/tools/power/cpupower" # Not direct clone, will use generic sysfs cpufreq scripts instead below if needed
}

def run_cmd(cmd):
    try:
        subprocess.run(cmd, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        pass

def main():
    if not os.path.exists(TARGET_DIR):
        print(f"Target dir {TARGET_DIR} not found.")
        return

    for name, clone_url in xeon_cuda_repos.items():
        if "tree/master" not in clone_url:
            clone_path = os.path.join(TARGET_DIR, name)
            if not os.path.exists(clone_path):
                print(f"Cloning {name}...")
                run_cmd(f"git clone {clone_url} {clone_path}")
                time.sleep(1)

if __name__ == '__main__':
    main()
