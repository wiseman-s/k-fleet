"""Generate simple K-FLEET app icons (192 and 512) as PNGs."""
from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs("app/static/icons", exist_ok=True)

def make_icon(size, path):
    img = Image.new("RGB", (size, size), color=(15, 23, 42))  # #0f172a
    draw = ImageDraw.Draw(img)

    # Green square border accent
    border = max(4, size // 40)
    draw.rectangle(
        [border, border, size - border - 1, size - border - 1],
        outline=(34, 197, 94),  # #22c55e
        width=border
    )

    # Try to load a font, fall back to default
    text = "KF"
    try:
        font = ImageFont.truetype("arial.ttf", int(size * 0.42))
    except Exception:
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

    if font:
        # Center the text
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            ((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
            text,
            fill=(226, 232, 240),  # #e2e8f0
            font=font
        )

    img.save(path, "PNG")
    print(f"Saved {path}")

make_icon(192, "app/static/icons/icon-192.png")
make_icon(512, "app/static/icons/icon-512.png")
print("Done.")