# Ditado Local

Ditado offline para Windows com atalho global, Whisper local, aceleração por GPU/CUDA e fallback com Vosk.

O objetivo é simples: clicar em qualquer caixa de texto, apertar um atalho, falar e receber o texto colado no aplicativo focado, sem depender de serviços externos de transcrição.

## Estado atual

- Windows
- Instalador guiado: `install.ps1`
- Configuração local: `config.json`
- Perfis prontos: `precisao`, `equilibrado`, `rapido`
- Atalho global: `Ctrl+Alt+D`
- Motor principal: `Whisper small` via `faster-whisper`
- GPU: CUDA com `int8_float16`, quando disponível
- Fallback: Vosk
- Instalação automática no login via Agendador de Tarefas
- App de bandeja para trocar perfil e controlar o serviço

## Como usar

1. Clique em uma caixa de texto.
2. Pressione `Ctrl+Alt+D`.
3. Fale.
4. Aguarde a transcrição e colagem automática.

Você também pode pressionar `Ctrl+Alt+D` novamente para finalizar manualmente.

## Instalação rápida

Execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

O instalador:

- verifica Python
- instala dependências
- detecta GPU NVIDIA
- lista microfones
- cria `config.json`
- registra o serviço no login do Windows

## Instalação manual

Instale dependências principais:

```powershell
python -m pip install -r requirements.txt
```

Para usar GPU/CUDA no Windows:

```powershell
python -m pip install --extra-index-url https://pypi.ngc.nvidia.com -r requirements-gpu-cu12.txt
```

Opcionalmente, baixe o modelo Vosk para fallback offline:

```powershell
powershell -ExecutionPolicy Bypass -File .\baixar-modelo-vosk.ps1
```

Instale ou reinicie o serviço no login:

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar-autostart.ps1
```

Abra o app de bandeja:

```powershell
.\iniciar-tray.bat
```

Instale o app de bandeja no login:

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar-tray-autostart.ps1
```

Remova do início do Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\desinstalar-autostart.ps1
```

## Testes manuais

Listar microfones:

```powershell
python ditar.py --list-devices
```

Testar volume:

```powershell
python ditar.py --device-name "External Mic" --test-seconds 5
```

Ditado manual:

```powershell
python ditar.py --device-name "External Mic" --clipboard
```

Diagnóstico completo:

```powershell
python diagnostico.py
```

Diagnóstico em JSON:

```powershell
python diagnostico.py --json
```

## Perfis

Os perfis ficam em `profiles/`:

- `precisao`: Whisper small, GPU, `beam_size 5`, silêncio mais conservador.
- `equilibrado`: Whisper small, GPU, silêncio menor.
- `rapido`: Whisper base, GPU, `beam_size 1`, menor latência.

Para trocar manualmente, edite `active_profile` em `config.json` e reinicie o serviço. Pelo tray, use o menu `Perfil`.

## Arquivos importantes

- `dictado_hotkey.py`: serviço residente com atalho global.
- `ditar.py`: utilitário manual para teste e ditado no terminal.
- `diagnostico.py`: relatório local de ambiente, GPU, pacotes e microfones.
- `install.ps1`: instalador guiado do MVP.
- `baixar-modelo-vosk.ps1`: baixa o modelo Vosk opcional de português.
- `instalar-autostart.ps1`: registra o serviço no login do Windows.
- `instalar-tray-autostart.ps1`: registra o app de bandeja no login do Windows.
- `desinstalar-autostart.ps1`: remove o serviço.
- `tray_app.py`: app de bandeja do Windows.
- `profiles/`: perfis de precisão e velocidade.
- `prompts/pt-br-default.txt`: prompt de contexto para melhorar transcrição em português.
- `docs/OPTIMIZATION.md`: guia de precisão e velocidade.
- `docs/COMMUNITY.md`: plano de comunidade.

## Dados locais

Estes arquivos não devem ser publicados no GitHub:

- `models/`
- `recordings/`
- `ditado.txt`
- `*.log`
- `config.json`

Eles estão no `.gitignore`.

## Roadmap

Veja [ROADMAP.md](ROADMAP.md).

## Créditos

Este projeto usa:

- `faster-whisper` para transcrição com Whisper local.
- `Vosk` como alternativa/fallback offline.
- Bibliotecas NVIDIA CUDA/cuDNN/cuBLAS para aceleração por GPU no Windows.

## Licença

MIT. Veja [LICENSE](LICENSE).
