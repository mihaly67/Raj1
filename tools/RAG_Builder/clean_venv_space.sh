#!/bin/bash
echo "[*] VENV és felesleges pip cache gigabájtok takarítása a Jules gépen..."
cd /home/Jules/MX_LINUX_RAG

# A Pip cache takarítása (akár 3-4 GB)
rm -rf ~/.cache/pip

# Töröljük az eddigi gigantikus venv-et
rm -rf venv

echo "[*] Felesleges adatok törölve!"
echo "[*] Most futtasd újra a optimalizált telepítőt: bash install_rag_deps_cuda.sh"
