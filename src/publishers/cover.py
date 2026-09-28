"""note カバー画像の生成（1280×670）"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.config import MODEL_NAME, ROOT, WEEKDAY_JA, Series

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


def _font(size: int, bold: bool = False):
    for path in _BOLD if bold else _REGULAR:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def generate_intro_cover(output_path) -> str:
    """無料の紹介記事用カバー"""
    top, bottom, accent = (26, 42, 88), (8, 12, 32), (255, 214, 140)
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw_ctx = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        draw_ctx.line([(0, y), (WIDTH, y)], fill=tuple(int(a * (1 - t) + b * t) for a, b in zip(top, bottom)))

    rng = random.Random(7)
    ball_font = _font(28, bold=True)
    for row in range(3):
        for col in range(3):
            x, y, r = 960 + col * 115 + (55 if row % 2 else 0), 150 + row * 130, 44
            if x + r > WIDTH - 10:
                continue
            draw_ctx.ellipse([x - r, y - r, x + r, y + r], outline=accent, width=3)
            draw_ctx.text((x, y), f"{rng.randint(1, 43):02d}", font=ball_font, fill=accent, anchor="mm")

    draw_ctx.text((70, 150), "暦 × 統計で", font=_font(76, bold=True), fill=(255, 255, 255), anchor="lm")
    draw_ctx.text((70, 250), "数字を選ぶ", font=_font(76, bold=True), fill=(255, 255, 255), anchor="lm")
    draw_ctx.text((74, 360), "このノートの読み方と、毎週の検証のしかた", font=_font(38), fill=accent, anchor="lm")
    draw_ctx.text((74, 430), "ロト6 / ロト7 / ナンバーズ3・4", font=_font(34), fill=(255, 255, 255), anchor="lm")

    draw_ctx.rectangle([0, HEIGHT - 92, WIDTH, HEIGHT], fill=(0, 0, 0))
    draw_ctx.rectangle([0, HEIGHT - 96, WIDTH, HEIGHT - 92], fill=accent)
    draw_ctx.text((WIDTH // 2, HEIGHT - 46), f"統計×暦モデル {MODEL_NAME}", font=_font(34, bold=True), fill=accent, anchor="mm")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return str(output_path)


def generate_cover(series: Series, draw: int, target, ko: dict, output_path) -> str:
    top, bottom, accent = series.color
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw_ctx = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        draw_ctx.line([(0, y), (WIDTH, y)], fill=tuple(int(a * (1 - t) + b * t) for a, b in zip(top, bottom)))

    title = f"{series.title_name}予想"
    title_font = _font(92, bold=True)
    title_right = 70 + draw_ctx.textlength(title, font=title_font)

    # 右側に、文字と重ならない格子状の数字ボール
    rng = random.Random(draw)
    ball_font = _font(30, bold=True)
    r = 46
    for row in range(4):
        for col in range(3):
            x = 930 + col * 120 + (60 if row % 2 else 0) + rng.randint(-8, 8)
            y = 80 + row * 125 + rng.randint(-8, 8)
            skip = rng.random() < 0.25
            if skip or x + r > WIDTH - 10 or (y - r < 180 and x - r < title_right + 20) or (y - r < 280 and x - r < 800):
                continue
            label = str(rng.randint(0, 9)) if series.key == "numbers" else f"{rng.randint(1, 43):02d}"
            draw_ctx.ellipse([x - r, y - r, x + r, y + r], outline=accent, width=3)
            draw_ctx.text((x, y), label, font=ball_font, fill=accent, anchor="mm")

    draw_ctx.text((70, 120), title, font=title_font, fill=(255, 255, 255), anchor="lm")
    draw_ctx.text(
        (74, 245), f"第{draw}回　{target.month}/{target.day}（{WEEKDAY_JA[target.weekday()]}）抽せん",
        font=_font(50, bold=True), fill=accent, anchor="lm",
    )
    koyomi_line = f"{ko['rokuyo']}｜{ko['kyusei_name']}｜{ko['kanshi']}"
    if ko["lucky_days"]:
        koyomi_line += "｜" + "・".join(ko["lucky_days"])
    draw_ctx.text((76, 345), koyomi_line, font=_font(38), fill=(255, 255, 255), anchor="lm")
    draw_ctx.text((76, 420), "データ分析 × 暦　10パターン", font=_font(40, bold=True), fill=(255, 255, 255), anchor="lm")

    draw_ctx.rectangle([0, HEIGHT - 92, WIDTH, HEIGHT], fill=(0, 0, 0))
    draw_ctx.rectangle([0, HEIGHT - 96, WIDTH, HEIGHT - 92], fill=accent)
    draw_ctx.text((WIDTH // 2, HEIGHT - 46), f"統計×暦モデル {MODEL_NAME}", font=_font(34, bold=True), fill=accent, anchor="mm")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return str(output_path)
