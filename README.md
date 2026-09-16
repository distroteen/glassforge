# GlassForge

**Efeitos de vidro (blur, glassmorphism, liquid glass, acrylic) totalmente
customizáveis para janelas no Linux — com GUI completa, perfis exportáveis
e integração nativa com Hyprland, Sway, GNOME, KDE e X11 (picom).**

> ⚠️ Status: projeto funcional em estágio inicial (v1.0.0). Testado
> logicamente (config, geração de regras, import/export) neste repositório;
> a validação visual em cada compositor depende do seu ambiente — veja
> "Limitações conhecidas" abaixo antes de abrir issues.

---

## ✨ O que o GlassForge faz

- Um **painel/overlay GTK4** com efeito de vidro desenhado por ele mesmo
  (tint, ruído, ondulação animada "liquid glass", bordas e sombra),
  totalmente customizável por sliders na GUI.
- **Geração automática de configuração do compositor** para o blur *real*
  do que está atrás da janela:
  - **Hyprland** → bloco `decoration { blur { ... } }` + `windowrulev2` + `layerrule`
  - **X11 (picom)** → `picom.conf` com `dual_kawase`, cantos arredondados, opacidade
  - **GNOME** → script `gsettings` para a extensão *Blur my Shell*
  - **Sway / KDE** → detecção + instruções (blur nativo do Sway é limitado; KWin tem efeito próprio)
- **Perfis exportáveis/importáveis** em `.json` (arquivo `glassforge_config`
  ou `glassforge_profile`), prontos para compartilhar ou versionar.
- **Regras por aplicativo** (ex.: desativar o efeito em jogos/terminais pesados).
- **Easter egg:** clique 7 vezes na versão, na aba "Sobre", para desbloquear o
  **Modo Desenvolvedor** — editor JSON ao vivo, sistema de plugins Python,
  monitor de performance, visualizador de logs, gerador de unidade systemd
  para autostart, e um console Python restrito.

## 🖥️ Compatibilidade

| Ambiente               | Blur real do fundo | Como |
|-------------------------|:---:|---|
| Hyprland                | ✅  | regras nativas (`decoration.blur`, `layerrule`) |
| X11 + picom             | ✅  | `picom.conf` gerado automaticamente |
| GNOME (Wayland/X11)     | ⚠️  | requer extensão *Blur my Shell* |
| KDE Plasma (KWin)       | ⚠️  | usa o efeito "Blur" nativo do KWin (habilitar manualmente) |
| Sway                    | ⚠️  | blur nativo limitado no wlroots puro; só transparência garantida |

O GlassForge detecta automaticamente seu ambiente (`XDG_CURRENT_DESKTOP`,
`XDG_SESSION_TYPE`) e sugere o gerador correto — mas você sempre pode
escolher manualmente na aba **Compositor**.

## 🚀 Instalação rápida

```bash
git clone https://github.com/SEU_USUARIO/glassforge.git
cd glassforge
./install.sh
glassforge
```

Veja **[INSTALL.md](INSTALL.md)** para instruções detalhadas por distro
(Ubuntu/Debian, Fedora, Arch, openSUSE) e por compositor.

## 🧩 Estrutura do projeto

```
glassforge/
├── glassforge/
│   ├── app.py               # aplicação GTK4/libadwaita
│   ├── config.py            # modelo de dados, persistência, import/export
│   ├── detect.py            # detecção de compositor/ambiente
│   ├── overlay_window.py    # painel de vidro (Cairo) + layer-shell
│   ├── settings_window.py   # GUI de configuração (todas as abas)
│   ├── dev_mode.py          # Modo Desenvolvedor (easter egg)
│   ├── generators/          # hyprland.py, picom.py, gnome.py
│   ├── presets/             # perfis de exemplo prontos para importar
│   └── plugins_example/     # exemplo de plugin para o Modo Dev
├── install.sh
├── requirements.txt
├── glassforge.desktop
└── INSTALL.md
```

## 🔌 Plugins (Modo Desenvolvedor)

Coloque um `.py` em `~/.config/glassforge/plugins/` com uma função
`register(app_context)`:

```python
def register(app_context):
    profile = app_context["config"].active_profile()
    print(f"Perfil ativo: {profile.name}")
```

Veja `glassforge/plugins_example/hello_plugin.py`.

## 📤 Exportar/Importar perfis

Na aba **Perfis**, use "Exportar configuração" para gerar um `.json`
portável, ou "Importar" para carregar um perfil de outra máquina. Formato:

```json
{
  "glassforge_profile": {
    "name": "Meu vidro",
    "effect_type": "liquid_glass",
    "blur_radius": 32,
    "opacity": 0.7,
    "tint_color": "#8ec5ff"
  }
}
```

Perfis prontos em `glassforge/presets/`.

## ⚠️ Limitações conhecidas

- Um app comum **não pode** borrar o conteúdo atrás de si mesmo sem ajuda
  do compositor — isso é uma limitação de segurança/arquitetura do Wayland,
  não do GlassForge. Por isso a geração de config de compositor existe.
- `gtk4-layer-shell` nem sempre está empacotado em todas as distros/versões;
  sem ele, o overlay ainda funciona como janela comum (sem ancoragem de
  camada), mas o `layerrule` do Hyprland não vai encontrá-lo pelo namespace.
- GNOME em Wayland é o ambiente mais restrito: sem a extensão *Blur my
  Shell*, você terá apenas transparência, não blur.

## 🤝 Contribuindo

PRs bem-vindos, especialmente: suporte a KWin via script/D-Bus, suporte a
Sway com `swaybg`/composição alternativa, testes automatizados de UI com
`Xvfb`, e novos presets de efeito.

## 📄 Licença

MIT — veja [LICENSE](LICENSE).
