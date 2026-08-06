"""Histórico de links já publicados — evita repetir a mesma notícia.

Mais confiável que comparar títulos (que podem variar em cada fonte):
guardamos o link original da matéria usada em cada vídeo já publicado.
"""
import json
import os

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "posted_links.json")
MAX_HISTORY = 200


def load_used_links() -> set[str]:
    if not os.path.exists(HISTORY_PATH):
        return set()
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_used_link(link: str) -> None:
    links = list(load_used_links())
    links.append(link)
    links = links[-MAX_HISTORY:]
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)
