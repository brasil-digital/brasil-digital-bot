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


def generate_content(article: dict) -> dict:
    """Transforma UMA notícia real (já coletada via RSS) em roteiro de Short.

    A regra inegociável: o modelo só pode usar o que está no texto da fonte.
    Nada de estatística, citação ou fato extra inventado ("achômetro" proibido).
    """
    prompt = f"""Você é o editor de tecnologia do canal SÉRIO de notícias "Brasil Digital" no YouTube.

REGRA INEGOCIÁVEL: baseie-se EXCLUSIVAMENTE nas informações fornecidas abaixo, extraídas de uma matéria jornalística real. É PROIBIDO inventar números, datas, nomes, citações, causas ou consequências que não estejam no texto. Se um detalhe não estiver claro na fonte, seja mais genérico em vez de inventar — este é um canal de notícias verificadas, não de especulação ("zero achômetro").

Fonte: {article['source']}
Link original: {article['link']}
Título original (pode estar em inglês): {article['title']}
Resumo/trecho da matéria: {article['summary']}
Publicado: {article.get('published') or 'recentemente'}

Tarefa: adapte essa notícia real para um roteiro de YouTube Short vertical (~40-55 segundos), traduzindo pro português brasileiro num tom de apresentador de telejornal de tecnologia — sério, direto, sem sensacionalismo e sem opinião pessoal.

Responda APENAS com JSON válido, sem markdown, seguindo exatamente este formato:
{{
  "category": "uma destas categorias: ia, big-techs, ciberseguranca, mercado-tech, ciencia",
  "subject": "assunto principal em poucas palavras (ex: 'OpenAI', 'Nova lei de IA na UE')",
  "hook": "chamada curta que resume a notícia (máx 90 caracteres)",
  "slides": [
    {{"text": "slide 1 — manchete/hook (máx 80 caracteres)"}},
    {{"text": "slide 2 — fato principal da notícia (máx 100 caracteres)"}},
    {{"text": "slide 3 — contexto ou detalhe importante (máx 100 caracteres)"}},
    {{"text": "slide 4 — por que isso importa (máx 100 caracteres)"}},
    {{"text": "Fonte: {article['source']}\\nBrasil Digital"}}
  ],
  "narration_script": "roteiro COMPLETO para narração em voz masculina séria, português brasileiro natural, 70 a 100 palavras (~45s falados), tom de apresentador de telejornal de tecnologia. SEM inventar fatos além da fonte fornecida. SEM indicações de cena ou colchetes — só o texto narrado.",
  "youtube_title": "título objetivo pro Short (máx 90 caracteres, sem clickbait exagerado, sem emojis em excesso)",
  "youtube_description": "descrição com 2 parágrafos curtos resumindo a notícia + uma linha 'Fonte: {article['source']} — {article['link']}' + 6 a 8 hashtags relevantes",
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
