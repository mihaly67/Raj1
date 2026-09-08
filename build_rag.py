import os
import sqlite3
import json
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Konfiguráció
TARGET_DIR = "/home/misi/MX_LINUX_RAG"
DB_PATH = "/home/misi/MX_LINUX_RAG/mx_linux_hybrid.db"
FAISS_PATH = "/home/misi/MX_LINUX_RAG/mx_linux_vector.index"
EXTENSIONS = {'.py', '.c', '.h', '.cpp', '.sh', '.md', '.rst', '.json', '.yaml', '.txt', '.conf', '.mk', '.dts', '.dtsi'}
CHUNK_SIZE = 1500

def get_files(directory):
    file_list = []
    for root, _, files in os.walk(directory):
        if '.git' in root or 'node_modules' in root or '__pycache__' in root:
            continue
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in EXTENSIONS:
                file_list.append(os.path.join(root, file))
    return file_list

def chunk_text(text, max_length):
    """Egyszerű darabolás karakterhossz alapján."""
    chunks = []
    for i in range(0, len(text), max_length):
        chunks.append(text[i:i+max_length])
    return chunks

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # FTS5 tábla a kulcsszavas kereséshez
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS rag_docs USING fts5(
            path, content, tokenize='porter'
        )
    ''')

    # Metaadat tábla a vektorok azonosítóihoz
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rag_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

def main():
    print(f"[*] Fájlok keresése a {TARGET_DIR} könyvtárban...")
    files = get_files(TARGET_DIR)
    print(f"[*] Összesen {len(files)} feldolgozandó fájl található.")

    print("[*] SQLite adatbázis inicializálása...")
    conn, cursor = init_db(DB_PATH)

    print("[*] SentenceTransformer modell betöltése (all-MiniLM-L6-v2) CPU-n...")
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    dimension = model.get_sentence_embedding_dimension()

    print("[*] FAISS index inicializálása (L2 távolság)...")
    index = faiss.IndexFlatL2(dimension)

    print("[*] Fájlok feldolgozása, chunkolása és vektorizálása...")

    for filepath in tqdm(files, desc="Fájlok feldolgozása"):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            continue

        if not content.strip():
            continue

        chunks = chunk_text(content, CHUNK_SIZE)

        for chunk in chunks:
            # 1. SQLite FTS beszúrás
            cursor.execute("INSERT INTO rag_docs (path, content) VALUES (?, ?)", (filepath, chunk))

            # 2. SQLite Meta beszúrás (hogy tudjuk melyik FAISS ID melyik szöveghez tartozik)
            cursor.execute("INSERT INTO rag_meta (path, content) VALUES (?, ?)", (filepath, chunk))
            doc_id = cursor.lastrowid

            # 3. FAISS Vektorizálás és indexelés
            # Tqdm frissítés miatt ezt egyenként csináljuk (optimalizálható lenne batch-ekkel, de a konzol kimenet miatt így jobban látszik)
            vector = model.encode([chunk], convert_to_numpy=True)
            faiss.normalize_L2(vector)
            index.add(vector)

    conn.commit()
    conn.close()

    print("[*] FAISS index mentése a lemezre...")
    faiss.write_index(index, FAISS_PATH)
    print(f"[*] Kész! SQLite DB mentve: {DB_PATH}")
    print(f"[*] FAISS Index mentve: {FAISS_PATH}")

if __name__ == "__main__":
    main()
