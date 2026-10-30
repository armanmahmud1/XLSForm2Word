"""Generate the application icon (assets/icon.ico and assets/icon.png)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SIZE = 1024

WINDOW_FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in WINDOW_FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _rounded_gradient(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient = Image.new("RGBA", (size, size))
    pixels = gradient.load()
    top = (67, 160, 71)
    bottom = (27, 94, 32)
    for y in range(size):
        ratio = y / max(size - 1, 1)
        color = tuple(
            int(top[index] + (bottom[index] - top[index]) * ratio) for index in range(3)
        )
        for x in range(size):
            pixels[x, y] = (*color, 255)

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    inset = int(size * 0.035)
    mask_draw.rounded_rectangle(
        (inset, inset, size - inset, size - inset),
        radius=int(size * 0.22),
        fill=255,
    )
    image.putalpha(mask)
    image.alpha_composite(Image.new("RGBA", (size, size), (0, 0, 0, 0)))
    return image


def create_icon() -> Image.Image:
    canvas = _rounded_gradient(SIZE)
    draw = ImageDraw.Draw(canvas)

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    page = (286, 194, 742, 836)
    shadow_draw.rounded_rectangle(
        (page[0] + 14, page[1] + 20, page[2] + 14, page[3] + 20),
        radius=34,
        fill=(0, 0, 0, 65),
    )
    canvas.alpha_composite(shadow)

    draw.rounded_rectangle(page, radius=34, fill=(255, 255, 255, 255))
    draw.rounded_rectangle(
        (page[0], page[1], page[2], page[1] + 158),
        radius=34,
        fill=(46, 125, 50, 255),
    )
    draw.rectangle(
        (page[0], page[1] + 110, page[2], page[1] + 158),
        fill=(46, 125, 50, 255),
    )

    small_font = _font(104)
    big_font = _font(300)
    label_font = _font(56)

    draw.text(
        ((page[0] + page[2]) / 2, page[1] + 82),
        "XLS",
        font=small_font,
        fill=(255, 255, 255, 255),
        anchor="mm",
    )
    draw.text(
        ((page[0] + page[2]) / 2, 500),
        "W",
        font=big_font,
        fill=(46, 125, 50, 255),
        anchor="mm",
    )
    draw.line(
        (page[0] + 80, 700, page[2] - 80, 700),
        fill=(200, 221, 203, 255),
        width=10,
    )
    draw.text(
        ((page[0] + page[2]) / 2, 766),
        "WORD",
        font=label_font,
        fill=(107, 114, 128, 255),
        anchor="mm",
    )
    return canvas


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = create_icon()
    png = icon.resize((512, 512), Image.Resampling.LANCZOS)
    png.save(ASSETS / "icon.png", format="PNG")

    ico_sizes = [
        (16, 16),
        (24, 24),
        (32, 32),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256),
    ]
    icon.resize((256, 256), Image.Resampling.LANCZOS).save(
        ASSETS / "icon.ico",
        format="ICO",
        sizes=ico_sizes,
    )
    print(f"Created {ASSETS / 'icon.ico'}")
    print(f"Created {ASSETS / 'icon.png'}")


if __name__ == "__main__":
    main()
