"""
GNOME/Mutter não expõe uma API de blur-behind para aplicações comuns em Wayland.
O caminho suportado é a extensão "Blur my Shell". Este módulo gera:
  1) um script shell com os comandos `gsettings` equivalentes ao perfil escolhido;
  2) uma checagem/instrução de instalação da extensão via extensions.gnome.org.
Isso é documentado explicitamente para o usuário na GUI (aba "Compositor").
"""
from __future__ import annotations
from ..config import EffectProfile

SCHEMA = "org.gnome.shell.extensions.blur-my-shell"


def is_extension_likely_installed() -> bool:
    import shutil
    return shutil.which("gnome-extensions") is not None


def generate_script(profile: EffectProfile) -> str:
    sigma = max(1, profile.blur_radius)
    brightness = max(0.3, 1.0 - profile.tint_strength * 0.5)
    return "\n".join([
        "#!/usr/bin/env bash",
        "# Gerado pelo GlassForge - aplica o perfil de vidro via extensão Blur my Shell.",
        "# Requer: extensão 'Blur my Shell' instalada e habilitada.",
        "#   https://extensions.gnome.org/extension/3193/blur-my-shell/",
        "set -e",
        f'gsettings set {SCHEMA} sigma {sigma} || true',
        f'gsettings set {SCHEMA} brightness {round(brightness, 2)} || true',
        f'gsettings set {SCHEMA}.appfolder blur true || true',
        f'gsettings set {SCHEMA}.window-list blur true || true',
        f'gsettings set {SCHEMA}.panel blur true || true',
        f'gsettings set {SCHEMA}.overview blur true || true',
        'echo "Perfil GlassForge aplicado às configurações do Blur my Shell."',
    ])


def install_hint() -> str:
    return (
        "GNOME/Wayland não permite que um app comum aplique blur no que está atrás dele.\n"
        "Instale a extensão GNOME 'Blur my Shell' (extensions.gnome.org/extension/3193) "
        "e o GlassForge vai configurá-la automaticamente para casar com seu perfil ativo."
    )
