# Brasil Digital bot — guia para o Claude

Bot do canal YouTube **Brasil Digital** (@brazildigital, channel `UCVXyxst4cIDX8IKnd1v4JUw`): notícias de tecnologia e IA em PT-BR. Dono: Ronny (fala português; responda em português, simples e direto).

## Regra de ouro
**Nunca inventar notícia.** O conteúdo vem de matérias reais (RSS de fontes verificadas). O Claude só adapta o texto da fonte — nada de fato, número ou citação fora dela. A fonte é sempre citada na descrição.

## Onde roda
GitHub Actions (nada roda no PC). Branch padrão: **`master`**.

| Workflow | Quando | O que faz |
|---|---|---|
| `postar.yml` (Brasil Digital - Postar Short) | 9h e 21h UTC | Short automático a partir do RSS |
| idem, cron `0 16 * * *` com `FILA=1` | 12h Boston | publica o próximo JSON de `data/fila/` (ordem alfabética) e move p/ `data/manual/`; fila vazia = não posta |
| `video_longo.yml` | seg/qua/sex 15h UTC | vídeo longo 16:9 (~3,5–4 min) |
| `upload_manual.yml` | manual | publica vídeo PRONTO vindo de um GitHub Release |
| `alerta.yml` | quando qualquer um acima falha | avisa o Ronny no Telegram |

**Ao criar um workflow novo, adicione o `name:` dele na lista `workflows:` do `alerta.yml`** (tem que bater exatamente).

## Pipeline do Short (`src/main.py`)
`news_fetcher.py` (RSS, notícias < 30h) → `history.py` (descarta links já usados, `data/posted_links.json`) → `content_generator.py` (Claude Haiku escolhe a mais relevante pro brasileiro comum e escreve o roteiro) → `narration.py` (OpenAI TTS, voz fixa `onyx`) → `video_creator.py` (1080×1920, marca d'água do papagaio da Rádio IA Fala Brasil) + `thumbnail.py` (capa = 1º quadro + `thumbnails.set`) → `youtube_uploader.py` (categoria 28).

Roteiro **manual**: JSON em `data/manual/` no mesmo formato que `generate_content` devolve (campos `category, subject, hook, slides[], narration_script, youtube_title, youtube_description, tags, source, source_link, thumb_text, badge, image_prompt`). Narração 70–100 palavras. Disparo: Actions → Postar Short → campo `roteiro` = caminho do JSON (ou `fila`). Pode ter `video_file` + `cover_file` para publicar um vídeo já montado.

Vídeo longo: `src/longform.py` + `longform_writer.py` (roteiro a partir do texto COMPLETO da matéria, via trafilatura) + `longform_video.py`. Histórico em `data/longform_history.json`. **Sem música**, voz `onyx`, app Fala Brasil só no cartão final.

## Testar sem publicar
- Vídeo longo: `DRY_RUN=1 OUT_DIR=... python src/longform.py`
- Nunca disparar o workflow real só para testar — ele publica no canal de verdade.

## Armadilhas conhecidas
- YouTube rejeita `<` e `>` em título/descrição (`invalidDescription`) — o uploader já troca por ‹ ›.
- O workflow commita `posted_links.json` de volta: **sempre `git pull --rebase` antes de dar push**.
- Se o push final do workflow falhar (instabilidade do GitHub), o vídeo SAI publicado; só o histórico se perde → adicionar o link à mão em `posted_links.json`.
- Workflow novo recém-criado às vezes dá 404 no `gh workflow run` — fazer mais um push trivial.
- Haiku às vezes devolve JSON inválido no roteiro do Short — `content_generator.py` tenta 3x antes de falhar.
- Sonnet devolve bloco de "thinking" antes do texto: pegar o bloco `type == "text"`.
- Não publicar clipe alheio cru (risco de strike / conteúdo reutilizado) — sempre transformar com análise. Só repostar com autorização do autor e crédito.
- Evitar política partidária/eleitoral.

## Segredos (GitHub → Settings → Secrets)
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. **Nunca** escrever valores de chaves em arquivos do repositório (ele é público). O Ronny grava segredos ele mesmo.
