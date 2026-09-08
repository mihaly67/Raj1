#!/bin/bash
set -e
echo "[*] VENV Létrehozása az MX_LINUX_RAG könyvtárban a saját gépen (Jules)..."
cd /home/Jules/MX_LINUX_RAG
python3 -m venv venv
source venv/bin/activate

echo "[*] Függőségek telepítése (faiss-gpu, sentence-transformers, tqdm) CUDA támogatással..."
pip install --upgrade pip
# Kifejezetten a CUDA-s PyTorch-ot telepítjük
pip install sentence-transformers tqdm
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
# faiss-gpu telepítése a hardveres gyorsításhoz
pip install faiss-gpu

echo "[*] Függőségek telepítve CUDA támogatással! A RAG építő szkript futtatásához indítsd el:"
echo "source /home/Jules/MX_LINUX_RAG/venv/bin/activate"
echo "python3 /home/Jules/build_rag_cuda.py"
