#!/bin/bash
set -e
echo "[*] VENV Létrehozása az MX_LINUX_RAG könyvtárban..."
cd /home/misi/MX_LINUX_RAG
python3 -m venv venv
source venv/bin/activate

echo "[*] Függőségek telepítése (faiss-cpu, sentence-transformers, tqdm)..."
pip install --upgrade pip
pip install faiss-cpu sentence-transformers tqdm torch --extra-index-url https://download.pytorch.org/whl/cpu

echo "[*] Függőségek telepítve. A RAG építő szkript futtatásához indítsd el:"
echo "source /home/misi/MX_LINUX_RAG/venv/bin/activate"
echo "python3 /home/misi/build_rag.py"
