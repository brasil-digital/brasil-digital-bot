import os
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

# YouTube Shorts: vertical 9:16
W, H = 1080, 1920


def _find_font(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


FONT_BOLD = _find_font([
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
])
FONT_REG = _find_font([
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
])
FONT_DISPLAY = _find_font([
    "C:/Windows/Fonts/impact.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
])

# Paleta Brasil Digital — mesma família de cores da Rádio IA Fala Brasil
GREEN = (0, 168, 89)
YELLOW = (255, 210, 0)
BLUE = (0, 120, 200)
WHITE = (245, 245, 245)
BG_A = (8, 10, 18)

GRADIENTS = {
    "ia":             ((5, 10, 30), (12, 25, 55)),
    "big-techs":      ((5, 20, 25), (10, 40, 45)),
    "ciberseguranca": ((25, 5, 10), (50, 10, 15)),
    "mercado-tech":   ((5, 20, 10), (10, 40, 20)),
    "ciencia":        ((10, 15, 30), (20, 30, 55)),
    "default":        ((8, 12, 20), (16, 24, 38)),
}

CATEGORY_LABELS = {
    "ia": "INTELIGÊNCIA ARTIFICIAL",
    "big-techs": "BIG TECHS",
    "ciberseguranca": "CIBERSEGURANÇA",
    "mercado-tech": "MERCADO TECH",
    "ciencia": "CIÊNCIA E TECH",
}

TITLE_CARD_DUR = 1.3
BRAND_NAME = "BRASIL DIGITAL"


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _gradient(draw, top, bot):
    for y in range(H):
        t = y / H
        r = int(top[0] + (bot[0] - top[0]) * t)
        g = int(top[1] + (bot[1] - top[1]) * t)
        b = int(top[2] + (bot[2] - top[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def _wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _watermark(img, draw, logo_path, opacity=0.18, size_frac=0.72, y_offset=-40):
    if not (logo_path and os.path.exists(logo_path)):
        return img, draw
    try:
        wm = Image.open(logo_path).convert("RGBA")
        wm_size = int(W * size_frac)
        wm = wm.resize((wm_size, wm_size), Image.LANCZOS)
        r, g, b, a = wm.split()
        a = a.point(lambda x: int(x * opacity))
        wm.putalpha(a)
        wm_x = (W - wm_size) // 2
        wm_y = (H - wm_size) // 2 + y_offset
        img_rgba = img.convert("RGBA")
        img_rgba.paste(wm, (wm_x, wm_y), wm)
        img = img_rgba.convert("RGB")
        draw = ImageDraw.Draw(img)
    except Exception:
        pass
    return img, draw


def _make_slide(slide_text, slide_num, total_slides, category, subject, logo_path):
    img = Image.new("RGB", (W, H), BG_A)
    draw = ImageDraw.Draw(img)

    grad = GRADIENTS.get(category, GRADIENTS["default"])
    _gradient(draw, grad[0], grad[1])

    img, draw = _watermark(img, draw, logo_path)

    # Faixas Brasil
    draw.rectangle([(0, 0), (W, 10)], fill=GREEN)
    draw.rectangle([(0, 10), (W, 20)], fill=YELLOW)
    draw.rectangle([(0, H - 20), (W, H - 10)], fill=YELLOW)
    draw.rectangle([(0, H - 10), (W, H)], fill=GREEN)

    f_brand = _font(FONT_BOLD, 36)
    f_subject = _font(FONT_REG, 30)
    f_main = _font(FONT_BOLD, 60)
    f_cta = _font(FONT_BOLD, 46)

    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((100, 100), Image.LANCZOS)
            img.paste(logo, (40, 35), logo)
        except Exception:
            pass

    draw.text((W - 40, 65), BRAND_NAME, font=f_brand, fill=BLUE, anchor="rm")

    if subject and slide_num < total_slides:
        draw.text((W // 2, 170), subject.upper(), font=f_subject, fill=YELLOW, anchor="mm")

    sep_y = 220
    draw.rectangle([(80, sep_y), (W - 80, sep_y + 2)], fill=(60, 70, 80))

    is_cta = slide_num == total_slides
    font_main = f_cta if is_cta else f_main
    max_w = W - 120
    lines = _wrap_text(slide_text, font_main, max_w, draw)

    line_h = 74 if not is_cta else 66
    total_text_h = len(lines) * line_h
    start_y = (H - total_text_h) // 2 + 30

    for i, line in enumerate(lines):
        y = start_y + i * line_h
        draw.text((W // 2 + 2, y + 2), line, font=font_main, fill=(0, 0, 0), anchor="mm")
        color = YELLOW if is_cta else WHITE
        draw.text((W // 2, y), line, font=font_main, fill=color, anchor="mm")

    dot_r, dot_gap = 10, 35
    total_w = total_slides * (2 * dot_r) + (total_slides - 1) * (dot_gap - 2 * dot_r)
    start_x = (W - total_w) // 2 + dot_r
    for d in range(total_slides):
        cx = start_x + d * dot_gap
        cy = H - 50
        color = BLUE if d == slide_num - 1 else (60, 70, 80)
        draw.ellipse([(cx - dot_r, cy - dot_r), (cx + dot_r, cy + dot_r)], fill=color)

    return img


def _fit_display_font(draw, text, max_width, max_lines, start_size, min_size=56):
    size = start_size
    while size > min_size:
        font = _font(FONT_DISPLAY, size)
        lines = _wrap_text(text, font, max_width, draw)
        if len(lines) <= max_lines and all(
            draw.textbbox((0, 0), l, font=font)[2] <= max_width for l in lines
        ):
            return font, lines
        size -= 8
    font = _font(FONT_DISPLAY, min_size)
    return font, _wrap_text(text, font, max_width, draw)


def _make_title_card(category, subject, hook, logo_path):
    img = Image.new("RGB", (W, H), BG_A)
    draw = ImageDraw.Draw(img)

    grad = GRADIENTS.get(category, GRADIENTS["default"])
    top = tuple(min(255, int(c * 1.6)) for c in grad[0])
    bot = tuple(min(255, int(c * 2.6)) for c in grad[1])
    _gradient(draw, top, bot)

    img, draw = _watermark(img, draw, logo_path, opacity=0.12, size_frac=0.9, y_offset=0)

    draw.rectangle([(0, 0), (W, 18)], fill=GREEN)
    draw.rectangle([(0, 18), (W, 36)], fill=YELLOW)
    draw.rectangle([(0, H - 36), (W, H - 18)], fill=YELLOW)
    draw.rectangle([(0, H - 18), (W, H)], fill=GREEN)

    logo_bottom = 150
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((190, 190), Image.LANCZOS)
            mask = Image.new("L", logo.size, 0)
            ImageDraw.Draw(mask).ellipse([(0, 0), logo.size], fill=255)
            img.paste(logo, ((W - logo.width) // 2, 110), mask)
            logo_bottom = 110 + logo.height
        except Exception:
            pass

    f_brand = _font(FONT_BOLD, 50)
    draw.text((W // 2, logo_bottom + 55), BRAND_NAME,
              font=f_brand, fill=YELLOW, anchor="mm",
              stroke_width=4, stroke_fill=(0, 0, 0))

    label = CATEGORY_LABELS.get(category, "TECNOLOGIA")
    f_tag = _font(FONT_BOLD, 42)
    tb = draw.textbbox((0, 0), label, font=f_tag)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    tag_y = 640
    draw.rounded_rectangle(
        [(W // 2 - tw // 2 - 34, tag_y - th // 2 - 24),
         (W // 2 + tw // 2 + 34, tag_y + th // 2 + 24)],
        radius=20, fill=BLUE)
    draw.text((W // 2, tag_y), label, font=f_tag, fill=WHITE, anchor="mm")

    subject_up = (subject or "TECNOLOGIA").upper()
    font_subj, lines = _fit_display_font(draw, subject_up, W - 140, 3, 180)
    asc, desc = font_subj.getmetrics()
    line_h = int((asc + desc) * 1.02)
    total_h = line_h * len(lines)
    y0 = 1010 - total_h // 2
    for i, line in enumerate(lines):
        draw.text((W // 2, y0 + i * line_h), line, font=font_subj,
                  fill=WHITE, anchor="mm", stroke_width=10, stroke_fill=(0, 0, 0))

    if hook:
        f_hook = _font(FONT_BOLD, 50)
        hook_lines = _wrap_text(hook, f_hook, W - 200, draw)[:2]
        hy = y0 + total_h + 80
        for i, hl in enumerate(hook_lines):
            draw.text((W // 2, hy + i * 62), hl, font=f_hook,
                      fill=YELLOW, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))

    f_cta = _font(FONT_BOLD, 40)
    draw.text((W // 2, H - 140), "NOTÍCIA VERIFICADA",
              font=f_cta, fill=WHITE, anchor="mm",
              stroke_width=3, stroke_fill=(0, 0, 0))

    return img


def _audio_duration(audio_path: str) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", audio_path
    ], capture_output=True, text=True)
    import json
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "audio":
            return float(stream.get("duration", 45))
    return 45.0


def create_video(content, output_path="/tmp/brasil_digital_video.mp4", logo_path=None, audio_path=None):
    slides = content["slides"]
    category = content.get("category", "default")
    subject = content.get("subject", "")

    print(f"🎬 Criando Short: {content.get('youtube_title', BRAND_NAME)}")
    print(f"   Categoria: {category} | Assunto: {subject} | {len(slides)} slides")

    if audio_path and os.path.exists(audio_path):
        total_duration = _audio_duration(audio_path)
        print(f"   Duração do áudio: {total_duration:.1f}s")
    else:
        total_duration = len(slides) * 9.0

    card_dur = TITLE_CARD_DUR if total_duration > 8 else 0
    slide_dur = (total_duration - card_dur) / len(slides)

    with tempfile.TemporaryDirectory() as tmp:
        imgs = []
        if card_dur:
            card = _make_title_card(category, subject, content.get("hook", ""), logo_path)
            card_path = os.path.join(tmp, "slide_card.png")
            card.save(card_path)
            imgs.append((card_path, card_dur))
            print("   Cartão de título (capa do Short)")
        for i, slide in enumerate(slides):
            img = _make_slide(slide["text"], i + 1, len(slides), category, subject, logo_path)
            path = os.path.join(tmp, f"slide_{i:02d}.png")
            img.save(path)
            imgs.append((path, slide_dur))
            print(f"   Slide {i+1}/{len(slides)}")

        concat_file = os.path.join(tmp, "slides.txt")
        with open(concat_file, "w") as f:
            for path, dur in imgs:
                f.write(f"file '{path}'\n")
                f.write(f"duration {dur:.3f}\n")
            f.write(f"file '{imgs[-1][0]}'\n")

        slides_mp4 = os.path.join(tmp, "slides_silent.mp4")
        result = subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_file,
            "-vf", "fps=30,scale=1080:1920:flags=lanczos,format=yuv420p",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            slides_mp4,
        ], capture_output=True)

        if result.returncode != 0:
            raise Exception(f"FFmpeg slides error: {result.stderr.decode()[-500:]}")

        if audio_path and os.path.exists(audio_path):
            result = subprocess.run([
                "ffmpeg", "-y",
                "-i", slides_mp4,
                "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                output_path,
            ], capture_output=True)
        else:
            os.rename(slides_mp4, output_path)
            result = type("R", (), {"returncode": 0})()

        if result.returncode != 0:
            raise Exception(f"FFmpeg merge error: {result.stderr.decode()[-500:]}")

    print(f"✅ Vídeo criado: {output_path}")
    return output_path
