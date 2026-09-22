"""Capa/thumbnail que puxa clique: imagem gerada por IA do assunto + texto gigante.

Estilo da identidade do canal (arte "BRAZIL DIGITAL"): azul-escuro, brilho
verde/amarelo, letras grossas branco + amarelo, selo vermelho.

A imagem é só ilustração do tema (sem texto, sem logo, sem pessoa real) —
os fatos continuam vindo da fonte, a capa não afirma nada além do roteiro.
"""
import base64
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_ANTON = os.path.join(ASSETS, "fonts", "Anton-Regular.ttf")
FONT_MONT = os.path.join(ASSETS, "fonts", "Montserrat.ttf")

WHITE = (255, 255, 255)
YELLOW = (255, 214, 0)
GREEN = (0, 200, 90)
RED = (228, 20, 30)
NAVY = (4, 10, 30)
HANDLE = "@brazildigital"

IMAGE_STYLE = (
    "Vertical 9:16 photorealistic cinematic image for a YouTube thumbnail. "
    "High contrast, dramatic lighting, vivid colors, one clear focal subject, "
    "strong emotion. Leave the lower half slightly darker and uncluttered. "
    "Absolutely no text, letters, numbers, logos, watermarks or brand names. "
    "Do not depict any real, identifiable person or celebrity. Scene: "
)


def generate_background(image_prompt: str, out_path: str) -> str | None:
    """Gera o fundo com a OpenAI. Falhou? Devolve None e a capa usa o fundo neon."""
    if not image_prompt:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        r = client.images.generate(
            model="gpt-image-1", size="1024x1536", quality="medium",
            prompt=IMAGE_STYLE + image_prompt,
        )
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(r.data[0].b64_json))
        return out_path
    except Exception as e:
        print(f"⚠️  Imagem da capa falhou ({e}); usando fundo neon.")
        return None


def _mont(size, weight=b"Black"):
    f = ImageFont.truetype(FONT_MONT, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def _neon_background() -> Image.Image:
    """Fundo de reserva no estilo da arte do canal: navy + ondas verde/amarelo."""
    img = Image.new("RGB", (W, H), NAVY)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    for i, color in enumerate([GREEN, YELLOW, (0, 120, 255)]):
        off = i * 90
        pts = [(x, 1250 + off + int(160 * __import__("math").sin((x + off * 3) / 170))) for x in range(0, W + 20, 20)]
        d.line(pts, fill=color, width=22)
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    img = Image.blend(img, glow, 0.85)
    ImageDraw.Draw(img).ellipse([(W - 520, -260), (W + 260, 520)], outline=(0, 140, 255), width=6)
    return img


def _cover_fit(bg: Image.Image) -> Image.Image:
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * scale) + 1, int(bg.height * scale) + 1), Image.LANCZOS)
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    return bg.crop((left, top, left + W, top + H))


def _shade(img: Image.Image) -> Image.Image:
    """Escurece topo e metade de baixo pra o texto saltar sobre qualquer foto."""
    overlay = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(overlay)
    for y in range(H):
        if y < 380:
            a = int(150 * (1 - y / 380))
        elif y > 950:
            a = int(225 * min(1, (y - 950) / 600))
        else:
            a = 0
        d.line([(0, y), (W, y)], fill=a)
    black = Image.new("RGB", (W, H), (0, 0, 0))
    return Image.composite(black, img, overlay)


def _splits(words, n):
    """Todas as formas de dividir as palavras em n linhas (ordem mantida)."""
    if n == 1:
        yield [" ".join(words)]
        return
    for i in range(1, len(words) - n + 2):
        for rest in _splits(words[i:], n - 1):
            yield [" ".join(words[:i])] + rest


def _fit_lines(draw, words, font_path, max_w, max_h, max_size=250, min_size=100):
    """Escolhe a quebra de linha (1-3 linhas) que deixa a letra MAIOR cabendo na caixa."""
    ref = ImageFont.truetype(font_path, 100)
    asc, desc = ref.getmetrics()
    best = None
    for n in range(1, min(3, len(words)) + 1):
        for lines in _splits(words, n):
            widest = max(draw.textlength(l, font=ref) for l in lines)
            size = min(max_size, int(100 * max_w / widest),
                       int(100 * max_h / (n * (asc + desc) * 0.98)))
            if best is None or size > best[0]:
                best = (size, lines)
    size, lines = best
    return ImageFont.truetype(font_path, max(size, min_size)), lines


def _pill(draw, center, text, font, fill, fg=WHITE, pad=(40, 22)):
    w = draw.textlength(text, font=font)
    asc, desc = font.getmetrics()
    h = asc
    x0, y0 = center[0] - w / 2 - pad[0], center[1] - h / 2 - pad[1]
    x1, y1 = center[0] + w / 2 + pad[0], center[1] + h / 2 + pad[1]
    draw.rounded_rectangle([(x0, y0 + 6), (x1, y1 + 6)], radius=(y1 - y0) / 2, fill=(0, 0, 0))
    draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=(y1 - y0) / 2, fill=fill)
    draw.text(center, text, font=font, fill=fg, anchor="mm")


def make_cover(content: dict, bg_path: str | None = None) -> Image.Image:
    if bg_path and os.path.exists(bg_path):
        img = _cover_fit(Image.open(bg_path).convert("RGB"))
    else:
        img = _neon_background()
    img = _shade(img)

    # faixa verde-amarela fininha no topo (identidade Brasil)
    d = ImageDraw.Draw(img)
    d.rectangle([(0, 0), (W, 12)], fill=GREEN)
    d.rectangle([(0, 12), (W, 22)], fill=YELLOW)

    # selo vermelho (ALERTA / URGENTE / NOVIDADE ...)
    badge = (content.get("badge") or "NOVIDADE").upper()[:20]
    _pill(d, (W // 2, 200), badge, _mont(54), RED)

    # texto gigante: 1ª linha branca, depois amarelo (igual à arte do canal)
    text = (content.get("thumb_text") or content.get("subject") or "TECNOLOGIA").upper()
    # caixa do texto no terço de baixo, deixando a imagem (rosto/objeto) livre em cima
    font, lines = _fit_lines(d, text.split(), FONT_ANTON, W - 100, 560)
    asc, desc = font.getmetrics()
    lh = int((asc + desc) * 0.98)
    y_bottom = 1560  # acima da área coberta pelo título/botões do Shorts
    y0 = y_bottom - lh * len(lines)
    for i, line in enumerate(lines):
        color = WHITE if i == 0 and len(lines) > 1 else YELLOW
        y = y0 + i * lh + lh // 2
        # brilho atrás do texto
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).text((W // 2, y), line, font=font, anchor="mm",
                                  fill=color + (140,))
        img.paste(glow.filter(ImageFilter.GaussianBlur(22)), (0, 0), glow.filter(ImageFilter.GaussianBlur(22)))
        d = ImageDraw.Draw(img)
        d.text((W // 2, y), line, font=font, fill=color, anchor="mm",
               stroke_width=12, stroke_fill=(0, 0, 0))

    # marca do canal
    d.text((W // 2, y_bottom + 70), "BRAZIL DIGITAL  •  " + HANDLE, font=_mont(40, b"ExtraBold"),
           fill=WHITE, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    return img
