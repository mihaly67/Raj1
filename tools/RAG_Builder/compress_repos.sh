#!/bin/bash
set -e

TARGET_DIR="/home/misi/MX_LINUX_RAG"

echo "[*] Tömörítő szkript indítása..."
cd "$TARGET_DIR"

# Töröljük a korábbi hibás (32 byte-os) fájlokat
echo "[*] Korábbi hibás tömörítések törlése..."
rm -f *.tar.xz

# Kiszűrjük a mappákat
DIRECTORIES=$(find . -maxdepth 1 -type d | grep -v '^\.$' | grep -v '\.git' | grep -v 'venv' | sed 's|^\./||')
TOTAL_DIRS=$(echo "$DIRECTORIES" | wc -l)
CURRENT_DIR_NUM=1

echo "[*] Összesen $TOTAL_DIRS könyvtár vár maximális szintű (xz -9) tömörítésre."
echo "--------------------------------------------------------------------------------"

for DIR in $DIRECTORIES; do
    echo "[$CURRENT_DIR_NUM / $TOTAL_DIRS] Csomagolás: $DIR"

    # A pv hibát okozott, ezért eltávolítjuk. A tar beépített J kapcsolójával használjuk az xz-t.
    # Exportáljuk az XZ_DEFAULTS változót, hogy maximalizáljuk a tömörítést és használja a szálakat.
    export XZ_OPT="-9 -T0"

    # Közvetlen tömörítés
    tar -cJf "${DIR}.tar.xz" "$DIR"

    echo "✅ $DIR csomagolása befejeződött -> ${DIR}.tar.xz"
    echo "--------------------------------------------------------------------------------"
    ((CURRENT_DIR_NUM++))
done

echo "[*] 🎉 Minden repó sikeresen be lett csomagolva!"
