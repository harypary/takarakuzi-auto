"""note カバー画像の生成（1280×670）"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.config import ROOT

WIDTH, HEIGHT = 1280, 670

_BOLD = [
    ROOT / "assets/fonts/NotoSansJP-Bold.ttf",
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("C:/Windows/Fonts/meiryob.ttc"),
    Path("C:/Windows/Fonts/YuGothB.ttc"),
]
_REGULAR = [
    ROOT / "assets/fonts/NotoSansJP-Regular.ttf",
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("C:/Windows/Fonts/meiryo.ttc"),
    Path("C:/Windows/Fonts/YuGothM.ttc"),
]


_SYMBOL = [
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("C:/Windows/Fonts/seguisym.ttf"),
]


def _symbol_font(size: int):
    """星座記号（♈〜♓）用。日本語フォントには記号が入っていないことがあるため別に用意する"""
    for path in _SYMBOL:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return _font(size, bold=True)


def _font(size: int, bold: bool = False):
    for path in _BOLD if bold else _REGULAR:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _gradient(draw_ctx, top, bottom) -> None:
    for y in range(HEIGHT):
        t = y / HEIGHT
        draw_ctx.line([(0, y), (WIDTH, y)], fill=tuple(int(a * (1 - t) + b * t) for a, b in zip(top, bottom)))


def _footer(draw_ctx, accent) -> None:
    from src.love_config import BRAND

    draw_ctx.rectangle([0, HEIGHT - 92, WIDTH, HEIGHT], fill=(0, 0, 0))
    draw_ctx.rectangle([0, HEIGHT - 96, WIDTH, HEIGHT - 92], fill=accent)
    draw_ctx.text((WIDTH // 2, HEIGHT - 46), f"恋愛占い　{BRAND}", font=_font(34, bold=True), fill=accent, anchor="mm")


def _save(img, output_path) -> str:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return str(output_path)


def generate_sign_cover(sign: dict, headline: str, period_text: str, output_path) -> str:
    """星座別の記事カバー（エレメント別の配色）"""
    from src.astro.signs import ELEMENT_ACCENT, ELEMENT_COLORS

    colors = ELEMENT_COLORS[sign["element"]]
    accent = ELEMENT_ACCENT[sign["element"]]
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw_ctx = ImageDraw.Draw(img)
    _gradient(draw_ctx, colors["bg_start"], colors["bg_end"])

    rng = random.Random(sum(ord(c) for c in sign["en"]))
    for _ in range(60):
        x, y = rng.randint(820, WIDTH - 20), rng.randint(30, HEIGHT - 120)
        r = rng.choice([1, 1, 2, 3])
        draw_ctx.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
    draw_ctx.text((1040, 230), sign["symbol"], font=_symbol_font(260), fill=accent, anchor="mm")

    draw_ctx.text((70, 130), sign["name"], font=_font(96, bold=True), fill=(255, 255, 255), anchor="lm")
    draw_ctx.text((74, 245), headline, font=_font(56, bold=True), fill=accent, anchor="lm")
    draw_ctx.text((74, 340), period_text, font=_font(40), fill=(255, 255, 255), anchor="lm")
    draw_ctx.text((74, 410), f"{sign['period']}生まれ／{sign['element']}のエレメント", font=_font(32),
                  fill=(255, 255, 255), anchor="lm")
    _footer(draw_ctx, accent)
    return _save(img, output_path)


def generate_ranking_cover(headline: str, period_text: str, output_path) -> str:
    """12星座まとめ記事のカバー"""
    from src.astro.signs import ZODIAC_SIGNS

    accent = (255, 214, 160)
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw_ctx = ImageDraw.Draw(img)
    _gradient(draw_ctx, (58, 26, 96), (16, 8, 32))

    symbol_font = _symbol_font(44)
    for i, sign in enumerate(ZODIAC_SIGNS):
        draw_ctx.text((900 + (i % 3) * 120, 90 + (i // 3) * 115), sign["symbol"], font=symbol_font,
                      fill=accent, anchor="mm")

    # 右側の星座記号（x=860〜）に重ならない大きさ
    draw_ctx.text((70, 150), headline, font=_font(56, bold=True), fill=(255, 255, 255), anchor="lm")
    draw_ctx.text((74, 270), period_text, font=_font(44), fill=accent, anchor="lm")
    draw_ctx.text((74, 360), "12星座すべての恋愛運を占いました", font=_font(36), fill=(255, 255, 255), anchor="lm")
    _footer(draw_ctx, accent)
    return _save(img, output_path)
