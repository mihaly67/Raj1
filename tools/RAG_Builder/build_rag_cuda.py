import os
import sqlite3
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Konfiguráció a saját géphez
TARGET_DIR = "/home/Jules/MX_LINUX_RAG" # Kérlek, ide másold át a repókat a VPS-ről, vagy klónozd le őket újra!
DB_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_hybrid.db"
FAISS_PATH = "/home/Jules/MX_LINUX_RAG/mx_linux_vector.index"
REPO_LIST_PATH = "/home/Jules/MX_LINUX_RAG/vectorized_repos.txt"
EXTENSIONS = {'.py', '.c', '.h', '.cpp', '.sh', '.md', '.rst', '.json', '.yaml', '.txt', '.conf', '.mk', '.dts', '.dtsi'}
CHUNK_SIZE = 1500
BATCH_SIZE = 64 # A P2000 memóriájától függően növelhető (pl. 128)

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
            path TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

def main():
    if not os.path.exists(TARGET_DIR):
        print(f"Hiba: A {TARGET_DIR} mappa nem létezik. Kérlek, először hozd létre és másold át ide a repókat.")
        return

    print(f"[*] Fájlok keresése a {TARGET_DIR} könyvtárban...")
    files, repos = get_files_and_repos(TARGET_DIR)
    print(f"[*] Összesen {len(files)} feldolgozandó fájl található {len(repos)} repóból.")

    print(f"[*] Repolista mentése ide: {REPO_LIST_PATH}")
    with open(REPO_LIST_PATH, 'w', encoding='utf-8') as f:
        for r in sorted(repos):
            f.write(r + '\n')

    print("[*] SQLite adatbázis inicializálása...")
    conn, cursor = init_db(DB_PATH)

    print("[*] SentenceTransformer modell betöltése (all-MiniLM-L6-v2) GPU-n (CUDA)...")
    # A 'cuda' argumentum automatikusan átirányítja a terhelést a Quadro P2000-re.
    model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')
    dimension = model.get_sentence_embedding_dimension()

    print("[*] FAISS GPU index inicializálása (L2 távolság)...")
    res = faiss.StandardGpuResources() # FAISS GPU erőforrások inicializálása
    cpu_index = faiss.IndexFlatL2(dimension)
    index = faiss.index_cpu_to_gpu(res, 0, cpu_index) # Mozgatás a 0-s azonosítójú GPU-ra

    print("[*] Fájlok feldolgozása és chunkolása...")
    all_chunks = []
    chunk_metadata = []

    for filepath in tqdm(files, desc="Fájlok olvasása"):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue

        if not content.strip():
            continue

        chunks = chunk_text(content, CHUNK_SIZE)
        for chunk in chunks:
            all_chunks.append(chunk)
            chunk_metadata.append(filepath)

    print(f"[*] Összesen {len(all_chunks)} db chunk (szövegrészlet) vár vektorizálásra.")
    print("[*] Vektorizálás és Indexelés (Batch feldolgozás GPU-val)...")

    # Batch (kötegelt) vektorizálás a GPU maximális kihasználásáért
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE), desc="Vektorizálás"):
        batch_chunks = all_chunks[i:i+BATCH_SIZE]
        batch_paths = chunk_metadata[i:i+BATCH_SIZE]

        # SQL adatbázis frissítése
        for filepath, chunk in zip(batch_paths, batch_chunks):
            cursor.execute("INSERT INTO rag_docs (path, content) VALUES (?, ?)", (filepath, chunk))
            cursor.execute("INSERT INTO rag_meta (path, content) VALUES (?, ?)", (filepath, chunk))

        # Vektorizálás és hozzáadás a FAISS-hez
        vectors = model.encode(batch_chunks, convert_to_numpy=True)
        faiss.normalize_L2(vectors)
        index.add(vectors)

    conn.commit()
    conn.close()

    print("[*] FAISS index visszamásolása a CPU-ra és mentés a lemezre...")
    # Mentéshez vissza kell alakítani CPU-s indexszé
    cpu_index_to_save = faiss.index_gpu_to_cpu(index)
    faiss.write_index(cpu_index_to_save, FAISS_PATH)

    print(f"[*] Kész! SQLite DB mentve: {DB_PATH}")
    print(f"[*] FAISS Index mentve: {FAISS_PATH}")
    print(f"[*] A vektorizált repók listája megtalálható: {REPO_LIST_PATH}")

if __name__ == "__main__":
    main()
