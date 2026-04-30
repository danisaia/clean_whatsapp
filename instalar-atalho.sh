#!/usr/bin/env bash
set -e

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BIN_DIR="${PREFIX:-/data/data/com.termux/files/usr}/bin"
COMMAND_PATH="$BIN_DIR/limpar-whatsapp"

mkdir -p "$BIN_DIR"

cat > "$COMMAND_PATH" <<EOF
#!/usr/bin/env bash
set -e
cd "$APP_DIR"
exec python3 "$APP_DIR/scripts/clean_whatsapp.py" "\$@"
EOF

chmod +x "$COMMAND_PATH"

echo "Atalho instalado com sucesso."
echo "Agora você pode abrir o app digitando:"
echo
echo "  limpar-whatsapp"
