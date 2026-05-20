# Contribuindo

Obrigado por considerar contribuir com o Ditado Local.

## Como ajudar

- Testar em diferentes microfones, GPUs e versões do Windows.
- Reportar erros com log, modelo usado e configuração de áudio.
- Melhorar documentação de instalação.
- Criar perfis de precisão/velocidade.
- Adicionar suporte a novos atalhos, idiomas e motores locais.

## Desenvolvimento local

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-gpu-cu12.txt
python -m py_compile dictado_hotkey.py ditar.py
```

## Antes de abrir um pull request

- Não inclua `models/`, `recordings/`, logs ou transcrições locais.
- Explique o problema que a mudança resolve.
- Se mexer em performance, inclua tempos comparativos no log ou na descrição.
- Se mexer em precisão, inclua exemplos reais ou uma gravação de teste sintética.
