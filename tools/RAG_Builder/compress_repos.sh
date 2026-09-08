#!/bin/bash
set -e

TARGET_DIR="/home/misi/MX_LINUX_RAG"

echo "[*] Végleges Párhuzamos-Biztonságos tömörítő szkript indítása..."
cd "$TARGET_DIR"

echo "[*] Korábbi hibás tömörítések törlése..."
find . -maxdepth 1 -name "*.tar.gz" -delete

# Kiszűrjük a mappákat, elmentjük őket egy listába
find . -maxdepth 1 -type d | grep -v '^\.$' | grep -v '\.git' | grep -v 'venv' | sed 's|^\./||' > dir_list.txt

TOTAL_DIRS=$(wc -l < dir_list.txt)
echo "[*] Összesen $TOTAL_DIRS könyvtár vár csomagolásra."
echo "--------------------------------------------------------------------------------"
echo "[*] Figyelem: Mostantól egyszerre 6 különböző repót csomagol a gép (sima gzip-el),"
echo "[*] így a memóriahasználat minimális marad, miközben az összes Ryzen mag dolgozik!"

# Csomagoló függvény definiálása (exportálni kell, hogy az xargs elérje)
compress_dir() {
    DIR="$1"
    # Sima GZIP: nagyon kevés memória, 1 magot használ 100%-on
    tar -czf "${DIR}.tar.gz" "$DIR"
    if [ $? -eq 0 ] && [ -s "${DIR}.tar.gz" ]; then
        echo "✅ $DIR befejeződött -> ${DIR}.tar.gz"
    else
        echo "❌ HIBA a(z) $DIR csomagolásakor."
    fi
}
export -f compress_dir

# Az xargs párhuzamosan elindít maximum 6 csomagoló folyamatot (-P 6)
# Így kb 6 mag mindig 100%-on megy, de a RAM nem terhelődik túl a multi-threading puffereléssel.
cat dir_list.txt | xargs -n 1 -P 6 -I {} bash -c 'compress_dir "{}"'

echo "--------------------------------------------------------------------------------"
echo "[*] 🎉 Minden repó párhuzamos csomagolása befejeződött!"
rm -f dir_list.txt
