"""
Gerador de configuração picom.conf (X11) a partir de um EffectProfile.
Usado como alvo de compatibilidade quando o usuário está em X11 (não-Wayland),
ou em DEs que ainda rodam picom (XFCE, i3, bspwm, etc).
"""
from __future__ import annotations
from typing import List
from ..config import EffectProfile, WindowRule

MARK_BEGIN = "# >>> GlassForge managed block >>>"
MARK_END = "# <<< GlassForge managed block <<<"


def generate(profile: EffectProfile, window_rules: List[WindowRule] | None = None) -> str:
    window_rules = window_rules or []
    opacity_rules = ",\n  ".join(
        f'"{round(r.opacity*100)}:class_g = \'{r.app_id}\'"'
        for r in window_rules if r.enabled and r.app_id
    )
    corner_radius = profile.border_radius
    blur_strength = profile.blur_radius
    return "\n".join([
        MARK_BEGIN,
        f"# Perfil ativo: {profile.name}",
        "backend = \"glx\";",
        "vsync = true;",
        "",
        "blur-method = \"dual_kawase\";",
        f"blur-strength = {min(20, max(1, blur_strength // 2))};",
        "blur-background = true;",
        "blur-background-fixed = true;",
        'blur-background-exclude = [',
        '  "window_type = \'dock\'",',
        '  "window_type = \'desktop\'"',
        '];',
        "",
        f"corner-radius = {corner_radius};",
        'rounded-corners-exclude = [',
        '  "window_type = \'dock\'"',
        '];',
        "",
        f"active-opacity = {round(min(1.0, profile.opacity + 0.15), 2)};",
        f"inactive-opacity = {round(profile.opacity, 2)};",
        "opacity-rule = [",
        (f"  {opacity_rules}" if opacity_rules else "  # (sem regras por app definidas)"),
        "];",

        "",
        "shadow = true;",
        f"shadow-opacity = {round(profile.shadow_strength, 2)};",
        "shadow-radius = 18;",
        MARK_END,
    ])


def merge_into_config(existing_text: str, generated_block: str) -> str:
    if MARK_BEGIN in existing_text and MARK_END in existing_text:
        pre = existing_text.split(MARK_BEGIN)[0]
        post = existing_text.split(MARK_END)[1]
        return pre + generated_block + post
    sep = "\n" if existing_text and not existing_text.endswith("\n") else ""
    return existing_text + sep + "\n" + generated_block + "\n"
