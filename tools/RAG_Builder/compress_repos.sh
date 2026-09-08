#!/bin/bash
set -e

TARGET_DIR="/home/misi/MX_LINUX_RAG"

echo "[*] Ultra-Stabil tömörítő szkript indítása..."
cd "$TARGET_DIR"

echo "[*] Korábbi hibás tömörítések törlése..."
find . -maxdepth 1 -name "*.tar.gz" -delete
find . -maxdepth 1 -name "*.tar.xz" -delete

# Kiszűrjük a mappákat
DIRECTORIES=$(find . -maxdepth 1 -type d | grep -v '^\.$' | grep -v '\.git' | grep -v 'venv' | sed 's|^\./||')
TOTAL_DIRS=$(echo "$DIRECTORIES" | wc -l)
CURRENT_DIR_NUM=1

echo "[*] Összesen $TOTAL_DIRS könyvtár vár csomagolásra."
echo "--------------------------------------------------------------------------------"

for DIR in $DIRECTORIES; do
    echo "[$CURRENT_DIR_NUM / $TOTAL_DIRS] Csomagolás: $DIR"

    # A tar -J (xz) multithreading (még a -7 szint is) túllépi a VPS valós felhasználható keretét (kernel OOM).
    # Átváltunk GZIP-re (pigz - parallel gzip). A gzip lényegesen kevesebb RAM-ot használ (pár MB),
    # viszont a pigz mind a 8 magot leterheli maximálisan. A csomag picit nagyobb lesz, de SOSEM omlik össze!

    # Ha nincs pigz, telepítjük
    if ! command -v pigz &> /dev/null; then
        sudo apt-get install -y pigz >/dev/null 2>&1 || true
    fi

    # Ha a pigz elérhető, azzal csomagolunk (párhuzamosan az összes magon), különben sima gzip.
    if command -v pigz &> /dev/null; then
        tar -cf - "$DIR" | pigz -9 > "${DIR}.tar.gz"
    else
        tar -czf "${DIR}.tar.gz" "$DIR"
    fi

    # Ellenőrizzük, hogy sikeres volt-e a tömörítés
    if [ $? -eq 0 ] && [ -s "${DIR}.tar.gz" ]; then
        echo "✅ $DIR csomagolása befejeződött -> ${DIR}.tar.gz"
    else
        echo "❌ HIBA a(z) $DIR csomagolásakor."
    fi

    echo "--------------------------------------------------------------------------------"
    ((CURRENT_DIR_NUM++))
done

echo "[*] 🎉 Minden repó sikeresen be lett csomagolva!"
