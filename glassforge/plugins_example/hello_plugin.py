"""
Plugin de exemplo do GlassForge.
Copie este arquivo para ~/.config/glassforge/plugins/ para ativá-lo.
Todo plugin deve expor uma função `register(app_context: dict)`.
"""


def register(app_context: dict) -> None:
    config = app_context["config"]
    profile = config.active_profile()
    print(f"[hello_plugin] GlassForge carregado com perfil ativo: {profile.name}")
    # Exemplo: um plugin real poderia, aqui, se inscrever em eventos do compositor
    # via D-Bus, adicionar novas EffectType customizadas, ou expor um servidor
    # HTTP local para controle remoto do efeito.
