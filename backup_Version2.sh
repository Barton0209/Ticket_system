#!/usr/bin/env bash
set -euo pipefail

SRC="$(pwd)"
DEST_BASE="/c/Backup"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DEST="${DEST_BASE}/Ticket_system_${TIMESTAMP}"

EXCLUDES=(--exclude='.git' --exclude='venv' --exclude='node_modules')

mkdir -p "$DEST"
echo "Source: $SRC"
echo "Destination: $DEST"

# 1) rsync
if command -v rsync >/dev/null 2>&1; then
  echo "Using rsync..."
  rsync -av "${EXCLUDES[@]}" --progress "$SRC/" "$DEST/"
  echo "Backup completed: $DEST"
  exit 0
fi

# 2) robocopy (если на Windows — доступен через cmd)
if command -v cmd.exe >/dev/null 2>&1 && command -v robocopy >/dev/null 2>&1; then
  echo "Using robocopy..."
  # Преобразуем пути в Windows-формат
  WIN_SRC=$(cygpath -w "$SRC")
  WIN_DEST=$(cygpath -w "$DEST")
  # Выполнить robocopy
  cmd.exe /c "robocopy \"$WIN_SRC\" \"$WIN_DEST\" /E /MT:8 /XD .git venv node_modules /R:2 /W:5"
  echo "Backup completed: $DEST"
  exit 0
fi

# 3) fallback — cp или tar
echo "rsync and robocopy not found — using cp/tar fallback"
if cp --help >/dev/null 2>&1; then
  cp -a "$SRC/." "$DEST/"
  echo "Backup completed with cp: $DEST"
  exit 0
else
  # tar stream
  (cd "$SRC" && tar -cf - .) | (cd "$DEST" && tar -xf -)
  echo "Backup completed with tar: $DEST"
  exit 0
fi