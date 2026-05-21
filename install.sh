#!/usr/bin/env bash
# Local Ditado — instalador para Linux e macOS.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Local Ditado — instalador (Linux/macOS) =="

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ não encontrado. Instale e tente novamente." >&2
  exit 1
fi
python3 --version

# Dependência de sistema do PortAudio (sounddevice).
if [[ "$OSTYPE" == linux* ]]; then
  if command -v apt-get >/dev/null 2>&1; then
    echo "Instalando libportaudio2 (pode pedir sudo)..."
    sudo apt-get update -y && sudo apt-get install -y libportaudio2 xclip
  else
    echo "Atenção: instale o PortAudio pelo gerenciador da sua distro (ex.: portaudio)."
  fi
elif [[ "$OSTYPE" == darwin* ]]; then
  if command -v brew >/dev/null 2>&1; then
    brew list portaudio >/dev/null 2>&1 || brew install portaudio
  else
    echo "Atenção: instale o Homebrew e 'brew install portaudio'."
  fi
fi

echo
echo "Instalando o motor (engine) e dependências..."
python3 -m pip install --upgrade pip
python3 -m pip install -e "${ROOT}/engine[app,vad]"

echo
echo "Microfones encontrados:"
python3 -m localditado.cli devices || true

echo
echo "Diagnóstico:"
python3 -m localditado.cli doctor || true

cat <<'EOF'

Instalação concluída.
  Inicie o serviço:   local-ditado service   (atalho Ctrl+Alt+D)
  Bandeja:            local-ditado tray
  App desktop:        veja app/README.md

macOS: conceda permissão de Acessibilidade ao terminal/app para o atalho e a colagem.
Linux/Wayland: o atalho global é limitado; registre 'local-ditado once' no seu desktop
              ou use uma sessão X11.
EOF
