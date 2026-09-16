"""
GlassForge - app.py
Ponto de entrada da aplicação GTK4/libadwaita.
"""
from __future__ import annotations

import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk  # noqa: E402

from .config import ConfigManager
from .settings_window import GlassForgeSettingsWindow
from .overlay_window import OverlayWindow, load_overlay_css

APP_ID = "dev.glassforge.GlassForge"


class GlassForgeApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.cfg = ConfigManager()
        self.settings_window: GlassForgeSettingsWindow | None = None
        self.overlay_window: OverlayWindow | None = None
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self._install_css()

        autostart = "--overlay-only" in sys.argv
        if not autostart:
            self.settings_window = GlassForgeSettingsWindow(app, self.cfg)
            self.settings_window.present()

        if self.cfg.config.autostart or autostart:
            self.overlay_window = OverlayWindow(app, self.cfg.config.active_profile())
            self.overlay_window.present()

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_string(load_overlay_css())
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )


def main() -> int:
    app = GlassForgeApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
