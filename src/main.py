import json
import os
import sys
import traceback

from news_fetcher import fetch_candidates, pick_unused
from history import load_used_links, save_used_link
from content_generator import generate_content, pick_most_engaging
from narration import generate_narration
from video_creator import create_video
from youtube_uploader import upload_video
from thumbnail import generate_background, make_cover

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")
QUEUE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fila")
MANUAL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "manual")
COVER_PATH = "/tmp/bd_cover.jpg"


def _make_cover(content: dict) -> None:
    """Gera a capa (imagem IA + texto gigante) e grava o caminho em content['cover_path']."""
    print("\n🖼️  Criando capa/thumbnail...")
    bg = generate_background(content.get("image_prompt", ""), "/tmp/bd_cover_bg.png")
    make_cover(content, bg).save(COVER_PATH, quality=90)
    content["cover_path"] = COVER_PATH


def _publish_manual(path: str):
    """Publica um roteiro JÁ ESCRITO (data/manual/*.json), pulando RSS e Claude.

    O JSON segue o mesmo formato que content_generator.generate_content devolve
    (category, subject, hook, slides, narration_script, youtube_title,
    youtube_description, tags, source, source_link). A fonte continua sendo
    citada na descrição — a regra de zero achômetro vale do mesmo jeito.
    """
    with open(path, encoding="utf-8") as f:
        content = json.load(f)
    for key in ("slides", "narration_script", "youtube_title", "youtube_description", "source", "source_link"):
        if not content.get(key):
            raise Exception(f"Roteiro manual sem o campo obrigatório '{key}': {path}")

    if content["source_link"] in load_used_links():
        raise Exception(f"Esse roteiro já foi publicado (link no histórico): {content['source_link']}")

    print(f"📝 Roteiro manual: {path}")
    print(f"   Fonte : {content['source']} — {content['source_link']}")
    print(f"   Título: {content['youtube_title']}\n")

    repo = os.path.join(os.path.dirname(__file__), "..")
    if content.get("video_file"):
        # vídeo já editado à mão (ex.: análise de clipe viral) — só publica
        video_path = os.path.join(repo, content["video_file"])
        if content.get("cover_file"):
            content["cover_path"] = os.path.join(repo, content["cover_file"])
        print(f"🎬 Vídeo pronto: {video_path}")
    else:
        print("🎙️  Gerando narração...")
        audio_path = generate_narration(content["narration_script"], "/tmp/bd_narration.mp3")
        _make_cover(content)

        print("\n🎬 Criando YouTube Short...")
        logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None
        video_path = create_video(content, "/tmp/bd_video.mp4", logo_path=logo, audio_path=audio_path)

    print("\n📤 Publicando no YouTube...")
    result = upload_video(video_path, content)
    save_used_link(content["source_link"])

    print("\n🎉 Short publicado!")
    print(f"   Título: {content['youtube_title']}")
    print(f"   URL   : {result['url']}")


def _publish_next_from_queue():
    """Publica o próximo roteiro de data/fila/ (ordem alfabética) e move pra data/manual/.

    Usado pelo horário extra do dia: 1 pauta forte escrita à mão por vez.
    Fila vazia não é erro — só não publica nada nesse horário.
    """
    used = load_used_links()
    queue = sorted(f for f in os.listdir(QUEUE_DIR) if f.endswith(".json")) if os.path.isdir(QUEUE_DIR) else []
    for name in queue:
        path = os.path.join(QUEUE_DIR, name)
        with open(path, encoding="utf-8") as f:
            link = json.load(f).get("source_link")
        done_path = os.path.join(MANUAL_DIR, name)
        if link in used:
            print(f"⏭️  {name} já publicado antes — tirando da fila.")
            os.replace(path, done_path)
            continue
        _publish_manual(path)
        os.replace(path, done_path)
        return
    print("📭 Fila vazia — nada extra pra publicar agora.")


def main():
    print("🇧🇷 Brasil Digital Bot — Iniciando...\n")

    try:
        if os.environ.get("FILA", "").strip() == "1":
            _publish_next_from_queue()
            return

        manual_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("MANUAL_JSON", "").strip()
        if manual_path:
            _publish_manual(manual_path)
            return

        print("📡 Buscando notícias reais e recentes de Tecnologia/IA...")
        candidates = fetch_candidates()
        print(f"   {len(candidates)} notícias candidatas encontradas nas fontes.")
        if not candidates:
            raise Exception("Nenhuma notícia recente encontrada em nenhuma fonte — abortando (sem inventar pauta).")

        used_links = load_used_links()
        unused = [c for c in candidates if c["link"] not in used_links]
        if not unused:
            raise Exception("Todas as notícias recentes já foram publicadas — nada novo e verificado pra postar agora.")
        try:
            article = pick_most_engaging(unused)
        except Exception as e:  # escolha editorial falhou: cai pra mais recente
            print(f"⚠️  Escolha por engajamento falhou ({e}); usando a mais recente.")
            article = pick_unused(candidates, used_links)

        print(f"✅ Notícia escolhida: [{article['source']}] {article['title']}")
        print(f"   Link: {article['link']}\n")

        print("📝 Adaptando a notícia (roteiro fiel à fonte, sem invenção)...")
        content = generate_content(article)
        print(f"   Categoria: {content['category']} — {content['subject']}")
        print(f"   Título: {content['youtube_title']}\n")

        print("🎙️  Gerando narração...")
        audio_path = generate_narration(content["narration_script"], "/tmp/bd_narration.mp3")
        _make_cover(content)

        print("\n🎬 Criando YouTube Short...")
        logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None
        video_path = create_video(content, "/tmp/bd_video.mp4", logo_path=logo, audio_path=audio_path)

        print("\n📤 Publicando no YouTube...")
        result = upload_video(video_path, content)

        save_used_link(article["link"])

        print(f"\n🎉 Short publicado!")
        print(f"   Fonte : {article['source']} — {article['link']}")
        print(f"   Título: {content['youtube_title']}")
        print(f"   URL   : {result['url']}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
