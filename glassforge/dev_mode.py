"""
GlassForge - dev_mode.py

Conteúdo desbloqueado pelo easter egg (7 cliques na versão, na aba "Sobre").
Ferramentas voltadas a desenvolvedores/power users:

  - Editor JSON bruto do perfil ativo (com aplicação a quente)
  - Console de plugins Python (carrega scripts de ~/.config/glassforge/plugins)
  - Monitor de performance simples (FPS do preview, uso de memória do processo)
  - Visualizador de logs
  - Gerenciador de atalhos Hyprland relacionados ao GlassForge
  - Exportar como serviço systemd --user (autostart robusto)
  - Console de scripting (exec restrito, só sobre o próprio app)
"""
from __future__ import annotations

import importlib.util
import json
import os
import resource
import sys
import traceback
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib  # noqa: E402

from .config import ConfigManager, PLUGINS_DIR, LOG_FILE, CONFIG_DIR


SYSTEMD_UNIT_TEMPLATE = """[Unit]
Description=GlassForge - efeitos de vidro para Linux
After=graphical-session.target

[Service]
ExecStart={exec_path}
Restart=on-failure
Environment=GLASSFORGE_AUTOSTART=1

[Install]
WantedBy=graphical-session.target
"""


class DeveloperModePage(Gtk.Box):
    def __init__(self, cfg: ConfigManager):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                          margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
        self.cfg = cfg

        banner = Adw.Banner(title="Modo Desenvolvedor ativo - use com cuidado, sem rede de segurança.",
                             revealed=True)
        self.append(banner)

        notebook = Gtk.Notebook()
        self.append(notebook)
        notebook.append_page(self._build_json_editor(), Gtk.Label(label="Editor JSON"))
        notebook.append_page(self._build_plugins_tab(), Gtk.Label(label="Plugins"))
        notebook.append_page(self._build_perf_tab(), Gtk.Label(label="Performance"))
        notebook.append_page(self._build_logs_tab(), Gtk.Label(label="Logs"))
        notebook.append_page(self._build_systemd_tab(), Gtk.Label(label="Autostart (systemd)"))
        notebook.append_page(self._build_console_tab(), Gtk.Label(label="Console"))

    # ---------- editor JSON ----------
    def _build_json_editor(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12)
        box.append(Gtk.Label(
            label="Edite o perfil ativo diretamente em JSON e aplique a quente.",
            xalign=0, wrap=True))
        self._json_view = Gtk.TextView(monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        buf = self._json_view.get_buffer()
        buf.set_text(json.dumps(self.cfg.config.active_profile().to_dict(), indent=2, ensure_ascii=False))
        scroller = Gtk.ScrolledWindow(child=self._json_view, vexpand=True)
        box.append(scroller)

        btn_row = Gtk.Box(spacing=8)
        apply_btn = Gtk.Button(label="Aplicar", css_classes=["suggested-action"])
        apply_btn.connect("clicked", self._on_apply_json)
        self._json_status = Gtk.Label(label="", xalign=0)
        btn_row.append(apply_btn)
        btn_row.append(self._json_status)
        box.append(btn_row)
        return box

    def _on_apply_json(self, _btn):
        buf = self._json_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        try:
            from .config import EffectProfile
            data = json.loads(text)
            profile = self.cfg.config.active_profile()
            updated = EffectProfile.from_dict({**profile.to_dict(), **data, "id": profile.id})
            for i, p in enumerate(self.cfg.config.profiles):
                if p.id == profile.id:
                    self.cfg.config.profiles[i] = updated
                    break
            self.cfg.save()
            self._json_status.set_label("✅ Aplicado com sucesso.")
        except Exception as exc:  # noqa: BLE001 - console de dev mostra o erro cru de propósito
            self._json_status.set_label(f"❌ Erro: {exc}")

    # ---------- plugins ----------
    def _build_plugins_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12)
        box.append(Gtk.Label(
            label=f"Plugins Python em: {PLUGINS_DIR}\n"
                  "Cada plugin deve expor uma função `register(app_context)`.",
            xalign=0, wrap=True))
        self._plugins_list = Gtk.TextView(editable=False, monospace=True)
        box.append(Gtk.ScrolledWindow(child=self._plugins_list, vexpand=True))
        reload_btn = Gtk.Button(label="Recarregar plugins")
        reload_btn.connect("clicked", self._on_reload_plugins)
        box.append(reload_btn)
        self._on_reload_plugins(None)
        return box

    def _on_reload_plugins(self, _btn):
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        results = []
        for file in sorted(PLUGINS_DIR.glob("*.py")):
            try:
                spec = importlib.util.spec_from_file_location(file.stem, file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # nosec B301 - execução intencional de plugins locais do usuário
                if hasattr(module, "register"):
                    module.register({"config": self.cfg.config})
                    results.append(f"[OK] {file.name}")
                else:
                    results.append(f"[AVISO] {file.name} não define register()")
            except Exception as exc:  # noqa: BLE001
                results.append(f"[ERRO] {file.name}: {exc}")
        if not results:
            results = [f"(nenhum plugin encontrado em {PLUGINS_DIR})"]
        self._plugins_list.get_buffer().set_text("\n".join(results))

    # ---------- performance ----------
    def _build_perf_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12)
        self._perf_label = Gtk.Label(xalign=0, use_markup=True)
        box.append(self._perf_label)
        refresh_btn = Gtk.Button(label="Atualizar")
        refresh_btn.connect("clicked", lambda b: self._update_perf())
        box.append(refresh_btn)
        self._update_perf()
        GLib.timeout_add_seconds(2, self._auto_update_perf)
        return box

    def _auto_update_perf(self) -> bool:
        self._update_perf()
        return True

    def _update_perf(self) -> None:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        mem_mb = usage.ru_maxrss / 1024  # KB -> MB em Linux
        self._perf_label.set_markup(
            f"<b>Memória (RSS máx.):</b> {mem_mb:.1f} MB\n"
            f"<b>Tempo de CPU (usuário):</b> {usage.ru_utime:.2f}s\n"
            f"<b>Tempo de CPU (sistema):</b> {usage.ru_stime:.2f}s\n"
            f"<b>PID:</b> {os.getpid()}"
        )

    # ---------- logs ----------
    def _build_logs_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12)
        self._log_view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        box.append(Gtk.ScrolledWindow(child=self._log_view, vexpand=True))
        reload_btn = Gtk.Button(label="Recarregar log")
        reload_btn.connect("clicked", lambda b: self._reload_log())
        box.append(reload_btn)
        self._reload_log()
        return box

    def _reload_log(self) -> None:
        if LOG_FILE.exists():
            text = LOG_FILE.read_text(encoding="utf-8", errors="replace")[-20000:]
        else:
            text = f"(sem logs ainda em {LOG_FILE})"
        self._log_view.get_buffer().set_text(text)

    # ---------- systemd ----------
    def _build_systemd_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12)
        box.append(Gtk.Label(
            label="Gera uma unidade systemd --user para iniciar o GlassForge junto com a sessão gráfica.",
            xalign=0, wrap=True))
        gen_btn = Gtk.Button(label="Gerar e instalar unidade (~/.config/systemd/user)")
        gen_btn.connect("clicked", self._on_install_systemd)
        self._systemd_status = Gtk.Label(xalign=0)
        box.append(gen_btn)
        box.append(self._systemd_status)
        return box

    def _on_install_systemd(self, _btn):
        try:
            unit_dir = Path.home() / ".config" / "systemd" / "user"
            unit_dir.mkdir(parents=True, exist_ok=True)
            exec_path = sys.executable + " -m glassforge"
            unit_text = SYSTEMD_UNIT_TEMPLATE.format(exec_path=exec_path)
            (unit_dir / "glassforge.service").write_text(unit_text, encoding="utf-8")
            self.cfg.config.autostart = True
            self.cfg.save()
            self._systemd_status.set_label(
                "✅ Unidade criada. Ative com: systemctl --user enable --now glassforge.service")
        except OSError as exc:
            self._systemd_status.set_label(f"❌ Erro: {exc}")

    # ---------- console ----------
    def _build_console_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12)
        box.append(Gtk.Label(
            label="Console Python restrito ao contexto do app (self.cfg disponível). "
                  "Use por sua conta e risco.",
            xalign=0, wrap=True))
        self._console_input = Gtk.Entry(placeholder_text="ex.: cfg.config.active_profile().blur_radius")
        self._console_input.connect("activate", self._on_console_run)
        self._console_output = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        box.append(self._console_input)
        box.append(Gtk.ScrolledWindow(child=self._console_output, vexpand=True))
        return box

    def _on_console_run(self, entry: Gtk.Entry) -> None:
        code = entry.get_text()
        buf = self._console_output.get_buffer()
        end = buf.get_end_iter()
        safe_globals = {"__builtins__": {"len": len, "range": range, "print": print, "round": round}}
        safe_locals = {"cfg": self.cfg}
        try:
            result = eval(code, safe_globals, safe_locals)  # nosec B307 - console de dev, sandbox mínimo
            buf.insert(end, f">>> {code}\n{result!r}\n\n")
        except Exception:  # noqa: BLE001
            buf.insert(end, f">>> {code}\n{traceback.format_exc()}\n")
        entry.set_text("")
