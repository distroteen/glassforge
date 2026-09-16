# Guia de Instalação - GlassForge

## 1. Instalação automática (recomendada)

```bash
git clone https://github.com/distroteen/glassforge.git
cd glassforge
chmod +x install.sh
./install.sh
```

O script detecta seu gerenciador de pacotes (`apt`, `dnf`, `pacman`,
`zypper`), instala GTK4 + libadwaita + PyGObject + `gtk4-layer-shell`
quando disponível, copia o app para `~/.local/lib/glassforge`, cria o
executável `~/.local/bin/glassforge` e registra o `.desktop` no menu.

Depois, garanta que `~/.local/bin` está no seu `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"   # adicione ao ~/.bashrc ou ~/.zshrc
```

## 2. Instalação manual por distro

### Ubuntu / Debian (apt)

```bash
sudo apt update
sudo apt install python3 python3-gi python3-gi-cairo python3-pip \
    gir1.2-gtk-4.0 gir1.2-adw-1 libgtk-4-1 libadwaita-1-0

# gtk4-layer-shell (necessário para o overlay em Wayland/Hyprland/Sway):
sudo apt install gir1.2-gtk4layershell-1.0 2>/dev/null || \
  echo "Pacote pode ter outro nome na sua versão do Ubuntu; veja https://github.com/wmww/gtk4-layer-shell"
```

### Fedora (dnf)

```bash
sudo dnf install python3 python3-gobject python3-pip gtk4 libadwaita gtk4-layer-shell
```

### Arch Linux / Manjaro (pacman)

```bash
sudo pacman -S python python-gobject python-pip gtk4 libadwaita gtk4-layer-shell
```

### openSUSE (zypper)

```bash
sudo zypper install python3 python3-gobject python3-pip gtk4 libadwaita-1-0 gtk4-layer-shell
```

Depois, em qualquer distro:

```bash
git clone https://github.com/SEU_USUARIO/glassforge.git
cd glassforge
python3 -m glassforge
```

## 3. Configuração por compositor

### Hyprland (recomendado — suporte completo)

1. Abra o GlassForge, vá em **Compositor** → selecione `hyprland` (ou deixe
   em `auto`, ele detecta via `HYPRLAND_INSTANCE_SIGNATURE`).
2. Clique em **Gerar agora**. Copie o bloco gerado (ou automatize com o
   script abaixo) para o seu `~/.config/hypr/hyprland.conf`:

```bash
# Aplica o bloco gerado automaticamente (mantém o resto do seu hyprland.conf intacto)
python3 -c "
from glassforge.config import ConfigManager
from glassforge.generators import hyprland
from pathlib import Path
cfg = ConfigManager()
p = cfg.config.active_profile()
block = hyprland.generate(p, cfg.config.window_rules)
conf_path = Path.home() / '.config' / 'hypr' / 'hyprland.conf'
existing = conf_path.read_text() if conf_path.exists() else ''
conf_path.write_text(hyprland.merge_into_config(existing, block))
print('hyprland.conf atualizado.')
"
hyprctl reload
```

### X11 com picom

1. Instale o picom: `sudo apt install picom` (ou equivalente).
2. Na aba **Compositor**, selecione `picom` e gere a configuração.
3. Salve o bloco gerado em `~/.config/picom/picom.conf` e rode:
   ```bash
   picom --config ~/.config/picom/picom.conf -b
   ```

### GNOME

1. Instale a extensão **Blur my Shell**:
   <https://extensions.gnome.org/extension/3193/blur-my-shell/>
2. Na aba **Compositor**, selecione `gnome`, clique em **Gerar agora**.
3. Salve o script gerado (ex.: `~/.local/bin/glassforge-gnome-apply.sh`),
   dê permissão de execução e rode-o para aplicar o perfil ativo:
   ```bash
   chmod +x ~/.local/bin/glassforge-gnome-apply.sh
   ~/.local/bin/glassforge-gnome-apply.sh
   ```

### KDE Plasma (KWin)

O KWin tem um efeito de "Blur" nativo. Habilite manualmente em:
**Configurações do Sistema → Efeitos de Área de Trabalho → Blur** (ative
e ajuste a intensidade). O GlassForge ainda não escreve a config do KWin
diretamente (contribuições são bem-vindas — ver README).

### Sway

O Sway (wlroots puro) não expõe blur nativo configurável como o Hyprland.
O overlay do GlassForge funcionará com transparência via
`gtk4-layer-shell`, mas sem blur real do conteúdo atrás. Considere migrar
para Hyprland se blur real for essencial ao seu fluxo.

## 4. Autostart

Duas opções:

**a) Via Modo Desenvolvedor (recomendado):** abra o GlassForge, clique 7x
na versão na aba "Sobre" para desbloquear o **Modo Desenvolvedor**, vá na
aba **Autostart (systemd)** e clique em "Gerar e instalar unidade". Depois:

```bash
systemctl --user enable --now glassforge.service
```

**b) Manual:** adicione `glassforge --overlay-only` ao autostart da sua
sessão gráfica (Hyprland: `exec-once = glassforge --overlay-only` no
`hyprland.conf`; GNOME/KDE: use o utilitário de "Aplicativos de
Inicialização" do seu ambiente).

## 5. Solução de problemas

- **Janela do overlay aparece sem transparência real:** confirme que seu
  compositor está ativo (Hyprland/Sway sempre estão; em X11, confirme que
  o `picom` está rodando com `pgrep picom`).
- **`ModuleNotFoundError: No module named 'gi'`:** o PyGObject não foi
  instalado corretamente — reinstale o pacote do seu gerenciador de
  pacotes (não apenas via `pip`, pois os bindings GTK dependem de libs de
  sistema).
- **`ValueError: Namespace Gtk4LayerShell not available`:** seu sistema
  não tem `gtk4-layer-shell` instalado; o app cai automaticamente para uma
  janela comum (sem ancoragem de camada), mas ainda funciona.
