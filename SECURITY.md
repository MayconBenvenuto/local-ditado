# Segurança

O Ditado Local grava áudio do microfone e cola texto no aplicativo focado. Isso exige cuidado.

## Dados sensíveis

- Não publique arquivos de `recordings/`.
- Não publique `ditado.txt`.
- Não publique logs se eles contiverem texto sensível.

## Reportando vulnerabilidades

Abra uma issue com detalhes suficientes para reproduzir, mas sem expor dados privados. Para problemas sensíveis, descreva o impacto e combine um canal privado com os mantenedores.

## Modelo de segurança atual

- O reconhecimento roda localmente.
- O serviço usa atalho global do Windows.
- O texto é enviado para a área de transferência e colado na janela focada.
- Modelos baixados de terceiros devem ser tratados como dependências externas.
