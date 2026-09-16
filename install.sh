#!/usr/bin/env bash
# GlassForge - instalador
# Detecta a distro, instala dependências de sistema (GTK4, libadwaita, PyGObject,
# gtk4-layer-shell) e registra o app no menu (.desktop).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_PREFIX="${HOME}/.local"
BIN_DIR="${INSTALL_PREFIX}/bin"
APPS_DIR="${INSTALL_PREFIX}/share/applications"
LIB_DIR="${INSTALL_PREFIX}/lib/glassforge"

echo "==> GlassForge installer"

detect_pkg_manager() {
    if command -v apt >/dev/null 2>&1; then echo "apt"
    elif command -v dnf >/dev/null 2>&1; then echo "dnf"
    elif command -v pacman >/dev/null 2>&1; then echo "pacman"
    elif command -v zypper >/dev/null 2>&1; then echo "zypper"
    else echo "unknown"
    fi
}

PKG_MANAGER="$(detect_pkg_manager)"
echo "==> Gerenciador de pacotes detectado: ${PKG_MANAGER}"

install_system_deps() {
    case "$PKG_MANAGER" in
        apt)
            sudo apt update
            sudo apt install -y \
                python3 python3-gi python3-gi-cairo python3-pip \
                gir1.2-gtk-4.0 gir1.2-adw-1 \
                libgtk-4-1 libadwaita-1-0 \
                gir1.2-gtk4layershell-1.0 || echo "AVISO: gtk4-layer-shell pode não estar no repositório da sua distro/versão; veja INSTALL.md."
            ;;
        dnf)
            sudo dnf install -y \
                python3 python3-gobject python3-pip \
                gtk4 libadwaita \
                gtk4-layer-shell || echo "AVISO: gtk4-layer-shell pode precisar de um COPR; veja INSTALL.md."
            ;;
        pacman)
            sudo pacman -Sy --needed --noconfirm \
                python python-gobject python-pip \
                gtk4 libadwaita gtk4-layer-shell
            ;;
        zypper)
            sudo zypper install -y \
                python3 python3-gobject python3-pip \
                gtk4 libadwaita-1-0 gtk4-layer-shell || true
            ;;
        *)
            echo "!! Gerenciador de pacotes não reconhecido."
            echo "!! Instale manualmente: python3, PyGObject, GTK4, libadwaita, gtk4-layer-shell."
            echo "!! Veja INSTALL.md para instruções detalhadas por distro."
            ;;
    esac
}

install_system_deps

echo "==> Instalando GlassForge em ${LIB_DIR}"
mkdir -p "$LIB_DIR" "$BIN_DIR" "$APPS_DIR"
cp -r "$REPO_DIR/glassforge" "$LIB_DIR/"
cp "$REPO_DIR/requirements.txt" "$LIB_DIR/"

python3 -m pip install --user -r "$REPO_DIR/requirements.txt" --break-system-packages 2>/dev/null \
    || python3 -m pip install --user -r "$REPO_DIR/requirements.txt"

cat > "$BIN_DIR/glassforge" << EOF
#!/usr/bin/env bash
export PYTHONPATH="${LIB_DIR}:\${PYTHONPATH:-}"
exec python3 -m glassforge "\$@"
EOF
chmod +x "$BIN_DIR/glassforge"

sed "s|Exec=glassforge|Exec=${BIN_DIR}/glassforge|" "$REPO_DIR/glassforge.desktop" \
    > "$APPS_DIR/glassforge.desktop"

echo ""
echo "==> Instalação concluída."
echo "==> Garanta que ${BIN_DIR} está no seu PATH (ex.: adicione ao ~/.bashrc ou ~/.zshrc):"
echo "       export PATH=\"\$HOME/.local/bin:\$PATH\""
echo "==> Rode com:  glassforge"
echo "==> Ou pelo menu de aplicativos: GlassForge"
echo ""
echo "==> Leia o INSTALL.md para configuração específica do seu compositor"
echo "    (Hyprland, Sway, GNOME, KDE ou X11/picom)."
