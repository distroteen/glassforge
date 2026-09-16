"""
Gerador de regras Hyprland (hyprland.conf) a partir de um EffectProfile / WindowRule.
Hyprland é hoje o compositor wlroots com suporte de blur mais completo e configurável,
então é o alvo "de referência" para o efeito liquid glass real (blur do que está atrás).
"""
from __future__ import annotations
from typing import List
from ..config import EffectProfile, WindowRule, EffectType

MARK_BEGIN = "# >>> GlassForge managed block - não editar manualmente (edite via GUI) >>>"
MARK_END = "# <<< GlassForge managed block <<<"


def _blur_block(profile: EffectProfile) -> str:
    passes = 3 if profile.effect_type in (EffectType.LIQUID_GLASS, EffectType.ACRYLIC) else 2
    vibrancy = round(min(profile.saturation_boost, 2.0), 2)
    noise = round(profile.noise, 3)
    return (
        "decoration {\n"
        "    blur {\n"
        "        enabled = true\n"
        f"        size = {max(1, profile.blur_radius // 2)}\n"
        f"        passes = {passes}\n"
        f"        noise = {noise}\n"
        f"        vibrancy = {vibrancy}\n"
        "        vibrancy_darkness = 0.0\n"
        f"        new_optimizations = true\n"
        f"        xray = false\n"
        "        special = false\n"
        "    }\n"
        f"    rounding = {profile.border_radius}\n"
        f"    active_opacity = {round(profile.opacity + (1-profile.opacity)*0.3, 2)}\n"
        f"    inactive_opacity = {round(profile.opacity, 2)}\n"
        "}\n"
    )


def _window_rules(rules: List[WindowRule]) -> str:
    lines = []
    for r in rules:
        if not r.enabled or not r.app_id:
            continue
        lines.append(f"windowrulev2 = opacity {round(r.opacity,2)} override,class:^({r.app_id})$")
        lines.append(f"windowrulev2 = rounding {profile_rounding_placeholder()},class:^({r.app_id})$"
                      if False else f"windowrulev2 = bordersize 1,class:^({r.app_id})$")
        if r.effect != EffectType.NONE:
            lines.append(f"windowrulev2 = blur,class:^({r.app_id})$")
    return "\n".join(lines)


def profile_rounding_placeholder() -> int:
    return 12


def generate(profile: EffectProfile, window_rules: List[WindowRule] | None = None) -> str:
    window_rules = window_rules or []
    body = [
        MARK_BEGIN,
        f"# Perfil ativo: {profile.name} ({profile.effect_type.value})",
        _blur_block(profile),
        "# Regras por aplicativo geradas pelo GlassForge:",
        _window_rules(window_rules),
        "",
        "# Camada do próprio painel GlassForge (overlay GTK via layer-shell):",
        'layerrule = blur, glassforge',
        f'layerrule = ignorezero, glassforge',
        MARK_END,
    ]
    return "\n".join(x for x in body if x is not None)


def merge_into_config(existing_text: str, generated_block: str) -> str:
    """Substitui o bloco antigo do GlassForge (se existir) ou anexa ao final."""
    if MARK_BEGIN in existing_text and MARK_END in existing_text:
        pre = existing_text.split(MARK_BEGIN)[0]
        post = existing_text.split(MARK_END)[1]
        return pre + generated_block + post
    sep = "\n" if existing_text and not existing_text.endswith("\n") else ""
    return existing_text + sep + "\n" + generated_block + "\n"
