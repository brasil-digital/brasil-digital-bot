"""Busca notícias reais e recentes de Tecnologia/IA em fontes jornalísticas
verificadas via RSS — nenhum fato é inventado aqui, só coletado.

Canal sério: o conteúdo final (content_generator.py) é obrigado a se basear
SOMENTE no texto retornado por essas fontes, nunca a inventar.
"""
import datetime
import html
import re

import feedparser

# (nome da fonte, URL do feed RSS) — todas testadas e retornando itens válidos.
# Preferimos feeds de categoria/editoria (IA, tech) em vez do feed geral do
# site, pra não puxar loteria, promoção de produto, guia de compra etc.
FEEDS = [
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("Ars Technica", "https://arstechnica.com/ai/feed/"),
    ("Wired", "https://www.wired.com/feed/tag/ai/latest/rss"),
    ("Canaltech", "https://canaltech.com.br/rss/inteligencia-artificial/"),
    ("Olhar Digital", "https://olhardigital.com.br/editorias/inteligencia-artificial/feed/"),
    ("InfoMoney", "https://www.infomoney.com.br/tudo-sobre/inteligencia-artificial/feed/"),
]

MAX_AGE_HOURS = 30  # cobre a janela entre os 2 posts diários com folga
LIMIT_PER_FEED = 8

# Filtro de segurança: mesmo em feeds de categoria, descarta ruído óbvio
# (loteria, cupom/promoção, guia de compra) que não é notícia de tecnologia/IA.
NOISE_PATTERNS = re.compile(
    r"loteria|quina|lotof[aá]cil|mega-?sena|resultado da|cupom|% ?off|"
    r"promo[cç][aã]o|achados|onde comprar|melhor pre[cç]o",
    re.IGNORECASE,
)


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_candidates(max_age_hours: int = MAX_AGE_HOURS) -> list[dict]:
    """Retorna lista de notícias recentes reais, mais novas primeiro."""
    now = datetime.datetime.now(datetime.timezone.utc)
    candidates = []

    for source, url in FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            print(f"⚠️  Falha ao ler feed de {source}: {e}")
            continue

        if getattr(parsed, "bozo", 0) and not parsed.entries:
            print(f"⚠️  Feed de {source} inválido/vazio, pulando.")
            continue

        for entry in parsed.entries[:LIMIT_PER_FEED]:
            struct = entry.get("published_parsed") or entry.get("updated_parsed")
            pub_dt = None
            age_h = None
            if struct:
                pub_dt = datetime.datetime(*struct[:6], tzinfo=datetime.timezone.utc)
                age_h = (now - pub_dt).total_seconds() / 3600
                if age_h > max_age_hours or age_h < 0:
                    continue

            summary = _clean_html(entry.get("summary", "") or entry.get("description", ""))[:700]
            title = _clean_html(entry.get("title", ""))
            link = entry.get("link", "")

            if not title or not link:
                continue
            if NOISE_PATTERNS.search(title):
                continue

            candidates.append({
                "source": source,
                "title": title,
                "link": link,
                "summary": summary,
                "published": pub_dt.isoformat() if pub_dt else None,
                "age_hours": age_h if age_h is not None else 999,
            })

    candidates.sort(key=lambda c: c["age_hours"])
    return candidates


def pick_unused(candidates: list[dict], used_links: set[str]) -> dict | None:
    """Escolhe a notícia real mais recente que ainda não foi publicada no canal."""
    for c in candidates:
        if c["link"] not in used_links:
            return c
    return None
