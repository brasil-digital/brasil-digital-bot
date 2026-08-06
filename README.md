# Brasil Digital Bot

Bot que publica 2 YouTube Shorts por dia no canal **Brasil Digital**
(@brazildigital) com notícias reais e verificadas de Tecnologia/IA.

## Por que é diferente do ritmos-bot

O `ritmos-bot` (canal Ritmos do Brasil) deixa o Claude **criar** o conteúdo
livremente (curiosidades sobre música). Aqui não: como é um canal sério de
notícias, o roteiro **nunca é inventado** — o Claude só traduz/adapta um
texto real, coletado por RSS de veículos de tecnologia confiáveis, e é
proibido por instrução de acrescentar qualquer fato, número ou citação que
não esteja na fonte.

## Pipeline

1. **`src/news_fetcher.py`** — busca notícias recentes (< 30h) via RSS em
   TechCrunch, MIT Technology Review, The Verge, Ars Technica, Wired,
   Canaltech, Olhar Digital e InfoMoney (todas as editorias de IA/tech,
   não os feeds gerais — evita loteria, cupom, guia de compra).
2. **`src/history.py`** — guarda em `data/posted_links.json` os links já
   usados, pra nunca repetir a mesma notícia (o workflow faz commit desse
   arquivo depois de cada publicação).
3. **`src/content_generator.py`** — Claude Haiku adapta a notícia escolhida
   pra um roteiro de Short em português, citando a fonte, SEM inventar
   nada além do texto fornecido.
4. **`src/narration.py`** — OpenAI TTS, voz masculina fixa `onyx` (tom de
   âncora/telejornal, séria e consistente).
5. **`src/video_creator.py`** — monta o Short vertical 1080×1920 com
   slides + narração + marca d'água da logo (mesma logo da Rádio IA Fala
   Brasil, reaproveitada como identidade irmã).
6. **`src/youtube_uploader.py`** — publica no canal via YouTube Data API v3
   (categoria "Science & Technology").

## Configuração inicial (precisa ser feita manualmente, uma vez)

1. Crie o repo no GitHub: `brasil-digital/brasil-digital-bot` (ou nome que
   preferir) e faça o push desta pasta.
2. Gere o token do YouTube **logado na conta do canal Brasil Digital**:
   ```
   python get_youtube_token.py
   ```
   (usa as mesmas credenciais OAuth client_id/client_secret do projeto
   Google Cloud já existente — reaproveitar as do ritmos-bot é possível,
   mas o REFRESH_TOKEN tem que ser gerado de novo, logado no canal certo.)
3. Rode `python check_channels.py` pra confirmar o ID do canal Brasil
   Digital antes de configurar os secrets.
4. Configure os secrets no GitHub (Settings → Secrets → Actions):
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`
   - `YOUTUBE_CLIENT_ID`
   - `YOUTUBE_CLIENT_SECRET`
   - `YOUTUBE_REFRESH_TOKEN`
5. O workflow `.github/workflows/postar.yml` já está configurado pra rodar
   às 6h e 18h BRT todo dia (mesmo horário do ritmos-bot). Pode disparar
   manualmente antes via aba Actions → "Run workflow" pra testar.

## Teste local (sem publicar)

Rode só a coleta de notícias pra conferir o que está saindo nos feeds:
```
python -c "import sys; sys.path.insert(0,'src'); from news_fetcher import fetch_candidates; [print(c['source'], '-', c['title']) for c in fetch_candidates()]"
```

## Atenção

- **Nunca** editar `content_generator.py` pra deixar o Claude "livre" — a
  regra de se basear só na fonte é o que garante que o canal não vira
  achômetro.
- Se algum feed sair do ar ou mudar de URL, o bot simplesmente ignora essa
  fonte naquele dia (não quebra o pipeline inteiro).
