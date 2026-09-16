"""
Detecção do compositor/ambiente gráfico ativo, para o modo "auto" do GlassForge.
"""
from __future__ import annotations
import os
import shutil
from .config import CompositorTarget


def is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(
        os.environ.get("WAYLAND_DISPLAY")
    )


def detect_desktop() -> str:
    return (os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "").lower()


def detect_compositor() -> CompositorTarget:
    desktop = detect_desktop()
    if "hyprland" in desktop or os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return CompositorTarget.HYPRLAND
    if "sway" in desktop or os.environ.get("SWAYSOCK"):
        return CompositorTarget.SWAY
    if "gnome" in desktop:
        return CompositorTarget.GNOME
    if "kde" in desktop or "plasma" in desktop:
        return CompositorTarget.KWIN
    if not is_wayland() and shutil.which("picom"):
        return CompositorTarget.PICOM
    # fallback conservador
    return CompositorTarget.PICOM if not is_wayland() else CompositorTarget.HYPRLAND


def capability_summary() -> dict:
    """Usado na aba 'Compositor' da GUI para explicar ao usuário o que é suportado de fato."""
    wl = is_wayland()
    comp = detect_compositor()
    notes = {
        CompositorTarget.HYPRLAND: "Suporte completo: blur real do conteúdo atrás da janela via regras nativas.",
        CompositorTarget.SWAY: "Sway (wlroots) não expõe blur nativo como o Hyprland; efeito limitado a transparência.",
        CompositorTarget.GNOME: "Requer extensão 'Blur my Shell' para blur real; sem ela, apenas transparência do painel.",
        CompositorTarget.KWIN: "KWin (Plasma) tem efeito 'Blur' embutido, habilitável em Configurações > Efeitos de Área.",
        CompositorTarget.PICOM: "X11 via picom: blur real suportado (dual_kawase).",
        CompositorTarget.AUTO: "Detecção automática pendente.",
    }
    return {
        "wayland": wl,
        "desktop": detect_desktop(),
        "compositor": comp,
        "note": notes.get(comp, ""),
    }
