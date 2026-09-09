import os
import sqlite3
import signal
import sys
import gc
import torch
import subprocess
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Konfiguráció a saját géphez
TARGET_DIR = "/home/Jules/MX_LINUX_RAG"
DB_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_hybrid.db"
FAISS_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_vector.index"
REPO_LIST_PATH = "/home/Jules/MX_LINUX_RAG/vectorized_repos.txt"
EXTENSIONS = {'.py', '.c', '.h', '.cpp', '.sh', '.md', '.rst', '.json', '.yaml', '.txt', '.conf', '.mk', '.dts', '.dtsi'}

CHUNK_SIZE = 1500
BATCH_SIZE = 32
MAX_CHUNKS_IN_RAM = 2000

SHUTDOWN_REQUESTED = False

def signal_handler(sig, frame):
    global SHUTDOWN_REQUESTED
    if not SHUTDOWN_REQUESTED:
        print("\n\n[!] Megszakítás (Ctrl+C) észlelve! Kérlek, várj amíg a program biztonságosan elmenti az eddigi adatokat...")
        SHUTDOWN_REQUESTED = True
    else:
        print("\n[!] Már folyamatban van a mentés és leállítás. Türelem...")

signal.signal(signal.SIGINT, signal_handler)

def shutdown_machine():
    """Leállítja a fizikai gépet a feladat végeztével."""
    print("\n[!] Vektorizálás befejeződött. A gép leállítása (shutdown) indul...")
    try:
        # Biztonsági hiba (Code Review): A plaintext jelszó (1104) eltávolítva.
        # A fizikai gép pkexec/sudoers szabályaira támaszkodunk, hogy végrehajtsa.
        cmd = "sudo shutdown -h now"
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print(f"Hiba a leállítás során: {e}")

def get_files_and_repos(directory):
    file_list = []
    vectorized_repos = set()
    for root, _, files in os.walk(directory):
        if '.git' in root or 'node_modules' in root or '__pycache__' in root:
            continue
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in EXTENSIONS:
                full_path = os.path.join(root, file)
                file_list.append(full_path)

                rel_path = os.path.relpath(root, directory)
                repo_name = rel_path.split(os.sep)[0]
                vectorized_repos.add(repo_name)

    return file_list, vectorized_repos

def chunk_text(text, max_length):
    chunks = []
    for i in range(0, len(text), max_length):
        chunks.append(text[i:i+max_length])
    return chunks

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS rag_docs USING fts5(
            path, content, tokenize='porter'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rag_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE
        )
    ''')
    conn.commit()
    return conn, cursor

def get_processed_files(cursor):
    cursor.execute("SELECT DISTINCT path FROM rag_meta")
    rows = cursor.fetchall()
    return set([row[0] for row in rows])

def save_state(conn, index, faiss_path, cursor, fully_processed_paths):
    for p in fully_processed_paths:
        cursor.execute("INSERT OR IGNORE INTO rag_meta (path) VALUES (?)", (p,))

    conn.commit()
    cpu_index_to_save = faiss.index_gpu_to_cpu(index)
    faiss.write_index(cpu_index_to_save, faiss_path)

    gc.collect()
    torch.cuda.empty_cache()

    print("\n[*] Állapot biztonságosan elmentve! Később folytathatod ugyanezzel a paranccsal.")

def process_batch(model, index, cursor, batch_chunks, batch_paths):
    vectors = model.encode(batch_chunks, convert_to_numpy=True)
    faiss.normalize_L2(vectors)
    index.add(vectors)

    for p, t in zip(batch_paths, batch_chunks):
        cursor.execute("INSERT INTO rag_docs (path, content) VALUES (?, ?)", (p, t))

def main():
    if not os.path.exists(TARGET_DIR):
        print(f"Hiba: A {TARGET_DIR} mappa nem létezik.")
        return

    print(f"[*] Fájlok keresése a {TARGET_DIR} könyvtárban...")
    files, repos = get_files_and_repos(TARGET_DIR)

    with open(REPO_LIST_PATH, 'w', encoding='utf-8') as f:
        for r in sorted(repos):
            f.write(r + '\n')

    print("[*] SQLite adatbázis inicializálása...")
    conn, cursor = init_db(DB_PATH)

    processed_files = get_processed_files(cursor)
    remaining_files = [f for f in files if f not in processed_files]

    print(f"[*] Összes fájl: {len(files)} | Már feldolgozva: {len(processed_files)} | Hátralévő: {len(remaining_files)}")
    if len(remaining_files) == 0:
        print("[*] Minden fájl feldolgozva!")
        shutdown_machine()
        return

    print("[*] SentenceTransformer modell betöltése GPU-n (CUDA)...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
    dimension = model.get_sentence_embedding_dimension()

    res = faiss.StandardGpuResources()
    if os.path.exists(FAISS_PATH):
        print("[*] Meglévő FAISS index betöltése a lemezről...")
        cpu_index = faiss.read_index(FAISS_PATH)
    else:
        print("[*] Új FAISS index létrehozása...")
        cpu_index = faiss.IndexFlatL2(dimension)

    index = faiss.index_cpu_to_gpu(res, 0, cpu_index)

    print("[*] Szövegek előkészítése és vektorizálása...")

    current_batch_chunks = []
    current_batch_paths = []

    fully_processed_paths = set()
    files_processed_since_save = 0

    for filepath in tqdm(remaining_files, desc="Fájlok feldolgozása"):
        if SHUTDOWN_REQUESTED:
            current_batch_chunks = []
            current_batch_paths = []
            break

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            fully_processed_paths.add(filepath)
            continue

        if not content.strip():
            fully_processed_paths.add(filepath)
            continue

        chunks = chunk_text(content, CHUNK_SIZE)
        current_batch_chunks.extend(chunks)
        current_batch_paths.extend([filepath] * len(chunks))

        while len(current_batch_chunks) >= BATCH_SIZE:
            if SHUTDOWN_REQUESTED:
                break

            batch_texts = current_batch_chunks[:BATCH_SIZE]
            batch_paths = current_batch_paths[:BATCH_SIZE]

            process_batch(model, index, cursor, batch_texts, batch_paths)

            current_batch_chunks = current_batch_chunks[BATCH_SIZE:]
            current_batch_paths = current_batch_paths[BATCH_SIZE:]

        if SHUTDOWN_REQUESTED:
            current_batch_chunks = []
            current_batch_paths = []
            break

        fully_processed_paths.add(filepath)
        files_processed_since_save += 1

        if files_processed_since_save >= 1000 or len(current_batch_chunks) >= MAX_CHUNKS_IN_RAM:
            while len(current_batch_chunks) > 0:
                chunk_sz = min(BATCH_SIZE, len(current_batch_chunks))
                batch_texts = current_batch_chunks[:chunk_sz]
                batch_paths = current_batch_paths[:chunk_sz]

                process_batch(model, index, cursor, batch_texts, batch_paths)

                current_batch_chunks = current_batch_chunks[chunk_sz:]
                current_batch_paths = current_batch_paths[chunk_sz:]

            save_state(conn, index, FAISS_PATH, cursor, fully_processed_paths)
            fully_processed_paths.clear()
            files_processed_since_save = 0

    if len(current_batch_chunks) > 0 and not SHUTDOWN_REQUESTED:
        while len(current_batch_chunks) > 0:
            chunk_sz = min(BATCH_SIZE, len(current_batch_chunks))
            batch_texts = current_batch_chunks[:chunk_sz]
            batch_paths = current_batch_paths[:chunk_sz]

            process_batch(model, index, cursor, batch_texts, batch_paths)

            current_batch_chunks = current_batch_chunks[chunk_sz:]
            current_batch_paths = current_batch_paths[chunk_sz:]

    save_state(conn, index, FAISS_PATH, cursor, fully_processed_paths)

    if not SHUTDOWN_REQUESTED:
        shutdown_machine()

if __name__ == "__main__":
    main()
