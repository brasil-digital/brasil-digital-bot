"""Vídeo LONGO do Brasil Digital (aba Vídeos): 3-4 min, 16:9, notícia real.

Uso:
  python src/longform.py                      → pauta automática (RSS + texto completo)
  python src/longform.py data/longos/x.json   → roteiro pronto (mesmo formato de write_script)
  DRY_RUN=1 → monta o vídeo e a capa, mas não publica (pra conferir antes)
"""
import base64
import datetime
import json
import os
import shutil
import sys
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor

from news_fetcher import LONGFORM_FEEDS, fetch_candidates
from longform_writer import CATEGORIES, pick_and_write
from longform_video import concat, render_end_card, render_section
from narration import generate_narration
from thumbnail import _neon_background, generate_background, make_cover_wide
from youtube_uploader import upload_video

ROOT = os.path.join(os.path.dirname(__file__), "..")
HISTORY_PATH = os.path.join(ROOT, "data", "longform_history.json")
MAX_AGE_HOURS = 72  # 3 vídeos por semana: janela entre um e outro
APP_LINE = "📱 Baixe o app Fala Brasil: https://falabrasil.digital"

SCENE_STYLE = (
    "Horizontal 16:9 photorealistic cinematic news b-roll image, dramatic lighting, rich detail, "
    "documentary style. Absolutely no text, letters, numbers, logos, watermarks or brand names. "
    "Do not depict any real, identifiable person, celebrity or politician. Scene: "
)


def load_history() -> list[dict]:
    try:
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(script: dict, url: str) -> None:
    hist = load_history()
    hist.append({
        "date": datetime.date.today().isoformat(),
        "title": script["youtube_title"],
        "category": script["category"],
        "link": script["source_link"],
        "url": url,
    })
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(hist[-100:], f, ensure_ascii=False, indent=2)


def scene_image(prompt: str, out_path: str) -> str:
    """Imagem do bloco (1536x1024). Falhou? Fundo neon do canal, o vídeo não para."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        r = client.images.generate(model="gpt-image-1", size="1536x1024", quality="medium",
                                   prompt=SCENE_STYLE + prompt)
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(r.data[0].b64_json))
    except Exception as e:
        print(f"⚠️  Imagem falhou ({e}); usando fundo neon.")
        _neon_background(1536, 1024).save(out_path)
    return out_path


def _ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


def build_description(script: dict, durations: list[float]) -> str:
    """Descrição + capítulos automáticos (YouTube exige 00:00, 3+ capítulos, cada um ≥10s)."""
    chapters, t = [], 0.0
    for sec, dur in zip(script["sections"], durations):
        if not chapters or (t - chapters[-1][0] >= 10 and dur >= 10):
            chapters.append((t, sec["heading"]))
        t += dur
    parts = [script["youtube_description"].strip()]
    if len(chapters) >= 3:
        parts.append("Capítulos:\n" + "\n".join(f"{_ts(s)} {h}" for s, h in chapters))
    parts.append(f"Fonte: {script['source']} — {script['source_link']}")
    parts.append(APP_LINE)
    parts.append(" ".join(script.get("hashtags") or ["#BrasilDigital"]))
    return "\n\n".join(parts)


def produce(script: dict, workdir: str) -> tuple[str, str, list[float]]:
    sections = script["sections"]
    label = CATEGORIES.get(script["category"], "TECNOLOGIA")

    print(f"\n🎙️  Narração ({len(sections)} blocos) + 🖼️  imagens...")
    with ThreadPoolExecutor(max_workers=4) as pool:
        imgs = list(pool.map(
            lambda p: scene_image(p[1]["image_prompt"], os.path.join(workdir, f"img_{p[0]}.png")),
            enumerate(sections)))
        audios = list(pool.map(
            lambda p: generate_narration(p[1]["narration"], os.path.join(workdir, f"voz_{p[0]}.mp3")),
            enumerate(sections)))
        cover_bg = pool.submit(generate_background, script.get("thumb_image_prompt", ""),
                               os.path.join(workdir, "capa_bg.png"), True).result()

    cover = os.path.join(workdir, "capa.jpg")
    make_cover_wide(script, cover_bg).save(cover, quality=90)

    print("\n🎬 Montando os blocos...")
    parts, durations = [], []
    for i, sec in enumerate(sections):
        out = os.path.join(workdir, f"bloco_{i:02d}.mp4")
        durations.append(render_section(i, sec, imgs[i], audios[i], out, workdir, label, script["source"],
                                        title_text=script.get("thumb_text") if i == 0 else None))
        parts.append(out)
        print(f"   Bloco {i + 1}/{len(sections)}: {sec['heading']} ({durations[-1]:.0f}s)")
    end = os.path.join(workdir, "final_app.mp4")
    render_end_card(end, workdir)
    parts.append(end)

    video = os.path.join(workdir, "video_longo.mp4")
    concat(parts, video, workdir)
    print(f"✅ Vídeo: {sum(durations) + 5:.0f}s")
    return video, cover, durations


def main():
    print("🇧🇷 Brasil Digital — VÍDEO LONGO\n")
    try:
        history = load_history()
        manual = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ROTEIRO_LONGO", "").strip()
        if manual:
            with open(manual, encoding="utf-8") as f:
                script = json.load(f)
            print(f"📝 Roteiro pronto: {manual}")
        else:
            print("📡 Buscando notícias reais (tech, IA, golpes, guerra tech, política tech)...")
            used = {h["link"] for h in history}
            candidates = [c for c in fetch_candidates(MAX_AGE_HOURS, LONGFORM_FEEDS) if c["link"] not in used]
            print(f"   {len(candidates)} candidatas.")
            if not candidates:
                raise Exception("Nenhuma notícia nova e recente — não publica (sem inventar pauta).")
            script = pick_and_write(candidates, history)

        print(f"\n✅ [{script['category']}] {script['youtube_title']}")
        print(f"   Fonte: {script['source']} — {script['source_link']}")

        workdir = tempfile.mkdtemp(prefix="bd_longo_")
        video, cover, durations = produce(script, workdir)
        content = {
            "youtube_title": script["youtube_title"],
            "youtube_description": build_description(script, durations),
            "tags": script.get("tags", []),
            "cover_path": cover,
        }

        if os.environ.get("DRY_RUN") == "1":
            out_dir = os.environ.get("OUT_DIR", workdir)
            os.makedirs(out_dir, exist_ok=True)
            for p in (video, cover):
                shutil.copy(p, out_dir)
            with open(os.path.join(out_dir, "roteiro.json"), "w", encoding="utf-8") as f:
                json.dump(script, f, ensure_ascii=False, indent=2)
            with open(os.path.join(out_dir, "descricao.txt"), "w", encoding="utf-8") as f:
                f.write(content["youtube_title"] + "\n\n" + content["youtube_description"])
            print(f"\n🧪 DRY_RUN: nada publicado. Arquivos em {out_dir}")
            return

        print("\n📤 Publicando no YouTube...")
        result = upload_video(video, content)
        save_history(script, result["url"])
        print(f"\n🎉 Vídeo publicado: {result['url']}")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
