#!/usr/bin/env bash
set -e

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
BIN_DIR="${PREFIX:-/data/data/com.termux/files/usr}/bin"
COMMAND_PATH="$BIN_DIR/clean-whatsapp"

mkdir -p "$BIN_DIR"

cat > "$COMMAND_PATH" <<EOF
#!/usr/bin/env bash
set -e
cd "$APP_DIR"
exec python3 "$APP_DIR/scripts/clean_whatsapp.py" "\$@"
EOF

chmod +x "$COMMAND_PATH"

case "${LANG:-en}" in
  pt*|PT*)
    echo "Atalho do Clean WhatsApp instalado com sucesso."
    echo "Agora você pode abrir o Clean WhatsApp digitando:"
    ;;
  es*|ES*)
    echo "Acceso directo de Clean WhatsApp instalado correctamente."
    echo "Ahora puedes abrir Clean WhatsApp escribiendo:"
    ;;
  fr*|FR*)
    echo "Raccourci Clean WhatsApp installé avec succès."
    echo "Vous pouvez maintenant ouvrir Clean WhatsApp en tapant :"
    ;;
  *)
    echo "Clean WhatsApp shortcut installed successfully."
    echo "You can now open Clean WhatsApp by typing:"
    ;;
esac
echo
echo "  clean-whatsapp"
