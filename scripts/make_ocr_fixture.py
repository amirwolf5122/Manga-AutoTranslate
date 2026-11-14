#!/usr/bin/env python3
import argparse
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "fonts", "Vazirmatn-Bold.ttf")

WORDS = [
    "WHERE ARE YOU GOING",
    "THE HIDDEN POWER",
    "I WILL NEVER GIVE UP",
    "SHADOW STRIKE",
]


def _font(px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, px)


def _text_size(text: str, f) -> tuple:
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    bb = d.textbbox((0, 0), text, font=f)
    return bb[2] - bb[0], bb[3] - bb[1]


def make_rotated(text: str, angle_deg: float, font_px: int = 54,
                 size=(1200, 700)) -> tuple:
    f = _font(font_px)
    tw, th = _text_size(text, f)
    a = math.radians(abs(angle_deg))
    ext_w = tw * math.cos(a) + th * math.sin(a) + 2 * font_px
    ext_h = tw * math.sin(a) + th * math.cos(a) + 2 * font_px
    W = max(int(size[0]), int(ext_w) + 80)
    H = max(int(size[1]), int(ext_h) + 80)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = W // 2, H // 2
    d.text((cx - tw / 2, cy - th / 2), text, font=f, fill=(20, 20, 20))
    rot = layer.rotate(angle_deg, resample=Image.BICUBIC, expand=False,
                       center=(cx, cy))
    img = Image.alpha_composite(img.convert("RGBA"), rot).convert("RGB")
    gt = {"kind": "rotated", "text": text, "angle": angle_deg,
          "center": [cx, cy], "size": [W, H]}
    return img, gt


def _draw_arc(img: ImageDraw.Draw, text: str, radius: float,
              cx: int, cy: int, f, bulge_up: bool = True,
              fill=(20, 20, 20)):
    pts = []
    widths = [_text_size(ch, f)[0] if ch != " " else _text_size("n", f)[0]
              for ch in text]
    total_ang = sum(w / radius for w in widths)
    theta = -total_ang / 2
    glyph_cache = {}
    for ch, w in zip(text, widths):
        if ch != " ":
            th = theta + (w / radius) / 2
            if bulge_up:
                x = cx + radius * math.sin(th)
                y = cy - radius * math.cos(th)
                rot = -math.degrees(th)
            else:
                x = cx + radius * math.sin(th)
                y = cy + radius * math.cos(th)
                rot = +math.degrees(th)
            key = int(rot * 10)
            if key not in glyph_cache:
                gs = f.size * 3
                glyph_cache[key] = Image.new("RGBA", (gs, gs), (0, 0, 0, 0))
                gd = ImageDraw.Draw(glyph_cache[key])
                gb = gd.textbbox((0, 0), ch, font=f)
                gd.text(((gs - (gb[2] - gb[0])) / 2 - gb[0],
                         (gs - (gb[3] - gb[1])) / 2 - gb[1]),
                        ch, font=f, fill=fill)
            g = glyph_cache[key]
            g2 = g.rotate(rot, resample=Image.BICUBIC, expand=False)
            gs = g.size[0]
            img.canvas.paste(
                Image.alpha_composite(
                    img.canvas.crop((int(x - gs / 2), int(y - gs / 2),
                                     int(x + gs / 2), int(y + gs / 2))
                    ).convert("RGBA"), g2).convert("RGB"),
                (int(x - gs / 2), int(y - gs / 2)))
            pts.append((x, y, rot))
        theta += w / radius
    return pts


class _ArcCanvas:

    def __init__(self, img):
        self.canvas = img
        self.draw = ImageDraw.Draw(img)


def make_curved(text: str, radius: float, font_px: int = 52,
                bulge_up: bool = True, pad: int = 70) -> tuple:
    f = _font(font_px)
    widths = [_text_size(ch, f)[0] if ch != " " else _text_size("n", f)[0]
              for ch in text]
    total_ang = sum(w / radius for w in widths)
    half = total_ang / 2
    chord = 2 * radius * math.sin(half)
    gs = f.size * 3
    m = gs // 2 + pad
    W = int(chord + 2 * m)
    H = int(radius + gs + 2 * pad)
    img = Image.new("RGB", (W, H), (255, 255, 255))
    ac = _ArcCanvas(img)
    cx = W / 2
    cy = (radius + m) if bulge_up else (H - radius - m)
    pts = _draw_arc(ac, text, radius, cx, cy, f, bulge_up=bulge_up)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    gt = {"kind": "curved", "text": text, "radius": radius,
          "center": [int(sum(xs) / len(xs)), int(sum(ys) / len(ys))],
          "size": [W, H],
          "angle_mean": sum(p[2] for p in pts) / len(pts)}
    return img, gt


def make_curved_page(text: str, radius: float, font_px: int = 52,
                     bulge_up: bool = True, size=(1600, 2260),
                     cy_frac: float = 0.5) -> tuple:
    from PIL import Image
    img = Image.new("RGB", size, (255, 255, 255))
    ac = _ArcCanvas(img)
    f = _font(font_px)
    cx = size[0] / 2
    cy = size[1] * cy_frac + (radius if bulge_up else -radius)
    pts = _draw_arc(ac, text, radius, cx, cy, f, bulge_up=bulge_up)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    gt = {"kind": "curved", "text": text, "radius": radius,
          "center": [int(sum(xs) / len(xs)), int(sum(ys) / len(ys))],
          "size": list(size),
          "angle_mean": sum(p[2] for p in pts) / len(pts)}
    return img, gt


def make_page_mixed() -> tuple:
    gt = {"kind": "page_mixed", "items": [], "size": None}
    f = _font(52)
    W, H = 1600, 2260
    img = Image.new("RGB", (W, H), (255, 255, 255))
    plans = [(WORDS[0], -18, (430, 250)), (WORDS[1], 10, (1150, 400)),
             (WORDS[2], -26, (560, 600))]
    for text, ang, (cx, cy) in plans:
        tw, th = _text_size(text, f)
        a = math.radians(abs(ang))
        ew = tw * math.cos(a) + th * math.sin(a)
        eh = tw * math.sin(a) + th * math.cos(a)
        cx = min(max(cx, ew / 2 + 20), W - ew / 2 - 20)
        cy = min(max(cy, eh / 2 + 20), H - eh / 2 - 20)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(layer)
        dl.text((cx - tw / 2, cy - th / 2), text, font=f, fill=(20, 20, 20))
        rot = layer.rotate(ang, resample=Image.BICUBIC, expand=False,
                           center=(cx, cy))
        img = Image.alpha_composite(img.convert("RGBA"), rot).convert("RGB")
        gt["items"].append({"kind": "rotated", "text": text,
                            "angle": ang, "center": [int(cx), int(cy)]})
    for text, r, up, ytop in ((WORDS[3], 300, True, 800),
                              ("DESTINY", 560, False, 1400)):
        sub, g = make_curved(text, r, font_px=50, bulge_up=up)
        img.paste(sub, ((W - sub.size[0]) // 2, ytop))
        g["center"] = [g["center"][0] + (W - sub.size[0]) // 2,
                       g["center"][1] + ytop]
        g["size"] = [W, H]
        gt["items"].append(g)
    gt["size"] = [W, H]
    return img, gt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "ci_imgs",
                                                  "fixtures"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    gt = {"font": os.path.relpath(FONT, ROOT), "fixtures": {}}

    def put(name, img, g):
        img.save(os.path.join(args.out, name))
        gt["fixtures"][name] = g
        print("  ساخته شد:", name, img.size)

    for ang in (-26, -18, -10, 10, 18):
        put(f"rot_{ang:+d}.png".replace("+", "p").replace("-", "m"),
            *make_rotated(WORDS[0], ang))
    put("arc_r260.png", *make_curved_page(WORDS[1], 300, bulge_up=True,
                                          cy_frac=0.5))
    put("arc_r520.png", *make_curved_page(WORDS[2], 560,
                                          bulge_up=False,
                                          cy_frac=0.5))
    put("page_mixed.png", *make_page_mixed())

    with open(os.path.join(args.out, "ground_truth.json"), "w",
              encoding="utf-8") as fh:
        json.dump(gt, fh, ensure_ascii=False, indent=1)
    print("  حقیقتِ زمینی:", os.path.join(args.out, "ground_truth.json"))


if __name__ == "__main__":
    sys.exit(main())
