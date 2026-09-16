"""
GlassForge - overlay_window.py

Renderiza o painel de vidro em si (tint, ruído, borda, "ripple" líquido) usando
Cairo dentro de uma Gtk.DrawingArea sobre uma janela RGBA transparente.

O BLUR real do conteúdo atrás da janela (o que está "abaixo") é responsabilidade
do compositor (ver glassforge/generators/*). Esta classe cuida da identidade visual
do próprio painel GlassForge e funciona como:
  - HUD/dock decorativo customizável, e
  - superfície de pré-visualização ao vivo dentro da janela de configurações.

Em Wayland (Hyprland/Sway), tenta usar gtk4-layer-shell para ancorar a janela como
uma camada (layer-surface) — necessário para o layerrule de blur do Hyprland pegar.
Em X11/GNOME, cai para uma Gtk.Window comum com visual RGBA (funciona com picom).
"""
from __future__ import annotations

import math
import time
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Graphene, Gsk  # noqa: E402

try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402
    HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    HAS_LAYER_SHELL = False

from .config import EffectProfile, EffectType


def hex_to_rgba(hex_color: str, alpha: float) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    ok = rgba.parse(hex_color) if hex_color.startswith("#") or hex_color.startswith("rgb") else False
    if not ok:
        rgba.parse("#ffffff")
    rgba.alpha = alpha
    return rgba


class GlassSurface(Gtk.DrawingArea):
    """Widget que desenha o efeito de vidro configurável."""

    def __init__(self, profile: EffectProfile):
        super().__init__()
        self.profile = profile
        self._t0 = time.monotonic()
        self.set_draw_func(self._on_draw)
        if profile.animate_ripple:
            GLib.timeout_add(33, self._tick)  # ~30fps, suficiente para uma ondulação sutil

    def set_profile(self, profile: EffectProfile) -> None:
        self.profile = profile
        self.queue_draw()

    def _tick(self) -> bool:
        self.queue_draw()
        return True  # continua o timer enquanto o widget existir

    def _on_draw(self, area, cr, width, height):
        p = self.profile
        cr.save()

        # 1. Base translúcida com leve gradiente (dá profundidade ao "vidro")
        grad = cr.__class__  # placeholder para evitar import extra de cairo puro
        import cairo

        pattern = cairo.LinearGradient(0, 0, 0, height)
        base = hex_to_rgba(p.tint_color, p.opacity)
        top_a = min(1.0, p.opacity + 0.10)
        bot_a = max(0.0, p.opacity - 0.10)
        pattern.add_color_stop_rgba(0.0, base.red, base.green, base.blue, top_a)
        pattern.add_color_stop_rgba(1.0, base.red, base.green, base.blue, bot_a)

        self._rounded_rect(cr, 0, 0, width, height, p.border_radius)
        cr.set_source(pattern)
        cr.fill_preserve()

        # 2. Ondulação "liquid glass": distorce sutilmente a opacidade em faixas senoidais
        if p.animate_ripple:
            t = time.monotonic() - self._t0
            cr.save()
            self._rounded_rect(cr, 0, 0, width, height, p.border_radius)
            cr.clip()
            n_bands = 5
            for i in range(n_bands):
                phase = t * (2 * math.pi / (p.animation_speed_ms / 1000.0)) + i * 1.3
                y = (math.sin(phase) * 0.5 + 0.5) * height
                band_h = height / (n_bands * 1.4)
                cr.set_source_rgba(base.red, base.green, base.blue, 0.05)
                cr.rectangle(0, y - band_h / 2, width, band_h)
                cr.fill()
            cr.restore()

        # 3. Ruído sutil (grão de vidro fosco)
        if p.noise > 0:
            import random
            rnd = random.Random(42)  # semente fixa: ruído estável entre frames, sem "chuvisco"
            cr.save()
            self._rounded_rect(cr, 0, 0, width, height, p.border_radius)
            cr.clip()
            dots = int(width * height * p.noise / 40)
            for _ in range(min(dots, 4000)):
                x = rnd.uniform(0, width)
                y = rnd.uniform(0, height)
                cr.set_source_rgba(1, 1, 1, rnd.uniform(0.01, 0.05))
                cr.rectangle(x, y, 1, 1)
                cr.fill()
            cr.restore()

        # 4. Borda de vidro (highlight)
        border = hex_to_rgba(p.border_color if p.border_color.startswith("#") else "#ffffff",
                              1.0)
        self._rounded_rect(cr, 0.5, 0.5, width - 1, height - 1, p.border_radius)
        cr.set_line_width(p.border_width)
        cr.set_source_rgba(border.red, border.green, border.blue, 0.5)
        cr.stroke()

        cr.restore()

    @staticmethod
    def _rounded_rect(cr, x, y, w, h, r):
        r = max(0, min(r, min(w, h) / 2))
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()


class OverlayWindow(Gtk.Window):
    """Janela transparente e sem decoração usada como HUD/dock/painel GlassForge."""

    def __init__(self, app: Gtk.Application, profile: EffectProfile,
                 width: int = 420, height: int = 220, anchor_edges=("top", "right")):
        super().__init__(application=app, title="GlassForge Overlay")
        self.set_decorated(False)
        self.set_default_size(width, height)

        # Visual RGBA (necessário para transparência em X11/GNOME via picom/mutter)
        self.add_css_class("glassforge-overlay")

        self.surface_widget = GlassSurface(profile)
        self.set_child(self.surface_widget)

        if HAS_LAYER_SHELL:
            LayerShell.init_for_window(self)
            LayerShell.set_namespace(self, "glassforge")  # usado pelo layerrule do Hyprland
            LayerShell.set_layer(self, LayerShell.Layer.OVERLAY)
            for edge in anchor_edges:
                edge_enum = {
                    "top": LayerShell.Edge.TOP,
                    "bottom": LayerShell.Edge.BOTTOM,
                    "left": LayerShell.Edge.LEFT,
                    "right": LayerShell.Edge.RIGHT,
                }[edge]
                LayerShell.set_anchor(self, edge_enum, True)
            LayerShell.set_margin(self, LayerShell.Edge.TOP, 16)
            LayerShell.set_margin(self, LayerShell.Edge.RIGHT, 16)
            LayerShell.set_exclusive_zone(self, -1)

    def apply_profile(self, profile: EffectProfile) -> None:
        self.surface_widget.set_profile(profile)


def load_overlay_css() -> str:
    """CSS aplicado globalmente para permitir fundo transparente nas janelas GlassForge."""
    return """
    window.glassforge-overlay {
        background-color: transparent;
    }
    """
