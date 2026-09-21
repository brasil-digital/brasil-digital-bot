import json
import os

import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

CATEGORY_LABELS = {
    "ia": "INTELIGÊNCIA ARTIFICIAL",
    "big-techs": "BIG TECHS",
    "ciberseguranca": "CIBERSEGURANÇA",
    "mercado-tech": "MERCADO TECH",
    "ciencia": "CIÊNCIA E TECH",
}


MAX_PICK_CANDIDATES = 30


def pick_most_engaging(candidates: list[dict]) -> dict:
    """Escolhe, entre notícias REAIS já coletadas, a que mais prende o público brasileiro.

    Só escolhe — não altera nem inventa nada. Os vídeos que funcionaram no canal
    foram os práticos/curiosos (IA que liga por você, "esse vídeo é IA?"); os de
    bastidor corporativo (evento, investimento, benchmark) ficaram com 0-5 views.
    """
    pool = candidates[:MAX_PICK_CANDIDATES]
    listing = "\n".join(
        f"{i}. [{c['source']}] {c['title']} — {c['summary'][:200]}" for i, c in enumerate(pool)
    )
    prompt = f"""Você é o editor de pauta do canal "Brasil Digital" (YouTube Shorts de tecnologia/IA para brasileiros comuns, no Brasil e nos EUA).

Escolha a notícia com MAIS potencial de prender a atenção, gerar comentários e compartilhamentos. Priorize o que afeta a vida da pessoa comum: celular, WhatsApp, Instagram, apps, golpes e segurança, dinheiro, emprego, saúde, IA que a pessoa pode usar, coisas chocantes ou curiosas que dão vontade de mandar pra alguém.
EVITE: eventos e ingressos, rodadas de investimento, valuation, briga de executivos, benchmark técnico, política interna de empresa, notícia que só interessa a quem trabalha no setor.

Notícias:
{listing}

Responda APENAS com o número da notícia escolhida."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    idx = int("".join(ch for ch in response.content[0].text if ch.isdigit()))
    chosen = pool[idx]
    print(f"🎯 Pauta escolhida por engajamento ({idx} de {len(pool)} candidatas)")
    return chosen


def generate_content(article: dict) -> dict:
    """Transforma UMA notícia real (já coletada via RSS) em roteiro de Short.

    A regra inegociável: o modelo só pode usar o que está no texto da fonte.
    Nada de estatística, citação ou fato extra inventado ("achômetro" proibido).
    """
    prompt = f"""Você é o roteirista do canal "Brasil Digital" no YouTube — notícias REAIS de tecnologia contadas de um jeito que prende, pra brasileiro comum.

REGRA INEGOCIÁVEL: baseie-se EXCLUSIVAMENTE nas informações fornecidas abaixo, extraídas de uma matéria jornalística real. É PROIBIDO inventar números, datas, nomes, citações, causas ou consequências que não estejam no texto. Se um detalhe não estiver claro na fonte, seja mais genérico em vez de inventar — este é um canal de notícias verificadas, não de especulação ("zero achômetro").

Fonte: {article['source']}
Link original: {article['link']}
Título original (pode estar em inglês): {article['title']}
Resumo/trecho da matéria: {article['summary']}
Publicado: {article.get('published') or 'recentemente'}

Tarefa: adapte essa notícia real para um roteiro de YouTube Short vertical (~40-55 segundos) em português brasileiro. Tom de CONVERSA, como um amigo que entende de tecnologia contando uma novidade: frases curtas, fale com "você", explique o que isso muda na vida da pessoa. Nada de tom de telejornal nem jargão (se usar termo técnico, explique em 3 palavras). Pode ter emoção e surpresa, mas sem exagerar nem distorcer o fato.

GANCHO DOS PRIMEIROS 2 SEGUNDOS (crítico pro Short não ser pulado): identifique o detalhe MAIS surpreendente ou consequente da notícia — não o mais óbvio — e abra com ele em forma de afirmação de impacto ou pergunta direta. Isso é reordenar informação real, não inventar nada. Evite aberturas fracas e genéricas como "Nesta semana...", "Segundo uma nova pesquisa...", "A empresa X anunciou que..." — vá direto no fato que mais importa. O "hook" e a PRIMEIRA FRASE do "narration_script" devem transmitir esse mesmo gancho (podem usar palavras um pouco diferentes, mas o mesmo impacto), porque o espectador ouve a narração ao mesmo tempo em que vê o hook na tela.

Responda APENAS com JSON válido, sem markdown, seguindo exatamente este formato:
{{
  "category": "uma destas categorias: ia, big-techs, ciberseguranca, mercado-tech, ciencia",
  "subject": "assunto principal em poucas palavras (ex: 'OpenAI', 'Nova lei de IA na UE')",
  "hook": "gancho de impacto com o fato mais surpreendente da notícia, afirmação forte ou pergunta direta (máx 90 caracteres) — não um resumo neutro",
  "slides": [
    {{"text": "slide 1 — manchete/hook (máx 80 caracteres)"}},
    {{"text": "slide 2 — fato principal da notícia (máx 100 caracteres)"}},
    {{"text": "slide 3 — contexto ou detalhe importante (máx 100 caracteres)"}},
    {{"text": "slide 4 — o que isso muda pra você (máx 100 caracteres)"}},
    {{"text": "Fonte: {article['source']}\\nBrasil Digital"}}
  ],
  "narration_script": "roteiro COMPLETO para narração em voz masculina séria, português brasileiro natural, 70 a 100 palavras (~45s falados), tom de conversa falando com 'você'. A PRIMEIRA FRASE precisa ser o mesmo gancho de impacto do campo 'hook' (mesmo fato surpreendente em destaque), só depois vem o contexto/explicação. TERMINE com uma pergunta curta e direta pro espectador responder nos comentários, ligada ao tema (ex: 'Você usaria isso?', 'Você cairia nesse golpe?') seguida de 'Segue o Brasil Digital.'. SEM inventar fatos além da fonte fornecida. SEM indicações de cena ou colchetes — só o texto narrado.",
  "youtube_title": "título que dá vontade de clicar (máx 70 caracteres): desperte curiosidade ou mostre o que a pessoa ganha/perde, pode falar com 'você', no máximo 1 emoji. Tem que ser 100% verdadeiro segundo a fonte — curiosidade sim, mentira ou exagero nunca. Evite títulos de manchete neutra tipo 'Empresa X anuncia Y'.",
  "youtube_description": "descrição com 2 parágrafos curtos resumindo a notícia + a mesma pergunta do final da narração convidando a comentar + uma linha 'Fonte: {article['source']} — {article['link']}' + 6 a 8 hashtags relevantes",
  "tags": ["tecnologia", "shorts", "...mais 8 tags relevantes ao tema específico da notícia"]
}}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    content = json.loads(text.strip())

    content["source"] = article["source"]
    content["source_link"] = article["link"]
    if content.get("category") not in CATEGORY_LABELS:
        content["category"] = "ciencia"
    return content
