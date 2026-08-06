import os
import sys
import traceback

from news_fetcher import fetch_candidates, pick_unused
from history import load_used_links, save_used_link
from content_generator import generate_content
from narration import generate_narration
from video_creator import create_video
from youtube_uploader import upload_video

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png")


def main():
    print("🇧🇷 Brasil Digital Bot — Iniciando...\n")

    try:
        print("📡 Buscando notícias reais e recentes de Tecnologia/IA...")
        candidates = fetch_candidates()
        print(f"   {len(candidates)} notícias candidatas encontradas nas fontes.")
        if not candidates:
            raise Exception("Nenhuma notícia recente encontrada em nenhuma fonte — abortando (sem inventar pauta).")

        used_links = load_used_links()
        article = pick_unused(candidates, used_links)
        if not article:
            raise Exception("Todas as notícias recentes já foram publicadas — nada novo e verificado pra postar agora.")

        print(f"✅ Notícia escolhida: [{article['source']}] {article['title']}")
        print(f"   Link: {article['link']}\n")

        print("📝 Adaptando a notícia (roteiro fiel à fonte, sem invenção)...")
        content = generate_content(article)
        print(f"   Categoria: {content['category']} — {content['subject']}")
        print(f"   Título: {content['youtube_title']}\n")

        print("🎙️  Gerando narração...")
        audio_path = generate_narration(content["narration_script"], "/tmp/bd_narration.mp3")

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
