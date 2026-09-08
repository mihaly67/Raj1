#!/bin/bash
set -e

TARGET_DIR="/home/misi/MX_LINUX_RAG"

echo "[*] Tömörítő szkript indítása. Függőségek ellenőrzése (pv, tar, xz)..."
sudo apt-get update >/dev/null 2>&1 || true
sudo apt-get install -y pv xz-utils tar >/dev/null 2>&1 || true

cd "$TARGET_DIR"

# Kiszűrjük a mappákat
DIRECTORIES=$(find . -maxdepth 1 -type d | grep -v '^\.$' | grep -v '\.git' | grep -v 'venv' | sed 's|^\./||')
TOTAL_DIRS=$(echo "$DIRECTORIES" | wc -l)
CURRENT_DIR_NUM=1

echo "[*] Összesen $TOTAL_DIRS könyvtár vár maximális szintű (xz -9) tömörítésre."
echo "[*] Megjegyzés: A 'xz -9T0' minden elérhető CPU magot használni fog a tömörítéshez."
echo "--------------------------------------------------------------------------------"

for DIR in $DIRECTORIES; do
    echo "[$CURRENT_DIR_NUM / $TOTAL_DIRS] Csomagolás: $DIR"

    # Kiszámoljuk a mappa méretét a folyamatjelzőhöz
    SIZE_BYTES=$(du -sb "$DIR" | awk '{print $1}')

    # Maximális xz tömörítés több szálon (-9T0 = legmagasabb fokozat, 0 = összes mag)
    tar -cf - "$DIR" | pv -s "$SIZE_BYTES" | xz -9T0 > "${DIR}.tar.xz"

    # Opcionális: Ha akarod, hogy az eredeti mappa törlődjön, vedd ki a kommentet az alábbi sorból
    # rm -rf "$DIR"

    echo "✅ $DIR csomagolása befejeződött -> ${DIR}.tar.xz"
    echo "--------------------------------------------------------------------------------"
    ((CURRENT_DIR_NUM++))
done

echo "[*] 🎉 Minden repó sikeresen be lett csomagolva!"
echo "[*] A letöltéshez használd az scp-t a saját gépeden, például:"
echo "scp misi@5.189.163.88:/home/misi/MX_LINUX_RAG/*.tar.xz /home/Jules/MX_LINUX_RAG/"
