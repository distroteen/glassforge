"""
GlassForge - config.py
Modelo de configuração, persistência e import/export de perfis de efeito.
"""
from __future__ import annotations

import json
import os
import uuid
import copy
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional

APP_NAME = "glassforge"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
PROFILES_DIR = CONFIG_DIR / "profiles"
PLUGINS_DIR = CONFIG_DIR / "plugins"
LOG_FILE = CONFIG_DIR / "glassforge.log"
STATE_FILE = CONFIG_DIR / "state.json"


class EffectType(str, Enum):
    NONE = "none"
    BLUR = "blur"
    GLASSMORPHISM = "glassmorphism"
    LIQUID_GLASS = "liquid_glass"
    ACRYLIC = "acrylic"
    FROSTED = "frosted"


class CompositorTarget(str, Enum):
    AUTO = "auto"
    HYPRLAND = "hyprland"
    SWAY = "sway"
    PICOM = "picom"
    GNOME = "gnome"
    KWIN = "kwin"


@dataclass
class WindowRule:
    """Regra por aplicativo/app_id (override do preset global)."""
    app_id: str = ""
    match_title: str = ""
    effect: EffectType = EffectType.GLASSMORPHISM
    blur_radius: int = 24
    opacity: float = 0.85
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["effect"] = self.effect.value
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "WindowRule":
        d = dict(d)
        d["effect"] = EffectType(d.get("effect", "glassmorphism"))
        return WindowRule(**d)


@dataclass
class EffectProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "Padrão"
    effect_type: EffectType = EffectType.LIQUID_GLASS
    blur_radius: int = 28          # px, usado nos geradores de compositor
    noise: float = 0.04            # ruído sutil sobre o vidro (0-1)
    opacity: float = 0.72          # opacidade do painel (0-1)
    tint_color: str = "#8ec5ff"    # cor de matiz do vidro
    tint_strength: float = 0.18    # 0-1
    border_radius: int = 18        # px
    border_width: float = 1.2      # px
    border_color: str = "rgba(255,255,255,0.35)"
    shadow_strength: float = 0.35  # 0-1
    saturation_boost: float = 1.15 # >1 realça cores por trás (efeito "liquid")
    animate_ripple: bool = True    # ondulação sutil tipo "liquid glass"
    animation_speed_ms: int = 4200
    follow_accent_color: bool = True
    dark_mode_aware: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["effect_type"] = self.effect_type.value
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EffectProfile":
        d = dict(d)
        d["effect_type"] = EffectType(d.get("effect_type", "liquid_glass"))
        return EffectProfile(**d)


@dataclass
class AppConfig:
    active_profile_id: str = ""
    profiles: List[EffectProfile] = field(default_factory=list)
    window_rules: List[WindowRule] = field(default_factory=list)
    compositor_target: CompositorTarget = CompositorTarget.AUTO
    autostart: bool = False
    developer_mode: bool = False
    telemetry_opt_in: bool = False  # sempre False por padrão; nunca enviado sem ação explícita
    schema_version: int = 1

    def active_profile(self) -> EffectProfile:
        for p in self.profiles:
            if p.id == self.active_profile_id:
                return p
        return self.profiles[0] if self.profiles else default_profiles()[0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "active_profile_id": self.active_profile_id,
            "compositor_target": self.compositor_target.value,
            "autostart": self.autostart,
            "developer_mode": self.developer_mode,
            "telemetry_opt_in": self.telemetry_opt_in,
            "profiles": [p.to_dict() for p in self.profiles],
            "window_rules": [r.to_dict() for r in self.window_rules],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AppConfig":
        profiles = [EffectProfile.from_dict(p) for p in d.get("profiles", [])] or default_profiles()
        rules = [WindowRule.from_dict(r) for r in d.get("window_rules", [])]
        return AppConfig(
            active_profile_id=d.get("active_profile_id", profiles[0].id),
            profiles=profiles,
            window_rules=rules,
            compositor_target=CompositorTarget(d.get("compositor_target", "auto")),
            autostart=d.get("autostart", False),
            developer_mode=d.get("developer_mode", False),
            telemetry_opt_in=d.get("telemetry_opt_in", False),
            schema_version=d.get("schema_version", 1),
        )


def default_profiles() -> List[EffectProfile]:
    return [
        EffectProfile(
            id="liquid-default", name="Liquid Glass",
            effect_type=EffectType.LIQUID_GLASS, blur_radius=32, opacity=0.68,
            tint_color="#9fd3ff", tint_strength=0.22, border_radius=22,
            animate_ripple=True,
        ),
        EffectProfile(
            id="frosted-default", name="Frosted / Acrylic",
            effect_type=EffectType.ACRYLIC, blur_radius=40, opacity=0.55,
            tint_color="#ffffff", tint_strength=0.12, border_radius=14,
            animate_ripple=False,
        ),
        EffectProfile(
            id="dark-default", name="Dark Glass",
            effect_type=EffectType.GLASSMORPHISM, blur_radius=22, opacity=0.80,
            tint_color="#141821", tint_strength=0.35, border_radius=16,
            animate_ripple=False, dark_mode_aware=False,
        ),
        EffectProfile(
            id="minimal-blur", name="Blur Minimalista",
            effect_type=EffectType.BLUR, blur_radius=12, opacity=0.9,
            tint_color="#000000", tint_strength=0.0, border_radius=8,
            animate_ripple=False,
        ),
    ]


class ConfigManager:
    """Carrega, salva, exporta e importa a configuração do GlassForge."""

    def __init__(self, config_dir: Path = CONFIG_DIR):
        self.config_dir = config_dir
        self.config_file = config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        self.config: AppConfig = self.load()

    def load(self) -> AppConfig:
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                return AppConfig.from_dict(data)
            except (json.JSONDecodeError, KeyError, ValueError):
                backup = self.config_file.with_suffix(".json.corrupt")
                self.config_file.rename(backup)
        cfg = AppConfig(profiles=default_profiles())
        cfg.active_profile_id = cfg.profiles[0].id
        return cfg

    def save(self) -> None:
        tmp = self.config_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.config_file)

    def export_to(self, path: str, profile_only: Optional[EffectProfile] = None) -> None:
        """Exporta config completa (ou apenas um perfil) para um .json portável."""
        if profile_only is not None:
            payload = {"glassforge_profile": profile_only.to_dict()}
        else:
            payload = {"glassforge_config": self.config.to_dict()}
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_from(self, path: str) -> str:
        """Importa um .json exportado. Retorna uma mensagem de status."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if "glassforge_config" in data:
            self.config = AppConfig.from_dict(data["glassforge_config"])
            self.save()
            return "Configuração completa importada."
        if "glassforge_profile" in data:
            profile = EffectProfile.from_dict(data["glassforge_profile"])
            profile.id = uuid.uuid4().hex[:8]  # evita colisão de IDs
            self.config.profiles.append(profile)
            self.save()
            return f"Perfil '{profile.name}' importado."
        raise ValueError("Arquivo não reconhecido como perfil/config do GlassForge.")

    def duplicate_profile(self, profile: EffectProfile) -> EffectProfile:
        new = copy.deepcopy(profile)
        new.id = uuid.uuid4().hex[:8]
        new.name = f"{profile.name} (cópia)"
        self.config.profiles.append(new)
        self.save()
        return new

    def delete_profile(self, profile_id: str) -> None:
        self.config.profiles = [p for p in self.config.profiles if p.id != profile_id]
        if self.config.active_profile_id == profile_id and self.config.profiles:
            self.config.active_profile_id = self.config.profiles[0].id
        self.save()
