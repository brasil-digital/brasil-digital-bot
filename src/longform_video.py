"""Monta o vídeo longo 16:9 (1920x1080) a partir do roteiro em blocos.

Cada bloco = narração própria + imagem própria com movimento (zoom/pan) +
título do bloco + legenda frase a frase + fonte. No fim, 5s do cartão do
app Fala Brasil. Sem música, só narração.
"""
import json
import os
import re
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 30
PAUSE = 0.45  # respiro entre um bloco e outro

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_ANTON = os.path.join(ASSETS, "fonts", "Anton-Regular.ttf")
FONT_MONT = os.path.join(ASSETS, "fonts", "Montserrat.ttf")
LOGO = os.path.join(ASSETS, "logo.png")
APP_ICON = os.path.join(ASSETS, "fala_brasil_icon.png")

WHITE = (255, 255, 255)
YELLOW = (255, 214, 0)
GREEN = (0, 200, 90)
RED = (228, 20, 30)
NAVY = (4, 10, 30)

ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2"]


def _mont(size, weight=b"ExtraBold"):
    f = ImageFont.truetype(FONT_MONT, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise Exception(f"FFmpeg falhou: {r.stderr.decode(errors='ignore')[-800:]}")


def audio_duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
                       capture_output=True, text=True)
    return float(json.loads(r.stdout)["format"]["duration"])


def _wrap(draw, text, font, max_w):
    lines, cur = [], []
    for word in text.split():
        test = " ".join(cur + [word])
        if cur and draw.textlength(test, font=font) > max_w:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))
    return lines


def caption_chunks(text: str, max_chars: int = 84) -> list[str]:
    """Frases da narração em pedaços de no máx ~2 linhas de legenda."""
    chunks = []
    for sent in re.split(r"(?<=[.!?…])\s+", text.strip()):
        words = sent.split()
        if not words:
            continue
        # partes de tamanho parecido, pra não sobrar "pra" sozinho na tela
        k = -(-len(sent) // max_chars)
        target = len(sent) / k
        parts, cur = [], []
        for word in words:
            cur.append(word)
            if len(parts) < k - 1 and len(" ".join(cur)) >= target:
                parts.append(" ".join(cur))
                cur = []
        if cur:
            parts.append(" ".join(cur))
        chunks += parts
    return chunks


def _caption_png(text, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = _mont(46)
    lines = _wrap(d, text, font, 1500)[:3]
    lh = 60
    y0 = H - 70 - lh * len(lines)
    widest = max(d.textlength(l, font=font) for l in lines)
    d.rounded_rectangle([(W / 2 - widest / 2 - 28, y0 - 16), (W / 2 + widest / 2 + 28, H - 58)],
                        radius=14, fill=(0, 0, 0, 165))
    for i, line in enumerate(lines):
        d.text((W / 2, y0 + i * lh + lh / 2 - 6), line, font=font, fill=WHITE, anchor="mm")
    img.save(path)


def _frame_png(heading, category_label, source, path):
    """Moldura fixa do bloco: marca, categoria, título do bloco e fonte."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # sombra suave no topo pra marca ler sobre qualquer imagem
    for y in range(200):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, int(140 * (1 - y / 200))))
    d.rectangle([(0, 0), (W, 7)], fill=GREEN)
    d.rectangle([(0, 7), (W, 13)], fill=YELLOW)
    x = 44
    if os.path.exists(LOGO):
        logo = Image.open(LOGO).convert("RGBA")
        logo.thumbnail((78, 78), Image.LANCZOS)
        img.paste(logo, (x, 34), logo)
        x += logo.width + 16
    d.text((x, 73), "BRASIL DIGITAL", font=_mont(34, b"Black"), fill=WHITE, anchor="lm",
           stroke_width=3, stroke_fill=(0, 0, 0))
    # categoria à direita
    cf = _mont(26, b"Black")
    cw = d.textlength(category_label, font=cf)
    d.rounded_rectangle([(W - 44 - cw - 44, 50), (W - 44, 96)], radius=23, fill=RED)
    d.text((W - 44 - 22 - cw / 2, 73), category_label, font=cf, fill=WHITE, anchor="mm")
    # título do bloco (capítulo)
    if heading:
        hf = _mont(40, b"Black")
        hw = d.textlength(heading.upper(), font=hf)
        d.rectangle([(44, 136), (54, 196)], fill=YELLOW)
        d.rectangle([(54, 136), (54 + hw + 40, 196)], fill=(0, 0, 0, 175))
        d.text((74, 166), heading.upper(), font=hf, fill=WHITE, anchor="lm")
    # fonte
    sf = _mont(24, b"SemiBold")
    st = f"Fonte: {source}"
    sw = d.textlength(st, font=sf)
    d.rounded_rectangle([(W - 44 - sw - 32, 24 + 96), (W - 44, 24 + 136)], radius=10, fill=(0, 0, 0, 150))
    d.text((W - 44 - 16 - sw / 2, 24 + 116), st, font=sf, fill=(220, 220, 220), anchor="mm")
    img.save(path)


def _title_png(text, path):
    """Título gigante no começo do vídeo (primeiros segundos do gancho)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([(0, 330), (W, 750)], fill=(0, 0, 0, 150))
    size = 170
    while size > 80:
        font = ImageFont.truetype(FONT_ANTON, size)
        lines = _wrap(d, text.upper(), font, 1700)
        if len(lines) <= 2:
            break
        size -= 10
    lh = int(size * 1.15)
    y0 = 540 - lh * len(lines) / 2
    for i, line in enumerate(lines):
        color = WHITE if i == 0 and len(lines) > 1 else YELLOW
        d.text((W / 2, y0 + i * lh + lh / 2), line, font=font, fill=color, anchor="mm",
               stroke_width=8, stroke_fill=(0, 0, 0))
    img.save(path)


def _end_card_png(path):
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(4 + 6 * t), int(10 + 30 * t), int(30 + 30 * t)))
    d.rectangle([(0, 0), (W, 10)], fill=GREEN)
    d.rectangle([(0, 10), (W, 18)], fill=YELLOW)
    d.rectangle([(0, H - 18), (W, H - 10)], fill=YELLOW)
    d.rectangle([(0, H - 10), (W, H)], fill=GREEN)
    d.text((W / 2, 170), "OBRIGADO POR ASSISTIR", font=_mont(58, b"Black"), fill=WHITE, anchor="mm")
    d.text((W / 2, 245), "Se inscreva no BRASIL DIGITAL  •  @brazildigital", font=_mont(38, b"Bold"),
           fill=YELLOW, anchor="mm")
    if os.path.exists(APP_ICON):
        icon = Image.open(APP_ICON).convert("RGBA")
        icon.thumbnail((300, 300), Image.LANCZOS)
        mask = Image.new("L", icon.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([(0, 0), icon.size], radius=60, fill=255)
        img.paste(icon, ((W - icon.width) // 2, 360), mask)
    d.text((W / 2, 745), "Baixe o app Fala Brasil", font=_mont(64, b"Black"), fill=WHITE, anchor="mm")
    d.text((W / 2, 830), "falabrasil.digital", font=_mont(52, b"ExtraBold"), fill=YELLOW, anchor="mm")
    img.save(path)


MOTIONS = [
    # zoom in no centro
    ("1+0.13*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    # zoom out
    ("1.13-0.13*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    # pan esquerda → direita
    ("1.12", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"),
    # pan direita → esquerda
    ("1.12", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),
]


def render_section(idx, section, img_path, audio_path, out_path, tmp, category_label, source, title_text=None):
    speech = audio_duration(audio_path)
    dur = speech + PAUSE
    n = int(dur * FPS) + 1
    z, x, y = (m.format(n=n) for m in MOTIONS[idx % len(MOTIONS)])

    frame = os.path.join(tmp, f"frame_{idx}.png")
    _frame_png(section.get("heading", ""), category_label, source, frame)
    overlays = [(frame, None)]
    if title_text:
        tp = os.path.join(tmp, f"title_{idx}.png")
        _title_png(title_text, tp)
        overlays.append((tp, (0.0, 3.8)))

    chunks = caption_chunks(section["narration"])
    total_chars = sum(len(c) for c in chunks) or 1
    t = 0.0
    for j, chunk in enumerate(chunks):
        span = speech * len(chunk) / total_chars
        cp = os.path.join(tmp, f"cap_{idx}_{j}.png")
        _caption_png(chunk, cp)
        overlays.append((cp, (t, t + span)))
        t += span

    cmd = ["ffmpeg", "-y", "-i", img_path]
    for p, _ in overlays:
        cmd += ["-i", p]
    cmd += ["-i", audio_path]

    filt = [f"[0:v]scale=3840:-2,crop=3840:2160,zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={W}x{H}:fps={FPS}[v0]"]
    for k, (_, window) in enumerate(overlays, start=1):
        en = f":enable='between(t,{window[0]:.2f},{window[1]:.2f})'" if window else ""
        filt.append(f"[v{k-1}][{k}:v]overlay=0:0{en}[v{k}]")
    audio_idx = len(overlays) + 1
    filt.append(f"[{audio_idx}:a]apad[a]")

    cmd += ["-filter_complex", ";".join(filt), "-map", f"[v{len(overlays)}]", "-map", "[a]",
            "-t", f"{dur:.3f}"] + ENC + [out_path]
    _run(cmd)
    return dur


def render_end_card(out_path, tmp, seconds=5):
    png = os.path.join(tmp, "endcard.png")
    _end_card_png(png)
    _run(["ffmpeg", "-y", "-loop", "1", "-i", png, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
          "-t", str(seconds), "-vf", f"scale={W}:{H}"] + ENC + [out_path])


def concat(parts, out_path, tmp):
    lst = os.path.join(tmp, "parts.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p).replace(os.sep, '/')}'\n")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
          "-movflags", "+faststart", out_path])
