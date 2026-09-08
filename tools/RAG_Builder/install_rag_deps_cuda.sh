#!/bin/bash

# A felhasználó kérésére NEM hozunk létre új 5GB-os venv-et, hanem a már meglévő
# központi 8GB-os környezetet aktiváljuk a fizikai gépen.
VENV_PATH="/home/Jules/jules_venv"

echo "[*] Központi VENV aktiválása ($VENV_PATH)..."
source "$VENV_PATH/bin/activate"

echo "[*] Függőségek ellenőrzése és telepítése a központi venv-be..."
pip install --upgrade pip

# Telepítjük a hiányzó CUDA-s RAG csomagokat
pip install --no-cache-dir sentence-transformers tqdm faiss-gpu

echo "[*] Függőségek telepítve CUDA támogatással! A RAG építő szkript futtatásához indítsd el:"
echo "source $VENV_PATH/bin/activate"
echo "python3 /home/Jules/MX_LINUX_RAG/build_rag_cuda.py"
