# 05 — PRODUÇÃO AUDIOVISUAL

Implemente um pipeline modular para transformar roteiros aprovados em ativos audiovisuais.

## Etapas
- Briefing e storyboard.
- Coleta/geração de assets permitidos.
- Narração/áudio.
- Transcrição e legendas.
- Edição e composição.
- Thumbnail.
- Renderização.
- Controle de qualidade.
- Exportação e armazenamento.

## Requisitos técnicos
- Verificar ferramentas instaladas e versões.
- Usar FFmpeg quando apropriado.
- Integrar transcrição real quando disponível.
- Identificar claramente qualquer mock ou fallback.
- Validar proporção, resolução, codec, duração e áudio.
- Evitar assets sem licença ou origem conhecida.
- Manter metadados, versão e vínculo com o canal.
- Processos longos devem ser assíncronos, retomáveis e observáveis.
- Armazenar arquivos no Drive quando a integração estiver autorizada e configurada; não inventar IDs ou links.

## Qualidade
Criar verificações automáticas para:
- Arquivo válido e reproduzível.
- Áudio presente e níveis aceitáveis.
- Sincronização de legendas.
- Duração e proporção.
- Frames pretos ou congelados anormais quando tecnicamente detectáveis.
- Thumbnail existente.
- Integridade do arquivo final.

## Critérios de aceite
Um vídeo de teste local, sem publicação, deve percorrer o pipeline e gerar relatório de qualidade. Identificar dependências externas indisponíveis sem simular conclusão.
