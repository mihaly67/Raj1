import os
import subprocess
import time

TARGET_DIR = "/home/misi/MX_LINUX_RAG"

extra_repos = {
    "cpufreq": "https://github.com/vagnum08/cpufreq.git", # CPU tuning tool
    "intel-undervolt": "https://github.com/kitsunyan/intel-undervolt.git", # undervolting intel
    "undervolt": "https://github.com/georgewhewell/undervolt.git", # undervolt python script
    "hp-z440-fan-control": "https://github.com/s0up/hp-z440-fan-control.git", # HP Z440 specific
    "linux-intel-undervolt-gui": "https://github.com/mihic/linux-intel-undervolt-gui.git",
    "cpupower-gui": "https://github.com/vagnum08/cpupower-gui.git",
    "turbostat": "https://github.com/torvalds/linux/tree/master/tools/power/x86/turbostat", # Note: not directly cloneable, using alternatives
    "NVIDIA-Linux-x86_64": "https://github.com/NVIDIA/open-gpu-kernel-modules.git", # CUDA/Nvidia kernel
    "cuda-samples": "https://github.com/NVIDIA/cuda-samples.git", # CUDA
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

    for name, clone_url in extra_repos.items():
        if "tree/master" not in clone_url:
            clone_path = os.path.join(TARGET_DIR, name)
            if not os.path.exists(clone_path):
                print(f"Cloning {name}...")
                run_cmd(f"git clone {clone_url} {clone_path}")
                time.sleep(1)

if __name__ == '__main__':
    main()
