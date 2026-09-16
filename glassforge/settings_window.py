"""
GlassForge - settings_window.py
GUI principal de configuração (libadwaita). Abas: Aparência, Efeitos, Compositor,
Perfis, Regras por App, Sobre. Contém o easter egg dos 7 cliques -> Modo Desenvolvedor.
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib  # noqa: E402

from .config import ConfigManager, EffectProfile, EffectType, CompositorTarget, WindowRule
from .overlay_window import GlassSurface
from . import detect
from .generators import hyprland, picom, gnome
from .dev_mode import DeveloperModePage

APP_VERSION = "1.0.0"
EASTER_EGG_CLICKS_NEEDED = 7


class GlassForgeSettingsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Gtk.Application, cfg: ConfigManager):
        super().__init__(application=app, title="GlassForge - Configurações")
        self.cfg = cfg
        self.set_default_size(980, 680)

        self._egg_clicks = 0
        self._dev_page_added = False

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        self.split_view = Adw.NavigationSplitView()
        toolbar_view.set_content(self.split_view)
        self.set_content(toolbar_view)

        # --- Sidebar de navegação ---
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.listbox = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.listbox.connect("row-selected", self._on_row_selected)

        self._pages = {}
        self._add_page("appearance", "🎨  Aparência", self._build_appearance_page())
        self._add_page("effects", "✨  Efeitos", self._build_effects_page())
        self._add_page("compositor", "🖥️  Compositor", self._build_compositor_page())
        self._add_page("profiles", "🗂️  Perfis", self._build_profiles_page())
        self._add_page("rules", "🧩  Regras por App", self._build_rules_page())
        self._add_page("about", "ℹ️  Sobre", self._build_about_page())

        sidebar_page = Adw.NavigationPage(title="GlassForge", child=Gtk.ScrolledWindow(child=self.listbox))
        content_page = Adw.NavigationPage(title="Configurações", child=self.stack)
        self.split_view.set_sidebar(sidebar_page)
        self.split_view.set_content(content_page)

        self.listbox.select_row(self.listbox.get_row_at_index(0))

    # ---------- infraestrutura de páginas ----------
    def _add_page(self, key: str, label: str, widget: Gtk.Widget) -> None:
        row = Gtk.ListBoxRow()
        row.set_child(Gtk.Label(label=label, xalign=0, margin_top=10, margin_bottom=10, margin_start=12))
        row.key = key
        self.listbox.append(row)
        scroller = Gtk.ScrolledWindow(child=widget)
        self.stack.add_named(scroller, key)
        self._pages[key] = row

    def _on_row_selected(self, listbox, row):
        if row is not None:
            self.stack.set_visible_child_name(row.key)

    def _add_dev_mode_page(self) -> None:
        if self._dev_page_added:
            return
        self._dev_page_added = True
        dev_page = DeveloperModePage(self.cfg)
        self._add_page("devmode", "🛠️  Modo Desenvolvedor", dev_page)
        self.cfg.config.developer_mode = True
        self.cfg.save()
        toast_holder = Adw.ToastOverlay()
        # Mostrar aviso rápido via título da janela (evita dependências extras de overlay aqui)
        self.set_title("GlassForge - Modo Desenvolvedor desbloqueado 🛠️")

    # ---------- páginas ----------
    def _build_appearance_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=24,
                       margin_bottom=24, margin_start=24, margin_end=24)

        preview = GlassSurface(self.cfg.config.active_profile())
        preview.set_size_request(-1, 180)
        frame = Gtk.Frame(child=preview, margin_bottom=12)
        box.append(Gtk.Label(label="Pré-visualização ao vivo", xalign=0, css_classes=["title-4"]))
        box.append(frame)
        self._preview_widget = preview

        group = Adw.PreferencesGroup(title="Cores e Transparência")
        box.append(group)

        color_row = Adw.ActionRow(title="Cor de matiz (tint)")
        color_btn = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog())
        rgba = self._parse_color(self.cfg.config.active_profile().tint_color)
        color_btn.set_rgba(rgba)
        color_btn.connect("notify::rgba", self._on_tint_color_changed)
        color_row.add_suffix(color_btn)
        group.add(color_row)

        opacity_row = Adw.ActionRow(title="Opacidade do painel")
        opacity_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.1, 1.0, 0.01)
        opacity_scale.set_value(self.cfg.config.active_profile().opacity)
        opacity_scale.set_size_request(220, -1)
        opacity_scale.connect("value-changed", lambda s: self._update_active(opacity=s.get_value()))
        opacity_row.add_suffix(opacity_scale)
        group.add(opacity_row)

        radius_row = Adw.ActionRow(title="Raio das bordas")
        radius_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 40, 1)
        radius_scale.set_value(self.cfg.config.active_profile().border_radius)
        radius_scale.set_size_request(220, -1)
        radius_scale.connect("value-changed", lambda s: self._update_active(border_radius=int(s.get_value())))
        radius_row.add_suffix(radius_scale)
        group.add(radius_row)

        return box

    def _build_effects_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=24,
                       margin_bottom=24, margin_start=24, margin_end=24)

        group = Adw.PreferencesGroup(title="Tipo de efeito")
        box.append(group)

        effect_row = Adw.ComboRow(title="Efeito de vidro")
        effect_model = Gtk.StringList.new([e.value for e in EffectType])
        effect_row.set_model(effect_model)
        current_idx = list(EffectType).index(self.cfg.config.active_profile().effect_type)
        effect_row.set_selected(current_idx)
        effect_row.connect("notify::selected", self._on_effect_type_changed)
        group.add(effect_row)

        blur_row = Adw.ActionRow(title="Intensidade do blur (aplicada ao compositor)")
        blur_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 64, 1)
        blur_scale.set_value(self.cfg.config.active_profile().blur_radius)
        blur_scale.set_size_request(220, -1)
        blur_scale.connect("value-changed", lambda s: self._update_active(blur_radius=int(s.get_value())))
        blur_row.add_suffix(blur_scale)
        group.add(blur_row)

        noise_row = Adw.ActionRow(title="Ruído do vidro fosco")
        noise_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 0.3, 0.01)
        noise_scale.set_value(self.cfg.config.active_profile().noise)
        noise_scale.set_size_request(220, -1)
        noise_scale.connect("value-changed", lambda s: self._update_active(noise=s.get_value()))
        noise_row.add_suffix(noise_scale)
        group.add(noise_row)

        sat_row = Adw.ActionRow(title="Realce de saturação (efeito líquido)")
        sat_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1.0, 2.0, 0.05)
        sat_scale.set_value(self.cfg.config.active_profile().saturation_boost)
        sat_scale.set_size_request(220, -1)
        sat_scale.connect("value-changed", lambda s: self._update_active(saturation_boost=s.get_value()))
        sat_row.add_suffix(sat_scale)
        group.add(sat_row)

        ripple_row = Adw.SwitchRow(title="Ondulação animada (liquid glass)",
                                    active=self.cfg.config.active_profile().animate_ripple)
        ripple_row.connect("notify::active", lambda r, p: self._update_active(animate_ripple=r.get_active()))
        group.add(ripple_row)

        return box

    def _build_compositor_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=24,
                       margin_bottom=24, margin_start=24, margin_end=24)

        info = detect.capability_summary()
        status = Adw.PreferencesGroup(title="Ambiente detectado")
        box.append(status)
        status.add(Adw.ActionRow(title="Sessão", subtitle="Wayland" if info["wayland"] else "X11"))
        status.add(Adw.ActionRow(title="Desktop", subtitle=info["desktop"] or "desconhecido"))
        status.add(Adw.ActionRow(title="Compositor alvo sugerido", subtitle=info["compositor"].value))
        status.add(Adw.ActionRow(title="Nota de suporte", subtitle=info["note"]))

        group = Adw.PreferencesGroup(title="Alvo de configuração")
        box.append(group)
        target_row = Adw.ComboRow(title="Gerar configuração para")
        model = Gtk.StringList.new([c.value for c in CompositorTarget])
        target_row.set_model(model)
        target_row.set_selected(list(CompositorTarget).index(self.cfg.config.compositor_target))
        target_row.connect("notify::selected", self._on_compositor_target_changed)
        group.add(target_row)

        apply_row = Adw.ActionRow(title="Gerar e aplicar bloco de configuração",
                                   subtitle="Cria/atualiza o bloco gerenciado pelo GlassForge no arquivo do compositor")
        apply_btn = Gtk.Button(label="Gerar agora", css_classes=["suggested-action"], valign=Gtk.Align.CENTER)
        apply_btn.connect("clicked", self._on_generate_compositor_config)
        apply_row.add_suffix(apply_btn)
        group.add(apply_row)

        self._compositor_output = Gtk.TextView(editable=False, monospace=True,
                                                wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self._compositor_output.get_buffer().set_text("# A prévia da configuração gerada aparece aqui.")
        out_frame = Gtk.Frame(child=self._compositor_output)
        out_frame.set_size_request(-1, 220)
        box.append(out_frame)

        return box

    def _build_profiles_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=24,
                       margin_bottom=24, margin_start=24, margin_end=24)

        box.append(Gtk.Label(label="Perfis salvos", xalign=0, css_classes=["title-4"]))
        self._profiles_list = Gtk.ListBox(css_classes=["boxed-list"])
        box.append(self._profiles_list)
        self._refresh_profiles_list()

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        new_btn = Gtk.Button(label="Novo perfil")
        new_btn.connect("clicked", self._on_new_profile)
        dup_btn = Gtk.Button(label="Duplicar selecionado")
        dup_btn.connect("clicked", self._on_duplicate_profile)
        del_btn = Gtk.Button(label="Excluir selecionado", css_classes=["destructive-action"])
        del_btn.connect("clicked", self._on_delete_profile)
        btn_row.append(new_btn)
        btn_row.append(dup_btn)
        btn_row.append(del_btn)
        box.append(btn_row)

        box.append(Gtk.Separator())
        box.append(Gtk.Label(label="Importar / Exportar", xalign=0, css_classes=["title-4"]))
        io_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        export_btn = Gtk.Button(label="Exportar configuração (.json)")
        export_btn.connect("clicked", self._on_export)
        import_btn = Gtk.Button(label="Importar (.json)")
        import_btn.connect("clicked", self._on_import)
        io_row.append(export_btn)
        io_row.append(import_btn)
        box.append(io_row)

        return box

    def _build_rules_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=24,
                       margin_bottom=24, margin_start=24, margin_end=24)
        box.append(Gtk.Label(
            label="Defina exceções por aplicativo (ex.: desativar efeito em jogos/terminais pesados).",
            xalign=0, wrap=True))

        self._rules_list = Gtk.ListBox(css_classes=["boxed-list"])
        box.append(self._rules_list)
        self._refresh_rules_list()

        add_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._new_rule_entry = Gtk.Entry(placeholder_text="app_id / classe da janela (ex.: kitty, code)")
        add_btn = Gtk.Button(label="Adicionar regra", css_classes=["suggested-action"])
        add_btn.connect("clicked", self._on_add_rule)
        add_row.append(self._new_rule_entry)
        add_row.append(add_btn)
        box.append(add_row)

        return box

    def _build_about_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=48,
                       margin_start=24, margin_end=24, halign=Gtk.Align.CENTER)
        box.append(Gtk.Label(label="GlassForge", css_classes=["title-1"]))
        box.append(Gtk.Label(label="Efeitos de vidro totalmente customizáveis para Linux."))

        version_btn = Gtk.Button(label=f"versão {APP_VERSION}", css_classes=["flat"])
        version_btn.connect("clicked", self._on_version_clicked)
        box.append(version_btn)

        box.append(Gtk.Label(
            label="Suporte: Hyprland · Sway · GNOME (via extensão) · KDE/KWin · X11 (picom)",
            css_classes=["dim-label"], margin_top=12))
        box.append(Gtk.Label(
            label="Licença MIT · github.com/SEU_USUARIO/glassforge",
            css_classes=["dim-label"]))
        return box

    # ---------- easter egg ----------
    def _on_version_clicked(self, button: Gtk.Button) -> None:
        self._egg_clicks += 1
        remaining = EASTER_EGG_CLICKS_NEEDED - self._egg_clicks
        if self._egg_clicks >= EASTER_EGG_CLICKS_NEEDED:
            self._egg_clicks = 0
            self._add_dev_mode_page()
        elif remaining <= 3:
            button.set_label(f"versão {APP_VERSION} ({remaining} para desbloquear algo...)")

    # ---------- handlers ----------
    def _parse_color(self, hex_color: str):
        rgba = Adw.__dict__  # noop, mantém import Adw referenciado
        import gi
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gdk
        c = Gdk.RGBA()
        c.parse(hex_color)
        return c

    def _update_active(self, **kwargs) -> None:
        profile = self.cfg.config.active_profile()
        for k, v in kwargs.items():
            setattr(profile, k, v)
        self.cfg.save()
        self._preview_widget.set_profile(profile)

    def _on_tint_color_changed(self, btn, _pspec):
        rgba = btn.get_rgba()
        hex_color = "#{:02x}{:02x}{:02x}".format(
            int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255))
        self._update_active(tint_color=hex_color)

    def _on_effect_type_changed(self, row, _pspec):
        selected = list(EffectType)[row.get_selected()]
        self._update_active(effect_type=selected)

    def _on_compositor_target_changed(self, row, _pspec):
        selected = list(CompositorTarget)[row.get_selected()]
        self.cfg.config.compositor_target = selected
        self.cfg.save()

    def _on_generate_compositor_config(self, _btn):
        profile = self.cfg.config.active_profile()
        rules = self.cfg.config.window_rules
        target = self.cfg.config.compositor_target
        if target == CompositorTarget.AUTO:
            target = detect.detect_compositor()

        if target == CompositorTarget.HYPRLAND:
            text = hyprland.generate(profile, rules)
        elif target == CompositorTarget.PICOM:
            text = picom.generate(profile, rules)
        elif target == CompositorTarget.GNOME:
            text = gnome.generate_script(profile) + "\n\n# " + gnome.install_hint()
        else:
            text = f"# Geração automática ainda não implementada para: {target.value}\n" \
                   f"# Perfil ativo: {profile.name} (blur={profile.blur_radius}, opacidade={profile.opacity})"

        self._compositor_output.get_buffer().set_text(text)

    def _refresh_profiles_list(self) -> None:
        child = self._profiles_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._profiles_list.remove(child)
            child = nxt
        for profile in self.cfg.config.profiles:
            row = Adw.ActionRow(title=profile.name, subtitle=profile.effect_type.value)
            row.profile_id = profile.id
            activate_btn = Gtk.Button(label="Ativar", valign=Gtk.Align.CENTER)
            activate_btn.connect("clicked", lambda b, pid=profile.id: self._activate_profile(pid))
            row.add_suffix(activate_btn)
            if profile.id == self.cfg.config.active_profile_id:
                row.add_css_class("accent")
            self._profiles_list.append(row)

    def _activate_profile(self, profile_id: str) -> None:
        self.cfg.config.active_profile_id = profile_id
        self.cfg.save()
        self._preview_widget.set_profile(self.cfg.config.active_profile())
        self._refresh_profiles_list()

    def _on_new_profile(self, _btn):
        new_profile = EffectProfile(name="Novo perfil")
        self.cfg.config.profiles.append(new_profile)
        self.cfg.config.active_profile_id = new_profile.id
        self.cfg.save()
        self._refresh_profiles_list()

    def _on_duplicate_profile(self, _btn):
        row = self._profiles_list.get_selected_row()
        if row is None:
            return
        for p in self.cfg.config.profiles:
            if p.id == row.profile_id:
                self.cfg.duplicate_profile(p)
                break
        self._refresh_profiles_list()

    def _on_delete_profile(self, _btn):
        row = self._profiles_list.get_selected_row()
        if row is None or len(self.cfg.config.profiles) <= 1:
            return
        self.cfg.delete_profile(row.profile_id)
        self._refresh_profiles_list()

    def _refresh_rules_list(self) -> None:
        child = self._rules_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._rules_list.remove(child)
            child = nxt
        for rule in self.cfg.config.window_rules:
            row = Adw.ActionRow(title=rule.app_id, subtitle=f"efeito: {rule.effect.value}")
            toggle = Gtk.Switch(active=rule.enabled, valign=Gtk.Align.CENTER)
            toggle.connect("notify::active", lambda s, p, r=rule: self._toggle_rule(r, s.get_active()))
            row.add_suffix(toggle)
            self._rules_list.append(row)

    def _toggle_rule(self, rule: WindowRule, active: bool) -> None:
        rule.enabled = active
        self.cfg.save()

    def _on_add_rule(self, _btn):
        text = self._new_rule_entry.get_text().strip()
        if not text:
            return
        self.cfg.config.window_rules.append(WindowRule(app_id=text))
        self.cfg.save()
        self._new_rule_entry.set_text("")
        self._refresh_rules_list()

    def _on_export(self, _btn):
        dialog = Gtk.FileDialog(initial_name="glassforge-config.json")
        dialog.save(self, None, self._on_export_finish)

    def _on_export_finish(self, dialog, result):
        try:
            gfile = dialog.save_finish(result)
            self.cfg.export_to(gfile.get_path())
        except GLib.Error:
            pass

    def _on_import(self, _btn):
        dialog = Gtk.FileDialog()
        dialog.open(self, None, self._on_import_finish)

    def _on_import_finish(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
            self.cfg.import_from(gfile.get_path())
            self._refresh_profiles_list()
            self._refresh_rules_list()
        except (GLib.Error, ValueError, OSError):
            pass
