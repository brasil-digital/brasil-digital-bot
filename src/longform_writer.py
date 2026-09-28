"""Pauta + roteiro dos VÍDEOS LONGOS (aba Vídeos, 3-4 min, 16:9).

Mesma regra dos Shorts: zero achômetro. A diferença é que aqui o roteiro
é escrito a partir do TEXTO COMPLETO da matéria (o resumo do RSS não
sustenta 3 minutos sem inventar), e a pauta gira entre temas variados.
"""
import json
import os

import anthropic
import trafilatura

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

PICK_MODEL = "claude-haiku-4-5-20251001"
WRITE_MODEL = "claude-sonnet-5"

CATEGORIES = {
    "ia": "INTELIGÊNCIA ARTIFICIAL",
    "golpes": "GOLPES E FAKE NEWS",
    "guerra-tech": "GUERRA TECNOLÓGICA",
    "politica-tech": "POLÍTICA E TECNOLOGIA",
    "ciberseguranca": "CIBERSEGURANÇA",
    "big-techs": "BIG TECHS",
    "brasil-tech": "BRASIL TECH",
    "ciencia": "CIÊNCIA E TECH",
}

MIN_ARTICLE_CHARS = 2500
MAX_ARTICLE_CHARS = 14000
MAX_PICK_CANDIDATES = 60


def _json(response):
    # modelos novos podem devolver um bloco de raciocínio antes do texto
    text = next(b.text for b in response.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


CHANNEL_FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=UCVXyxst4cIDX8IKnd1v4JUw"


def channel_recent_titles() -> list[str]:
    """Últimos ~15 títulos do canal (Shorts + vídeos), pra não repetir assunto."""
    try:
        import feedparser
        return [e.title for e in feedparser.parse(CHANNEL_FEED).entries]
    except Exception:
        return []


def rank_stories(candidates: list[dict], recent: list[dict]) -> list[dict]:
    """Devolve até 6 notícias REAIS em ordem de preferência (só escolhe, não altera)."""
    pool = candidates[:MAX_PICK_CANDIDATES]
    listing = "\n".join(
        f"{i}. [{c['source']}] {c['title']} — {c['summary'][:180]}" for i, c in enumerate(pool)
    )
    recent_lines = [f"- [vídeo longo, {r['category']}] {r['title']}" for r in recent[-8:]]
    recent_lines += [f"- {t}" for t in channel_recent_titles()]
    recent_txt = "\n".join(recent_lines) or "- (nenhum ainda)"
    prompt = f"""Você é o editor de pauta do canal "Brasil Digital" no YouTube. Vamos produzir um VÍDEO de 3 a 4 minutos (não Short) pra brasileiros comuns, no Brasil e nos EUA, sobre tecnologia no mundo real: inteligência artificial, golpes com IA e fake news, guerra tecnológica (drones, ciberataques, IA militar), política e regulação da tecnologia, big techs, cibersegurança, tecnologia no Brasil.

Escolha as notícias com MAIS potencial de gerar clique, tempo assistido e comentários: fatos com consequência grande, surpreendentes, que o público vai querer entender melhor ou mandar pra alguém. Tem que ter assunto pra 3 minutos.

EVITE:
- política partidária e eleitoral (candidatos, Lula x Bolsonaro, pesquisas de voto, checagem de fala de político). Checagem de fake news só serve se for sobre golpe, deepfake ou tecnologia.
- eventos e ingressos, rodadas de investimento, valuation, benchmark técnico, notícia de nicho que só interessa a quem trabalha no setor, promoção de produto.
- repetir o ASSUNTO de qualquer vídeo recente do canal abaixo (Shorts incluídos), mesmo que a notícia seja outra, e repetir a categoria dos últimos vídeos longos. Varie o tema.

Vídeos publicados recentemente no canal:
{recent_txt}

Notícias disponíveis:
{listing}

Responda APENAS com JSON: {{"ranking": [números das 6 melhores, da melhor pra pior]}}"""
    r = client.messages.create(model=PICK_MODEL, max_tokens=100,
                               messages=[{"role": "user", "content": prompt}])
    idxs = _json(r)["ranking"]
    return [pool[i] for i in idxs if isinstance(i, int) and 0 <= i < len(pool)]


def fetch_full_text(url: str) -> str:
    """Texto completo da matéria (sem menu/anúncio). Vazio se não der pra ler (paywall etc.)."""
    try:
        html = trafilatura.fetch_url(url)
        return (trafilatura.extract(html, include_comments=False) or "") if html else ""
    except Exception as e:
        print(f"⚠️  Não consegui ler {url}: {e}")
        return ""


def write_script(article: dict, text: str) -> dict:
    """Roteiro de 3-4 min fiel à matéria. Nenhum fato fora do texto da fonte."""
    categories = ", ".join(CATEGORIES)
    prompt = f"""Você é o roteirista do canal "Brasil Digital" no YouTube: notícias REAIS de tecnologia explicadas de um jeito profissional e envolvente, pra brasileiro comum.

REGRA INEGOCIÁVEL: use EXCLUSIVAMENTE as informações do texto da matéria abaixo. É PROIBIDO inventar números, datas, nomes, citações, causas, consequências ou "especialistas dizem". Se algo não está no texto, não diga. Pode explicar termos técnicos com palavras simples e reorganizar a ordem dos fatos — isso não é inventar. Se a matéria estiver em inglês, traduza com fidelidade.

Fonte: {article['source']}
Link: {article['link']}
Título original: {article['title']}
Publicado: {article.get('published') or 'recentemente'}

TEXTO DA MATÉRIA:
\"\"\"
{text[:MAX_ARTICLE_CHARS]}
\"\"\"

Escreva um roteiro de vídeo de 3 a 4 minutos (450 a 560 palavras de narração no total), dividido em 6 a 8 blocos:
1. GANCHO (bloco 1, 30-45 palavras): o fato mais surpreendente ou consequente, direto, sem "Olá pessoal" nem "neste vídeo". Termine com um motivo pra continuar assistindo ("e o mais preocupante vem agora", "e isso muda uma coisa pra você" — só se for verdade segundo o texto).
2. Blocos do meio: o que aconteceu, quem está envolvido, os detalhes e números da matéria, o contexto. Um assunto por bloco.
3. Penúltimo bloco: "o que isso muda pra você" — consequência prática para o brasileiro comum, SÓ com o que o texto permite concluir (se o texto não permite, explique por que o assunto importa sem inventar desdobramentos).
4. Último bloco (curto): uma pergunta pro espectador responder nos comentários + "Se inscreve no Brasil Digital pra entender a tecnologia que está mudando o mundo."

Tom: jornalista de tecnologia sério e acessível, fala com "você", frases curtas e claras pra narração em voz alta. Nada de sensacionalismo mentiroso, nada de emoji na narração, nada de colchetes ou indicação de cena. Números por extenso só quando ficar mais natural de ouvir.

Responda APENAS com JSON válido, sem markdown:
{{
  "category": "uma destas: {categories}",
  "subject": "assunto em 2-5 palavras",
  "youtube_title": "título de vídeo com curiosidade e 100% verdadeiro segundo a fonte, máx 70 caracteres, no máximo 1 emoji, sem 'Empresa X anuncia Y'",
  "youtube_description": "3 parágrafos curtos resumindo a notícia + a pergunta do final convidando a comentar. NÃO coloque fonte, links nem hashtags (o sistema acrescenta).",
  "hashtags": ["#BrasilDigital", "mais 5 a 7 hashtags do tema"],
  "tags": ["10 a 15 tags de busca em português (e 2-3 em inglês se o tema for internacional)"],
  "thumb_text": "2 a 5 palavras GIGANTES pra capa, sem pontuação, verdadeiras segundo a fonte",
  "badge": "UM: ALERTA, URGENTE, EXCLUSIVO, ENTENDA, GUERRA TECH, GOLPE, FAKE NEWS, NOVIDADE, POLÊMICA",
  "thumb_image_prompt": "cena fotográfica dramática em INGLÊS pra capa (1-2 frases). PROIBIDO: texto, logos, marcas, pessoas reais ou famosas.",
  "sections": [
    {{
      "heading": "título curto do bloco pra aparecer na tela e virar capítulo do YouTube (2-6 palavras), sobre o CONTEÚDO do bloco — nunca nomes de bastidor como 'Gancho', 'Introdução', 'Conclusão' ou 'Pergunta final'",
      "narration": "texto narrado do bloco",
      "image_prompt": "cena fotográfica em INGLÊS que ilustra ESTE bloco (1-2 frases), variada em relação às outras. PROIBIDO: texto, logos, marcas, pessoas reais/famosas/políticos identificáveis."
    }}
  ]
}}"""
    r = client.messages.create(model=WRITE_MODEL, max_tokens=6000,
                               messages=[{"role": "user", "content": prompt}])
    script = _json(r)
    if script.get("category") not in CATEGORIES:
        script["category"] = "ia"
    script["source"] = article["source"]
    script["source_link"] = article["link"]
    words = sum(len(s["narration"].split()) for s in script["sections"])
    print(f"   Roteiro: {len(script['sections'])} blocos, {words} palavras")
    if words < 330:
        raise Exception(f"Roteiro curto demais ({words} palavras) — matéria sem assunto pra vídeo longo.")
    return script


def pick_and_write(candidates: list[dict], recent: list[dict]) -> dict:
    """Tenta as notícias do ranking até achar uma com texto completo legível."""
    for article in rank_stories(candidates, recent):
        print(f"🔎 Tentando: [{article['source']}] {article['title']}")
        text = fetch_full_text(article["link"])
        if len(text) < MIN_ARTICLE_CHARS:
            print(f"   Texto curto/indisponível ({len(text)} caracteres), próxima.")
            continue
        try:
            return write_script(article, text)
        except Exception as e:
            print(f"   Roteiro falhou ({e}), próxima.")
    raise Exception("Nenhuma das pautas escolhidas tinha texto completo pra um vídeo longo.")
