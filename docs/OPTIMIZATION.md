# Otimização de precisão e velocidade

## O que mais impacta precisão

1. Microfone correto e próximo da boca.
2. Baixo ruído ambiente.
3. Modelo Whisper maior.
4. Prompt de contexto com palavras comuns do usuário.
5. `beam_size` maior, geralmente `5`.

## O que mais impacta velocidade

1. GPU/CUDA funcionando.
2. Modelo menor.
3. Áudio mais curto.
4. Menor tempo de silêncio automático.
5. `beam_size` menor.

## Perfil recomendado atual

```powershell
pythonw dictado_hotkey.py --config .\config.json
```

Use `active_profile` em `config.json` para alternar entre `precisao`, `equilibrado` e `rapido`.

## Experimentos seguros

Para reduzir latência sem derrubar muito a precisão:

- Testar `--silence-seconds 1.5`
- Manter `--whisper-model small`
- Manter `--beam-size 5`
- Manter GPU com `--whisper-device cuda`

No MVP, isso corresponde a editar `profiles/equilibrado.json` ou usar o perfil `equilibrado`.

Para máxima precisão:

- Testar `--whisper-model medium`, se a GPU tiver memória suficiente.
- Usar prompt de contexto mais completo.
- Evitar `beam-size 1`.

Para máxima velocidade:

- Testar `--whisper-model base`
- Testar `--beam-size 1`
- Testar `--silence-seconds 0.8`

Essa combinação pode reduzir qualidade, então deve ser um perfil separado.
